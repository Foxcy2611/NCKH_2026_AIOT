# Nhận xét kết quả lượng tử hóa và lựa chọn mô hình triển khai

## 1. Phạm vi đánh giá

Sau giai đoạn xây dựng lại dữ liệu, tiền xử lý và quy trình huấn luyện, hai kiến trúc có kết quả tốt nhất và có ý nghĩa nhất cho bài toán triển khai Edge AI là:

- **V1 — DS-CNN dùng `SeparableConv2D`**
- **V5 — Standard CNN dùng `Conv2D`**

Hai mô hình có macro-topology gần như tương đương:

```text
Conv block 16
→ BatchNorm
→ MaxPool

Conv block 32
→ BatchNorm
→ MaxPool

Conv block 64
→ BatchNorm
→ MaxPool

Flatten
→ Dense 64
→ Dropout
→ Dense 1
```

Khác biệt chính nằm ở phần convolution:

```text
V1: SeparableConv2D
V5: Conv2D chuẩn
```

Điều này làm V1 và V5 trở thành một cặp so sánh phù hợp để đánh giá trade-off giữa:

```text
độ chính xác
↔
chi phí tính toán trên MCU
```

Các kiến trúc V2, V3 và V4 không tiếp tục được đưa sang vòng lượng tử hóa vì kết quả FP32 trước đó không tạo ra lợi thế đủ lớn so với V1/V5. Việc tiếp tục lượng tử toàn bộ các kiến trúc này sẽ làm tăng số lượng thí nghiệm nhưng không bổ sung nhiều thông tin cho quyết định triển khai cuối.

---

## 2. Xử lý V0

V0 là mô hình thử nghiệm ban đầu trước khi pipeline dữ liệu và huấn luyện hiện tại được hoàn thiện.

V0 không còn được xem là một ứng viên trong quá trình lựa chọn mô hình và **không cần đưa vào bảng benchmark cuối**.

Có thể loại V0 khỏi các artifact đang sử dụng trong Phase 2/Phase 3 vì:

- dữ liệu hiện tại đã được xây dựng lại;
- split Train/Validation/Test đã được kiểm soát rõ hơn;
- preprocessing và normalization đã được chuẩn hóa;
- kiến trúc V1–V5 được huấn luyện lại trên pipeline mới;
- V1 và V5 đã cung cấp đủ hai điểm so sánh có giá trị cho quyết định Edge AI.

Nếu repository đã dùng Git, lịch sử commit là đủ để truy vết giai đoạn prototype. Báo cáo chính không cần dành một phép đánh giá định lượng riêng cho V0.

Nếu cần nhắc đến lịch sử phát triển, chỉ cần mô tả ngắn:

> Mô hình thử nghiệm ban đầu được sử dụng để xác định các hạn chế của dữ liệu và quy trình huấn luyện. Sau khi hoàn thiện lại dataset, preprocessing và phương pháp đánh giá, các kiến trúc V1–V5 được huấn luyện lại và sử dụng cho quá trình lựa chọn mô hình chính thức.

---

# 3. Kết quả V1 trước và sau lượng tử hóa

## 3.1. FP32 baseline

V1 FP32 đạt:

| Chỉ số | V1 FP32 |
|---|---:|
| Accuracy | 89.31% |
| Asthma Precision | 71.43% |
| Asthma Recall | 92.11% |
| Asthma F1 | 80.46% |

Confusion matrix:

```text
[[35,  3],
 [14,107]]
```

Điểm đáng chú ý là V1 đã giữ được Asthma Recall khá cao, nhưng còn nhiều Non-Asthma bị phân loại nhầm thành Asthma.

---

## 3.2. PTQ INT8

Sau PTQ Full INT8:

| Chỉ số | V1 PTQ INT8 |
|---|---:|
| Accuracy | **93.71%** |
| Asthma Precision | **83.33%** |
| Asthma Recall | **92.11%** |
| Asthma F1 | **87.50%** |

Confusion matrix:

```text
[[35,  3],
 [ 7,114]]
```

So với FP32:

