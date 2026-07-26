#include "Audio_IO/I2S_Mic.h"
#include <string.h>

#define Total_Samples 80000   // 5s @ 16kHz
#define Val_Threshold 5000
#define Vote_Round 3

static uint8_t vote_asthma_count = 0;
static uint8_t vote_normal_count = 0;
static uint8_t vote_unsure_count = 0;
static uint8_t current_vote_round = 0;

static uint32_t total_tests = 0;
static uint32_t total_asthma_alerts = 0;

System_State curr_state = STATE_LISTENING;

int16_t* audio_buffer = nullptr;
float* audio_float_buff = nullptr;
int sample_cnt = 0;

static float mel_power_buff[N_MELS][MAX_FRAMES];
static float mel_db_buff[N_MELS][MAX_FRAMES];

void Process_Audio_Stream(void){
    int32_t raw_samples[Buffer_Samples];
    size_t bytes_read = 0;

    i2s_read(I2S_Port, raw_samples, sizeof(int32_t) * Buffer_Samples, &bytes_read, portMAX_DELAY);
    int samples_read = bytes_read / sizeof(int32_t);

    if (samples_read == 0) return;

    int16_t chunk[Buffer_Samples];
    for (int i = 0; i < samples_read; i++) {
        int32_t amplified = (raw_samples[i] >> 16) * Amplify_Factor;

        if(amplified > 32767) amplified = 32767;
        if(amplified < -32768) amplified = -32768;

        chunk[i] = (int16_t)amplified;
    }

    if(curr_state == STATE_LISTENING){
        
        uint32_t sum_energy = 0;
        for(int i = 0; i < samples_read; i++){
            sum_energy += abs(chunk[i]);
        }
        uint32_t avg_energy = sum_energy / samples_read;

        if(avg_energy > Val_Threshold){
            Serial.printf("[VAD] Phát hiện tiếng động! - Năng lượng: %d\n", avg_energy);
            Serial.println("Bắt đầu ghi !!");
            curr_state = STATE_RECORDING;
            sample_cnt = 0;

            for(int i = 0; i < samples_read; i++){
                audio_buffer[sample_cnt] = chunk[i];
                sample_cnt++;
            }
        }

    } else if(curr_state == STATE_RECORDING){
        
        for(int i = 0; i < samples_read; i++){
            if(sample_cnt < Total_Samples){
                audio_buffer[sample_cnt] = chunk[i];
                sample_cnt++;
            }
        }

        if (sample_cnt >= Total_Samples) {
            Serial.println("[MIC] Đã thu đủ 5 giây âm thanh! Chuyển sang AI ...");
            curr_state = STATE_PROCESSING;
        }

    } else if(curr_state == STATE_PROCESSING){
        Serial.println("\n--- BẮT ĐẦU TIỀN XỬ LÝ ---\n");

        Normalize_To_Float(audio_buffer, audio_float_buff, Total_Samples);
        Serial.println("1. Hoàn thành chuẩn hóa về Float [-1.0, 1.0]");

        Butterworth_Reset();
        Butterworth_Process_Buffer(audio_float_buff, Total_Samples);
        Serial.println("2. Hoàn thành bộ lọc Butterworth.");

        Apply_Pre_Emphasis(audio_float_buff, Total_Samples);
        Serial.println("3. Hoàn thành bộ lọc Pre-Emphasis.");

        int num_frames = Compute_Mel_Power_Spectrogram(
            audio_float_buff, Total_Samples, 
            mel_power_buff, MAX_FRAMES
        );
        Serial.println("4. Hoàn thành trích xuất năng lượng Mel.");

        Power_To_dB_RefMax(mel_power_buff, mel_db_buff, num_frames);
        Serial.println("5. Hoàn thành ma trận Mel-Spectrogram dB!");
        Serial.println("------------------------------");

        curr_state = STATE_INTERFACE;

    } else if(curr_state == STATE_INTERFACE){
        Asthma_Result result = Run_Asthma_Interface(mel_db_buff);

        if (result.Predicted_Class == 0) vote_asthma_count++;
        else if (result.Predicted_Class == 1) vote_normal_count++;
        else vote_unsure_count++;

        current_vote_round++;

        Serial.printf("[VOTE] Lần %u/%u - Asthma:%u | Normal:%u | Unsure:%u\n",
            current_vote_round, Vote_Round, vote_asthma_count, 
            vote_normal_count, vote_unsure_count);

        if (current_vote_round >= Vote_Round) {
            Serial.println("\n========== KẾT LUẬN SAU 3 LẦN ĐO ==========");
            if (vote_asthma_count > vote_normal_count) {
                Serial.println(">>> CẢNH BÁO: HEN SUYỄN - ASTHMA");
            } else if (vote_normal_count > vote_asthma_count) {
                Serial.println(">>> BÌNH THƯỜNG - NORMAL");
            } else {
                Serial.println(">>> KHÔNG CHẮC CHẮN, ĐỀ NGHỊ ĐO LẠI");
            }
            Serial.println("============================================\n");

            vote_asthma_count = 0;
            vote_normal_count = 0;
            vote_unsure_count = 0;
            current_vote_round = 0;
        }

        total_tests++;
        if (result.Predicted_Class == 0) total_asthma_alerts++;

        if (total_tests % 10 == 0) {
            Serial.printf("[THỐNG KÊ] Tổng %lu lần đo, có %lu lần báo Asthma (%.1f%%)\n",
                total_tests, total_asthma_alerts,
                (float)total_asthma_alerts / total_tests * 100.0f);
        }

        curr_state = STATE_LISTENING;
        sample_cnt = 0;
        Serial.println("\n[HỆ THỐNG] Sẵn sàng! Đang lắng nghe...\n");
    }
}

void I2S_Mic_Init(int SCK_Pin, int WS_Pin, int SD_Pin){
    audio_buffer = (int16_t*)heap_caps_malloc(Total_Samples * sizeof(int16_t), MALLOC_CAP_SPIRAM);
    audio_float_buff = (float*)heap_caps_malloc(Total_Samples * sizeof(float), MALLOC_CAP_SPIRAM);

    if (audio_buffer == nullptr || audio_float_buff == nullptr) {
        Serial.println("[LỖI CRITICAL] Không đủ PSRAM để cấp phát mảng âm thanh!");
        while(1);
    }

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