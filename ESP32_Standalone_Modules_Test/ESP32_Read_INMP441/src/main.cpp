#include <Arduino.h>
#include <driver/i2s.h>

/*
===============================================================================
Project thu Environment V2 bằng đúng đường thu của Patient Node Final.

Chuẩn đã đồng nhất:
- INMP441: SCK=GPIO14, WS=GPIO15, SD=GPIO16.
- 16 kHz, mono, I2S 32-bit.
- Dịch phải 16 bit, gain 1 và giới hạn về PCM16.
- Chỉ truyền PCM16 nhị phân qua Serial; không chèn log khi đang stream.
===============================================================================
*/

namespace {
    constexpr i2s_port_t kI2SPort = I2S_NUM_0;

    constexpr int kI2SSck = 14;
    constexpr int kI2SWs = 15;
    constexpr int kI2SSd = 16;

    constexpr uint32_t kSampleRate = 16000;
    constexpr size_t kBufferSamples = 256;
    constexpr int32_t kAmplifyFactor = 1;

    int32_t raw_samples[kBufferSamples];
    int16_t pcm16_samples[kBufferSamples];
    bool streaming_enabled = false;

    [[noreturn]] void StopOnInitError(const char* message) {
        // Log chỉ xuất hiện khi khởi tạo thất bại, trước giai đoạn thu PCM.
        Serial.println(message);
        while (true) delay(1000);
    }
}

void setup() {
    Serial.begin(460800);
    delay(300);

    const i2s_config_t i2s_config = {
        .mode = i2s_mode_t(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = kSampleRate,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_RIGHT,
        .communication_format = i2s_comm_format_t(I2S_COMM_FORMAT_STAND_I2S),
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,
        .dma_buf_len = kBufferSamples,
        .use_apll = false,
        .tx_desc_auto_clear = false,
        .fixed_mclk = 0,
    };

    const i2s_pin_config_t pin_config = {
        .bck_io_num = kI2SSck,
        .ws_io_num = kI2SWs,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num = kI2SSd,
    };

    if (i2s_driver_install(kI2SPort, &i2s_config, 0, nullptr) != ESP_OK) {
        StopOnInitError("I2S_DRIVER_INSTALL_FAILED");
    }

    if (i2s_set_pin(kI2SPort, &pin_config) != ESP_OK) {
        StopOnInitError("I2S_SET_PIN_FAILED");
    }

    i2s_zero_dma_buffer(kI2SPort);
}

void loop() {
    while (Serial.available() > 0) {
        const char command = static_cast<char>(Serial.read());

        if (command == 'R') {
            // Bắt đầu tại ranh giới một I2S chunk mới, tránh lệch byte PCM16.
            i2s_zero_dma_buffer(kI2SPort);
            streaming_enabled = true;
        } else if (command == 'S') {
            streaming_enabled = false;
        }
    }

    if (!streaming_enabled) {
        delay(1);
        return;
    }

    size_t bytes_read = 0;
    const esp_err_t read_result = i2s_read(
        kI2SPort,
        raw_samples,
        sizeof(raw_samples),
        &bytes_read,
        portMAX_DELAY
    );

    if (read_result != ESP_OK || bytes_read == 0) return;

    const size_t samples_read = bytes_read / sizeof(int32_t);
    for (size_t index = 0; index < samples_read; ++index) {
        int32_t sample = (raw_samples[index] >> 16) * kAmplifyFactor;

        if (sample > INT16_MAX) sample = INT16_MAX;
        if (sample < INT16_MIN) sample = INT16_MIN;

        pcm16_samples[index] = static_cast<int16_t>(sample);
    }

    Serial.write(
        reinterpret_cast<const uint8_t*>(pcm16_samples),
        samples_read * sizeof(int16_t)
    );
}