```text
Asthma bị bỏ sót:
3 → 3

Non-Asthma bị báo nhầm Asthma:
14 → 7
```

PTQ INT8 làm thay đổi 7/159 prediction và trong tập Test hiện tại:

```text
7 thay đổi có lợi
0 thay đổi bất lợi
```

Như vậy, Accuracy tăng:

```text
89.31%
   ↓
93.71%
```

mà Asthma Recall vẫn được giữ nguyên ở `92.11%`.

Đây là kết quả đặc biệt đáng chú ý vì sự cải thiện không đến từ việc đánh đổi khả năng phát hiện Asthma để lấy Accuracy tổng thể.

---

# 4. Kết quả V5 trước và sau lượng tử hóa

## 4.1. FP32 baseline

V5 FP32 đạt:

| Chỉ số | V5 FP32 |
|---|---:|
| Accuracy | 91.82% |
| Asthma Precision | 77.78% |
| Asthma Recall | 92.11% |
| Asthma F1 | 84.34% |

Confusion matrix:

```text
[[35,  3],
 [10,111]]
```

Ở trạng thái FP32, V5 tốt hơn V1 rõ rệt về Accuracy và F1.

---

## 4.2. PTQ INT8

Sau PTQ Full INT8:

| Chỉ số | V5 PTQ INT8 |
|---|---:|
| Accuracy | **93.08%** |
| Asthma Precision | **81.40%** |
| Asthma Recall | **92.11%** |
| Asthma F1 | **86.42%** |

Confusion matrix:

```text
[[35,  3],
 [ 8,113]]
```

PTQ làm thay đổi 2/159 prediction và cả hai thay đổi đều có lợi trong tập Test hiện tại.

---

# 5. So sánh trực tiếp V1 PTQ INT8 và V5 PTQ INT8

Đây là phép so sánh quan trọng nhất cho quyết định triển khai.

| Chỉ số | V1 — SepConv PTQ INT8 | V5 — Conv PTQ INT8 |
|---|---:|---:|
| Accuracy | **93.71%** | 93.08% |
| Asthma Precision | **83.33%** | 81.40% |
| Asthma Recall | **92.11%** | **92.11%** |
| Asthma F1 | **87.50%** | 86.42% |
| Non-Asthma báo nhầm Asthma | **7** | 8 |
| TFLite INT8 size | **543,976 B** | 560,776 B |
| Parameters FP32 | **527,994** | 548,161 |

Một điểm rất đáng chú ý:

```text
FP32:
V5 > V1

sau PTQ INT8:
V1 ≳ V5
```

V5 từng là model tốt hơn nếu chỉ nhìn vào kết quả FP32, nhưng sau khi đưa điều kiện deployment vào phép đánh giá, V1 trở thành ứng viên rất mạnh.

---

# 6. Vì sao parameter count chưa phản ánh đúng lợi thế của V1?

V1 có khoảng:

```text
527,994 parameters
```

V5 có khoảng:

```text
548,161 parameters
```

Chênh lệch parameter chỉ khoảng:

```text
20,167 parameters
≈ 3.82%
```

Nếu chỉ nhìn kích thước model, hai kiến trúc có vẻ gần nhau.

Nguyên nhân là phần:

```text
Flatten → Dense64
```

chiếm phần lớn parameter ở cả hai model.

Tuy nhiên, phần convolution của V1 dùng depthwise-separable convolution, trong khi V5 dùng convolution chuẩn.

Với input `(64, 129, 1)` và các channel `16 → 32 → 64`, ước tính MAC lý thuyết:

| Phần | V1 SepConv | V5 Conv2D |
|---|---:|---:|
| 3 convolution blocks | ~2.746 M MAC | ~20.063 M MAC |
| Dense classifier | ~0.524 M MAC | ~0.524 M MAC |
| **Tổng gần đúng** | **~3.270 M MAC** | **~20.588 M MAC** |

Tỷ lệ lý thuyết:

```text
V5 / V1 ≈ 6.30× tổng MAC
```

Riêng ba convolution block:

```text
V5 / V1 ≈ 7.31×
```

Đây là **ước tính lý thuyết**, chưa phải benchmark trên ESP32-S3. Runtime thực tế còn phụ thuộc vào:

- TensorFlow Lite Micro kernel;
- SIMD/vectorization;
- cache và memory access;
- tensor allocation;
- operator implementation của `SeparableConv2D`;
- clock và cấu hình ESP32-S3.

Tuy nhiên, chênh lệch này đủ lớn để V1 trở thành ứng viên deployment ưu tiên cần benchmark trước.

---

# 7. Phân tích probability shift

Để đánh giá sâu hơn ảnh hưởng của lượng tử hóa, sử dụng:

```text
|Δp| = |p_quantized - p_TFLite_FP32|
```

## 7.1. V1

| Variant | Mean \|Δp\| | Median \|Δp\| | P95 \|Δp\| | Max \|Δp\| | Prediction đổi |
|---|---:|---:|---:|---:|---:|
| PTQ INT8 | 0.06399 | 0.00389 | 0.43398 | 0.96735 | 7/159 |
| QAT INT8 | 0.04271 | 0.00390 | 0.33466 | 0.70439 | 5/159 |
| PTQ INT16x8 | **0.00130** | **0.00003** | **0.00809** | **0.02916** | **0/159** |

V1 PTQ INT8 có median deviation rất nhỏ nhưng một tail tương đối lớn.

Điều này nghĩa là:

- phần lớn sample gần như không đổi;
- một số hard sample thay đổi probability rất mạnh;
- trong tập Test hiện tại, 7 sample vượt decision boundary đều thay đổi theo hướng đúng.

Do đó không nên diễn giải rằng PTQ nói chung “làm model thông minh hơn”.

Cách viết chính xác hơn là:

> Trên tập Test hiện tại, perturbation do PTQ INT8 đã làm thay đổi một số output của V1 theo hướng có lợi, giảm số Non-Asthma bị phân loại nhầm thành Asthma từ 14 xuống 7 trong khi không làm tăng số Asthma bị bỏ sót.

---

## 7.2. V5

| Variant | Mean \|Δp\| | Median \|Δp\| | P95 \|Δp\| | Max \|Δp\| | Prediction đổi |
|---|---:|---:|---:|---:|---:|
| PTQ INT8 | 0.01121 | 0.00391 | 0.03837 | 0.36348 | 2/159 |
| QAT INT8 | 0.04121 | 0.00391 | 0.26458 | 0.95856 | 5/159 |
| PTQ INT16x8 | **0.00156** | **0.00003** | **0.01124** | **0.06485** | **0/159** |

V5 PTQ INT8 thay đổi nhẹ hơn V1 nhưng vẫn tạo ra hai thay đổi có lợi.

---

# 8. Nhận xét về QAT

QAT được xem là một hướng độc lập với PTQ, không phải bước bắt buộc sau PTQ.

Kết quả:

| Model | FP32 | QAT INT8 |
|---|---:|---:|
| V1 | 89.31% | 88.68% |
| V5 | 91.82% | 89.94% |

QAT không cải thiện kết quả của cả hai kiến trúc trong cấu hình hiện tại.

Với V1:

```text
FP32 CM:
[[35, 3],
 [14,107]]

QAT CM:
[[35, 3],
 [15,106]]
```

Với V5:

```text
FP32 CM:
[[35, 3],
 [10,111]]

QAT CM:
[[34, 4],
 [12,109]]
```

Do đó, QAT không được ưu tiên cho deployment hiện tại.

Điều này cũng là một kết quả nghiên cứu có giá trị:

> Kỹ thuật phức tạp hơn không mặc định tạo ra model tốt hơn. Với dataset và kiến trúc hiện tại, PTQ INT8 vừa đơn giản hơn vừa đạt kết quả Test tốt hơn QAT INT8.

---

# 9. Nhận xét về PTQ INT16x8

Cả V1 và V5 đều cho:

```text
0/159 prediction thay đổi so với FP32
```

