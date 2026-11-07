#include "Audio_IO/I2S_Mic.h"
/**/ // THAY ĐỔI P5: Sắp xếp số đo để lấy các mốc p10, p25, p95 và p99.
#include <algorithm>
#include <math.h>
#include <string.h>
#include "esp_heap_caps.h"

#if RUN_RAW_PCM16_TEST
#include "Raw_PCM16_Test/Raw_PCM16_Test_Samples.h"
#endif


#define Total_Samples 80000 // 5s cho 16 kHz
/**/ // THAY ĐỔI P5: Giữ 1 giây âm thanh trước khi VAD xác nhận.
#define Pre_Roll_Samples 16000
/**/ // THAY ĐỔI P5: Hai log VAD cho khoảng thử 60-75; ưu tiên thử mức 75.
#define Val_Threshold 75
/**/ // THAY ĐỔI P5: Phải có 4 khối 16 ms liên tiếp, tránh xung nhiễu đơn lẻ.
#define VAD_Consecutive_Required 4

#if RUN_RAW_PCM16_TEST
static_assert(kRawPcmSampleRate == Sample_Rate, "RAW sample rate phai la 16 kHz");
static_assert(kRawPcmSamplesPerTest == Total_Samples, "Moi RAW phai du 5 giay");
#endif

#define Vote_Round 3 // Đo 3 lần ms ra quyết định
static uint8_t vote_asthma_count = 0;
static uint8_t vote_non_asthma_count = 0;
static uint8_t vote_unsure_count = 0;
static uint8_t current_vote_round = 0;

// ==== THỐNG KÊ TỔNG (không reset theo vòng đo, chạy suốt phiên hoạt động) ====
static uint32_t total_tests = 0;
static uint32_t total_asthma_alerts = 0;

#if RUN_RAW_PCM16_TEST
System_State curr_state = STATE_RECORDING;
#else
System_State curr_state = STATE_LISTENING;
#endif

int16_t* audio_buffer = nullptr;
float* audio_float_buff = nullptr;
/**/ // THAY ĐỔI P5: Bộ đệm vòng 1 giây được cấp phát trong PSRAM.
int16_t* pre_roll_buffer = nullptr;
int sample_cnt = 0;

/**/ // THAY ĐỔI P5: Bỏ 100 khối đầu (~1,6 giây) sau reset để I2S ổn định.
static uint8_t warmup_chunk = 100;
/**/ // THAY ĐỔI P5: Đếm số khối liên tiếp vượt ngưỡng VAD.
static uint8_t vad_consecutive_chunks = 0;
/**/ // THAY ĐỔI P5: Vị trí ghi và số mẫu hợp lệ trong bộ đệm vòng.
static uint32_t pre_roll_write_index = 0;
static uint32_t pre_roll_valid_samples = 0;

// Dùng chung một ma trận: ban đầu chứa năng lượng Mel, sau đó được ghi đè
// tại chỗ thành Mel-Spectrogram dB. Không cần giữ đồng thời hai bản.
static float mel_spectrogram_buff[N_MELS][MAX_FRAMES];

#if RUN_RAW_PCM16_TEST
static size_t raw_test_index = 0;
static int raw_correct_label_count = 0;
static int raw_same_python_prediction_count = 0;
static int raw_exact_python_output_count = 0;
static int raw_max_python_output_difference = 0;
static float raw_max_python_probability_difference = 0.0f;
#endif

