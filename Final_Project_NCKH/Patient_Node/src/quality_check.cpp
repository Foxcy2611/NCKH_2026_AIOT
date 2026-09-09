#include "Core_Logic/Quality_Check.h"

#include <Arduino.h>
#include <math.h>

namespace {
    // Test chưa phải bản cuối
    constexpr float kMinRMS = 150.0f;           // RMS dưới mức này -> TOO_WEAK
    constexpr float kMinActiveRatio = 0.05f;    // < 5% block hoạt động -> INACTIVE
    constexpr float kMaxClippedRatio = 0.01f;   // > 1% sample clip -> TOO_LOUD

    constexpr int32_t  kClipLevel = 32000;         // gần max int16 (32767) -> coi là clip     
    constexpr int32_t  kActiveBlockThreshold = 80; // biên độ TB/block để coi là "có hoạt động"

    constexpr uint32_t kBlockSize = 256;          // ~16ms/block @16kHz

    const char* AudioQualityName(Audio_Quality_t quality){
        switch(quality){
            case AUDIO_OK:       return "AUDIO_OK";
            case AUDIO_TOO_WEAK: return "AUDIO_TOO_WEAK";
            case AUDIO_TOO_LOUD: return "AUDIO_TOO_LOUD";
            case AUDIO_INACTIVE: return "AUDIO_INACTIVE";
            default:             return "AUDIO_UNKNOWN";
        }
    }
} 

Audio_Quality_t AudioQuality_Check(
    const int16_t* audio,
    uint32_t samples,
    Audio_Quality_Metrics_t* out_metrics
){
    Audio_Quality_Metrics_t metrics = {0.0f, 0, 0, 0, 0};
    
    double sum_square = 0.0; // Dùng để tính tổng bình phương RMS
    uint32_t block_start = 0;

    while(block_start < samples){
        uint32_t block_end = block_start + kBlockSize;
        if(block_end > samples) block_end = samples;

        uint64_t block_abs_sum = 0; // MAV
        for(uint32_t idx = block_start ; idx < block_end ; idx++){
            const int32_t value = audio[idx];
            const int32_t abs_value = (value > 0) ? value : -value;

            sum_square += static_cast<double>(value) * static_cast<double>(value);
            if(abs_value > metrics.peak) metrics.peak = abs_value;
            if(abs_value > kClipLevel) metrics.clipped_samples++;

            // Cộng dồn tổng các block, để ko cần dùng đển sqrt tốn chu kỳ
            block_abs_sum += static_cast<uint32_t>(abs_value);
        }

        const uint32_t block_length = block_end - block_start;
        const uint32_t block_mav = static_cast<uint32_t>(block_abs_sum / block_length); // MAV

        if(block_mav > kActiveBlockThreshold){
            metrics.active_blocks++;
        }
        metrics.total_blocks++;

        block_start = block_end;
    }

    metrics.rms = static_cast<float>(sqrt(sum_square / samples));

    // % Block có hoạt động
    const float active_ratio = static_cast<float>(metrics.active_blocks) / metrics.total_blocks;
    // % Block chạm ngưỡng clipping
    const float clipped_ratio = static_cast<float>(metrics.clipped_samples) / samples;

    Audio_Quality_t result;

    if(active_ratio < kMinActiveRatio){
        result = AUDIO_INACTIVE;
    } else if(clipped_ratio > kMaxClippedRatio){
        result = AUDIO_TOO_LOUD;
    } else if(metrics.rms < kMinRMS){
        result = AUDIO_TOO_WEAK;
    } else {
        result = AUDIO_OK;
    }

    Serial.printf(
        "[QUALITY] RMS=%.1f Peak=%ld Clipped=%lu/%lu (%.2f%%) ActiveBlocks=%lu/%lu (%.1f%%) -> %s\n",
        metrics.rms,
        static_cast<long>(metrics.peak),
        static_cast<unsigned long>(metrics.clipped_samples),
        static_cast<unsigned long>(samples),
        clipped_ratio * 100.0f,
        static_cast<unsigned long>(metrics.active_blocks),
        static_cast<unsigned long>(metrics.total_blocks),
        active_ratio * 100.0f,
        AudioQualityName(result)
    );

    if(out_metrics != NULL){
        *out_metrics = metrics;
    }

    return result;
}
