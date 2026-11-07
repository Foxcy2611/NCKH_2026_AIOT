#include "Audio_IO/I2S_Mic.h"
#include "DSP_Preprocessing/DSP_Filter.h"
#include "DSP_Preprocessing/Mel_Scale.h"
#include "Model_AI/Inference_Asthma.h"

#include <esp_heap_caps.h>
#include <driver/gpio.h>
#include "Core_Logic/State_Machine.h"

/*
 * Luồng sử dụng thư viện I2S_Mic
 * --------------------------------
 * 1. I2S_Mic_Init(): cấp phát các buffer trong PSRAM, khởi tạo I2S RX,
 *    bỏ một số chunk đầu để DMA/INMP441 ổn định và kiểm tra nhanh micro.
 *    Node chỉ được thu âm khi bước này trả về true và mic_ready được chốt.
 *
 * 2. Manual Check:
 *    I2S_RecordSamples() thu liên tục đúng 80000 mẫu (5 giây ở 16 kHz),
 *    không dùng warm-up Monitor, ring buffer hoặc VAD.
 *
 * 3. Auto Monitor:
 *    - I2S_MonitorReset() bắt đầu phiên mới và yêu cầu warm-up 100 chunk.
 *    - I2S_MonitorListenStep() bỏ warm-up, sau đó liên tục ghi lịch sử vào
 *      ring buffer 1 giây. Chỉ khi ring đã đầy thì VAD mới được phép kích hoạt.
 *    - VAD xác nhận sau 4 chunk active liên tiếp. Chunk active đầu tiên được
 *      xem là onset; các mẫu từ onset đã nằm trong ring được chép sang đầu
 *      audio_buffer để không mất phần âm thanh dùng cho quyết định VAD.
 *    - I2S_MonitorCaptureStep() thu tiếp ngay sau onset cho đến khi
 *      audio_buffer đủ đúng 80000 mẫu, tức cửa sổ suy luận dài đúng 5 giây
 *      tính từ onset; không phải ghép cứng 1 giây lịch sử với 4 giây mới.
 *    - I2S_MonitorPrepareNextCapture() xóa trạng thái lần thu trước, tạo lại
 *      ring 1 giây nhưng không warm-up micro lần nữa trong cùng phiên Monitor.
 *
 * 4. Process_Record_Audio(): chỉ chạy sau khi buffer 5 giây đã hoàn chỉnh;
 *    hàm chuyển PCM16 sang float, chạy DSP, tạo Mel và gọi model TinyML.
 */
namespace {
    // Kích thước cửa sổ đầu vào: 5 giây x 16000 Hz = 80000 mẫu PCM16.
    constexpr uint32_t kTotalSamples = 80000;

    // Sức chứa ring buffer trước kích hoạt: 1 giây x 16000 Hz.
    constexpr uint32_t kPreRollSamples = 16000;

    // Ngưỡng VAD áp dụng trên trung bình trị tuyệt đối của từng chunk PCM16.
    constexpr uint32_t kVadThreshold = 75; // VAD_Trigger_Selection.ipynb

    // Số chunk active liên tiếp để xác nhận onset; 4 x 256/16000 ≈ 64 ms.
    constexpr uint8_t kVadConsecutiveRequired = 4;

    // Số chunk bị bỏ khi bắt đầu Monitor; 100 x 16 ms ≈ 1,6 giây warm-up.
    constexpr uint8_t kWarmupChunks = 100;

    // Số chunk bỏ riêng trước phép kiểm tra sức khỏe micro lúc khởi động.
    constexpr uint8_t kMicHealthWarmupChunks = 8;

    // Số chunk dùng để đo peak/non-zero/transition/clipping của micro.
    constexpr uint8_t kMicHealthMeasureChunks = 32;

    // Tỷ lệ mẫu khác 0 tối thiểu để loại trường hợp SD bị kéo thấp hoặc mất mic.
    constexpr float kMicHealthMinNonZeroRatio = 0.01f;

