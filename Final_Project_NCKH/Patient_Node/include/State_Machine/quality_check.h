#ifndef NCKH_QUALITY_CHECK_H
#define NCKH_QUALITY_CHECK_H

#include <stdint.h>
#include "system_state.h"

/*
- Với 3 state fail chia như sau
1. WEAK/INACTIVE: Tính RMS và MAV, chia Samples thành các block ~256
tính RMS/biên độ trung bình mỗi block     

X_RMS = sqrt( (1/N) · (n=0 -> N-1) Σ x[i]² ) => N = 80000 ; metrics.rms
X_MAV = (1/N) . (n=0 -> N-1) Σ |xi|          => N = len 1 block ; block_mav

+ RMS tính trung bình cả đoạn 5s
+ MAV tính theo từng block, tại từng thời điểm trong 5s (block) có thực sự phát âm thanh ?

=> Tính số block vượt ngưỡng "có hoạt động" (active block)
+ INACTIVE: active block < 5%
+ WEAK: Có hoạt động nhưng RMS toàn buffer dưới ngưỡng tối thiểu

2. Nhiễu rác: Dựa vào tỉ lệ bị clipping
+ Đếm số sample có biên độ chạm/gần chạm giới hạn
+ Tỷ lệ mà vượt ngưỡng -> Rác
*/

// Metric (Các chỉ số) tính được khi quét buffer
typedef struct {
    float rms;
    int32_t peak;               // Biên độ tuyệt đối max trong suốt buffer
    uint32_t clipped_samples;   // Số block chạm/gần chạm đỉnh
    uint32_t active_blocks;     // Số block hoạt động
    uint32_t total_blocks;      // Tổng block đã chia (80k / 256)
} Audio_Quality_Metrics_t;

Audio_Quality_t AudioQuality_Check(
    const int16_t* audio,
    uint32_t samples,
    Audio_Quality_Metrics_t* out_metrics
);

#endif /* NCKH_QUALITY_CHECK_H */