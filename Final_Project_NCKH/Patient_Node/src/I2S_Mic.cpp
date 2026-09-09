#include "Audio_IO/I2S_Mic.h"
#include "board_pinout.h"

#include "DSP_Preprocessing/DSP_Filter.h"
#include "DSP_Preprocessing/Mel_Scale.h"
#include "Model_AI/Interface_Asthma.h"

#include <esp_heap_caps.h>
#include "Core_Logic/State_Machine.h"
#include "Core_Logic/Quality_Check.h"

namespace {
    constexpr uint32_t kTotalSamples = 80000;
    constexpr uint32_t kPreRollSamples = 16000;
    constexpr uint32_t kVadThreshold = 75;
    constexpr uint8_t kVadConsecutiveRequired = 4;
    constexpr uint8_t kWarmupChunks = 100;
    constexpr uint8_t kVoteRounds = 3;

    Audio_Quality_t quality = AUDIO_OK;
    System_State current_state = MICRO_STATE_LISTENING;
    Interface_TinyML_t classification = INTERFACE_UNSURE;

    int16_t* audio_buffer = nullptr;
    float* audio_float_buffer = nullptr;
    int16_t* pre_roll_buffer = nullptr;
    uint32_t sample_count = 0;

    uint8_t warmup_chunks_remaining = kWarmupChunks;
    uint8_t vad_consecutive_chunks = 0;
    uint32_t pre_roll_write_index = 0;
    uint32_t pre_roll_valid_samples = 0;

    uint8_t asthma_votes = 0;
    uint8_t non_asthma_votes = 0;
    uint8_t unsure_votes = 0;
    uint8_t current_vote_round = 0;

    float mel_spectrogram_buffer[N_MELS][MAX_FRAMES];

    void Reset_Capture_State(){
        quality = AUDIO_OK;
        classification = INTERFACE_UNSURE;
        current_state = MICRO_STATE_LISTENING;
        sample_count = 0;
        pre_roll_write_index = 0;
        pre_roll_valid_samples = 0;
        vad_consecutive_chunks = 0;
        Serial.println("[VAD] Đang tạo lại bộ đệm 1 giây...");
    }

    void Update_Votes(const Asthma_Result& result){
        if(result.Predicted_Class == 0){
            asthma_votes++;
            classification = INTERFACE_ASTHMA_LIKE;
        } else if(result.Predicted_Class == 1){
            non_asthma_votes++;
            classification = INTERFACE_NON_ASTHMA;
        } else {
            unsure_votes++;
            classification = INTERFACE_UNSURE;
        }

        current_vote_round++;
        Serial.printf(
            "[VOTE] %u/%u | ASTHMA=%u | NON_ASTHMA=%u | UNSURE=%u\n",
            current_vote_round,
            kVoteRounds,
            asthma_votes,
            non_asthma_votes,
            unsure_votes
        );

        if(current_vote_round < kVoteRounds) return;

        if(asthma_votes > non_asthma_votes){
            Serial.println("[RESULT] Cảnh báo phát hiện âm thanh giống mẫu hen.");
        } else if(non_asthma_votes > asthma_votes){
            Serial.println("[RESULT] Không phát hiện âm thanh giống mẫu hen.");
        } else {
            Serial.println("[RESULT] Không chắc chắn, cần đo lại.");
        }

        asthma_votes = 0;
        non_asthma_votes = 0;
        unsure_votes = 0;
        current_vote_round = 0;
    }
}

