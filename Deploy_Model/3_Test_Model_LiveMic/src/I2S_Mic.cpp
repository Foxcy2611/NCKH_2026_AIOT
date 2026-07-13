#include "I2S_Mic.h"

#define Total_Samples 80000 // 5s cho 16 kHz
#define Val_Threshold 500

System_State curr_state = STATE_LISTENING;
int16_t* audio_buffer = nullptr;
float* audio_float_buff = nullptr;
int sample_cnt = 0;

static float mel_power_buff[129][64];
static float mel_db_buff[129][64];

void Process_Audio_Stream(void){
    // 1. Đọc 256 mẫu thô từ DMA
    int32_t raw_samples[Buffer_Samples];
    size_t bytes_read = 0;

    i2s_read(I2S_Port, raw_samples, sizeof(int32_t) * Buffer_Samples, &bytes_read, portMAX_DELAY);
    int samples_read = bytes_read / sizeof(int32_t);

    if (samples_read == 0) return; 

    // 2. Chuyển đổi về PCM 16-bit chuẩn
    int16_t chunk[Buffer_Samples];
    for (int i = 0; i < samples_read; i++) {
        chunk[i] = (raw_samples[i] >> 16) * Amplify_Factor;
    }

    // 3. Chuyển đổi trạng thái
    if(curr_state == STATE_LISTENING){
        // Tính năng lượng MAV của 256 mẫu hiện tại
        uint32_t sum_energy = 0;
        for(int i = 0 ; i < samples_read ; i++){
            sum_energy += abs(chunk[i]);
        } 
        uint32_t avg_enegry = sum_energy / samples_read;

        if(avg_enegry > Val_Threshold){
            Serial.printf("[VAD] Phat hien tieng dong ! - Nang luong: %d", avg_enegry);
            Serial.println("Bat dau ghi !!");
            curr_state = STATE_RECORDING;
            sample_cnt = 0;

            // Nhét luôn chukn vào kẻo lỡ mất dữ liệu đầu
            for(int i = 0 ; i < samples_read ; i++){
                audio_buffer[sample_cnt] = chunk[i];
                sample_cnt++;
            }
        } 

    } else if(curr_state == STATE_RECORDING){
        for(int i = 0 ; i < samples_read ; i++){
            if(sample_cnt < Total_Samples){
                audio_buffer[sample_cnt] = chunk[i];
                sample_cnt++;
            }
        }

        Serial.println("[MIC] Da thu du 5 giay am thanh! Chuyen sang AI...");
        curr_state = STATE_PROCESSING;

    } else if(curr_state == STATE_PROCESSING){
        Serial.println("\n--- BAT DAU TIEN XU LY ---\n");

        // 1. Reset bộ nhớ butterworth
        Butterworth_Reset();

        // 2. Lọc nhiễu thông dải
        Butterworth_Process_Buffer(audio_buffer, Total_Samples);
        Serial.println("1. Hoan thanh bo loc Butterworth.");

        // 3. Bù suy hao tần số cao
        Apply_Pre_Emphasis(audio_buffer, Total_Samples);
        Serial.println("2. Hoan thanh bo loc Pre-Amphasis.");

        // 4. Chuẩn hóa về [-1 1]
        Normalize_To_Float(audio_buffer, audio_float_buff, Total_Samples);
        Serial.println("3. Hoan thanh chuan hoa ve Float [-1.0 1.0]");

        // 5. Chạy STFT và năng lượng Mel
        int num_frames = Compute_Mel_Power_Spectrogram(
            audio_float_buff, Total_Samples, 
            mel_power_buff, 129
        );
        Serial.println("4. Hoan thanh trich xuat nang luong Mel.");

        // 6. Chuyển đổi sang đơn vị dB
        Power_To_dB_RefMax(mel_power_buff, mel_db_buff, num_frames);
        Serial.println("5. Hoan thanh ma tran Mel-Spectrogram dB!");
        Serial.println("------------------------------");

        Asthma_Result result = Run_Asthma_Interface(mel_db_buff);
        curr_state = STATE_LISTENING;
        sample_cnt = 0;
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
