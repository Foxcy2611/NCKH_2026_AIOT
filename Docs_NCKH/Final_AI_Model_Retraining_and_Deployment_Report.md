# Báo cáo chốt mô hình AI sau retraining và triển khai thử nghiệm trên ESP32-S3

## 1. Mục tiêu

Tài liệu này tổng hợp kết quả cuối của quá trình:

```text
Dataset V2
→ retrain các kiến trúc V1–V5
→ lượng tử hóa
→ profiling TFLite Micro trên ESP32-S3
→ kiểm tra RAW PCM16 → preprocessing C++ → inference
→ chọn Final AI Model
```

Mục tiêu là lựa chọn mô hình phù hợp nhất để thay thế model cũ và dùng làm model chuẩn cho Patient Node.

---

## 2. Hai ứng viên cuối

Sau Phase 2 và Phase 3, hai model còn lại để đánh giá triển khai là:

### V1 — DS-CNN dùng SeparableConv2D

```text
SeparableConv2D 16
→ BatchNorm
→ MaxPool
→ SeparableConv2D 32
→ BatchNorm
→ MaxPool
→ SeparableConv2D 64
→ BatchNorm
→ MaxPool
→ Flatten
→ Dense 64
→ Dropout
→ Dense 1
```

### V5 — Standard CNN dùng Conv2D

V5 giữ gần như cùng macro-topology với V1 nhưng thay các `SeparableConv2D` bằng `Conv2D` chuẩn.

Do đó, V1 và V5 tạo thành một cặp so sánh phù hợp giữa:

```text
độ chính xác
↔
chi phí tính toán trên MCU
```

---

## 3. Kết quả sau PTQ Full INT8

| Chỉ số | V1 PTQ INT8 | V5 PTQ INT8 |
|---|---:|---:|
| Test Accuracy | **93.71%** | 93.08% |
| Asthma Precision | **83.33%** | 81.40% |
| Asthma Recall | **92.11%** | **92.11%** |
| Asthma F1 | **87.50%** | 86.42% |
| Non-Asthma bị báo nhầm Asthma | **7** | 8 |
| TFLite INT8 size | **543,976 B** | 560,776 B |

Nhận xét:

- V1 và V5 giữ cùng Asthma Recall `92.11%`.
- V1 nhỉnh hơn V5 về Accuracy, Asthma Precision và Asthma F1.
- V1 nhỏ hơn V5 `16,800 B`, tương đương khoảng `3%`.
- V1 PTQ INT8 là model có kết quả phân loại tốt nhất trong các biến thể đã kiểm tra.

Điểm đáng chú ý là V5 từng tốt hơn V1 ở FP32, nhưng sau PTQ INT8 thì V1 lại nhỉnh hơn.

> **Việc lựa chọn kiến trúc chỉ dựa trên độ chính xác FP32 có thể chưa phản ánh tối ưu triển khai Edge AI. Mô hình nên được đánh giá sau lượng tử hóa và trên phần cứng đích trước khi đưa ra quyết định cuối.**

---

## 4. Static profiling trên ESP32-S3

Điều kiện benchmark:

```text
MCU        : ESP32-S3
CPU        : 240 MHz
Runtime    : TensorFlow Lite Micro
Resolver   : AllOpsResolver
Input      : tensor INT8 đã preprocess bằng Python
```

Kết quả:

| Chỉ số | V1 PTQ INT8 | V5 PTQ INT8 |
|---|---:|---:|
| Model size | **543,976 B** | 560,776 B |
| Tensor Arena used | 268,772 B | **267,844 B** |
| Tensor Arena cấu hình deploy | 280,000 B | 280,000 B |
| Peak RAM estimate | 269,060 B | **268,132 B** |
| Invoke latency min | **1870.565 ms** | 7884.584 ms |
| Invoke latency avg | **1870.816 ms** | 7884.750 ms |
| Invoke latency max | **1871.251 ms** | 7885.012 ms |
| Stability | PASS — 36/36 | PASS — 36/36 |
| Operator compatibility | PASS | PASS |
| Static sample result | 11/12 | 11/12 |

### 4.1. Tensor Arena

Hai model sử dụng lượng Tensor Arena gần như tương đương:

```text
V1: 268,772 B
V5: 267,844 B
```

Do ESP32-S3 có PSRAM đủ lớn, không tối ưu sát biên. Cấu hình triển khai được khóa ở:

```text
Tensor Arena = 280,000 B
```

Mục tiêu là giữ safety margin thay vì tiết kiệm vài kilobyte và tăng rủi ro thiếu bộ nhớ khi firmware hoàn chỉnh phức tạp hơn.

### 4.2. Latency

Khác biệt lớn nhất nằm ở thời gian `Invoke()`:

```text
V1: ~1.871 s
V5: ~7.885 s
```

V1 nhanh hơn V5 khoảng:

```text
7.885 / 1.871 ≈ 4.21×
```

Như vậy, lợi thế lý thuyết của `SeparableConv2D` đã chuyển thành lợi ích thực tế rõ rệt trên ESP32-S3.

---

## 5. Kiểm tra RAW PCM16 → preprocessing C++ → model

Sau static profiling, cùng bộ 12 WAV cố định được chuyển thành RAW PCM16 header.

ESP32-S3 tự thực hiện:

