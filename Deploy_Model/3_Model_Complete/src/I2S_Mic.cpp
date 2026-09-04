#include "Audio_IO/I2S_Mic.h"

#include <esp_heap_caps.h>

namespace {
constexpr uint32_t kTotalSamples = 80000;
constexpr uint32_t kPreRollSamples = 16000;
constexpr uint32_t kVadThreshold = 75;
constexpr uint8_t kVadConsecutiveRequired = 4;
constexpr uint8_t kWarmupChunks = 100;
constexpr uint8_t kVoteRounds = 3;

System_State current_state = STATE_LISTENING;

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

void Reset_Capture_State() {
    current_state = STATE_LISTENING;
    sample_count = 0;
    pre_roll_write_index = 0;
    pre_roll_valid_samples = 0;
    vad_consecutive_chunks = 0;
    Serial.println("[VAD] Dang tao lai bo dem 1 giay...");
}

void Update_Votes(const Asthma_Result& result) {
    if (result.Predicted_Class == 0) {
        asthma_votes++;
    } else if (result.Predicted_Class == 1) {
        non_asthma_votes++;
    } else {
        unsure_votes++;
    }

    current_vote_round++;
    Serial.printf(
        "[BO PHIEU] %u/%u | Asthma=%u | Non-Asthma=%u | Loi=%u\n",
        current_vote_round,
        kVoteRounds,
        asthma_votes,
        non_asthma_votes,
        unsure_votes
    );

    if (current_vote_round < kVoteRounds) return;

    if (asthma_votes > non_asthma_votes) {
        Serial.println("[KET LUAN] CANH BAO PHAT HIEN MAU ASTHMA.");
    } else if (non_asthma_votes > asthma_votes) {
        Serial.println("[KET LUAN] KHONG PHAT HIEN MAU ASTHMA.");
    } else {
        Serial.println("[KET LUAN] KHONG CHAC CHAN, CAN DO LAI.");
    }

    asthma_votes = 0;
    non_asthma_votes = 0;
    unsure_votes = 0;
    current_vote_round = 0;
}
}

void Process_Audio_Stream(void) {
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
    if (samples_read <= 0) return;

    for (int i = 0; i < samples_read; i++) {
        int32_t sample = (raw_samples[i] >> 16) * Amplify_Factor;
        if (sample > 32767) sample = 32767;
        if (sample < -32768) sample = -32768;
        chunk[i] = static_cast<int16_t>(sample);
    }

    if (current_state == STATE_LISTENING) {
        if (warmup_chunks_remaining > 0) {
            warmup_chunks_remaining--;
            if (warmup_chunks_remaining == 0) {
                Serial.println("[VAD] Khoi dong xong, dang tao bo dem 1 giay...");
            }
            return;
        }

        const bool pre_roll_was_full = pre_roll_valid_samples >= kPreRollSamples;
        for (int i = 0; i < samples_read; i++) {
            pre_roll_buffer[pre_roll_write_index] = chunk[i];
            pre_roll_write_index = (pre_roll_write_index + 1) % kPreRollSamples;
            if (pre_roll_valid_samples < kPreRollSamples) pre_roll_valid_samples++;
        }

        if (pre_roll_valid_samples < kPreRollSamples) return;
        if (!pre_roll_was_full) {
            Serial.println("[VAD] Bo dem da du 1 giay, bat dau lang nghe.");
        }

        uint32_t energy_sum = 0;
        for (int i = 0; i < samples_read; i++) {
            const int32_t value = chunk[i];
            energy_sum += value < 0 ? static_cast<uint32_t>(-value)
                                    : static_cast<uint32_t>(value);
        }
        const uint32_t average_energy = energy_sum / samples_read;

        if (average_energy > kVadThreshold) {
            if (vad_consecutive_chunks < kVadConsecutiveRequired) {
                vad_consecutive_chunks++;
            }
        } else {
            vad_consecutive_chunks = 0;
        }

        if (vad_consecutive_chunks >= kVadConsecutiveRequired) {
            for (uint32_t i = 0; i < kPreRollSamples; i++) {
                const uint32_t source_index =
                    (pre_roll_write_index + i) % kPreRollSamples;
                audio_buffer[i] = pre_roll_buffer[source_index];
            }
            sample_count = kPreRollSamples;
            vad_consecutive_chunks = 0;
            current_state = STATE_RECORDING;
            Serial.printf(
                "[VAD] Kich hoat o muc %lu, da giu lai 1 giay dau.\n",
                static_cast<unsigned long>(average_energy)
            );
        }
        return;
    }

    if (current_state == STATE_RECORDING) {
        for (int i = 0; i < samples_read && sample_count < kTotalSamples; i++) {
            audio_buffer[sample_count++] = chunk[i];
        }

        if (sample_count >= kTotalSamples) {
            current_state = STATE_PROCESSING;
            Serial.println("[MIC] Da thu du 5 giay.");
        }
        return;
    }

    if (current_state == STATE_PROCESSING) {
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
        if (frame_count != MAX_FRAMES) {
            Serial.printf("[LOI] So khung Mel=%d, can %d.\n", frame_count, MAX_FRAMES);
            Reset_Capture_State();
            return;
        }

        Power_To_dB_RefMax(
            mel_spectrogram_buffer,
            mel_spectrogram_buffer,
            frame_count
        );
        current_state = STATE_INTERFACE;
        return;
    }

    const Asthma_Result result = Run_Asthma_Interface(mel_spectrogram_buffer);
    Update_Votes(result);
    Reset_Capture_State();
}

void I2S_Mic_Init(int SCK_Pin, int WS_Pin, int SD_Pin) {
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

    if (audio_buffer == nullptr
        || audio_float_buffer == nullptr
        || pre_roll_buffer == nullptr) {
        Serial.println("[LOI] Khong du PSRAM cho bo dem am thanh.");
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

    if (i2s_driver_install(I2S_Port, &i2s_config, 0, nullptr) != ESP_OK
        || i2s_set_pin(I2S_Port, &pin_config) != ESP_OK) {
        Serial.println("[LOI] Khong khoi tao duoc I2S.");
        while (true) delay(100);
    }
}