    // Tỷ lệ chuyển mức tối thiểu để loại luồng mẫu bị đứng tại một giá trị.
    constexpr float kMicHealthMinTransitionRatio = 0.01f;

    // Tỷ lệ clipping tối đa trong vùng health-check để loại tín hiệu rác bão hòa.
    constexpr float kMicHealthMaxClippedRatio = 0.25f;

    // Thời gian chờ tối đa cho một lần đọc DMA; hết hạn được xem là lỗi I2S.
    constexpr TickType_t kI2SReadTimeout = pdMS_TO_TICKS(100);

    // Buffer PCM16 5 giây dùng chung cho Manual Check và mỗi lần Monitor capture.
    int16_t* audio_buffer = nullptr;

    // Buffer float 5 giây nhận dữ liệu đã normalize trước chuỗi DSP/Mel.
    float* audio_float_buffer = nullptr;

    // Ring buffer PCM16 một giây, liên tục ghi đè khi Monitor đang LISTENING.
    int16_t* pre_roll_buffer = nullptr;

    // Số mẫu hợp lệ hiện đã có trong audio_buffer của lần capture đang chạy.
    uint32_t sample_count = 0;

    // Bộ đếm chunk warm-up còn phải bỏ trước khi bắt đầu tạo ring pre-trigger.
    uint8_t warmup_chunks_remaining = kWarmupChunks;

    // Số chunk vượt ngưỡng VAD liên tiếp trong candidate hiện tại.
    uint8_t vad_consecutive_chunks = 0;

    // Vị trí sẽ ghi mẫu kế tiếp trong ring; tự quay vòng tại kPreRollSamples.
    uint32_t pre_roll_write_index = 0;

    // Số mẫu lịch sử hợp lệ trong ring, tăng tới tối đa kPreRollSamples.
    uint32_t pre_roll_valid_samples = 0;

    // Chỉ số trong ring của mẫu đầu tiên thuộc chunk active candidate.
    uint32_t vad_candidate_start_index = 0;

    // Tổng số mẫu active đã tích lũy từ candidate onset đến lúc VAD xác nhận.
    uint32_t vad_candidate_sample_count = 0;

    // Cờ chốt sau khi I2S init và Validate_MicSignal() đều thành công.
    bool mic_ready = false;

    // Driver I2S đã được start và có thể đọc DMA. Light Sleep chỉ đổi cờ này,
    // không giải phóng các buffer PSRAM hay cài lại driver.
    bool i2s_running = false;

    // Ma trận Mel tĩnh làm đầu vào trực tiếp cho Run_Asthma_Inference().
    float mel_spectrogram_buffer[N_MELS][MAX_FRAMES];

    void Reset_MonitorCaptureState(){
        sample_count = 0;
        pre_roll_write_index = 0;
        pre_roll_valid_samples = 0;
        vad_consecutive_chunks = 0;
        vad_candidate_start_index = 0;
        vad_candidate_sample_count = 0;
    }

    int Read_I2SChunk(int16_t* chunk, int capacity){
        if(chunk == nullptr || capacity <= 0 || !i2s_running) return -1;

        int32_t raw_samples[Buffer_Samples];
        size_t bytes_read = 0;
        const esp_err_t read_status = i2s_read(
            I2S_Port,
            raw_samples,
            sizeof(raw_samples),
            &bytes_read,
            kI2SReadTimeout
        );
        if(read_status != ESP_OK){
            Serial.printf(
                "[I2S ERROR] Monitor không đọc được audio chunk | Mã lỗi=%d\n",
                static_cast<int>(read_status)
            );
            return -1;
        }

        int samples_read = static_cast<int>(bytes_read / sizeof(int32_t));
        if(samples_read > capacity) samples_read = capacity;

        for(int i = 0; i < samples_read; ++i){
            int32_t sample = (raw_samples[i] >> 16) * Amplify_Factor;
            if(sample > 32767) sample = 32767;
            if(sample < -32768) sample = -32768;
            chunk[i] = static_cast<int16_t>(sample);
        }

        return samples_read;
    }