void Process_Audio_Stream(void){
    int32_t raw_samples[Buffer_Samples];
    int16_t chunk[Buffer_Samples];
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

    for(int i = 0 ; i < samples_read ; i++){
        int32_t sample = (raw_samples[i] >> 16) * Amplify_Factor;
        if(sample > 32767) sample = 32767;
        if(sample < -32768) sample = -32768;
        chunk[i] = static_cast<int16_t>(sample);
    }

    if(current_state == MICRO_STATE_LISTENING){
        if(warmup_chunks_remaining > 0){
            warmup_chunks_remaining--;
            if(warmup_chunks_remaining == 0){
                Serial.println("[VAD] Khởi động xong, đang tạo bộ đệm 1 giây...");
            }
            return;
        }

        const bool pre_roll_was_full = pre_roll_valid_samples >= kPreRollSamples;
        for(int i = 0 ; i < samples_read ; i++){
            pre_roll_buffer[pre_roll_write_index] = chunk[i];
            pre_roll_write_index = (pre_roll_write_index + 1) % kPreRollSamples;
            if(pre_roll_valid_samples < kPreRollSamples) pre_roll_valid_samples++;
        }

        if(pre_roll_valid_samples < kPreRollSamples) return;
        if(!pre_roll_was_full){
            Serial.println("[VAD] Bộ đệm đã đủ 1 giây, bắt đầu lắng nghe.");
        }

        uint32_t energy_sum = 0;
        for(int i = 0 ; i < samples_read ; i++){
            const int32_t value = chunk[i];
            energy_sum += value < 0 ? static_cast<uint32_t>(-value)
                                    : static_cast<uint32_t>(value);
        }
        const uint32_t average_energy = energy_sum / samples_read;

        if(average_energy > kVadThreshold){
            if(vad_consecutive_chunks < kVadConsecutiveRequired){
                vad_consecutive_chunks++;
            }
        } else {
            vad_consecutive_chunks = 0;
        }

        if(vad_consecutive_chunks >= kVadConsecutiveRequired){
            for(uint32_t i = 0 ; i < kPreRollSamples ; i++){
                const uint32_t source_index =
                    (pre_roll_write_index + i) % kPreRollSamples;
                audio_buffer[i] = pre_roll_buffer[source_index];
            }
            sample_count = kPreRollSamples;
            vad_consecutive_chunks = 0;
            current_state = MICRO_STATE_RECORDING;
            Serial.printf(
                "[VAD] Kích hoạt ở mức %lu, đã giữ lại 1 giây đầu.\n",
                static_cast<unsigned long>(average_energy)
            );
        }
        return;
    }

    if(current_state == MICRO_STATE_RECORDING){
        for(int i = 0 ; i < samples_read && sample_count < kTotalSamples ; i++){
            audio_buffer[sample_count++] = chunk[i];
        }

        if(sample_count >= kTotalSamples){
            current_state = MICRO_STATE_QUALITY;
            Serial.println("[MIC] Đã thu đủ 5 giây.");
        }
        return;
    }

    if(current_state == MICRO_STATE_QUALITY){
        Serial.println("[CHECK] Tiến hành kiểm tra chất lượng âm thanh.");

        Audio_Quality_Metrics_t metrics = {0.0f, 0, 0, 0, 0};
        quality = AudioQuality_Check(audio_buffer, kTotalSamples, &metrics);
        // Vẽ OLED từ metrics

        if(quality == AUDIO_INACTIVE){
            Serial.println("[QUALITY FAIL] Âm thanh gần như không có hoạt động. Yêu cầu thu lại.");
            Reset_Capture_State();
            return;
        } else if(quality == AUDIO_TOO_LOUD){
            Serial.println("[QUALITY FAIL] Âm thanh quá lớn hoặc bị clipping. Vui lòng thu lại.");
            Reset_Capture_State();
            return;
        } else if(quality == AUDIO_TOO_WEAK){
            Serial.println("[QUALITY FAIL] Âm thanh quá yếu. Vui lòng thu lại.");
            Reset_Capture_State();
            return;
        } else {
            Serial.println("[QUALITY OK] Âm thanh đạt yêu cầu. Tiến hành xử lý.");
            current_state = MICRO_STATE_PROCESSING;
        }
    }

    if(current_state == MICRO_STATE_PROCESSING){
        Normalize_To_Float(audio_buffer, audio_float_buffer, kTotalSamples);
        Butterworth_Reset();
        Butterworth_Process_Buffer(audio_float_buffer, kTotalSamples);
        Apply_Pre_Emphasis(audio_float_buffer, kTotalSamples);

        const int frame_count = Compute_Mel_Power_Spectrogram(
            audio_float_buffer,
            kTotalSamples,
            mel_spectrogram_buffer,
            MAX_FRAMES
        );
        if(frame_count != MAX_FRAMES){
            Serial.printf("[ERROR] Số Mel frame=%d, yêu cầu=%d.\n", frame_count, MAX_FRAMES);
            Reset_Capture_State();
            return;
        }

        Power_To_dB_RefMax(
            mel_spectrogram_buffer,
            mel_spectrogram_buffer,
            frame_count
        );
        current_state = MICRO_STATE_INTERFACE;
        return;
    }    

    const Asthma_Result result = Run_Asthma_Interface(mel_spectrogram_buffer);
    Update_Votes(result);

    StateMachine_SubmitAudioResult(
        quality, 
        classification, 
        ((classification == INTERFACE_ASTHMA_LIKE) ? result.Asthma_Prob : 
        (classification == INTERFACE_NON_ASTHMA) ? result.Non_Asthma_Prob : result.Unsure_Prob) / 100.0f
    );

    // Update Session

    Reset_Capture_State();
}