void Process_Audio_Stream(void){
#if RUN_RAW_PCM16_TEST
    if(curr_state == STATE_DONE){
        delay(1000);
        return;
    }
#endif
    int samples_read = Buffer_Samples;
    int16_t chunk[Buffer_Samples] = {0};

#if !RUN_RAW_PCM16_TEST
    // 1. Đọc 256 mẫu thô từ DMA
    int32_t raw_samples[Buffer_Samples];
    size_t bytes_read = 0;

    i2s_read(I2S_Port, raw_samples, sizeof(int32_t) * Buffer_Samples, &bytes_read, portMAX_DELAY);
    samples_read = bytes_read / sizeof(int32_t);

    if (samples_read == 0) return; 

    // 2. Chuyển đổi về PCM 16-bit chuẩn
    for (int i = 0; i < samples_read; i++) {
        int32_t amplified = (raw_samples[i] >> 16) * Amplify_Factor;
        
        if(amplified > 32767) amplified = 32767;
        if(amplified < -32768) amplified = -32768;

        chunk[i] = (int16_t)amplified;
    }
#endif

    // 3. Chuyển đổi trạng thái
    if(curr_state == STATE_LISTENING){
        /**/ // THAY ĐỔI P5: Không xét VAD trong 100 khối đầu sau reset.
        if(warmup_chunk > 0){
            warmup_chunk--;
            vad_consecutive_chunks = 0;
            if(warmup_chunk == 0){
                Serial.println(
                    /**/ // THAY ĐỔI P5: Sau warm-up phải tích lũy đủ bộ đệm 1 giây.
                    "[VAD] Đã bỏ 100 khối khởi động. Bắt đầu tạo bộ đệm 1 giây."
                );
            }
            return;
        }

        /**/ // THAY ĐỔI P5: Luôn lưu 1 giây gần nhất trước khi xét kích hoạt.
        const bool pre_roll_was_full =
            pre_roll_valid_samples >= Pre_Roll_Samples;
        for(int i = 0; i < samples_read; i++){
            pre_roll_buffer[pre_roll_write_index] = chunk[i];
            pre_roll_write_index++;
            if(pre_roll_write_index >= Pre_Roll_Samples){
                pre_roll_write_index = 0;
            }
            if(pre_roll_valid_samples < Pre_Roll_Samples){
                pre_roll_valid_samples++;
            }
        }

        /**/ // THAY ĐỔI P5: Chưa đủ 1 giây lịch sử thì chưa cho VAD kích hoạt.
        if(pre_roll_valid_samples < Pre_Roll_Samples){
            vad_consecutive_chunks = 0;
            return;
        }
        if(!pre_roll_was_full){
            Serial.println(
                "[VAD] Bộ đệm trước kích hoạt đã đủ 1 giây. Sẵn sàng lắng nghe."
            );
        }

        // Tính năng lượng WAV của 256 mẫu hiện tại
        uint32_t sum_energy = 0;
        for(int i = 0 ; i < samples_read ; i++){
            sum_energy += abs(chunk[i]);
        } 
        uint32_t avg_enegry = sum_energy / samples_read;

        /**/ // THAY ĐỔI P5: Một khối vượt ngưỡng chưa đủ để bắt đầu ghi.
        if(avg_enegry > Val_Threshold){
            if(vad_consecutive_chunks < VAD_Consecutive_Required){
                vad_consecutive_chunks++;
            }
        }else{
            vad_consecutive_chunks = 0;
        }

        /**/ // THAY ĐỔI P5: Chỉ kích hoạt sau 4 khối liên tiếp (~64 ms).
        if(vad_consecutive_chunks >= VAD_Consecutive_Required){
            Serial.printf(
                "[VAD] Phát hiện tiếng động! Năng lượng=%lu, liên tiếp=%u/%u\n",
                (unsigned long)avg_enegry,
                (unsigned int)vad_consecutive_chunks,
                (unsigned int)VAD_Consecutive_Required
            );
            Serial.println("Bắt đầu ghi !!");
            curr_state = STATE_RECORDING;
            vad_consecutive_chunks = 0;

            /**/ // THAY ĐỔI P5: Chép 1 giây lịch sử theo đúng thứ tự thời gian.
            for(int i = 0; i < Pre_Roll_Samples; i++){
                uint32_t source_index = pre_roll_write_index + i;
                if(source_index >= Pre_Roll_Samples){
                    source_index -= Pre_Roll_Samples;
                }
                audio_buffer[i] = pre_roll_buffer[source_index];
            }
            /**/ // THAY ĐỔI P5: Đã có 1 giây, trạng thái ghi chỉ thu thêm 4 giây.
            sample_cnt = Pre_Roll_Samples;
            Serial.printf(
                "[VAD] Đã lấy lại %d mẫu trước kích hoạt, thu tiếp %d mẫu.\n",
                Pre_Roll_Samples,
                Total_Samples - Pre_Roll_Samples
            );
        } 

    } else if(curr_state == STATE_RECORDING){
#if RUN_RAW_PCM16_TEST
        const RawPcm16TestSample& sample = kRawPcm16Tests[raw_test_index];
        Serial.printf(
            "\n[RAW_PCM16] Mẫu %u/%u: %s | true=%u | model=%s\n",
            static_cast<unsigned int>(raw_test_index + 1),
            static_cast<unsigned int>(kRawPcmTestCount),
            sample.source_name,
            static_cast<unsigned int>(sample.expected_label),
            Get_Asthma_Model_Name()
        );
        memcpy(audio_buffer, sample.pcm16, Total_Samples * sizeof(int16_t));
        sample_cnt = Total_Samples;
        curr_state = STATE_PROCESSING;
#else
        for(int i = 0 ; i < samples_read ; i++){
            if(sample_cnt < Total_Samples){
                audio_buffer[sample_cnt] = chunk[i];
                sample_cnt++;
            }
        }

        if (sample_cnt >= Total_Samples) {
            Serial.println("[MIC] Đã thu đủ 5 giây âm thanh! Chuyển sang AI ...");
            curr_state = STATE_PROCESSING;
        }
#endif

    } else if(curr_state == STATE_PROCESSING){
        Serial.println("\n--- BẮT ĐẦU TIỀN XỬ LÝ ---\n");

        // 1. Chuẩn hóa về [-1, 1] TRƯỚC (int16 -> float)
        Normalize_To_Float(audio_buffer, audio_float_buff, Total_Samples);
        Serial.println("1. Hoàn thành chuẩn hóa về Float [-1.0, 1.0]");

        // 2. Reset + Lọc Butterworth TRÊN FLOAT
        Butterworth_Reset();
        Butterworth_Process_Buffer(audio_float_buff, Total_Samples);   
        Serial.println("2. Hoàn thành bộ lọc Butterworth.");

        // C4 dùng pre_emphasis=0.0: giữ nguyên tín hiệu sau Butterworth.
        Serial.println("3. Bỏ qua Pre-Emphasis theo cấu hình C4.");

        // 4. Chạy STFT và năng lượng Mel
        int num_frames = Compute_Mel_Power_Spectrogram(
            audio_float_buff, Total_Samples, 
            mel_spectrogram_buff, MAX_FRAMES
        );
        Serial.println("4. Hoàn thành trích xuất năng lượng Mel.");

        // 5. Chuyển đổi sang đơn vị dB
        Power_To_dB_RefMax(
            mel_spectrogram_buff,
            mel_spectrogram_buff,
            num_frames
        );
        Serial.println("5. Hoàn thành ma trận Mel-Spectrogram dB!");
        Serial.println("------------------------------");

        //
        Serial.println("[DEBUG] mel_db_buff frame 0, 10 gia tri mel dau:");
        for (int m = 0; m < 10; m++) {
            Serial.printf("%.4f ", mel_spectrogram_buff[m][0]);
        }
        Serial.println();
        
        Serial.println("[DEBUG] mel_db_buff FRAME 64, 10 gia tri mel dau:");
        for (int m = 0; m < 10; m++){
            Serial.printf("%.4f ", mel_spectrogram_buff[m][64]);
        }
        Serial.println();

        curr_state = STATE_INFERENCE;

    } else if(curr_state == STATE_INFERENCE){
        Asthma_Result result = Run_Asthma_Inference(mel_spectrogram_buff);

#if RUN_RAW_PCM16_TEST
        const RawPcm16TestSample& sample = kRawPcm16Tests[raw_test_index];
        const float esp_probability = result.Non_Asthma_Prob / 100.0f;
        const bool correct_label = result.Predicted_Class == sample.expected_label;
        if (correct_label) raw_correct_label_count++;

        Serial.printf(
            "[RAW_RESULT] index=%u,file=%s,true=%u,esp_pred=%d,esp_raw=%d,esp_p_non=%.9f",
            static_cast<unsigned int>(raw_test_index),
            sample.source_name,
            static_cast<unsigned int>(sample.expected_label),
            result.Predicted_Class,
            static_cast<int>(result.Output_Raw_Int8),
            esp_probability
        );

        // Header RAW lưu oracle Python của đúng model/PCM16 đang nhúng.
        if (Asthma_Model_Has_Python_Reference()) {
            const int raw_difference = abs(
                static_cast<int>(result.Output_Raw_Int8) -
                static_cast<int>(sample.expected_output_int8)
            );
            const float probability_difference = fabsf(
                esp_probability - sample.expected_probability_non_asthma
            );
            const bool same_prediction =
                result.Predicted_Class == sample.expected_prediction;
            if (same_prediction) raw_same_python_prediction_count++;
            if (raw_difference == 0) raw_exact_python_output_count++;
            if (raw_difference > raw_max_python_output_difference) {
                raw_max_python_output_difference = raw_difference;
            }
            if (probability_difference > raw_max_python_probability_difference) {
                raw_max_python_probability_difference = probability_difference;
            }
            Serial.printf(
                ",py_pred=%u,py_raw=%d,py_p_non=%.9f,raw_diff=%d,prob_diff=%.9f\n",
                static_cast<unsigned int>(sample.expected_prediction),
                static_cast<int>(sample.expected_output_int8),
                sample.expected_probability_non_asthma,
                raw_difference,
                probability_difference
            );
        } else {
            Serial.println(",python_reference=N/A");
        }

        raw_test_index++;
        sample_cnt = 0;
        if (raw_test_index < kRawPcmTestCount) {
            curr_state = STATE_RECORDING;
        } else {
            Serial.println("\n========== TỔNG KẾT RAW PCM16 -> C++ -> MODEL ==========");
            Serial.printf("Model: %s\n", Get_Asthma_Model_Name());
            Serial.printf(
                "Đúng nhãn thật: %d/%u\n",
                raw_correct_label_count,
                static_cast<unsigned int>(kRawPcmTestCount)
            );
            if (Asthma_Model_Has_Python_Reference()) {
                Serial.printf(
                    "Cùng dự đoán Python oracle: %d/%u\n",
                    raw_same_python_prediction_count,
                    static_cast<unsigned int>(kRawPcmTestCount)
                );
                Serial.printf(
                    "Output INT8 trùng tuyệt đối: %d/%u | max_raw_diff=%d | max_prob_diff=%.9f\n",
                    raw_exact_python_output_count,
                    static_cast<unsigned int>(kRawPcmTestCount),
                    raw_max_python_output_difference,
                    raw_max_python_probability_difference
                );
            }
            Serial.println("=========================================================");
            curr_state = STATE_DONE;
        }
#else
        // Đếm vote
        if (result.Predicted_Class == 0) vote_asthma_count++;
        else if (result.Predicted_Class == 1) vote_non_asthma_count++;
        else vote_unsure_count++;
        
        current_vote_round++;
        
        Serial.printf("[VOTE] Lan %d/%d - Asthma:%d Non-Asthma:%d Unsure:%d\n",
            current_vote_round, Vote_Round, vote_asthma_count, vote_non_asthma_count, vote_unsure_count);

        if (current_vote_round >= Vote_Round) {
            // Đủ 3 lần -> đưa ra kết luận cuối
            Serial.println("\n========== KẾT LUẬN SAU 3 LẦN ĐO ==========");
            if (vote_asthma_count > vote_non_asthma_count) {
                Serial.println(">>> KẾT LUẬN CUỐI: CẢNH BÁO HEN SUYỄN");
            } else if (vote_non_asthma_count > vote_asthma_count) {
                Serial.println(">>> KẾT LUẬN CUỐI: KHÔNG PHÁT HIỆN MẪU ASTHMA");
            } else {
                Serial.println(">>> KẾT LUẬN CUỐI: KHÔNG CHẮC CHẮN, ĐỀ NGHỊ ĐO LẠI");
            }
            Serial.println("=============================================\n");

            // Reset để bắt đầu vòng đo mới
            vote_asthma_count = 0;
            vote_non_asthma_count = 0;
            vote_unsure_count = 0;
            current_vote_round = 0;
        }

        // ==== THÊM: cộng dồn thống kê ====
        total_tests++;
        if (result.Predicted_Class == 0) total_asthma_alerts++;

        if (total_tests % 10 == 0) {   // cứ mỗi 10 lần đo thì in ra 1 lần
            Serial.printf("[THONG KE] Tong %lu lan do, %lu lan bao Asthma (%.1f%%)\n",
                total_tests, total_asthma_alerts,
                (float)total_asthma_alerts / total_tests * 100.0f);
        }

        curr_state = STATE_LISTENING;
        sample_cnt = 0;
        /**/ // THAY ĐỔI P5: Làm mới lịch sử để lượt sau không dùng âm thanh cũ.
        pre_roll_write_index = 0;
        pre_roll_valid_samples = 0;
        vad_consecutive_chunks = 0;
        Serial.println(
            "\n[CAI DAT] Dang tao lai bo dem 1 giay truoc khi lang nghe..."
        );
#endif

    }
}