    bool Validate_MicSignal(){
        int16_t chunk[Buffer_Samples];

        // Bo qua mot vung ngan de DMA va microphone on dinh sau khi bat clock I2S.
        for(uint8_t index = 0; index < kMicHealthWarmupChunks; ++index){
            if(Read_I2SChunk(chunk, Buffer_Samples) <= 0){
                Serial.println("[MIC CHECK] Khong nhan duoc mau trong giai do warmup.");
                return false;
            }
        }

        uint32_t total_samples = 0;
        uint32_t non_zero_samples = 0;
        uint32_t transition_samples = 0;
        uint32_t clipped_samples = 0;
        int32_t peak = 0;
        int16_t previous_sample = 0;
        bool has_previous_sample = false;

        for(uint8_t index = 0; index < kMicHealthMeasureChunks; ++index){
            const int samples_read = Read_I2SChunk(chunk, Buffer_Samples);
            if(samples_read <= 0){
                Serial.println("[MIC CHECK] I2S timeout/khong co du lieu trong vung kiem tra.");
                return false;
            }

            for(int sample_index = 0; sample_index < samples_read; ++sample_index){
                const int16_t sample = chunk[sample_index];
                const int32_t absolute_sample = sample < 0
                    ? -static_cast<int32_t>(sample)
                    : static_cast<int32_t>(sample);

                ++total_samples;
                if(sample != 0) ++non_zero_samples;
                if(has_previous_sample && sample != previous_sample) ++transition_samples;
                if(absolute_sample >= 32000) ++clipped_samples;
                if(absolute_sample > peak) peak = absolute_sample;

                previous_sample = sample;
                has_previous_sample = true;
            }
        }

        if(total_samples == 0U) return false;

        const float non_zero_ratio =
            static_cast<float>(non_zero_samples) / total_samples;
        const float transition_ratio =
            static_cast<float>(transition_samples) / total_samples;
        const float clipped_ratio =
            static_cast<float>(clipped_samples) / total_samples;

        const bool signal_valid =
            peak > 0
            && non_zero_ratio >= kMicHealthMinNonZeroRatio
            && transition_ratio >= kMicHealthMinTransitionRatio
            && clipped_ratio <= kMicHealthMaxClippedRatio;

        Serial.printf(
            "[MIC CHECK] samples=%lu | peak=%ld | nonzero=%.2f%% | transition=%.2f%% | clipped=%.2f%% | %s\n",
            static_cast<unsigned long>(total_samples),
            static_cast<long>(peak),
            non_zero_ratio * 100.0f,
            transition_ratio * 100.0f,
            clipped_ratio * 100.0f,
            signal_valid ? "READY" : "INVALID"
        );

        return signal_valid;
    }
}

