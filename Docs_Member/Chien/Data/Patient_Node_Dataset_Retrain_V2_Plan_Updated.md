# Kế hoạch thu dữ liệu và nâng cấp Model V2 — Patient Node

## Mục lục

1. [Mục tiêu](#plan-v2-1)
2. [Pipeline Patient Node hiện tại](#plan-v2-2)
3. [Dữ liệu hiện có](#plan-v2-3)
4. [Bốn nhóm dữ liệu cần thu thêm](#plan-v2-4)
5. [Quy tắc thu Asthma / Non-Asthma qua loa](#plan-v2-5)
6. [Raw dài khoảng 6 giây nhưng model dùng 5 giây](#plan-v2-6)
7. [Thu âm môi trường như thế nào?](#plan-v2-7)
8. [Chia Train / Validation / Test](#plan-v2-8)
9. [Augmentation](#plan-v2-9)
10. [Silence không cần train nữa](#plan-v2-10)
11. [Hard-negative](#plan-v2-11)
12. [Hard-positive](#plan-v2-12)
13. [Mục tiêu của Model V2](#plan-v2-13)
14. [Thứ tự thực hiện đề xuất](#plan-v2-14)
15. [Cấu trúc dataset đề xuất](#plan-v2-15)
16. [Kết luận ngắn](#plan-v2-16)

---

<a id="plan-v2-1"></a>
## 1. Mục tiêu

Model hiện tại được **đóng băng và giữ làm baseline** để so sánh với phiên bản nâng cấp sau này.

Kết quả đánh giá gần nhất của model baseline:

| Lớp | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.6923 | 0.9000 | 0.7826 | 30 |
| Non-Asthma | 0.9595 | 0.8554 | 0.9045 | 83 |
| Accuracy |  |  | **0.8673** | 113 |

Điểm cần chú ý:

- Recall của Asthma hiện khá cao: khoảng **0.90**.
- Precision của Asthma còn thấp hơn mong muốn: khoảng **0.69**.
- Điều này cho thấy model có xu hướng bắt Asthma khá mạnh nhưng vẫn có một số mẫu Non-Asthma bị báo nhầm thành Asthma.
- Đã quan sát trường hợp âm thanh như vỗ tay có thể bị model nhận thành Asthma.
- Vì vậy Model V2 cần ưu tiên:
  - giữ Asthma Recall không giảm mạnh;
  - giảm false positive Asthma;
  - tăng độ ổn định với dữ liệu thu thật từ INMP441.

Model baseline không sửa trực tiếp. Mọi thay đổi tiếp theo được thực hiện trên dataset/model mới để có thể so sánh trước và sau.

---

<a id="plan-v2-2"></a>
## 2. Pipeline Patient Node hiện tại

```text
Thu đủ 5 giây âm thanh
        ↓
Quality Check
        ↓
DSP
        ↓
DS-CNN
        ↓
Inference
        ↓
ASTHMA / UNSURE / NON-ASTHMA
```

Quality Check được thực hiện **sau khi đã thu đủ 5 giây**.

Vì vậy cần phân biệt rõ:

- âm thanh dùng để kiểm tra Quality Check;
- âm thanh dùng để train model;
- âm thanh dùng để kiểm tra model;
- dữ liệu playback qua loa dùng để mô phỏng đường thu thực tế qua INMP441.

---

<a id="plan-v2-3"></a>
## 3. Dữ liệu hiện có và phần nào được kế thừa từ V1

Dataset V1 hiện có ba nhóm chính:

- **Asthma core**: 288 file raw, đã được chia theo bệnh nhân thành Train / Validation / Test.
- **Non-Asthma disease core**: các bệnh lý khác, cũng đã có membership Train / Validation / Test từ V1.
- **Environment tự thu**:
  - một file podcast dài khoảng 5 phút;
  - một file quạt + bàn phím dài khoảng 5 phút;
  - một file silence dài khoảng 5 phút.

### Core V1

Với Asthma và Non-Asthma disease core, **không random lại split**.

Nguyên tắc:

```text
File/source A từng ở Train V1 → V2 vẫn Train
File/source B từng ở Val V1   → V2 vẫn Val
File/source C từng ở Test V1  → V2 vẫn Test
```

Mục đích là giữ khả năng so sánh V1 ↔ V2 và tránh thay đổi kết quả chỉ vì đổi split.

### Environment V1

Các clip môi trường 5 giây của V1 trước đây được cắt từ hai recording dài rồi rải vào cả Train / Val / Test. Cách này có nguy cơ **data leakage**, vì các clip vẫn đến từ cùng một lần thu, cùng phòng, mic, gain, khoảng cách và nền âm.

Vì vậy trong V2:

- **không tái sử dụng split của các clip environment 5 giây cũ**;
- giữ lại hai file master:
  - `podcast_5min.wav`;
  - `key_fan_5min.wav`;
- coi mỗi file master là **một `session_id` độc lập**;
- thu thêm các session mới rồi chia lại environment theo session.

Ví dụ:

```text
podcast_old_01   ← file 5 phút cũ
podcast_new_02   ← lần thu độc lập mới
podcast_new_03   ← lần thu độc lập mới

keyfan_old_01
keyfan_new_02
keyfan_new_03
```

### Silence V1

Silence không còn được dùng như một sample `Non-Asthma` của DS-CNN.

File silence dài vẫn được giữ cho hai mục đích:

```text
Quality Check / VAD test
+
augmentation asset cho Asthma Train
```

Tức silence có thể được dùng để dịch vị trí tín hiệu Asthma trong augmentation, nhưng không mang label `Non-Asthma`.

---

<a id="plan-v2-4"></a>
## 4. Bốn nhóm dữ liệu cần thu / bổ sung

| Nhóm dữ liệu | Cách thu | Dùng để làm gì? | Quy mô đề xuất ban đầu |
|---|---|---|---:|
| **Asthma playback** | Phát raw Asthma qua loa, volume cố định, tắt EQ/enhancement, đặt loa gần INMP441 khi nguồn phát nhỏ | Bổ sung dữ liệu Asthma qua đúng đường thu thực tế; tìm hard-positive | **80–120 clip 5 s** nếu tiếp tục vòng playback |
| **Non-Asthma playback** | Phát raw Non-Asthma qua cùng setup loa + INMP441 | Đối chứng với Asthma playback và bổ sung dữ liệu thực tế | **80–120 clip 5 s** nếu tiếp tục vòng playback |
| **Environment mới** | Thu trực tiếp bằng INMP441 theo nhiều **session độc lập**: podcast, speech, fan, keyboard, fan+keyboard, clap, knock, room noise | Bổ sung Non-Asthma thực tế và hard-negative; đồng thời làm noise asset cho Asthma augmentation nếu session thuộc Train | Bắt đầu **3–5 session/nhóm**, khoảng **30–90 s/session**, sau đó chọn khoảng **60–120 clip 5 s tổng** cho vòng đầu |
| **Quality Check only** | Silence, quá yếu, clipping/quá lớn và các trường hợp lỗi rõ ràng | Test/tune Quality Check và VAD; không train DS-CNN | Giữ silence V1; bổ sung **20–30 clip/tình huống** nếu còn thiếu |

Các con số trên là mục tiêu vòng đầu, không phải quota cứng.

Ưu tiên:

```text
nhiều session/source độc lập
>
nhiều clip lặp lại từ cùng một recording
```

Đặc biệt với environment, không cần một session dài 5 phút. Một lần thu độc lập khoảng 30–90 giây đã đủ để tạo một số clip 5 giây hữu ích.

---

<a id="plan-v2-5"></a>
## 5. Quy tắc thu Asthma / Non-Asthma qua loa

Raw Asthma hiện có một vấn đề thực tế: khi phát bằng loa, dù để volume tối đa và tắt các chế độ xử lý âm thanh, một số file vẫn nghe khá nhỏ.

Do đó chốt quy ước:

```text
Raw audio
   ↓
Loa phát nguyên bản
Volume cố định
EQ / enhancement / spatial / bass boost = OFF
   ↓
Loa đặt rất gần INMP441
   ↓
INMP441 thu lại
   ↓
Tạo đoạn 5 giây
   ↓
Quality Check
   ↓
DSP + inference
```

Khoảng cách loa–micro rất gần chỉ là **điều kiện playback của thí nghiệm**, không phải khoảng cách sử dụng thực tế của Patient Node.

Không được kết luận rằng bệnh nhân phải ở cùng khoảng cách đó.

Âm ho ngoài đời có thể lớn hơn playback qua loa rất nhiều, trong khi wheeze/rít có thể nhỏ hơn. Do đó:

- không dùng độ lớn âm thanh làm dấu hiệu duy nhất của Asthma;
- không hạ Quality Check chỉ để cứu loa phát nhỏ;
- bài test người thật / khoảng cách sử dụng thực tế sẽ được đánh giá riêng.

---

<a id="plan-v2-6"></a>
## 6. Raw dài khoảng 6 giây nhưng model dùng 5 giây

Không nên cắt raw xuống 5 giây trước khi phát nếu chưa có quy tắc thống nhất.

Quy trình:

```text
Raw ~6 s
   ↓
phát nguyên raw
   ↓
INMP441 thu toàn bộ
   ↓
sau đó tạo cửa sổ 5 s
```

Với một số raw Asthma mà baseline liên tục nhận thành Non-Asthma, có thể phân tích thêm:

```text
0.0 – 5.0 s
0.5 – 5.5 s
1.0 – 6.0 s
```

Mục đích là xác định:

- lỗi do cửa sổ 5 giây bỏ mất phần đặc trưng;
- hay model thực sự không nhận được loại Asthma đó.

Các cửa sổ sinh ra từ cùng một raw **không được coi là các source độc lập**.

---

<a id="plan-v2-7"></a>
## 7. Thu âm môi trường như thế nào?

### 7.1. Định nghĩa session

Một **session** là một lần recording độc lập.

Ví dụ:

```text
podcast_session_01
podcast_session_02
podcast_session_03
```

Các session có thể khác nhau nhẹ về:

- thời điểm thu;
- nội dung phát / nội dung nói;
- khoảng cách hoặc hướng microphone;
- vị trí đặt thiết bị;
- tốc độ quạt;
- cách gõ bàn phím;
- điều kiện nền phòng.

Không bắt buộc phải đổi phòng hoàn toàn. Điều quan trọng là không lấy một recording duy nhất rồi chia các clip của nó sang nhiều split.

### 7.2. Hai recording cũ

Hai file:

```text
podcast_5min.wav
key_fan_5min.wav
```

được giữ lại, nhưng mỗi file chỉ được coi là **một session**.

Các clip 5 giây cũ từng bị rải vào cả Train / Val / Test sẽ không được dùng lại theo split cũ.

### 7.3. Session mới

Với âm liên tục như:

- podcast / speech;
- fan;
- keyboard;
- fan + keyboard;
- room noise;

mỗi session có thể dài khoảng:

```text
30–90 giây
```

hoặc dài hơn nếu thuận tiện. Không cần đủ 5 phút.

Sau khi session đã được gán split, mới cắt thành các cửa sổ 5 giây.

Với transient như:

- clap;
- knock;
- gõ vỏ thiết bị;

mỗi clip 5 giây nên có khoảng 1–2 sự kiện rõ thay vì spam sự kiện liên tục.

Mục tiêu là thu các tình huống thực tế model có thể gặp, đặc biệt các âm có khả năng gây false positive.

---

<a id="plan-v2-8"></a>
## 8. Chia Train / Validation / Test

V2 có **hai quy tắc chia khác nhau**.

### 8.1. Core Asthma và Non-Asthma disease

Giữ nguyên membership V1:

```text
A từng ở Train → vẫn Train
B từng ở Val   → vẫn Val
C từng ở Test  → vẫn Test
```

Không random lại Asthma core và các bệnh lý Non-Asthma core.

### 8.2. Environment

Environment được **rebuild split từ đầu theo `session_id`**.

Quy tắc mục tiêu:

```text
80% session → Train
10% session → Validation
10% session → Test
```

Với số session ít, không cần ép từng loại môi trường phải đúng tuyệt đối 80/10/10. Quan trọng nhất là:

```text
1 session_id chỉ thuộc đúng 1 split
```

Ví dụ đúng:

```text
podcast_session_01 → Train
podcast_session_02 → Train
podcast_session_03 → Validation
podcast_session_04 → Test
```

Sau đó:

```text
podcast_session_03
├── clip_001.wav
├── clip_002.wav
└── clip_003.wav

→ tất cả chỉ ở Validation
```

Không làm:

```text
cùng một file 5 phút
→ cắt random clip
→ rải clip vào Train / Val / Test
```

vì đó chính là leakage mà V2 cần loại bỏ.

### 8.3. Ghép thành Non-Asthma V2

```text
Non-Asthma Train V2
= Disease Core Train V1
+ Environment Train V2

Non-Asthma Val V2
= Disease Core Val V1
+ Environment Val V2

Non-Asthma Test V2
= Disease Core Test V1
+ Environment Test V2
```

---

<a id="plan-v2-9"></a>
## 9. Augmentation Asthma V2

Dataset Asthma V1 có khoảng **288 file gốc trước augmentation**.

V1 đã dùng các phép:

- trộn nhiễu môi trường;
- dịch vị trí tín hiệu trên nền silence;
- white noise;
- time stretch khoảng `0.8–1.2`;
- pitch shift khoảng `±0.5`;
- chuẩn hóa output về `16 kHz / 5 s`.

Ở V2, **không giữ nguyên toàn bộ Asthma augmented files của V1**.

Lý do: augmentation V1 phụ thuộc vào environment V1, trong khi environment đang được rebuild để xử lý leakage.

Quy trình mới:

```text
Asthma Train raw V1
        ↓
giữ nguyên membership Train
        ↓
generate augmentation lại từ đầu
        +
Environment TRAIN V2
        +
silence V1 augmentation asset
        ↓
Asthma Train V2
```

Validation và Test Asthma:

```text
giữ nguyên raw V1
không augmentation
```

Chỉ `Environment Train V2` được phép dùng để mix noise cho Asthma Train. Environment Val/Test tuyệt đối không được dùng làm augmentation asset của Train.

### Số lượng Asthma sau augmentation

Con số:

```text
833 Asthma Train
```

chỉ là kết quả của V1, **không phải target bắt buộc của V2**.

Sau khi biết số lượng thực tế của:

```text
Non-Asthma disease core Train
+
Environment Train V2
```

mới chọn target augmentation Asthma hợp lý.

V2 có thể có số mẫu Train lớn hơn 833. Mục tiêu là cân bằng hợp lý và tăng đa dạng, không phải giữ đúng một con số lịch sử.

---

<a id="plan-v2-10"></a>
## 10. Vai trò của Silence

Silence **không được đưa vào DS-CNN như một sample Non-Asthma**.

Vai trò của file silence V1:

```text
1. Quality Check / AUDIO_INACTIVE
2. VAD false-trigger test
3. augmentation asset cho Asthma Train
```

Với augmentation, silence có thể được dùng làm nền cho phép dịch vị trí tín hiệu Asthma trong cửa sổ 5 giây.

Điều này không mâu thuẫn với việc silence không thuộc dataset classifier:

```text
silence làm augmentation asset ≠ silence mang label Non-Asthma
```

Các trường hợp quá yếu, clipping hoặc lỗi rõ ràng cũng ưu tiên cho Quality Check thay vì bắt DS-CNN học nhiệm vụ của firmware.

---

<a id="plan-v2-11"></a>
## 11. Hard-negative

Các âm như:

- podcast;
- speech;
- clap;
- knock;
- bàn phím;
- quạt;
- room noise;

không nhất thiết đưa toàn bộ vào Non-Asthma.

Quy trình tốt hơn:

```text
Âm môi trường mới
        ↓
chạy model baseline
        ↓
xem prediction
        ↓
mẫu dễ nhầm Asthma / UNSURE
        ↓
ưu tiên đưa vào Non-Asthma Train
```

Những mẫu như vậy là **hard-negative**.

Ví dụ:

```text
clap_01 → ASTHMA
speech_08 → ASTHMA
keyboard_14 → UNSURE
fan_02 → NON-ASTHMA rất chắc
```

Ưu tiên:

```text
clap_01
speech_08
keyboard_14
```

Không cần nhồi nhiều `fan_02` nếu model đã xử lý tốt.

---

<a id="plan-v2-12"></a>
## 12. Hard-positive

Các raw Asthma mà model baseline liên tục nhận thành Non-Asthma là dữ liệu rất quan trọng.

Không bỏ các mẫu này.

Có thể gom riêng:

```text
hard_asthma/
```

Sau đó kiểm tra:

- nhiều cửa sổ 5 giây;
- playback qua loa → INMP441;
- prediction trước retrain;
- prediction sau retrain.

Model V2 nên cố cải thiện các hard-positive mà không làm giảm mạnh Asthma Recall tổng thể.

---

<a id="plan-v2-13"></a>
## 13. Mục tiêu của Model V2

Baseline hiện tại:

```text
Asthma Precision ≈ 0.69
Asthma Recall    ≈ 0.90
Accuracy         ≈ 0.87
```

Model V2 không cần cố tăng Accuracy bằng mọi giá.

Ưu tiên:

```text
giữ Asthma Recall gần mức hiện tại
        +
giảm Non-Asthma bị báo nhầm thành Asthma
        +
tăng Asthma Precision
        +
ổn định hơn với dữ liệu INMP441 thật
```

Khi so sánh Baseline và Model V2 cần ít nhất:

| Chỉ số | Baseline | Model V2 |
|---|---:|---:|
| Asthma Precision | 0.6923 | ? |
| Asthma Recall | 0.9000 | ? |
| Asthma F1 | 0.7826 | ? |
| Non-Asthma F1 | 0.9045 | ? |
| Accuracy | 0.8673 | ? |
| False Asthma trên hard-negative | ? | ? |

---

<a id="plan-v2-14"></a>
## 14. Thứ tự thực hiện đề xuất

```text
1. Đóng băng Baseline V1

2. Khôi phục / giữ nguyên membership của Core V1
   - Asthma: giữ Train / Val / Test theo bệnh nhân
   - Non-Asthma disease core: giữ đúng file ở split cũ

3. Loại các clip environment 5 s cũ khỏi split V2
   - giữ podcast_5min.wav
   - giữ key_fan_5min.wav
   - coi mỗi master là một session_id

4. Giữ silence V1 riêng
   - Quality Check / VAD
   - augmentation asset cho Asthma

5. Thu thêm environment theo nhiều session độc lập
   - podcast / speech
   - fan
   - keyboard
   - fan + keyboard
   - clap
   - knock
   - room noise

6. Chia Environment 80/10/10 theo session
   → rồi mới cắt clip 5 giây

7. Ghép Non-Asthma V2
   disease_core_split_V1 + environment_split_V2

8. Generate lại Asthma Train augmentation
   → chỉ dùng Environment Train V2 + silence asset
   → Val/Test Asthma giữ raw V1

9. Nếu tiếp tục playback Asthma / Non-Asthma
   → gắn source_id
   → chia theo source
   → ghép vào đúng split V2

10. Train DS-CNN Candidate V2
    → giữ pipeline Mel-Spectrogram hiện tại

11. Quantize INT8 và so với Baseline

12. Sau khi model ổn
    → chốt threshold
    → Quality Check
    → VAD
    → khoảng cách thực tế
    → FINAL V1
```

---

<a id="plan-v2-15"></a>
## 15. Cấu trúc dataset đề xuất

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
├── Quality_Check_Only/
│   ├── silence/
│   ├── too_weak/
│   └── clipping/
│
├── Playback_Optional/
│   ├── Asthma/
│   └── Non_Asthma/
│
└── metadata.csv
```

Dataset model cuối cùng được ráp theo logic:

```text
Asthma Train V2
= Asthma Core Train V1
+ augmentation generate lại

Asthma Val/Test V2
= Asthma Core Val/Test V1

Non-Asthma Train/Val/Test V2
= Non-Asthma Disease Core V1 tương ứng
+ Environment V2 tương ứng
```

Metadata cần giữ tối thiểu:

```text
file_name
label
subtype
source_id
session_id
split
original_source
capture_type
```

để có thể kiểm tra leakage và truy vết nguồn dữ liệu.

---

<a id="plan-v2-16"></a>
## 16. Kết luận ngắn

V2 không phải là chia random lại toàn bộ dataset V1.

Nguyên tắc chốt:

```text
Asthma core V1
→ giữ nguyên split

Non-Asthma disease core V1
→ giữ nguyên split

Environment V1 dạng clip 5 s
→ bỏ split cũ do có nguy cơ leakage

Podcast master + key_fan master
→ giữ lại như các session độc lập

Environment mới
→ thu thêm nhiều session
→ chia theo session
→ rồi mới cắt 5 s

Silence V1
→ Quality Check / VAD
→ đồng thời làm augmentation asset
→ không train như Non-Asthma

Asthma augmentation V1
→ không giữ nguyên
→ generate lại bằng Environment Train V2 + silence

833 mẫu Train
→ chỉ là con số V1
→ V2 có thể lớn hơn
```

Model V2 vẫn ưu tiên giữ nguyên:

```text
Mel-Spectrogram
→ DS-CNN
→ Quantization INT8
→ ESP32-S3
```

Nhờ vậy so sánh V1 ↔ V2 tập trung chủ yếu vào chất lượng dataset, cách chia dữ liệu và retraining, thay vì thay đổi đồng thời cả kiến trúc model.