void I2S_Mic_Init(int SCK_Pin, int WS_Pin, int SD_Pin){
    // Cấp phát bộ nhớ
    audio_buffer = (int16_t*)heap_caps_malloc(
        Total_Samples * sizeof(int16_t),
        MALLOC_CAP_SPIRAM
    );
    audio_float_buff = (float*)heap_caps_malloc(
        Total_Samples * sizeof(float),
        MALLOC_CAP_SPIRAM
    );
    /**/ // THAY ĐỔI P5: 16000 mẫu INT16 chiếm khoảng 32 KB PSRAM.
    pre_roll_buffer = (int16_t*)heap_caps_malloc(
        Pre_Roll_Samples * sizeof(int16_t),
        MALLOC_CAP_SPIRAM
    );

    /**/ // THAY ĐỔI P5: Kiểm tra cả bộ đệm trước kích hoạt.
    if (
        audio_buffer == nullptr
        || audio_float_buff == nullptr
        || pre_roll_buffer == nullptr
    ) {
        Serial.println("[LỖI CRITICAL] Không đủ PSRAM cho các bộ đệm âm thanh!");
        while(1); // Treo mạch ở đây luôn để dễ debug
    }

#if RUN_RAW_PCM16_TEST
    Serial.printf(
        "[RAW_PCM16] Đã cấp phát buffer; bỏ qua I2S hardware, sẽ chạy %u mẫu nhúng.\n",
        static_cast<unsigned int>(kRawPcmTestCount)
    );
    return;
#endif

    const i2s_config_t i2s_config = {
        .mode = i2s_mode_t(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = (uint32_t)Sample_Rate,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_RIGHT,
        .communication_format = i2s_comm_format_t(I2S_COMM_FORMAT_STAND_I2S),
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,
        .dma_buf_len = Buffer_Samples,
        .use_apll = false,
        .tx_desc_auto_clear = false,
        .fixed_mclk = 0 
    };

    const i2s_pin_config_t pin_config = {
        .bck_io_num = SCK_Pin,
        .ws_io_num = WS_Pin,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num = SD_Pin
    };

    i2s_driver_install(I2S_Port, &i2s_config, 0, NULL);
    i2s_set_pin(I2S_Port, &pin_config);
}

/**/ // THAY ĐỔI P5: Hàm mới đặt cuối file, đo đúng năng lượng mà VAD đang dùng.
#if RUN_VAD_CALIBRATION_TEST
void Run_VAD_Calibration(void){
    const uint16_t WARMUP_CHUNKS = 100;       // 1,6 giây
    const uint16_t QUIET_CHUNKS = 625;        // 10 giây
    const uint16_t PREPARE_CHUNKS = 188;      // khoảng 3 giây
    const uint16_t SIGNAL_CHUNKS = 938;       // khoảng 15 giây

    enum Calibration_Phase {
        CAL_WARMUP,
        CAL_QUIET,
        CAL_PREPARE,
        CAL_SIGNAL,
        CAL_DONE,
    };

    static Calibration_Phase phase = CAL_WARMUP;
    static uint16_t phase_chunk = 0;
    static uint32_t quiet_energy[QUIET_CHUNKS];
    static uint32_t signal_energy[SIGNAL_CHUNKS];

    if(phase == CAL_DONE){
        delay(1000);
        return;
    }

    int32_t raw_samples[Buffer_Samples];
    size_t bytes_read = 0;
    i2s_read(
        I2S_Port,
        raw_samples,
        sizeof(raw_samples),
        &bytes_read,
        portMAX_DELAY
    );

    const int samples_read = bytes_read / sizeof(int32_t);
    if(samples_read <= 0) return;

    uint32_t sum_energy = 0;
    for(int i = 0; i < samples_read; i++){
        int32_t sample = (raw_samples[i] >> 16) * Amplify_Factor;
        if(sample > 32767) sample = 32767;
        if(sample < -32768) sample = -32768;
        sum_energy += sample < 0 ? (uint32_t)(-sample) : (uint32_t)sample;
    }
    const uint32_t avg_energy = sum_energy / samples_read;

    if(phase == CAL_WARMUP){
        if(phase_chunk == 0){
            Serial.println("[VAD_CAL] Bước 1/4: bỏ 100 khối đầu để tránh nhiễu reset...");
        }
        phase_chunk++;
        if(phase_chunk >= WARMUP_CHUNKS){
            phase = CAL_QUIET;
            phase_chunk = 0;
            Serial.println("\n[VAD_CAL] Bước 2/4: GIỮ YÊN LẶNG trong 10 giây.");
        }
        return;
    }

    if(phase == CAL_QUIET){
        quiet_energy[phase_chunk++] = avg_energy;
        if(phase_chunk % 63 == 0){
            Serial.printf(
                "[VAD_CAL][YEN_LANG] %.0f/10 giây | energy hiện tại=%lu\n",
                phase_chunk * 256.0f / Sample_Rate,
                (unsigned long)avg_energy
            );
        }
        if(phase_chunk >= QUIET_CHUNKS){
            phase = CAL_PREPARE;
            phase_chunk = 0;
            Serial.println(
                "\n[VAD_CAL] Bước 3/4: chuẩn bị phát WAV liên tục. "
                "Bắt đầu sau khoảng 3 giây..."
            );
        }
        return;
    }

    if(phase == CAL_PREPARE){
        phase_chunk++;
        if(phase_chunk >= PREPARE_CHUNKS){
            phase = CAL_SIGNAL;
            phase_chunk = 0;
            Serial.println(
                "\n[VAD_CAL] Bước 4/4: PHÁT ÂM THANH LIÊN TỤC trong 15 giây!"
            );
        }
        return;
    }

    signal_energy[phase_chunk++] = avg_energy;
    if(phase_chunk % 63 == 0){
        Serial.printf(
            "[VAD_CAL][CO_AM_THANH] %.0f/15 giây | energy hiện tại=%lu\n",
            phase_chunk * 256.0f / Sample_Rate,
            (unsigned long)avg_energy
        );
    }

    if(phase_chunk < SIGNAL_CHUNKS) return;

    std::sort(quiet_energy, quiet_energy + QUIET_CHUNKS);
    std::sort(signal_energy, signal_energy + SIGNAL_CHUNKS);

    uint64_t quiet_sum = 0;
    uint64_t signal_sum = 0;
    for(uint16_t i = 0; i < QUIET_CHUNKS; i++) quiet_sum += quiet_energy[i];
    for(uint16_t i = 0; i < SIGNAL_CHUNKS; i++) signal_sum += signal_energy[i];

    const uint32_t quiet_mean = quiet_sum / QUIET_CHUNKS;
    const uint32_t signal_mean = signal_sum / SIGNAL_CHUNKS;
    const uint32_t quiet_p95 = quiet_energy[(QUIET_CHUNKS - 1) * 95 / 100];
    const uint32_t quiet_p99 = quiet_energy[(QUIET_CHUNKS - 1) * 99 / 100];
    const uint32_t signal_p10 = signal_energy[(SIGNAL_CHUNKS - 1) * 10 / 100];
    const uint32_t signal_p25 = signal_energy[(SIGNAL_CHUNKS - 1) * 25 / 100];
    const uint32_t signal_p50 = signal_energy[(SIGNAL_CHUNKS - 1) * 50 / 100];

    Serial.println("\n========== KẾT QUẢ ĐO NĂNG LƯỢNG VAD ==========");
    Serial.printf(
        "Yên lặng: min=%lu | mean=%lu | p95=%lu | p99=%lu | max=%lu\n",
        (unsigned long)quiet_energy[0],
        (unsigned long)quiet_mean,
        (unsigned long)quiet_p95,
        (unsigned long)quiet_p99,
        (unsigned long)quiet_energy[QUIET_CHUNKS - 1]
    );
    Serial.printf(
        "Có âm thanh: min=%lu | mean=%lu | p10=%lu | p25=%lu | "
        "p50=%lu | max=%lu\n",
        (unsigned long)signal_energy[0],
        (unsigned long)signal_mean,
        (unsigned long)signal_p10,
        (unsigned long)signal_p25,
        (unsigned long)signal_p50,
        (unsigned long)signal_energy[SIGNAL_CHUNKS - 1]
    );

    /**/ // THAY ĐỔI P5: So sánh ngưỡng VAD hiện tại với hai vùng vừa đo.
    Serial.printf("Ngưỡng VAD hiện tại = %u\n", (unsigned int)Val_Threshold);
    if(quiet_p99 >= Val_Threshold){
        Serial.println(
            "CẢNH BÁO: p99 yên lặng đã chạm/vượt ngưỡng hiện tại, "
            "có nguy cơ tự kích hoạt."
        );
    }
    if(signal_p25 <= Val_Threshold){
        Serial.println(
            "CẢNH BÁO: p25 tín hiệu chưa vượt ngưỡng hiện tại, "
            "có nguy cơ bỏ sót âm thanh yếu."
        );
    }

    if(signal_p25 > quiet_p99){
        const uint32_t suggested_threshold =
            quiet_p99 + (signal_p25 - quiet_p99) * 30 / 100;
        Serial.printf(
            "Ngưỡng gợi ý ban đầu = %lu "
            "(p99 yên lặng + 30%% khoảng cách đến p25 tín hiệu)\n",
            (unsigned long)suggested_threshold
        );
    }else{
        Serial.println(
            "KHÔNG ĐỦ TÁCH BIỆT: p25 tín hiệu <= p99 yên lặng. "
            "Chưa được giảm ngưỡng VAD."
        );
    }

    Serial.println(
        "Lưu toàn bộ kết quả này vào log. Reset ESP32 để đo một điều kiện khác."
    );
    Serial.println("=================================================\n");
    phase = CAL_DONE;
}
#endif
