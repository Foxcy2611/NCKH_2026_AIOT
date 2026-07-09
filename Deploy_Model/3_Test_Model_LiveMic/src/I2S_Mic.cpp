#include "I2S_Mic.h"

void I2S_Mic_Init(int SCK_Pin, int WS_Pin, int SD_Pin){
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

void I2S_Mic_Read_and_Send(void){
    int32_t raw_samples[Buffer_Samples];
    int16_t audio_samples[Buffer_Samples];
    size_t bytes_read = 0;

    i2s_read(I2S_Port, raw_samples, sizeof(int32_t) * Buffer_Samples, &bytes_read, portMAX_DELAY);
    
    int samples_read = bytes_read / sizeof(int32_t);

    if (samples_read > 0) {
        for (int i = 0; i < samples_read; i++) {
            audio_samples[i] = (raw_samples[i] >> 16) * Amplify_Factor; 
        }
        
        Serial.write((uint8_t*)audio_samples, samples_read * sizeof(int16_t));
    }
}