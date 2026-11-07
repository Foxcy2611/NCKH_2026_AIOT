#include "Audio_IO/I2S_Mic.h"

#include <esp_heap_caps.h>
#include <math.h>

namespace {
constexpr uint32_t kTotalSamples = 80000;
constexpr uint32_t kPreRollSamples = 16000;
constexpr uint32_t kVadThreshold = 75;
constexpr uint8_t kVadConsecutiveRequired = 4;
constexpr uint8_t kWarmupChunks = 100;
constexpr uint8_t kVoteRounds = 3;
// Debug calibration: dump moi cua so 5 giay. Tat co nay khi ket thuc calib.
constexpr bool kEnableCaptureSerialDump = true;

System_State current_state = STATE_LISTENING;

int16_t* audio_buffer = nullptr;
float* audio_float_buffer = nullptr;
int16_t* pre_roll_buffer = nullptr;
uint32_t sample_count = 0;

uint8_t warmup_chunks_remaining = kWarmupChunks;
uint8_t vad_consecutive_chunks = 0;
uint32_t pre_roll_write_index = 0;
uint32_t pre_roll_valid_samples = 0;
uint32_t vad_candidate_start_index = 0;
uint32_t vad_candidate_sample_count = 0;

uint8_t asthma_votes = 0;
uint8_t non_asthma_votes = 0;
uint8_t unsure_votes = 0;
uint8_t current_vote_round = 0;
float p_non_history[kVoteRounds] = {0.0f};
bool p_non_history_valid[kVoteRounds] = {false};

float mel_spectrogram_buffer[N_MELS][MAX_FRAMES];

uint32_t Calculate_Fnv1a32(const uint8_t* data, size_t length) {
    uint32_t hash = 2166136261UL;
    for (size_t i = 0; i < length; i++) {
        hash ^= data[i];
        hash *= 16777619UL;
    }
    return hash;
}

void Dump_Capture_Over_Serial(const int16_t* samples, uint32_t count) {
    if (!kEnableCaptureSerialDump) return;
    if (samples == nullptr || count != kTotalSamples) {
        Serial.println("[CAPTURE_DUMP][ERROR] Buffer PCM16 khong hop le.");
        return;
    }

    const uint8_t* bytes = reinterpret_cast<const uint8_t*>(samples);
    const size_t byte_count = static_cast<size_t>(count) * sizeof(int16_t);
    const uint32_t checksum = Calculate_Fnv1a32(bytes, byte_count);

    // Tu CAPTURE_BEGIN den CAPTURE_END khong duoc chen bat ky log text nao.
    // Script PC doc dung byte_count byte PCM16 little-endian roi kiem tra FNV-1a.
    Serial.flush();
    Serial.printf(
        "[CAPTURE_BEGIN] version=1 samples=%lu sample_rate=%lu channels=1 "
        "sample_width=2 encoding=pcm_s16le bytes=%lu fnv1a=%08lX\n",
        static_cast<unsigned long>(count),
        static_cast<unsigned long>(Sample_Rate),
        static_cast<unsigned long>(byte_count),
        static_cast<unsigned long>(checksum)
    );
    Serial.flush();

    const size_t bytes_written = Serial.write(bytes, byte_count);
    Serial.flush();
    Serial.printf(
        "\n[CAPTURE_END] bytes_written=%lu fnv1a=%08lX\n",
        static_cast<unsigned long>(bytes_written),
        static_cast<unsigned long>(checksum)
    );
    Serial.flush();

}

void Print_Pcm_Statistics(const int16_t* samples, uint32_t count) {
    if (samples == nullptr || count == 0) return;

    int16_t min_value = samples[0];
    int16_t max_value = samples[0];
    double sum = 0.0;
    double sum_squares = 0.0;

    for (uint32_t i = 0; i < count; i++) {
        const double value = static_cast<double>(samples[i]);
        if (samples[i] < min_value) min_value = samples[i];
        if (samples[i] > max_value) max_value = samples[i];
        sum += value;
        sum_squares += value * value;
    }

    const double mean = sum / static_cast<double>(count);
    double variance = sum_squares / static_cast<double>(count) - mean * mean;
    if (variance < 0.0) variance = 0.0;
    const double standard_deviation = sqrt(variance);
    const double rms = sqrt(sum_squares / static_cast<double>(count));

    Serial.printf(
        "[PCM] samples=%lu | min=%d | max=%d | mean=%.2f | "
        "std=%.2f | rms=%.2f\n",
        static_cast<unsigned long>(count),
        static_cast<int>(min_value),
        static_cast<int>(max_value),
        mean,
        standard_deviation,
        rms
    );
}

void Print_Pnon_Statistics() {
    float min_value = 1.0f;
    float max_value = 0.0f;
    float sum = 0.0f;
    uint8_t valid_count = 0;

    for (uint8_t i = 0; i < kVoteRounds; i++) {
        if (!p_non_history_valid[i]) continue;
        const float value = p_non_history[i];
        if (value < min_value) min_value = value;
        if (value > max_value) max_value = value;
        sum += value;
        valid_count++;
    }

    if (valid_count == 0) {
        Serial.println("[P_NON STATS] Khong co ket qua inference hop le.");
        return;
    }

    const float mean = sum / valid_count;
    float squared_error_sum = 0.0f;
    for (uint8_t i = 0; i < kVoteRounds; i++) {
        if (!p_non_history_valid[i]) continue;
        const float difference = p_non_history[i] - mean;
        squared_error_sum += difference * difference;
    }
    const float standard_deviation = sqrtf(squared_error_sum / valid_count);

    Serial.printf(
        "[P_NON STATS] n=%u | min=%.9f | max=%.9f | mean=%.9f | std=%.9f\n",
        static_cast<unsigned int>(valid_count),
        min_value,
        max_value,
        mean,
        standard_deviation
    );
}

void Reset_Capture_State() {
    current_state = STATE_LISTENING;
    sample_count = 0;
    pre_roll_write_index = 0;
    pre_roll_valid_samples = 0;
    vad_consecutive_chunks = 0;
    vad_candidate_start_index = 0;
    vad_candidate_sample_count = 0;
    Serial.println("[VAD] Dang tao lai bo dem 1 giay...");
}

void Update_Votes(const Asthma_Result& result) {
    if (current_vote_round < kVoteRounds) {
        p_non_history[current_vote_round] = result.Non_Asthma_Prob / 100.0f;
        p_non_history_valid[current_vote_round] = result.Predicted_Class >= 0;
    }

    if (result.Predicted_Class == 0) {
        asthma_votes++;
    } else if (result.Predicted_Class == 1) {
        non_asthma_votes++;
    } else {
        unsure_votes++;
    }

    current_vote_round++;
    Serial.printf(
        "[BO PHIEU] %u/%u | Asthma=%u | Non-Asthma=%u | Unsure=%u\n",
        current_vote_round,
        kVoteRounds,
        asthma_votes,
        non_asthma_votes,
        unsure_votes
    );

    if (current_vote_round < kVoteRounds) return;

    Print_Pnon_Statistics();

    // Ba vong chi ket luan khi co it nhat 2 phieu cung lop. Cac ket qua
    // UNSURE khong duoc phep bien 1 phieu don le thanh ket luan chac chan.
    if (asthma_votes >= 2) {
        Serial.println("[KET LUAN] CANH BAO PHAT HIEN MAU ASTHMA.");
    } else if (non_asthma_votes >= 2) {
        Serial.println("[KET LUAN] KHONG PHAT HIEN MAU ASTHMA.");
    } else {
        Serial.println("[KET LUAN] KHONG CHAC CHAN, CAN DO LAI.");
    }

    asthma_votes = 0;
    non_asthma_votes = 0;
    unsure_votes = 0;
    current_vote_round = 0;
    for (uint8_t i = 0; i < kVoteRounds; i++) {
        p_non_history[i] = 0.0f;
        p_non_history_valid[i] = false;
    }
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
            // Chunk active dau tien la candidate onset. Chunk nay da nam trong
            // ring, nen vi tri bat dau cach write index samples_read mau.
            if (vad_consecutive_chunks == 0) {
                vad_candidate_start_index =
                    (pre_roll_write_index + kPreRollSamples
                     - static_cast<uint32_t>(samples_read))
                    % kPreRollSamples;
                vad_candidate_sample_count = 0;
            }

            if (vad_consecutive_chunks < kVadConsecutiveRequired) {
                vad_consecutive_chunks++;
                vad_candidate_sample_count += static_cast<uint32_t>(samples_read);
            }
        } else {
            vad_consecutive_chunks = 0;
            vad_candidate_sample_count = 0;
        }