void I2S_Mic_Init(int SCK_Pin, int WS_Pin, int SD_Pin){
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
        while (true) delay(100);
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
        while (true) delay(100);
    }
}

bool Process_ManualCheck_Pipeline(void){
    // Chỉ được Abort trong quá trình thu
    if(!I2S_RecordSamples()){
        if(!StateMachine_IsAbortRequested()){
            StateMachine_ReportError("MANUAL_CAPTURE_FAILED");
        }
        return false;
    }

    StateMachine_NotifyCaptureDone();

    Audio_Quality_Metrics_t metrics = {0.0f, 0, 0, 0, 0};
    Audio_Quality_t quality = AudioQuality_Check(audio_buffer, kTotalSamples, &metrics);

    StateMachine_SubmitAudioQuality(quality);

    if(quality == AUDIO_INACTIVE){
        Serial.println("[QUALITY FAIL] Âm thanh gần như không có hoạt động. Yêu cầu thu lại.");
        return false;
    } else if(quality == AUDIO_TOO_LOUD){
        Serial.println("[QUALITY FAIL] Âm thanh quá lớn hoặc bị clipping. Vui lòng thu lại.");
        return false;
    } else if(quality == AUDIO_TOO_WEAK){
        Serial.println("[QUALITY FAIL] Âm thanh quá yếu. Vui lòng thu lại.");
        return false;
    } else {
        Serial.println("[QUALITY OK] Âm thanh đạt yêu cầu. Tiến hành xử lý.");
    }

    Normalize_To_Float(audio_buffer, audio_float_buffer, kTotalSamples);
    Butterworth_Reset();
    Butterworth_Process_Buffer(audio_float_buffer, kTotalSamples);
    Apply_Pre_Emphasis(audio_float_buffer, kTotalSamples);

    const int frame_count = Compute_Mel_Power_Spectrogram(
        audio_float_buffer,
        kTotalSamples,
        mel_spectrogram_buffer,
        MAX_FRAMES
    );
    if(frame_count != MAX_FRAMES){
        Serial.printf("[ERROR] Số Mel frame=%d, yêu cầu=%d.\n", frame_count, MAX_FRAMES);
        StateMachine_ReportError("INVALID_MEL_FRAME_COUNT");
        return false;
    }

    Power_To_dB_RefMax(mel_spectrogram_buffer, mel_spectrogram_buffer, frame_count);

    const Asthma_Result result = Run_Asthma_Interface(mel_spectrogram_buffer);

    const Interface_TinyML_t manual_classification =
        (result.Predicted_Class == 0) ? INTERFACE_ASTHMA_LIKE :
        (result.Predicted_Class == 1) ? INTERFACE_NON_ASTHMA : INTERFACE_UNSURE;

    const float manual_score =
        (manual_classification == INTERFACE_ASTHMA_LIKE) ? result.Asthma_Prob :
        (manual_classification == INTERFACE_NON_ASTHMA) ? result.Non_Asthma_Prob : result.Unsure_Prob;

    StateMachine_SubmitAudioResult(quality, manual_classification, manual_score / 100.0f);
    
    return true;
}


bool I2S_RecordSamples(void){
    if(audio_buffer == nullptr){
        Serial.println("[ERROR] Audio buffer chưa được cấp phát; cần gọi I2S_Mic_Init trước.");
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
        i2s_read(
            I2S_Port,
            raw_samples,
            sizeof(raw_samples),
            &bytes_read,
            portMAX_DELAY
        );
 
        const int samples_read = bytes_read / sizeof(int32_t);
        if(samples_read <= 0) continue;
 
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
