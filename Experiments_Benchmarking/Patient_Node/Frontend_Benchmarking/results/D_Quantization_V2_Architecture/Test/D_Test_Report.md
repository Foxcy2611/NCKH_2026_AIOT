# Báo cáo lượng tử hóa Frontend — Historical Test

- Plan SHA256: `5f65766e6f61863d01e1526c1314ba1e3f249769a2ea782b007ce8b3e84e1234`
- Split đánh giá: **Historical Test**
- Test accessed: **true**
- Thứ tự checkpoint được bàn giao từ phân tích bước C.
- Cảnh báo: Test 159 WAV đã được xem ở bước C; đây không phải holdout mới hoàn toàn độc lập.

## Phạm vi checkpoint

| Ưu tiên | Vai trò | Trial | Variant | Input |
|---:|---|---|---|---|
| 1 | EXPLICIT | `combo_pre0_mel40_fft2048__V2__s44` | `combo_pre0_mel40_fft2048` | `40 × 129 × 1` |

## Kết quả Historical Test

| Ưu tiên | Trial | Method | Accuracy | Macro F1 | Asthma Recall | Non-Asthma Recall | Đổi nhãn so với FP32 | Kích thước (byte) | I/O |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | `combo_pre0_mel40_fft2048__V2__s44` | `KERAS_FP32` | 0.9182 | 0.8886 | 0.8421 | 0.9421 | 0 | 160355 | float32 → float32 |
| 1 | `combo_pre0_mel40_fft2048__V2__s44` | `PTQ_INT8` | 0.8868 | 0.8521 | 0.8421 | 0.9008 | 5 | 23144 | int8 → int8 |
| 1 | `combo_pre0_mel40_fft2048__V2__s44` | `QAT_INT8` | 0.9119 | 0.8811 | 0.8421 | 0.9339 | 1 | 22944 | int8 → int8 |
| 1 | `combo_pre0_mel40_fft2048__V2__s44` | `PTQ_INT16x8` | 0.9182 | 0.8886 | 0.8421 | 0.9421 | 0 | 26872 | int16 → int16 |

## Confusion matrix và classification report

Quy ước: nhãn `0 = Asthma`, nhãn `1 = Non-Asthma`, hàng là nhãn thật và cột là nhãn dự đoán.

### 1. `combo_pre0_mel40_fft2048__V2__s44` — `KERAS_FP32`

- Accuracy: **0.9182**
- Balanced accuracy: **0.8921**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 32 | 6 |
| Non-Asthma | 7 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8205 | 0.8421 | 0.8312 | 38 |
| Non-Asthma | 0.9500 | 0.9421 | 0.9461 | 121 |
| accuracy | — | — | 0.9182 | 159 |
| macro avg | 0.8853 | 0.8921 | 0.8886 | 159 |
| weighted avg | 0.9191 | 0.9182 | 0.9186 | 159 |

### 1. `combo_pre0_mel40_fft2048__V2__s44` — `PTQ_INT8`

- Accuracy: **0.8868**
- Balanced accuracy: **0.8715**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 32 | 6 |
| Non-Asthma | 12 | 109 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7273 | 0.8421 | 0.7805 | 38 |
| Non-Asthma | 0.9478 | 0.9008 | 0.9237 | 121 |
| accuracy | — | — | 0.8868 | 159 |
| macro avg | 0.8375 | 0.8715 | 0.8521 | 159 |
| weighted avg | 0.8951 | 0.8868 | 0.8895 | 159 |

### 1. `combo_pre0_mel40_fft2048__V2__s44` — `QAT_INT8`

- Accuracy: **0.9119**
- Balanced accuracy: **0.8880**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 32 | 6 |
| Non-Asthma | 8 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8000 | 0.8421 | 0.8205 | 38 |
| Non-Asthma | 0.9496 | 0.9339 | 0.9417 | 121 |
| accuracy | — | — | 0.9119 | 159 |
| macro avg | 0.8748 | 0.8880 | 0.8811 | 159 |
| weighted avg | 0.9138 | 0.9119 | 0.9127 | 159 |

### 1. `combo_pre0_mel40_fft2048__V2__s44` — `PTQ_INT16x8`

- Accuracy: **0.9182**
- Balanced accuracy: **0.8921**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 32 | 6 |
| Non-Asthma | 7 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8205 | 0.8421 | 0.8312 | 38 |
| Non-Asthma | 0.9500 | 0.9421 | 0.9461 | 121 |
| accuracy | — | — | 0.9182 | 159 |
| macro avg | 0.8853 | 0.8921 | 0.8886 | 159 |
| weighted avg | 0.9191 | 0.9182 | 0.9186 | 159 |

## Trạng thái

- Đã có kết quả: **4/4** tổ hợp, bao gồm FP32 đối chứng.
- Báo cáo không tự thay đổi thứ tự ưu tiên checkpoint đã chuyển giao từ bước C.
- Validation có thể dùng để so sánh method lượng tử; historical Test chỉ dùng báo cáo sau khi phạm vi đã khóa.
- INT16x8 cần đường inference `int16_t`; không thay trực tiếp model INT8 hiện tại.
