# Kết luận bộ thông số kỹ thuật 

File markdown này dùng để kết luận phân vùng bộ nhớ cho toàn bộ quá trình suy luận (Inference) trên ESP32-S3 sau 2 tiến trình
- 1_Test_Model_Static_Profiling
- 2_Test_Model_LiveMic

## 1. Bảng thống kê số liệu model và Tensor

| Thông số | Giá trị |
|----------|----------|
| Model | `combo_pre0_mel40_fft2048__V1__s44` |
| Quantization | `QAT_INT8` |
| Phần cứng | ESP32-S3 |
| CPU frequency | 240 MHz |
| Inference framework | TensorFlow Lite Micro |
| Model size | 347,968 B ≈ 339.81 KiB |
| Input tensor shape | `(1, 40, 129, 1)` |
| Input tensor type | `int8` |
| Input elements | 5,160 |
| Input tensor size | 5,160 B ≈ 5.04 KiB |
| Input scale | `0.0039215689` |
| Input zero-point | `-128` |
| Output type | `int8` |
| Output scale | `0.00390625` |
| Output zero-point | `-128` |
| Label 0 | Asthma |
| Label 1 | Non-Asthma |

## 2. RAM và Tensor Arena

| Chỉ tiêu bộ nhớ | Kết quả log |
|----------------|-------------|
| Tensor Arena cấp phát trong bài profiling | 1.048.576 B (1 MiB) |
| Tensor Arena thực dùng | 169.380 B |
| Arena tối thiểu đề xuất trong log để thử lại | 186.368 B (182 KiB) |
| Arena chọn cho firmware cuối | 196.608 B (192 KiB) |
| Dung lượng dự phòng theo mức đã đo | 27.228 B (~26,59 KiB) |
| Internal RAM trống trước setup | 364.636 B |
| Internal RAM trống sau setup | 364.436 B |
| Internal RAM giảm khi setup | 200 B |
| PSRAM trống trước setup | 8.386.035 B |
| PSRAM trống sau setup | 7.337.443 B |
| PSRAM giảm khi setup | 1.048.592 B |
| Peak RAM estimate trong log | 169.668 B |

## 3. Bộ nhớ cho pipeline xử lý âm thanh

| Chỉ tiêu bộ nhớ | Kết quả log |
|----------------|-------------|
| Tensor Arena cấp phát trong bài profiling | 1.048.576 B (1 MiB) |
| Tensor Arena thực dùng | 169.380 B |
| Arena tối thiểu đề xuất trong log để thử lại | 186.368 B (182 KiB) |
| Arena chọn cho firmware cuối | 196.608 B (192 KiB) |
| Dung lượng dự phòng theo mức đã đo | 27.228 B (~26,59 KiB) |
| Internal RAM trống trước setup | 364.636 B |
| Internal RAM trống sau setup | 364.436 B |
| Internal RAM giảm khi setup | 200 B |
| PSRAM trống trước setup | 8.386.035 B |
| PSRAM trống sau setup | 7.337.443 B |
| PSRAM giảm khi setup | 1.048.592 B |
| Peak RAM estimate trong log | 169.668 B |

## 4. Cấu hình tham chiếu

Đây là cấu hình dự kiến, sẽ có 1 số thay đổi dựa quá trình nghiệm thu tại [Nghiệm thu Node](/Experiments_Benchmarking/Patient_Node/Final_V1_Validation/)

```cpp

#pragma once
#include <cstddef>
#include <cstdint>

// Hardware
constexpr uint32_t kTargetCpuMHz = 240;

// Audio acquisition
constexpr uint32_t kSampleRate = 16000;
constexpr size_t kAudioDurationSeconds = 5;
constexpr size_t kAudioSamples = 80000;
constexpr size_t kPreTriggerSamples = 16000;

// Spectrogram
constexpr size_t kMelBands = 40;
constexpr size_t kMelFrames = 129;
constexpr float kMelDbMin = -80.0f;
constexpr float kMelDbMax = 0.0f;

// TensorFlow Lite Micro
constexpr size_t kTensorArenaSize = 192 * 1024;
constexpr size_t kInputTensorElements = 40 * 129;

constexpr float kInputScale = 0.0039215689f;
constexpr int kInputZeroPoint = -128;

constexpr float kOutputScale = 0.00390625f;
constexpr int kOutputZeroPoint = -128;

// VAD and decision logic
constexpr int kVadThreshold = 75;
constexpr int kVadConsecutiveBlocks = 4;
constexpr int kVotingCount = 3;

// Model class mapping
constexpr int kClassAsthma = 0;
constexpr int kClassNonAsthma = 1;

```
