# Báo cáo lượng tử hóa Frontend — Validation

- Plan SHA256: `5f65766e6f61863d01e1526c1314ba1e3f249769a2ea782b007ce8b3e84e1234`
- Split đánh giá: **Validation**
- Test accessed: **false**
- Thứ tự checkpoint được bàn giao từ phân tích bước C.

## Phạm vi checkpoint

| Ưu tiên | Vai trò | Trial | Variant | Input |
|---:|---|---|---|---|
| 1 | EXPLICIT | `combo_pre0_mel40_fft2048__V2__s44` | `combo_pre0_mel40_fft2048` | `40 × 129 × 1` |

## Kết quả Validation

| Ưu tiên | Trial | Method | Accuracy | Macro F1 | Asthma Recall | Non-Asthma Recall | Đổi nhãn so với FP32 | Kích thước (byte) | I/O |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | `combo_pre0_mel40_fft2048__V2__s44` | `KERAS_FP32` | 0.9740 | 0.9657 | 0.9737 | 0.9741 | 0 | 160355 | float32 → float32 |
| 1 | `combo_pre0_mel40_fft2048__V2__s44` | `PTQ_INT8` | 0.9286 | 0.9064 | 0.8947 | 0.9397 | 7 | 23144 | int8 → int8 |
| 1 | `combo_pre0_mel40_fft2048__V2__s44` | `QAT_INT8` | 0.9805 | 0.9740 | 0.9737 | 0.9828 | 3 | 22944 | int8 → int8 |
| 1 | `combo_pre0_mel40_fft2048__V2__s44` | `PTQ_INT16x8` | 0.9740 | 0.9657 | 0.9737 | 0.9741 | 0 | 26872 | int16 → int16 |

## Confusion matrix và classification report

Quy ước: nhãn `0 = Asthma`, nhãn `1 = Non-Asthma`, hàng là nhãn thật và cột là nhãn dự đoán.

### 1. `combo_pre0_mel40_fft2048__V2__s44` — `KERAS_FP32`

- Accuracy: **0.9740**
- Balanced accuracy: **0.9739**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 37 | 1 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9250 | 0.9737 | 0.9487 | 38 |
| Non-Asthma | 0.9912 | 0.9741 | 0.9826 | 116 |
| accuracy | — | — | 0.9740 | 154 |
| macro avg | 0.9581 | 0.9739 | 0.9657 | 154 |
| weighted avg | 0.9749 | 0.9740 | 0.9742 | 154 |

### 1. `combo_pre0_mel40_fft2048__V2__s44` — `PTQ_INT8`

- Accuracy: **0.9286**
- Balanced accuracy: **0.9172**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 7 | 109 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8293 | 0.8947 | 0.8608 | 38 |
| Non-Asthma | 0.9646 | 0.9397 | 0.9520 | 116 |
| accuracy | — | — | 0.9286 | 154 |
| macro avg | 0.8969 | 0.9172 | 0.9064 | 154 |
| weighted avg | 0.9312 | 0.9286 | 0.9295 | 154 |

### 1. `combo_pre0_mel40_fft2048__V2__s44` — `QAT_INT8`

- Accuracy: **0.9805**
- Balanced accuracy: **0.9782**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 37 | 1 |
| Non-Asthma | 2 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9487 | 0.9737 | 0.9610 | 38 |
| Non-Asthma | 0.9913 | 0.9828 | 0.9870 | 116 |
| accuracy | — | — | 0.9805 | 154 |
| macro avg | 0.9700 | 0.9782 | 0.9740 | 154 |
| weighted avg | 0.9808 | 0.9805 | 0.9806 | 154 |

### 1. `combo_pre0_mel40_fft2048__V2__s44` — `PTQ_INT16x8`

- Accuracy: **0.9740**
- Balanced accuracy: **0.9739**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 37 | 1 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9250 | 0.9737 | 0.9487 | 38 |
| Non-Asthma | 0.9912 | 0.9741 | 0.9826 | 116 |
| accuracy | — | — | 0.9740 | 154 |
| macro avg | 0.9581 | 0.9739 | 0.9657 | 154 |
| weighted avg | 0.9749 | 0.9740 | 0.9742 | 154 |

## Trạng thái

- Đã có kết quả: **4/4** tổ hợp, bao gồm FP32 đối chứng.
- Báo cáo không tự thay đổi thứ tự ưu tiên checkpoint đã chuyển giao từ bước C.
- Validation có thể dùng để so sánh method lượng tử; historical Test chỉ dùng báo cáo sau khi phạm vi đã khóa.
- INT16x8 cần đường inference `int16_t`; không thay trực tiếp model INT8 hiện tại.
