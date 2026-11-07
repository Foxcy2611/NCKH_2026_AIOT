# ĐẶC TẢ CÁC HƯỚNG MỞ RỘNG — PATIENT NODE / EDGE AI V2+

> Tài liệu này mô tả các hướng mở rộng sau khi pipeline cơ sở đã chạy hoàn chỉnh:
>
> `Dataset → Train DS-CNN → Quantization INT8 → TFLite Micro → Deploy ESP32-S3 → Inference thực tế`.
>
> Mục đích là tạo một khung thí nghiệm và phần Future Work có thể dùng trong báo cáo; không yêu cầu phải triển khai toàn bộ.

<!-- TOC_START -->
## Mục lục

### Nhóm A — Model, Quantization và Front-End
- [1. Nguyên tắc mở rộng](#ext-1)
- [2. So sánh INT8 và INT16x8](#ext-2)
- [3. PTQ INT8 và QAT INT8](#ext-3)
- [4. DS-CNN model scaling](#ext-4)
- [5. DSP / Audio Front-End Ablation](#ext-5)
- [6. Mel Spectrogram Ablation](#ext-6)

### Nhóm B — Dataset, Generalization và Post-processing
- [7. Dataset Ablation](#ext-7)
- [8. Real-World Challenge Set](#ext-8)
- [9. Playback-domain vs Direct-domain](#ext-9)
- [10. Threshold và vùng UNSURE](#ext-10)
- [11. MONITOR Voting Strategy](#ext-11)
- [12. Quality Gate Ablation](#ext-12)
- [13. VAD mở rộng](#ext-13)
- [14. Adaptive Quality / Environment-aware Front-End](#ext-14)
- [15. OOD / Unknown Detection](#ext-15)

### Nhóm C — Tối ưu triển khai MCU
- [16. Model Compression ngoài Quantization](#ext-16)
- [17. Kernel Optimization](#ext-17)
- [18. Inference Pipeline Optimization](#ext-18)
- [19. Power Consumption](#ext-19)
- [20. Latency Breakdown](#ext-20)
- [21. Memory Profiling](#ext-21)
- [22. Long-term Inference Stability](#ext-22)
- [23. Network Robustness](#ext-23)

### Nhóm D — Hướng phát triển dài hạn
- [24. Sensor Fusion với MAX30102](#ext-24)
- [25. Multi-class Classification](#ext-25)
- [26. Personalization](#ext-26)

### Nhóm E — Cách chọn và trình bày thí nghiệm
- [27. 5 thí nghiệm nên ưu tiên](#ext-27)
- [28. Ma trận ưu tiên](#ext-28)
- [29. Cấu trúc phần Hướng mở rộng trong báo cáo](#ext-29)
- [30. Quy tắc khi báo cáo experiment](#ext-30)
- [31. Kết luận](#ext-31)

<!-- TOC_END -->


---

<a id="ext-1"></a>
## 1. Nguyên tắc mở rộng

Trước khi thử hướng mới, đóng băng baseline hiện tại:

```text
Baseline V2
├── Dataset / split cố định
├── DSP cố định
├── Mel Spectrogram cố định
├── DS-CNN cố định
├── PTQ INT8
├── threshold / UNSURE cố định
└── firmware deploy cố định
```

Mỗi experiment chỉ nên thay đổi **một nhóm biến chính**. Nếu thử `INT8 → INT16x8` thì phải giữ nguyên dataset, split, DSP, Mel, DS-CNN và checkpoint FP32.

---

<a id="ext-2"></a>
# 2. So sánh INT8 và INT16x8

Baseline hiện tại là **Full Integer INT8**. Hướng mở rộng trực tiếp nhất:

```text
INT8
vs
INT16x8
```

Trong INT16x8, activation dùng độ rộng lớn hơn còn weight vẫn giữ ở int8.

### Cần so sánh

| Chỉ số | FP32 | INT8 | INT16x8 |
|---|---:|---:|---:|
| Accuracy | | | |
| Asthma Precision | | | |
| Asthma Recall | | | |
| Asthma F1 | | | |
| Non-Asthma F1 | | | |
| Model size | | | |
| Tensor arena | | | |
| Inference latency | | | |
| Flash usage | | | |
| RAM usage | | | |

### Câu hỏi nghiên cứu

> INT16x8 có giữ được Recall/F1 của Asthma tốt hơn INT8 hay không, và mức cải thiện đó có đáng đổi lấy RAM/latency lớn hơn trên ESP32-S3 hay không?

**=> Trạng thái: Hoàn thành** - Truy cập tại đây [So sánh Quanzation](/AI_Training_Model/Phase3_Quantization_Model/Report_V1_v_V5_Analysis.md)

---

<a id="ext-3"></a>
# 3. PTQ INT8 và QAT INT8

Baseline:

```text
FP32 model
→ Post-Training Quantization
→ INT8
```


### PTQ là gì?

`PTQ = Post-Training Quantization`.

Luồng của PTQ:

```text
Train model FP32 hoàn chỉnh
        ↓
Model đã hội tụ
        ↓
Dùng representative dataset để calibration
        ↓
Quantize
        ↓
INT8 / INT16x8 model
```

Tức là **quantization xảy ra sau khi model đã train xong**. Model FP32 không được huấn luyện để tự thích nghi với sai số lượng tử hóa.

Ưu điểm:

- đơn giản;
- nhanh;
- không cần train lại toàn bộ model;
- rất phù hợp để tạo baseline TinyML.

Nhược điểm:

- nếu model nhạy với quantization thì Accuracy/Recall/F1 có thể giảm sau khi chuyển từ FP32 sang integer.

### QAT là gì?

`QAT = Quantization-Aware Training`.

Luồng khái niệm:

```text
Model FP32 đã train
        ↓
Fine-tune / train với fake-quantization
        ↓
Model học trong điều kiện mô phỏng lượng tử hóa
        ↓
Convert thành INT8
```

Trong lúc QAT, phép tính train vẫn dùng cơ chế phù hợp cho training, nhưng các bước **fake quantization** mô phỏng việc giá trị sẽ bị làm tròn và giới hạn như khi chạy integer. Vì vậy model có cơ hội điều chỉnh weight để chịu được quantization tốt hơn.

Ưu điểm:

- có khả năng giảm quantization loss;
- hữu ích khi PTQ làm giảm metric đáng kể.

Nhược điểm:

- pipeline phức tạp hơn;
- cần thêm thời gian fine-tune/train;
- không bảo đảm luôn tốt hơn PTQ nếu baseline INT8 vốn đã gần FP32.

### Hiểu nhanh trong project này

```text
PTQ:
DS-CNN FP32 đã train
→ quantize sau cùng
→ INT8
→ đây là baseline hiện tại

QAT:
DS-CNN FP32
→ fine-tune có mô phỏng INT8
→ convert INT8
→ so với PTQ INT8
```

Do đó QAT và PTQ **không phải hai kiểu model khác nhau**. Chúng là **hai chiến lược tạo model quantized**.

| Tiêu chí | PTQ | QAT |
|---|---|---|
| Quantization xảy ra | Sau training | Được mô phỏng trong training/fine-tune |
| Cần train lại | Không | Có |
| Độ phức tạp | Thấp | Cao hơn |
| Thời gian thực hiện | Nhanh | Lâu hơn |
| Khi nên dùng | Baseline / metric giữ tốt | PTQ làm giảm metric đáng kể |
| Output triển khai có thể là | INT8 | INT8 |


Hướng mở rộng:

```text
PTQ INT8
vs
QAT INT8
```

QAT mô phỏng ảnh hưởng lượng tử hóa trong quá trình train/fine-tune.

### Metric

- Accuracy
- Precision
- Recall
- F1
- Confusion Matrix
- Model size
- Latency
- RAM
- Độ lệch output so với FP32

### Câu hỏi nghiên cứu

> QAT có giảm quantization loss của DS-CNN so với PTQ INT8 hay không?

**=> Trạng thái: Hoàn thành** - Truy cập tại đây [So sánh Quanzation](/AI_Training_Model/Phase3_Quantization_Model/Report_V1_v_V5_Analysis.md)

---

<a id="ext-4"></a>
# 4. DS-CNN model scaling

Không cần đổi sang kiến trúc hoàn toàn khác. Có thể giữ DS-CNN và thay:

```text
số channel
số block
width multiplier
```

Ví dụ:

```text
DS-CNN Small
DS-CNN Baseline
DS-CNN Large
```

### Mục tiêu

Khảo sát trade-off:

```text
Accuracy / Recall
        ↕
Flash / RAM / latency
```

| Model | Params | Flash | Arena | Latency | Asthma Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| Small | | | | | | |
| Baseline | | | | | | |
| Large | | | | | | |

**=> Trạng thái: Hoàn thành** - Truy cập tại đây [So sánh Quanzation](/AI_Training_Model/Phase3_Quantization_Model/Report_V1_v_V5_Analysis.md)

---

<a id="ext-5"></a>
# 5. DSP / Audio Front-End Ablation

## 5.1. Dải tần filter

Thiết lập vẽ sơ đồ các dải tần, nhằm cắt gọt đi các dải tần thừa thãi, giúp âm thanh tập trung vùng có đặc trưng nhất.

## 5.2. Butterworth filter

Ví dụ:

```text
Không filter
Order 3
Order 5  ← baseline
Order 7
```

Không đổi đồng thời cả filter order và cutoff ở vòng đầu.

## 5.3. Pre-emphasis

So sánh:

```text
Không pre-emphasis
vs
pre-emphasis = 0.97
```

### Metric

- Accuracy
- Asthma Recall
- Non-Asthma False Positive
- DSP latency
- Robustness với noise

**Ưu tiên: Trung bình – Cao.**

---

<a id="ext-6"></a>
# 6. Mel Spectrogram Ablation

Có thể khảo sát:

```text
40 Mel bins
64 Mel bins  ← baseline
80 Mel bins
```

hoặc một số cấu hình window/hop khác.

Ngoài metric model, cần đo:

```text
thời gian tạo Mel
RAM frontend
input tensor size
```

### Câu hỏi nghiên cứu

> Tăng độ phân giải Mel có cải thiện phân lớp đủ nhiều để bù cho RAM và latency tăng hay không?

**Ưu tiên: Trung bình.**

---

<a id="ext-7"></a>
# 7. Dataset Ablation

Đây là hướng rất đáng làm với Dataset V2.

So sánh:

```text
Core only
Core + Playback
Core + Environment
Core + Playback + Environment  ← Full V2
```

### Mục tiêu

Định lượng tác dụng thực của:

- playback;
- hard-negative environment;
- dữ liệu môi trường thực.

### Metric quan trọng

Đặc biệt theo dõi:

```text
Non-Asthma → Asthma False Positive
```

### Câu hỏi nghiên cứu

> Hard-negative environment có giảm False Positive mà vẫn giữ Asthma Recall hay không?

**Ưu tiên: Rất cao.**

---

<a id="ext-8"></a>
# 8. Real-World Challenge Set

Giữ một tập riêng:

```text
Real_World_Challenge/
```

Có thể chứa:

- healthy cough trực tiếp;
- speech trực tiếp;
- room ambient chưa dùng;
- nguồn âm thật chưa từng train;
- khoảng cách khác baseline;
- điều kiện nhiễu khó.

Challenge set:

```text
KHÔNG dùng train
KHÔNG dùng chọn threshold
KHÔNG dùng augmentation
```

Mục tiêu là đo:

```text
dataset-domain performance
vs
real-world generalization
```

**Ưu tiên: Rất cao.**

---

<a id="ext-9"></a>
# 9. Playback-domain vs Direct-domain

Một hướng phân tích đáng giá:

```text
Dataset source
        ↓
Playback bằng loa
        ↓
INMP441
```

so với:

```text
Người thật
   ↓
INMP441
```

Có thể tạo:

```text
Test A → file dataset gốc
Test B → playback qua loa
Test C → âm trực tiếp thực tế
```

### Câu hỏi nghiên cứu

> Mô hình có học đặc trưng âm thanh cần thiết hay đang phụ thuộc vào channel loa → micro?

Nếu performance giảm mạnh ở Direct, cần nêu rõ domain shift.

**Ưu tiên: Rất cao về mặt nghiên cứu.**

---

<a id="ext-10"></a>
# 10. Threshold và vùng UNSURE

Model vẫn là binary:

```text
Asthma
Non-Asthma
```

`UNSURE` là post-processing.

Có thể mở rộng lựa chọn threshold bằng:

- ROC
- Precision–Recall curve
- F1
- Asthma Recall
- False Negative
- Unsure Rate

Có thể định nghĩa cost:

```text
Cost =
w1 × Asthma False Negative
+
w2 × Non-Asthma False Positive
+
w3 × Unsure Rate
```

**Ưu tiên: Cao**, vì không cần retrain.

---

<a id="ext-11"></a>
# 11. MONITOR Voting Strategy

Baseline có thể dùng:

```text
3 inference cycles
Asthma votes >= 2
→ confirmed Asthma event
```

Benchmark:

```text
1/3
2/3  ← baseline
3/3
```

Đánh giá:

- event recall
- false alarm rate
- latency
- số lần inference
- năng lượng

**Ưu tiên: Trung bình – Cao.**

---

<a id="ext-12"></a>
# 12. Quality Gate Ablation

So sánh:

```text
Không Quality Gate
vs
Quality Gate hiện tại
```

hoặc từng thành phần:

```text
RMS only
RMS + Active Ratio
RMS + Active Ratio + clipping
```

Metric:

- sample không hợp lệ bị chặn;
- sample hợp lệ bị reject;
- false inference do silence/noise;
- số inference tránh được.

**Ưu tiên: Cao.**

---

<a id="ext-13"></a>
# 13. VAD mở rộng

Khảo sát:

```text
Energy threshold
Consecutive chunks
Pre-trigger buffer
```

Metric:

- trigger recall
- false trigger/hour
- reaction time
- tỷ lệ giữ đủ phần đầu event

Một hướng sâu hơn:

```text
Fixed VAD threshold
vs
Noise-adaptive threshold
```

**Ưu tiên: Trung bình.**

---

<a id="ext-14"></a>
# 14. Adaptive Quality / Environment-aware Front-End

Có thể nghiên cứu:

```text
ước lượng noise floor
        ↓
chọn threshold / filter / gain phù hợp
```

Đây là hướng tăng robustness mà không nhất thiết tăng kích thước model.

**Ưu tiên: Future / optional.**

---

<a id="ext-15"></a>
# 15. OOD / Unknown Detection

Hiện `UNSURE` vẫn dựa vào output binary classifier.

Một hướng sâu hơn là phát hiện:

```text
Out-of-Distribution
```

Ví dụ:

- tiếng máy móc lạ;
- nhạc rất lớn;
- acoustic event ngoài domain.

Có thể nghiên cứu:

- confidence threshold;
- entropy;
- embedding distance;
- prototype / centroid;
- lightweight anomaly detector.

**Ưu tiên: Future work.**

---

<a id="ext-16"></a>
# 16. Model Compression ngoài Quantization

## 16.1. Pruning

Có thể thử:

```text
Unstructured pruning
Structured pruning
```

Nhưng phải kiểm tra runtime có tận dụng sparsity thật hay không.

## 16.2. Weight clustering

Có thể giảm độ phức tạp lưu trữ nhưng không chắc giảm runtime MCU.

**Ưu tiên: Thấp – Trung bình.**

---

<a id="ext-17"></a>
# 17. Kernel Optimization

Có thể so sánh:

```text
TFLite Micro generic kernels
vs
optimized kernels phù hợp ESP32-S3
```

Metric:

- latency
- CPU usage
- arena
- energy/inference

Đây là **runtime optimization**, không phải thay model.

---

<a id="ext-18"></a>
# 18. Inference Pipeline Optimization

Tối ưu:

```text
I2S capture
→ DSP
→ Mel
→ inference
```

theo hướng:

- double buffering;
- DMA;
- producer/consumer;
- giảm copy buffer;
- static allocation;
- tái sử dụng workspace.

Metric:

- end-to-end latency;
- peak RAM;
- dropped samples;
- CPU occupancy.

---

<a id="ext-19"></a>
# 19. Power Consumption

Nếu có thiết bị đo dòng, có thể đo:

```text
Standby
Recording
DSP
Inference
ESP-NOW TX
MAX30102 active
```

Báo cáo:

```text
mA trung bình
mWh/session
energy/inference
```

### Câu hỏi nghiên cứu

> Quantization/model optimization có giảm năng lượng thực tế hay chỉ giảm model size?

---

<a id="ext-20"></a>
# 20. Latency Breakdown

Không chỉ đo tổng latency.

Nên tách:

```text
Audio acquisition
DSP
Mel
Inference
Post-processing
Packet build
ESP-NOW
```

| Stage | Latency |
|---|---:|
| Capture | |
| DSP | |
| Mel | |
| DS-CNN inference | |
| Post-processing | |
| ESP-NOW | |
| Total | |

---

<a id="ext-21"></a>
# 21. Memory Profiling

Nên lưu:

```text
Model size
Tensor arena
Stack
Heap before inference
Minimum free heap
Peak RAM
Flash firmware
```

Đặc biệt quan trọng khi so:

```text
INT8
vs
INT16x8
```

---

<a id="ext-22"></a>
# 22. Long-term Inference Stability

Thử:

```text
MONITOR chạy vài giờ
```

Theo dõi:

- số inference;
- số trigger;
- false trigger;
- reset;
- memory drift;
- latency drift;
- I2S failure;
- state-machine failure.

Đây là hướng nối trực tiếp Edge AI với Embedded System.

---

<a id="ext-23"></a>
# 23. Network Robustness

Benchmark:

```text
ESP-NOW OK
ESP-NOW packet loss
Gateway offline
Wi-Fi loss
MQTT loss
LTE fallback
```

Metric:

- packet success rate;
- retry count;
- recovery time;
- lost event;
- duplicate event.

Đây là system-level evaluation, không phải model benchmark.

---

<a id="ext-24"></a>
# 24. Sensor Fusion với MAX30102

Một hướng dài hạn:

```text
Audio AI
+
Heart Rate
+
SpO2
```

Không nên vội đưa HR/SpO2 trực tiếp vào model nếu chưa có dataset đồng bộ đủ lớn.

Hướng an toàn hơn:

```text
Audio classifier
        +
Vitals context
        ↓
Decision support / event priority
```

**Ưu tiên: Future work.**

---

<a id="ext-25"></a>
# 25. Multi-class Classification

Hiện tại nên tiếp tục:

```text
Asthma
vs
Non-Asthma
```

Không nên chuyển ngay thành:

```text
Asthma
COPD
Bronchial
Pneumonia
Healthy
Environment
```

nếu dataset chưa đủ lớn và cân bằng.

Multi-class nên để ở phần **Future Work**.

---

<a id="ext-26"></a>
# 26. Personalization

Một hướng xa hơn:

```text
global model
        ↓
calibration theo từng người
```

Ví dụ điều chỉnh threshold dựa trên lịch sử cá nhân.

Cần:

- nhiều người;
- nhiều session/người;
- kiểm soát overfitting;
- privacy.

**Ưu tiên: Future work.**

---

<a id="ext-27"></a>
# 27. 5 thí nghiệm nên ưu tiên nếu thời gian hạn chế

## Experiment A — Quantization

```text
FP32
vs INT8
vs INT16x8
```

## Experiment B — PTQ vs QAT

```text
PTQ INT8
vs QAT INT8
```

## Experiment C — Dataset Ablation

```text
Core
Core + Playback
Core + Environment
Full V2
```

## Experiment D — Real-world Challenge

```text
Test chính
vs
healthy/direct/environment challenge
```

## Experiment E — Resource Benchmark

```text
Model size
RAM
Tensor Arena
Latency
Flash
```

Bộ này đủ mạnh để tạo một phần **Experimental Evaluation** rõ ràng mà không làm scope phình quá lớn.

---

<a id="ext-28"></a>
# 28. Ma trận ưu tiên

| Hướng | Giá trị nghiên cứu | Công sức | Khuyến nghị |
|---|---:|---:|---|
| INT8 vs INT16x8 | Rất cao | Trung bình | Nên làm |
| PTQ vs QAT | Cao | Trung bình | Nên làm nếu có thời gian |
| Dataset ablation | Rất cao | Trung bình | Nên làm |
| Real-world challenge | Rất cao | Thấp–Trung bình | Nên làm |
| Resource benchmark | Rất cao | Thấp | Nên làm |
| DS-CNN scaling | Cao | Trung bình | Có thể làm |
| DSP ablation | Cao | Trung bình | Có thể làm |
| Mel ablation | Trung bình | Trung bình | Optional |
| Threshold / UNSURE | Cao | Thấp | Nên làm |
| Voting strategy | Trung bình | Thấp | Có thể làm |
| Adaptive VAD | Trung bình | Trung bình | Future / optional |
| OOD detection | Cao | Cao | Future work |
| Pruning | Trung bình | Trung bình | Optional |
| Power benchmark | Cao | Trung bình | Nếu có thiết bị đo |
| Sensor fusion | Cao | Cao | Future work |
| Multi-class | Trung bình | Rất cao | Không ưu tiên |
| Personalization | Cao | Rất cao | Future work |

---

<a id="ext-29"></a>
# 29. Cấu trúc gợi ý cho phần “Hướng mở rộng” trong báo cáo

```text
7. HƯỚNG PHÁT TRIỂN

7.1. Nâng cao độ chính xác sau lượng tử hóa
     - INT16x8
     - Quantization-Aware Training

7.2. Tối ưu kiến trúc DS-CNN
     - Model scaling
     - Resource / accuracy trade-off

7.3. Tối ưu Audio Front-End
     - Filter
     - Mel configuration
     - Adaptive Quality Gate / VAD

7.4. Nâng cao khả năng tổng quát
     - Playback-domain vs direct-domain
     - Environment hard negatives
     - Real-world challenge set

7.5. Phát hiện dữ liệu ngoài phân bố
     - UNKNOWN / OOD

7.6. Tối ưu triển khai trên MCU
     - latency
     - RAM
     - Flash
     - optimized kernels
     - power

7.7. Mở rộng hệ thống
     - long-term robustness
     - network recovery
     - vitals context
```

---

<a id="ext-30"></a>
# 30. Quy tắc khi báo cáo experiment

Mỗi experiment nên có:

```text
1. Hypothesis
2. Biến thay đổi
3. Thành phần giữ cố định
4. Dataset / split
5. Metric
6. Kết quả
7. Trade-off
8. Kết luận
```

Ví dụ:

```text
Hypothesis:
INT16x8 giữ thông tin activation tốt hơn INT8.

Giữ cố định:
Dataset V2, DS-CNN, DSP, Mel.

So sánh:
INT8 vs INT16x8.

Metric:
F1, Recall, latency, arena, Flash.

Kết luận:
INT16x8 chỉ đáng dùng nếu accuracy/recall cải thiện đủ lớn
so với chi phí RAM và latency.
```

---

<a id="ext-31"></a>
# 31. Kết luận

Sau khi baseline:

```text
Train
→ Quantize INT8
→ Deploy ESP32-S3
→ Inference end-to-end
```

đã chạy ổn, các hướng mở rộng nên tập trung vào ba câu hỏi:

```text
1. Có thể tăng độ chính xác / Recall không?
2. Có thể giảm Flash / RAM / latency / power không?
3. Có thể tăng khả năng tổng quát ngoài dataset không?
```

Trong phạm vi Patient Node hiện tại, ba hướng đáng giá nhất là:

```text
Quantization comparison
+
Dataset / real-world robustness
+
MCU resource benchmark
```

Các hướng như multi-class, sensor fusion sâu, OOD detector hay personalization nên để ở **Future Work** thay vì đưa vào baseline ngay.