bool I2S_Mic_Init(int SCK_Pin, int WS_Pin, int SD_Pin){
    mic_ready = false;
    i2s_running = false;
    audio_buffer = static_cast<int16_t*>(heap_caps_malloc(
        kTotalSamples * sizeof(int16_t),
        MALLOC_CAP_SPIRAM
    ));
    audio_float_buffer = static_cast<float*>(heap_caps_malloc(
        kTotalSamples * sizeof(float),
        MALLOC_CAP_SPIRAM
    ));
    pre_roll_buffer = static_cast<int16_t*>(heap_caps_malloc(
        kPreRollSamples * sizeof(int16_t),
        MALLOC_CAP_SPIRAM
    ));

    if(audio_buffer == nullptr
        || audio_float_buffer == nullptr
        || pre_roll_buffer == nullptr){
        Serial.println("[ERROR] Không đủ PSRAM cho audio buffer.");
        return false;
    }

    const i2s_config_t i2s_config = {
        .mode = i2s_mode_t(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = Sample_Rate,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_RIGHT,
        .communication_format = i2s_comm_format_t(I2S_COMM_FORMAT_STAND_I2S),
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,
        .dma_buf_len = Buffer_Samples,
        .use_apll = false,
        .tx_desc_auto_clear = false,
        .fixed_mclk = 0,
    };

    const i2s_pin_config_t pin_config = {
        .bck_io_num = SCK_Pin,
        .ws_io_num = WS_Pin,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num = SD_Pin,
    };

    if(i2s_driver_install(I2S_Port, &i2s_config, 0, nullptr) != ESP_OK
        || i2s_set_pin(I2S_Port, &pin_config) != ESP_OK){
        Serial.println("[ERROR] Không khởi tạo được I2S.");
        return false;
    }
    i2s_running = true;

    // Giu chan SD o muc xac dinh neu micro bi thao. INMP441 van co the
    // drive duong data binh thuong khi dang ket noi.
    if(gpio_pulldown_en(static_cast<gpio_num_t>(SD_Pin)) != ESP_OK){
        Serial.println("[MIC CHECK] Khong bat duoc pull-down cho chan SD.");
        return false;
    }

    if(!Validate_MicSignal()){
        Serial.println("[MIC CHECK] Khong xac nhan duoc INMP441. Kiem tra day va khoi dong lai Node.");
        return false;
    }

    mic_ready = true;
    I2S_MonitorReset();
    return true;
}

bool I2S_Mic_IsReady(void){
    return mic_ready;
}

bool I2S_Mic_Suspend(void){
    if(!mic_ready) return false;
    if(!i2s_running) return true;

    if(i2s_stop(I2S_Port) != ESP_OK){
        Serial.println("[POWER] Không dừng được I2S trước Light Sleep.");
        return false;
    }

    i2s_running = false;
    Reset_MonitorCaptureState();
    return true;
}

bool I2S_Mic_Resume(void){
    if(!mic_ready) return false;
    if(i2s_running) return true;

    if(i2s_start(I2S_Port) != ESP_OK){
        Serial.println("[POWER] Không khởi động lại được I2S sau Light Sleep.");
        return false;
    }
    i2s_running = true;

    // Bỏ 8 chunk (khoảng 128 ms) để tránh dùng mẫu chuyển tiếp ngay sau khi
    // clock/DMA vừa hoạt động trở lại. Monitor vẫn có warm-up 1,6 giây riêng.
    int16_t chunk[Buffer_Samples];
    for(uint8_t index = 0; index < kMicHealthWarmupChunks; ++index){
        if(Read_I2SChunk(chunk, Buffer_Samples) <= 0){
            Serial.println("[POWER] I2S không có mẫu hợp lệ sau khi đánh thức.");
            i2s_running = false;
            i2s_stop(I2S_Port);
            return false;
        }
    }

    I2S_MonitorReset();
    return true;
}

bool Process_Record_Audio(
    Inference_TinyML_t* out_classification,
    float* out_score
){
    if(out_classification == nullptr
        || out_score == nullptr
        || audio_buffer == nullptr
        || audio_float_buffer == nullptr){
        Serial.println("[AI] Buffer hoặc con trỏ đầu ra không hợp lệ.");
        return false;
    }

    Serial.println("[AI] Tiến hành tiền xử lý Audio ...");

    Normalize_To_Float(audio_buffer, audio_float_buffer, kTotalSamples);
    Butterworth_Reset();
    Butterworth_Process_Buffer(audio_float_buffer, kTotalSamples);
    // C4 dùng pre_emphasis=0.0, không tiền nhấn tín hiệu.

    const int frame_count = Compute_Mel_Power_Spectrogram(
        audio_float_buffer,
        kTotalSamples,
        mel_spectrogram_buffer,
        MAX_FRAMES
    );
    if(frame_count != MAX_FRAMES){
        Serial.printf("[ERROR] Số Mel frame=%d, yêu cầu=%d.\n", frame_count, MAX_FRAMES);
        return false;
    }

    Power_To_dB_RefMax(mel_spectrogram_buffer, mel_spectrogram_buffer, frame_count);

    const Asthma_Result result = Run_Asthma_Inference(mel_spectrogram_buffer);

    const Inference_TinyML_t manual_classification =
        (result.Predicted_Class == 0) ? INFERENCE_ASTHMA_LIKE :
        (result.Predicted_Class == 1) ? INFERENCE_NON_ASTHMA : INFERENCE_UNSURE;

    const float manual_score =
        (manual_classification == INFERENCE_ASTHMA_LIKE) ? result.Asthma_Prob :
        (manual_classification == INFERENCE_NON_ASTHMA) ? result.Non_Asthma_Prob : result.Unsure_Prob;
    
    *out_classification = manual_classification;
    *out_score = manual_score / 100.0f; // Chuẩn hóa xác suất từ 0-100 về 0-1.
    
    return true;
}

bool I2S_RecordSamples(void){
    if(!mic_ready || audio_buffer == nullptr){
        Serial.println("[I2S ERROR] AUDIO_BUFFER_NOT_READY: cần gọi I2S_Mic_Init trước.");
        return false;
    }
 
    int32_t raw_samples[Buffer_Samples];
    uint32_t recorded = 0;
 
    Serial.println("[MIC] Manual Check: bắt đầu ghi 80000 samples...");
 
    while(recorded < kTotalSamples){
        // Kiểm tra SLEEP-abort mỗi vòng đọc chunk — không để hàm này
        // block hết 5s mới nhường quyền kiểm tra abort cho state machine.
        if(StateMachine_IsAbortRequested()){
            Serial.println("[MIC] Manual Check bị hủy giữa chừng bởi nút SLEEP.");
            return false;
        }
 
        size_t bytes_read = 0;
        const esp_err_t read_status = i2s_read(
            I2S_Port,
            raw_samples,
            sizeof(raw_samples),
            &bytes_read,
            kI2SReadTimeout
        );

        if(read_status != ESP_OK){
            Serial.printf(
                "[I2S ERROR] Manual Check không đọc được audio | Mã lỗi=%d | Đã thu=%lu/%lu samples\n",
                static_cast<int>(read_status),
                static_cast<unsigned long>(recorded),
                static_cast<unsigned long>(kTotalSamples)
            );
            return false;
        }
 
        const int samples_read = bytes_read / sizeof(int32_t);
        if(samples_read <= 0){
            Serial.println("[I2S ERROR] Manual Check timeout: khong co mau moi.");
            return false;
        }
 
        for(int i = 0 ; i < samples_read && recorded < kTotalSamples ; i++){
            int32_t sample = (raw_samples[i] >> 16) * Amplify_Factor;
            if(sample > 32767) sample = 32767;
            if(sample < -32768) sample = -32768;
            audio_buffer[recorded++] = static_cast<int16_t>(sample);
        }
    }
 
    Serial.printf(
        "[MIC] Manual Check: đã ghi đủ %lu samples.\n",
        static_cast<unsigned long>(recorded)
    );
    return true;
}



const int16_t* I2S_GetRecordedBuffer(void){
    return audio_buffer;
}

// Số sample cố định 1 lần Manual Check (80000)
uint32_t I2S_GetRecordedSampleCount(void){
    return kTotalSamples;
}

// Buffer trung gian dùng chung cho pipeline DSP 
// (Manual Check lẫn Auto Monitor sau này) 
// Chỉ hợp lệ sau khi I2S_Mic_Init() đã chạy.
float* I2S_GetFloatBuffer(void){
    return audio_float_buffer;
}
 
float (*I2S_GetMelBuffer(void))[MAX_FRAMES] {
    return mel_spectrogram_buffer;
}

void I2S_MonitorReset(void){
    Reset_MonitorCaptureState();
    warmup_chunks_remaining = kWarmupChunks;
}

void I2S_MonitorPrepareNextCapture(void){
    Reset_MonitorCaptureState();
    warmup_chunks_remaining = 0;
    Serial.println("[VAD] Đang tạo lại bộ đệm trước kích hoạt 1 giây...");
}

bool I2S_MonitorListenStep(void) {
    if(!mic_ready || audio_buffer == nullptr || pre_roll_buffer == nullptr) return false;

    int16_t chunk[Buffer_Samples];
    const int samples_read = Read_I2SChunk(chunk, Buffer_Samples);
    if(samples_read <= 0) return false;

    if(warmup_chunks_remaining > 0){
        --warmup_chunks_remaining;
        if(warmup_chunks_remaining == 0){
            Serial.println("[VAD] Micro ổn định, đang tạo bộ đệm 1 giây...");
        }
        return false;
    }

    const bool pre_roll_was_full = pre_roll_valid_samples >= kPreRollSamples;
    for(int i = 0; i < samples_read; ++i){
        pre_roll_buffer[pre_roll_write_index] = chunk[i];
        pre_roll_write_index = (pre_roll_write_index + 1U) % kPreRollSamples;
        if(pre_roll_valid_samples < kPreRollSamples) ++pre_roll_valid_samples;
    }

    if(pre_roll_valid_samples < kPreRollSamples) return false;
    if(!pre_roll_was_full){
        Serial.println("[VAD] Bộ đệm đã đủ 1 giây, bắt đầu lắng nghe.");
    }

    uint32_t energy_sum = 0;
    for(int i = 0; i < samples_read; ++i){
        const int32_t value = chunk[i];
        energy_sum += value < 0
            ? static_cast<uint32_t>(-value)
            : static_cast<uint32_t>(value);
    }
    const uint32_t average_energy = energy_sum
        / static_cast<uint32_t>(samples_read);

    if(average_energy > kVadThreshold){
        // Chunk active dau tien la candidate onset. Chunk nay da nam trong
        // ring, nen vi tri bat dau cach write index samples_read mau.
        if(vad_consecutive_chunks == 0){
            vad_candidate_start_index =
                (pre_roll_write_index + kPreRollSamples
                 - static_cast<uint32_t>(samples_read))
                % kPreRollSamples;
            vad_candidate_sample_count = 0;
        }

        if(vad_consecutive_chunks < kVadConsecutiveRequired){
            ++vad_consecutive_chunks;
            vad_candidate_sample_count += static_cast<uint32_t>(samples_read);
        }
    } else {
        vad_consecutive_chunks = 0;
        vad_candidate_sample_count = 0;
    }

    if (vad_consecutive_chunks >= kVadConsecutiveRequired) {
        uint32_t onset_samples = vad_candidate_sample_count;
        if(onset_samples > pre_roll_valid_samples){
            onset_samples = pre_roll_valid_samples;
        }
        if(onset_samples > kTotalSamples){
            onset_samples = kTotalSamples;
        }

        for(uint32_t i = 0; i < onset_samples; ++i){
            const uint32_t source_index =
                (vad_candidate_start_index + i) % kPreRollSamples;
            audio_buffer[i] = pre_roll_buffer[source_index];
        }

        sample_count = onset_samples;
        vad_consecutive_chunks = 0;
        vad_candidate_sample_count = 0;
        Serial.printf(
            "[VAD] Xác nhận ở mức %lu | onset=%lu mẫu (%.1f ms) | "
            "thu tiếp đến đủ 5 giây.\n",
            static_cast<unsigned long>(average_energy),
            static_cast<unsigned long>(onset_samples),
            onset_samples * 1000.0f / Sample_Rate
        );
        return true;
    }

    return false;
}

bool I2S_MonitorIsBufferReady(void) {
    return mic_ready
        && warmup_chunks_remaining == 0
        && pre_roll_valid_samples >= kPreRollSamples;
}

bool I2S_MonitorCaptureStep(void) {
    if(!mic_ready || audio_buffer == nullptr || sample_count == 0) return false;

    int16_t chunk[Buffer_Samples];
    const int samples_read = Read_I2SChunk(chunk, Buffer_Samples);
    if(samples_read <= 0) return false;

    for (int i = 0; i < samples_read && sample_count < kTotalSamples;
         ++i) {
        audio_buffer[sample_count++] = chunk[i];
    }

    if(sample_count < kTotalSamples) return false;

    Serial.println("[MIC] Monitor đã thu đủ 5 giây.");
    return true;
}