INT16x8 vì vậy thể hiện khả năng bảo toàn behavior FP32 rất tốt trên tập Test hiện tại.

Tuy nhiên:

- V1 INT16x8 vẫn chỉ đạt Accuracy bằng V1 FP32: `89.31%`;
- V5 INT16x8 vẫn chỉ đạt Accuracy bằng V5 FP32: `91.82%`;
- cả hai đều thấp hơn bản PTQ INT8 tương ứng.

Vì vậy INT16x8 được giữ như một **reference quantization variant**, nhưng không phải ứng viên deployment ưu tiên tại thời điểm này.

---

# 10. Kết luận lựa chọn model deployment

## 10.1. Kết luận từ benchmark trên laptop

Nếu chỉ xét kết quả model hiện tại:

```text
V1 PTQ INT8
Accuracy       = 93.71%
Asthma Recall  = 92.11%
Asthma F1      = 87.50%
Size           = 543,976 B
```

là biến thể tốt nhất trong các mô hình đã kiểm tra.

V5 PTQ INT8 đứng rất gần:

```text
Accuracy       = 93.08%
Asthma Recall  = 92.11%
Asthma F1      = 86.42%
Size           = 560,776 B
```

Nhưng V1 còn có lợi thế kiến trúc `SeparableConv2D`, cho chi phí MAC lý thuyết thấp hơn đáng kể.

Do đó:

> **V1 PTQ INT8 được chọn làm deployment candidate chính cho ESP32-S3.**

V5 PTQ INT8 được giữ làm:

> **reference/fallback candidate** để benchmark trực tiếp trên target.

---

### 10.2. Benchmark static trên ESP32-S3

Hai model **V1 PTQ INT8** và **V5 PTQ INT8** được benchmark trong cùng điều kiện trên ESP32-S3 ở **240 MHz**, sử dụng PSRAM và `AllOpsResolver`. Phép thử sử dụng các tensor INT8 đã được Python tiền xử lý sẵn, do đó kết quả tập trung vào **khả năng chạy TFLM, bộ nhớ và thời gian `Invoke()`**, chưa bao gồm chi phí preprocessing C++.

| Chỉ số | V1 PTQ INT8 | V5 PTQ INT8 |
|---|---:|---:|
| Model size | **543,976 B** | 560,776 B |
| Tensor Arena used | 268,772 B | **267,844 B** |
| Tensor Arena ưu tiên cấu hình khi deploy | **280,000 B** | **280,000 B** |
| Headroom so với arena used | 11,228 B (~4.2%) | 12,156 B (~4.5%) |
| Peak RAM estimate | 269,060 B | **268,132 B** |
| Invoke latency min | **1870.565 ms** | 7884.584 ms |
| Invoke latency trung bình | **1870.816 ms** | 7884.750 ms |
| Invoke latency max | **1871.251 ms** | 7885.012 ms |
| Stability | PASS — 36/36 | PASS — 36/36 |
| Operator compatibility | PASS | PASS |
| Static sample result | 11/12 | 11/12 |

V1 và V5 có nhu cầu Tensor Arena gần như tương đương; V5 thậm chí sử dụng ít hơn khoảng **928 B**, nên bộ nhớ không tạo ra khác biệt đáng kể giữa hai kiến trúc. Vì Tensor Arena quan sát được của cả hai model đều dưới 270 kB, hệ thống chọn cấu hình **280,000 B** để giữ một khoảng an toàn thay vì tối ưu sát biên.

Khác biệt lớn nhất nằm ở thời gian suy luận. V1 đạt trung bình **1870.816 ms**, trong khi V5 cần **7884.750 ms** cho một lần `Invoke()`. Như vậy, trên ESP32-S3 trong cấu hình thử nghiệm hiện tại, **V1 nhanh hơn khoảng 4.21 lần** so với V5. Kết quả này cho thấy lợi thế tính toán của `SeparableConv2D` trong V1 đã chuyển thành lợi ích thực tế trên phần cứng đích, trong khi kích thước model và yêu cầu bộ nhớ vẫn tương đương.