        if (vad_consecutive_chunks >= kVadConsecutiveRequired) {
            uint32_t onset_samples = vad_candidate_sample_count;
            if (onset_samples > pre_roll_valid_samples) {
                onset_samples = pre_roll_valid_samples;
            }
            if (onset_samples > kTotalSamples) {
                onset_samples = kTotalSamples;
            }

            for (uint32_t i = 0; i < onset_samples; i++) {
                const uint32_t source_index =
                    (vad_candidate_start_index + i) % kPreRollSamples;
                audio_buffer[i] = pre_roll_buffer[source_index];
            }

            sample_count = onset_samples;
            vad_consecutive_chunks = 0;
            vad_candidate_sample_count = 0;
            current_state = STATE_RECORDING;
            Serial.printf(
                "[VAD] Xac nhan o muc %lu | onset=%lu mau (%.1f ms) | "
                "thu tiep den du 5 giay.\n",
                static_cast<unsigned long>(average_energy),
                static_cast<unsigned long>(onset_samples),
                onset_samples * 1000.0f / Sample_Rate
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
            Print_Pcm_Statistics(audio_buffer, kTotalSamples);
            Dump_Capture_Over_Serial(audio_buffer, kTotalSamples);
        }
        return;
    }

    if (current_state == STATE_PROCESSING) {
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
        current_state = STATE_INFERENCE;
        return;
    }

    const Asthma_Result result = Run_Asthma_Inference(mel_spectrogram_buffer);
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