```text
RAW PCM16
→ normalize audio
→ Butterworth 100–2000 Hz
→ pre-emphasis
→ Mel extraction
→ dB + TOP_DB clip
→ normalize feature
→ quantize INT8
→ TFLM Invoke()
```

Đây là phép thử quan trọng vì preprocessing không còn được thực hiện sẵn bằng Python.

### 5.1. V1

Kết quả:

```text
Đúng nhãn thật                : 11/12
Cùng prediction Python V1     : 12/12
Output INT8 trùng tuyệt đối   : 9/12
Max raw difference            : 19
Max probability difference    : 0.074218750
```

Ba sample không trùng raw output tuyệt đối vẫn giữ nguyên quyết định cuối.

Điều này cho thấy implementation C++ và Python có sai số số học nhỏ ở một số mẫu, nhưng **decision parity đạt 12/12** trên bộ kiểm tra cố định.

### 5.2. V5

Kết quả:

```text
Đúng nhãn thật: 11/12
```

V5 chạy thành công toàn bộ pipeline C++ và inference trên cùng bộ RAW PCM16.

Không có Python reference riêng cho V5 trong bộ raw test hiện tại, do header reference được sinh cho V1. Tuy vậy, V5 không tạo ra lợi thế phân loại nào trên bộ 12 mẫu để bù cho latency cao hơn đáng kể.

---

## 6. So sánh cuối V1 và V5

| Tiêu chí | V1 PTQ INT8 | V5 PTQ INT8 | Ưu thế |
|---|---:|---:|---|
| Test Accuracy | **93.71%** | 93.08% | V1 |
| Asthma Recall | 92.11% | 92.11% | Hòa |
| Asthma F1 | **87.50%** | 86.42% | V1 |
| Model size | **543,976 B** | 560,776 B | V1 |
| Tensor Arena used | 268,772 B | **267,844 B** | Gần như tương đương |
| Avg Invoke latency | **1870.816 ms** | 7884.750 ms | **V1 ~4.21× nhanh hơn** |
| Static stability | PASS | PASS | Hòa |
| Operator compatibility | PASS | PASS | Hòa |
| RAW C++ pipeline | PASS | PASS | Hòa |
| Python decision parity | **12/12** | N/A | V1 đã xác minh |

V5 chỉ nhỉnh hơn V1 một lượng rất nhỏ ở Tensor Arena, khoảng `928 B`, không có ý nghĩa thực tế so với chênh lệch latency.

Ngược lại, V1:

- đạt metric phân loại tốt hơn;
- model nhỏ hơn;
- chạy nhanh hơn khoảng `4.21×`;
- đã xác minh prediction parity giữa Python và preprocessing C++ trên ESP32-S3.

---

## 7. Quyết định cuối

### Final AI Model

```text
Model architecture : V1 — DS-CNN / SeparableConv2D
Quantization       : PTQ Full INT8
Decision threshold : 0.5
Tensor Arena       : 280,000 B
Input shape        : [1, 64, 129, 1]
Input dtype        : INT8
Input scale        : 0.0039215689
Input zero point   : -128
Output dtype       : INT8
Output scale       : 0.00390625
Output zero point  : -128
```

**V1 PTQ INT8 được chọn làm Final AI Model cho Patient Node.**

V5 PTQ INT8 được giữ lại dưới vai trò:

```text
reference / fallback model
```

và không còn là ứng viên triển khai chính.

---

## 8. Kết luận retraining

Quá trình retraining có thể xem là **thành công và hoàn tất ở cấp độ AI model**.

Model mới đã vượt qua toàn bộ chuỗi xác minh:

```text
Dataset V2
    ↓
Training
    ↓
Architecture comparison
    ↓
PTQ Full INT8
    ↓
Laptop Test evaluation
    ↓
ESP32-S3 static profiling
    ↓
RAW PCM16
    ↓
C++ preprocessing
    ↓
TFLM inference
    ↓
FINAL AI MODEL
```

Kết quả cho thấy model cuối không chỉ có chất lượng phân loại tốt hơn mà còn phù hợp hơn với điều kiện MCU.

> **Kết luận quan trọng:** V5 đạt kết quả FP32 tốt hơn trong giai đoạn huấn luyện, nhưng V1 sau PTQ INT8 lại đạt metric phân loại tốt hơn và có latency thấp hơn khoảng 4.21 lần trên ESP32-S3. Điều này chứng minh rằng model tốt nhất trên máy tính không nhất thiết là model tốt nhất để triển khai Edge AI. Việc lựa chọn cuối cần xét đồng thời Accuracy, Recall/F1, quantization behavior, memory và latency trên phần cứng đích.

---

## 9. Trạng thái sau khi chốt model

```text
AI retraining             DONE
Architecture selection    DONE
Quantization              DONE
ESP32 static profiling    DONE
C++ preprocessing test    DONE
Final AI Model            FROZEN

Next:
Live INMP441 acquisition / integration
→ 3_Model_Complete
→ Patient Node CHECK / MONITOR / OLED / MAX30102 / ESP-NOW
```

Phần live microphone và tích hợp toàn Patient Node từ thời điểm này được xem là **deployment/integration validation**, không còn là vòng lựa chọn lại kiến trúc model, trừ khi phát hiện lỗi nghiêm trọng bắt nguồn trực tiếp từ model.