> **Kết luận:** Kết hợp với kết quả Phase 3, nơi V1 PTQ INT8 đạt Accuracy 93.71%, Asthma Recall 92.11% và Asthma F1 87.50%, V1 hiện là ứng viên triển khai ưu tiên. V5 vẫn được giữ làm model tham chiếu/fallback, nhưng latency cao hơn khoảng 4.21 lần khiến V1 có lợi thế rõ rệt cho triển khai thời gian thực trên ESP32-S3. Quyết định cuối được khóa sau khi V1 tiếp tục vượt qua bước `2_Test_Model_LiveMic` với preprocessing C++ và dữ liệu microphone thực.

> **Lưu ý:** Kết quả `11/12` ở static profiling chỉ là smoke/parity test trên một bộ mẫu nhỏ, không thay thế Accuracy chính thức trên tập Test 159 mẫu.


---

# 11. Kết luận quan trọng cho báo cáo

Đây là kết luận có giá trị nhất rút ra từ quá trình lựa chọn model:

> **Kết quả cho thấy việc lựa chọn kiến trúc chỉ dựa trên độ chính xác FP32 có thể chưa phản ánh tối ưu triển khai Edge AI. Mặc dù V5 đạt kết quả FP32 cao hơn, V1 sử dụng depthwise-separable convolution sau PTQ INT8 không những bảo toàn mà còn cải thiện hiệu năng phân loại trên tập Test hiện tại, đồng thời có tiềm năng giảm đáng kể chi phí tính toán trên MCU. Vì vậy, lựa chọn model triển khai cần được thực hiện sau cả giai đoạn lượng tử hóa và benchmark trên phần cứng đích, thay vì chỉ dựa trên kết quả FP32 trên máy tính.**

Kết luận này phản ánh đúng bản chất của bài toán Edge AI:

```text
Model tốt nhất trên laptop
không nhất thiết
=
Model tốt nhất để deploy
```

Thay vào đó cần tối ưu đồng thời:

```text
Accuracy / Recall / F1
        +
Model size
        +
Compute cost
        +
RAM
        +
Latency
        +
Operator support
        +
độ ổn định trên target
```

---

# 12. Quyết định experimental scope sau Phase 3

Sau kết quả V1 và V5, phạm vi thí nghiệm được thu gọn như sau:

```text
V0
└── loại khỏi benchmark chính

V2 / V3 / V4
└── dừng ở Phase 2, không tiếp tục quantization

V1
└── PTQ INT8 → deployment candidate chính

V5
└── PTQ INT8 → reference/fallback candidate

QAT
└── không ưu tiên

INT16x8
└── reference về khả năng bảo toàn FP32
```

Flow tiếp theo:

```text
V1 PTQ INT8 ─┐
             ├──> ESP32-S3 benchmark
V5 PTQ INT8 ─┘
                    │
                    ├── latency
                    ├── Tensor Arena
                    ├── peak RAM
                    ├── Flash
                    ├── operator compatibility
                    └── stability
                          │
                          ▼
                   FINAL MODEL FREEZE
```

---

# 13. Câu kết có thể dùng trực tiếp trong báo cáo

> Qua quá trình huấn luyện và lượng tử hóa, V1 và V5 được xác định là hai kiến trúc có giá trị thực tiễn nhất. V5 cho kết quả FP32 tốt hơn, tuy nhiên sau PTQ INT8, V1 đạt Accuracy 93.71%, Asthma Recall 92.11% và Asthma F1 87.50%, nhỉnh hơn V5 PTQ INT8 trong khi sử dụng depthwise-separable convolution. Kết quả này cho thấy đánh giá mô hình Edge AI không nên dừng ở độ chính xác FP32, mà cần xem xét đồng thời khả năng lượng tử hóa và chi phí triển khai trên phần cứng đích. Vì vậy, V1 PTQ INT8 được chọn làm ứng viên triển khai chính trên ESP32-S3, còn V5 PTQ INT8 được giữ làm mô hình tham chiếu/fallback cho vòng benchmark phần cứng cuối cùng.
