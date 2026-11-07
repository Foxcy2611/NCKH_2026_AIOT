# Workflow nâng cấp Model V2 — Patient Node

## Mục lục

1. [Mục tiêu](#workflow-v2-1)
2. [Nguyên tắc chốt của V2](#workflow-v2-2)
3. [Workflow tổng thể](#workflow-v2-3)
4. [Bước 1 — Đóng băng Baseline V1](#workflow-v2-4)
5. [Bước 2 — Khôi phục Core V1](#workflow-v2-5)
6. [Bước 3 — Rebuild Environment](#workflow-v2-6)
7. [Bước 4 — Thu Environment mới](#workflow-v2-7)
8. [Bước 5 — Chia Environment theo session](#workflow-v2-8)
9. [Bước 6 — Ghép Non-Asthma V2](#workflow-v2-9)
10. [Bước 7 — Generate lại Asthma Train V2](#workflow-v2-10)
11. [Bước 8 — Playback Asthma / Non-Asthma nếu cần](#workflow-v2-11)
12. [Bước 9 — Quality Check và metadata](#workflow-v2-12)
13. [Bước 10 — Train Candidate V2](#workflow-v2-13)
14. [Bước 11 — Quantize INT8](#workflow-v2-14)
15. [Bước 12 — Đánh giá Baseline vs V2](#workflow-v2-15)
16. [Bước 13 — Chốt model và firmware](#workflow-v2-16)
17. [Cấu trúc thư mục đề xuất](#workflow-v2-17)
18. [Checklist thực hiện](#workflow-v2-18)

---

<a id="workflow-v2-1"></a>
## 1. Mục tiêu

Model hiện tại được giữ nguyên làm **Baseline V1**.

Model V2 vẫn giữ hướng:

```text
Audio 16 kHz / 5 s
        ↓
DSP
        ↓
Mel-Spectrogram
        ↓
DS-CNN
        ↓
Quantization INT8
        ↓
ESP32-S3
```

V2 tập trung cải thiện:

- chất lượng dataset;
- loại bỏ leakage ở dữ liệu môi trường;
- tăng dữ liệu thực tế thu bằng INMP441;
- giảm false positive Asthma;
- giữ Asthma Recall gần mức V1;
- giữ nguyên kiến trúc chính để việc so sánh V1 ↔ V2 có ý nghĩa.

---

<a id="workflow-v2-2"></a>
## 2. Nguyên tắc chốt của V2

### Core Asthma

288 file Asthma raw đã được chia theo bệnh nhân ở V1.

```text
A từng ở Train → V2 vẫn Train
B từng ở Val   → V2 vẫn Val
C từng ở Test  → V2 vẫn Test
```

**Không random lại Core Asthma.**

### Core Non-Asthma disease

Các bệnh lý Non-Asthma cũ cũng giữ nguyên membership:

```text
file A từng ở Train → vẫn Train
file B từng ở Val   → vẫn Val
file C từng ở Test  → vẫn Test
```

**Không random lại phần disease core.**

### Environment V1

V1 từng lấy:

```text
podcast_5min.wav
key_fan_5min.wav
```

rồi cắt nhiều clip 5 s và rải vào cả Train / Val / Test.

Cách này có nguy cơ leakage vì các clip vẫn đến từ cùng một lần thu.

V2 xử lý:

```text
bỏ split clip 5 s environment cũ
↓
giữ lại file master
↓
mỗi master = 1 session_id
↓
thu thêm session độc lập
↓
chia lại Environment theo session
```

### Silence

Silence V1:

```text
KHÔNG train như Non-Asthma
```

nhưng vẫn giữ cho:

```text
Quality Check / VAD
+
augmentation asset cho Asthma Train
```

### Asthma augmentation

Không giữ nguyên toàn bộ Asthma augmented V1.

V2 sẽ:

```text
Asthma Train raw V1
+
Environment TRAIN V2
+
Silence V1
↓
generate augmentation lại
↓
Asthma Train V2
```

Con số `833` chỉ là kết quả của V1, không phải target cố định của V2.

---

<a id="workflow-v2-3"></a>
## 3. Workflow tổng thể

```text
Đóng băng Baseline V1
        ↓
Khôi phục Core V1
        ↓
Giữ nguyên split Core Asthma + Core Non-Asthma disease
        ↓
Xóa vai trò split cũ của các clip Environment V1
        ↓
Giữ podcast_5min + key_fan_5min như session master
        ↓
Thu thêm nhiều Environment session độc lập
        ↓
Gắn session_id
        ↓
Chia Environment 80/10/10 theo session
        ↓
Cắt mỗi session thành clip 5 s
        ↓
Ghép Environment vào Non-Asthma Core
        ↓
Generate lại Asthma augmentation
        ↓
Train DS-CNN Candidate V2
        ↓
Quantize INT8
        ↓
Đánh giá Baseline V1 vs Candidate V2
        ↓
Chốt threshold
        ↓
Chốt Quality Check
        ↓
Chốt VAD / khoảng cách thực tế
        ↓
Patient Node FINAL
```

---

<a id="workflow-v2-4"></a>
## 4. Bước 1 — Đóng băng Baseline V1

Lưu cố định:

- model `.keras`;
- model `.tflite` INT8;
- SHA-256;
- pipeline DSP + Mel-Spectrogram hiện tại;
- script train;
- script quantization;
- script augmentation;
- confusion matrix;
- Precision / Recall / F1;
- danh sách file Train / Val / Test V1;
- kết quả đánh giá Keras và INT8.

Baseline V1 không dùng để train tiếp.

```text
Baseline V1
→ chỉ dùng làm mốc so sánh
```

### Lưu ý về Test V1

Test V1 vẫn nên giữ để so sánh lịch sử.

Tuy nhiên phần environment V1 từng được cắt từ cùng master recording và rải qua nhiều split, nên **không coi phần environment đó là clean real-world test**.

V2 cần có thêm Test mới sạch theo `session_id`.

---

<a id="workflow-v2-5"></a>
## 5. Bước 2 — Khôi phục Core V1

Viết script dựng lại Core V1 từ membership cũ.

### Asthma

Lấy lại:

```text
Asthma/
├── train/
├── val/
└── test/
```

theo đúng split bệnh nhân V1.

Các file augmentation V1 không được coi là raw source.

Chỉ giữ raw parent để sau đó generate augmentation V2 lại từ đầu.

### Non-Asthma disease

Chỉ lấy các disease core:

```text
COPD
Healthy
Bronchial
Pneumonia
...
```

và giữ đúng membership cũ:

```text
Train V1 → Train V2
Val V1   → Val V2
Test V1  → Test V2
```

Tạm thời **không ghép Environment** ở bước này.

---

<a id="workflow-v2-6"></a>
## 6. Bước 3 — Rebuild Environment

Environment cũ hiện còn ba nguồn chính:

```text
podcast_5min.wav
key_fan_5min.wav
silence_5min.wav
```

Xử lý:

```text
podcast_5min.wav
→ session_id = podcast_old_01

key_fan_5min.wav
→ session_id = keyfan_old_01

silence_5min.wav
→ Quality Check / VAD
→ augmentation asset
```

Không dùng lại cách:

```text
1 file 5 phút
→ cắt random
→ ném clip sang Train / Val / Test
```

---

<a id="workflow-v2-7"></a>
## 7. Bước 4 — Thu Environment mới

Mỗi lần bấm record và tạo một recording độc lập được coi là một `session_id`.

Không bắt buộc mỗi session phải dài 5 phút.

Khuyến nghị:

```text
30–90 giây / session
```

hoặc dài hơn nếu thuận tiện.

### Các nhóm nên thu

| Nhóm | Cách thu |
|---|---|
| Podcast | phát đoạn nội dung khác nhau qua loa |
| Speech | người nói trực tiếp gần Patient Node |
| Fan | quạt chạy độc lập |
| Keyboard | gõ bàn phím độc lập |
| Fan + Keyboard | giữ lại tình huống thực tế cũ |
| Clap | 1–2 lần vỗ tay trong một cửa sổ 5 s |
| Knock | gõ bàn / vỏ thiết bị |
| Room noise | âm nền phòng bình thường |

Vòng đầu:

```text
3–5 session / nhóm
```

là đủ để kiểm tra workflow.

Không cần ép tất cả các nhóm phải có cùng số session.

### Làm session khác nhau như thế nào?

Có thể thay đổi nhẹ:

- thời điểm thu;
- nội dung podcast/speech;
- khoảng cách;
- hướng mic;
- vị trí thiết bị;
- tốc độ quạt;
- kiểu gõ phím;
- điều kiện nền.

Không bắt buộc phải đổi phòng hoàn toàn.

---

<a id="workflow-v2-8"></a>
## 8. Bước 5 — Chia Environment theo session

Chia theo:

```text
80% session → Train
10% session → Validation
10% session → Test
```

Nếu số session ít thì không cần ép chính xác tuyệt đối.

Quy tắc bắt buộc:

```text
1 session_id chỉ thuộc 1 split
```

Ví dụ:

```text
podcast_session_01 → Train
podcast_session_02 → Train
podcast_session_03 → Validation
podcast_session_04 → Test
```

Sau đó mới cắt:

```text
podcast_session_03
├── clip_001.wav
├── clip_002.wav
├── clip_003.wav
└── ...

→ tất cả chỉ thuộc Validation
```

Không split theo từng clip 5 s.

### Master recording cũ

Hai file cũ:

```text
podcast_old_01
keyfan_old_01
```

cũng được đối xử như các session bình thường.

Ví dụ có thể cho chúng vào Train rồi dùng session mới cho Val/Test.

---

<a id="workflow-v2-9"></a>
## 9. Bước 6 — Ghép Non-Asthma V2

Sau khi Environment đã có split sạch:

```text
Non-Asthma Train V2
=
Disease Core Train V1
+
Environment Train V2
```

```text
Non-Asthma Validation V2
=
Disease Core Validation V1
+
Environment Validation V2
```

```text
Non-Asthma Test V2
=
Disease Core Test V1
+
Environment Test V2
```

Silence không được ghép vào ba tập trên.

### Hard-negative

Sau khi thu có thể chạy Baseline V1 trên Environment.

Các mẫu như:

```text
Clap     → ASTHMA
Speech   → ASTHMA
Keyboard → UNSURE
```

là hard-negative có giá trị.

Tuy nhiên:

- không được chuyển mẫu từ Val/Test sang Train chỉ vì model dự đoán sai;
- hard-negative chỉ được ưu tiên **trong split mà session đã được gán**;
- Train hard-negative có thể dùng để retrain;
- Val/Test hard-negative dùng để đánh giá.

---

<a id="workflow-v2-10"></a>
## 10. Bước 7 — Generate lại Asthma Train V2

Core Asthma vẫn giữ split cũ.

### Train

```text
Asthma Train raw V1
        ↓
augmentation lại từ đầu
        +
Environment TRAIN V2
        +
silence V1
        ↓
Asthma Train V2
```

Các phép augmentation hiện có:

- mix environment noise;
- shift trên nền silence;
- white noise;
- time stretch;
- pitch shift.

Chỉ được dùng:

```text
Environment Train V2
```

Không được dùng Environment Val/Test làm augmentation asset.

### Validation / Test

```text
Asthma Validation V1
→ giữ raw

Asthma Test V1
→ giữ raw
```

Không augmentation.

### Target số lượng

Không cố giữ:

```text
833 Asthma
```

Sau khi biết:

```text
Non-Asthma Disease Train
+
Environment Train
```

mới chọn target Asthma augmentation hợp lý.

Ví dụ:

```text
Non-Asthma Train V2 ≈ 950
→ Asthma Train effective có thể target khoảng 950–1050
```

Không cần cân tuyệt đối từng file nếu training pipeline có sampling hợp lý.

---

<a id="workflow-v2-11"></a>
## 11. Bước 8 — Playback Asthma / Non-Asthma nếu cần

Playback qua loa vẫn có thể dùng để tăng tính thực tế của Dataset V2, nhưng không bắt buộc phải hoàn thành trước Environment.

Flow:

```text
Raw Asthma / Non-Asthma
        ↓
phát nguyên bản qua loa
        ↓
INMP441 thu lại
        ↓
giữ WAV thô
        ↓
gắn source_id / take_id
        ↓
chia theo source
        ↓
tạo clip 5 s
```

Các take của cùng raw phải ở cùng split.

Ví dụ:

```text
AST_001_take01
AST_001_take02
AST_001_take03

→ cùng Train hoặc cùng Val hoặc cùng Test
```

Không rải take của cùng source sang nhiều split.

---

<a id="workflow-v2-12"></a>
## 12. Bước 9 — Quality Check và metadata

Không xóa WAV chỉ vì Quality Check hiện tại fail.

Flow:

```text
Thu WAV thô
→ giữ file
→ tính RMS
→ tính Peak
→ tính MAV
→ tính Active Ratio
→ tính Clipping Ratio
→ chạy Quality Check hiện tại
→ ghi metadata
→ chưa xóa
```

Quality Check chưa Final nên không dùng threshold hiện tại để loại vĩnh viễn dữ liệu.

### Metadata tối thiểu

```text
file_name
label
subtype
source_id
session_id
take_id
capture_type
original_source
environment
sample_rate
duration
quality_result
rms
peak
mav
active_ratio
clipping_ratio
split
```

---

<a id="workflow-v2-13"></a>
## 13. Bước 10 — Train Candidate V2

Dataset cuối:

```text
Train V2
├── Asthma Train V2
└── Non-Asthma Train V2

Validation V2
├── Asthma Validation Core V1
└── Non-Asthma Validation V2

Test V2
├── Asthma Test Core V1
└── Non-Asthma Test V2
```

Giữ pipeline model:

```text
Audio 16 kHz / 5 s
        ↓
DSP hiện tại
        ↓
Mel-Spectrogram
        ↓
DS-CNN
        ↓
Candidate V2
```

Không đổi kiến trúc chính ở vòng retrain dataset.

---

<a id="workflow-v2-14"></a>
## 14. Bước 11 — Quantize INT8

Sau khi Candidate V2 đạt yêu cầu ở Keras:

```text
DS-CNN FP32 V2
        ↓
Quantization
        ↓
TFLite INT8 V2
```

Đánh giá lại:

- Precision;
- Recall;
- F1;
- confusion matrix;
- model size;
- inference latency;
- Tensor Arena / RAM nếu đo được.

---

<a id="workflow-v2-15"></a>
## 15. Bước 12 — Đánh giá Baseline vs V2

Có hai lớp benchmark.

### Benchmark lịch sử

Giữ test V1 để biết model mới có phá hành vi cũ không.

```text
Baseline V1
vs
Candidate V2
→ Test V1
```

Nhưng phải ghi chú rằng phần Environment V1 có nguy cơ leakage từ master recording.

### Benchmark sạch V2

Dùng:

```text
Environment Test V2
```

được tạo từ session độc lập chưa xuất hiện trong Train.

Đây mới là benchmark chính để đánh giá robustness environment.

### Chỉ số

| Chỉ số | Baseline V1 | Candidate V2 |
|---|---:|---:|
| Asthma Precision | 0.6923 | ? |
| Asthma Recall | 0.9000 | ? |
| Asthma F1 | 0.7826 | ? |
| Non-Asthma F1 | 0.9045 | ? |
| Accuracy | 0.8673 | ? |
| False Asthma trên Environment Test V2 | ? | ? |

Mục tiêu:

```text
giữ Asthma Recall gần baseline
+
tăng Asthma Precision
+
giảm false positive môi trường
+
ổn định hơn trên INMP441
```

---

<a id="workflow-v2-16"></a>
## 16. Bước 13 — Chốt model và firmware

Sau khi Model V2 ổn:

```text
Model V2
   ↓
chốt classification threshold
ASTHMA / UNSURE / NON-ASTHMA
   ↓
chốt Quality Check
   ↓
chốt VAD
   ↓
chốt khoảng cách sử dụng thực tế
   ↓
End-to-End Test
   ↓
Long-run Test
   ↓
Patient Node FINAL
```

Không chốt threshold quá sớm khi model còn retrain.

---

<a id="workflow-v2-17"></a>
## 17. Cấu trúc thư mục đề xuất

```text
Dataset_V2/
│
├── Core_V1/
│   ├── Asthma/
│   │   ├── train/
│   │   ├── val/
│   │   └── test/
│   │
│   └── Non_Asthma_Disease/
│       ├── train/
│       ├── val/
│       └── test/
│
├── Environment_Raw/
│   ├── podcast/
│   │   ├── session_old_01/
│   │   ├── session_02/
│   │   └── ...
│   ├── fan_keyboard/
│   ├── speech/
│   ├── fan/
│   ├── keyboard/
│   ├── clap/
│   ├── knock/
│   └── room_noise/
│
├── Environment_Split/
│   ├── train/
│   ├── val/
│   └── test/
│
├── Augmentation_Assets/
│   ├── silence_v1/
│   └── environment_train_v2/
│
├── Playback_Optional/
│   ├── Asthma/
│   └── Non_Asthma/
│
├── Quality_Check_Only/
│   ├── silence/
│   ├── too_weak/
│   └── clipping/
│
├── Final_Split/
│   ├── train/
│   │   ├── Asthma/
│   │   └── Non_Asthma/
│   ├── val/
│   │   ├── Asthma/
│   │   └── Non_Asthma/
│   └── test/
│       ├── Asthma/
│       └── Non_Asthma/
│
└── metadata.csv
```

---

<a id="workflow-v2-18"></a>
## 18. Checklist thực hiện

```text
[ ] Baseline V1 đã đóng băng
[ ] SHA-256 đã lưu
[ ] Split Core Asthma V1 đã xác định
[ ] Split Core Non-Asthma disease V1 đã xác định

[ ] Clip Environment V1 cũ không còn được dùng theo split cũ
[ ] podcast_5min đã gắn session_id
[ ] key_fan_5min đã gắn session_id
[ ] silence V1 đã tách khỏi classifier dataset

[ ] Danh sách Environment mới đã chốt
[ ] Đã thu 3–5 session/nhóm ở vòng đầu
[ ] Mỗi session có session_id
[ ] Environment đã chia theo session
[ ] Sau đó mới cắt 5 s

[ ] Non-Asthma V2 đã ghép disease core + environment
[ ] Asthma augmentation V1 cũ đã bỏ khỏi V2
[ ] Asthma Train V2 đã regenerate
[ ] Chỉ Environment Train được dùng augmentation
[ ] Silence chỉ dùng QC/VAD + augmentation asset

[ ] Metadata đã hoàn chỉnh
[ ] Candidate V2 đã train
[ ] TFLite INT8 V2 đã tạo

[ ] Đã so Baseline vs V2 trên Test V1
[ ] Đã đánh giá trên Environment Test V2 sạch

[ ] Classification threshold đã chốt
[ ] Quality Check đã chốt
[ ] VAD đã chốt
[ ] Khoảng cách thực tế đã chốt
[ ] End-to-End test hoàn tất
[ ] Long-run test hoàn tất
[ ] Patient Node FINAL
```
