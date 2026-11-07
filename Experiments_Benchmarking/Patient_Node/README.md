# Patient Node — Experiments & Benchmarking

Thư mục này quản lý toàn bộ thí nghiệm, phép kiểm chứng và phân tích dùng cho **Patient Node**.

Mục tiêu chính là tách rõ hai loại công việc:

```text
Patient_Node/
├── Final_V1_Validation/
│   └── kiểm chứng baseline hiện hành để đóng băng Patient Node FINAL V1
│
└── Extension/
    └── nghiên cứu các hướng mở rộng sau khi baseline đã được xác định
```

Hai nhánh này **không được trộn mục đích**:

- `Final_V1_Validation/`: trả lời câu hỏi *“Cấu hình hiện tại đã đủ bằng chứng để chốt V1 hay chưa?”*
- `Extension/`: trả lời câu hỏi *“Sau baseline V1, có thể cải thiện hoặc mở rộng hệ thống theo hướng nào?”*

Tài liệu liên quan:

- [Step_Done_V1.md](./Step_Done_V1.md)
- [Final V1 Validation](./Final_V1_Validation/README.md)
- [Research Extensions](./Extension/README.md)

---

## 1. Nguyên tắc tổ chức

### 1.1. Baseline không sửa trực tiếp trong experiment

Source đang dùng cho Patient Node và AI baseline phải được coi là mốc đối chiếu.

Không sửa trực tiếp source baseline chỉ để chạy một thử nghiệm.

Nếu cần thay tham số để khảo sát:

```text
baseline source
      ↓
reusable experiment function
      ↓
.ipynb / experiment runner truyền tham số
      ↓
artifact + metric + kết luận
```

Một experiment chỉ nên thay đổi **một nhóm biến chính**.

Ví dụ nếu khảo sát:

```text
Filter order: 3 / 5 / 7
```

thì phải giữ nguyên:

- Dataset / split;
- dải tần;
- pre-emphasis;
- Mel;
- kiến trúc V1;
- seed;
- training configuration.

---

## 2. Quy tắc sử dụng từng loại file

### `.py` — source có thể tái sử dụng

Dùng cho:

- hàm DSP / preprocessing;
- hàm generate feature;
- model builder;
- training / evaluation;
- threshold utilities;
- parser log;
- các tác vụ cần chạy lặp lại và reproducible.

Ví dụ:

```python
apply_bandpass(audio, low_cut=100, high_cut=2000, order=5)
apply_pre_emphasis(audio, coef=0.97)
extract_mel(audio, n_mels=64, n_fft=1024, hop_length=625)
```

Không nên copy cùng một thuật toán vào nhiều notebook khác nhau.

### `.ipynb` — experiment orchestration + analysis

Notebook dùng để:

- mô tả hypothesis bằng Markdown cell;
- import hàm từ `.py`;
- truyền tham số experiment;
- gọi generate artifact;
- gọi train/evaluate khi cần;
- load CSV/JSON/NPY;
- vẽ biểu đồ;
- phân tích kết quả;
- ghi kết luận ngay cạnh phép thử.

Ví dụ:

```python
from audio_frontend_ablation import build_features

for order in [3, 5, 7]:
    build_features(filter_order=order)
```

Notebook **không nên trở thành source chính** của pipeline.

Logic quan trọng phải nằm trong `.py`; notebook chủ yếu điều khiển và phân tích.

### `.npy` — artifact feature trung gian

Trong pipeline hiện tại:

```text
X_*.npy
= feature đầu vào model
= Mel-Spectrogram sau preprocessing
```

Nếu thay DSP / Mel thì:

```text
X_train
X_val
X_test
```

có thể thay đổi.

Trong khi đó:

```text
Y_train
Y_val
Y_test
```

là nhãn nên **không đổi** nếu dataset và split không đổi.

`Files_*.npy` lưu tên/path nguồn tương ứng với từng sample:

```text
X_val[i]
Y_val[i]
Files_val[i]
```

ba phần tử trên phải luôn cùng chỉ số.

`Files_*.npy` đặc biệt hữu ích để truy vết sample sai, false positive, false negative hoặc sample dùng để vẽ minh họa.

Không cần duplicate `Y_*` và `Files_*` cho từng variant nếu split được giữ cố định; chỉ cần kiểm tra thứ tự file khớp baseline.

### `.csv` — bảng kết quả dễ đọc

Dùng cho:

- prediction từng sample;
- threshold sweep;
- benchmark;
- latency;
- Quality Gate;
- VAD;
- bảng metric tổng hợp.

CSV nên giữ dữ liệu đủ để có thể phân tích lại mà không phải chạy model/hardware lần nữa.

### `.json` — cấu hình hoặc kết quả đã chốt

Dùng cho các artifact dạng:

```text
final_threshold.json
benchmark_config.json
experiment_metadata.json
```

Nên lưu:

- version;
- model;
- dataset;
- seed;
- tham số experiment;
- giá trị cuối được chọn;
- ngày / trạng thái nếu cần.

### `.log` — bằng chứng runtime / hardware

Dùng cho:

- ESP32-S3;
- Gateway;
- MQTT;
- Qt6;
- long-term test;
- serial benchmark.

Không dùng log làm nguồn duy nhất nếu có thể parse thành CSV/JSON.

### `.md` — mô tả và kết luận

Mỗi experiment/folder nên có README ngắn gồm:

```text
1. Mục tiêu
2. Baseline
3. Biến thay đổi
4. Thành phần giữ cố định
5. Cách chạy
6. Artifact tạo ra
7. Kết quả
8. Kết luận
```

---

## 3. Quy tắc Validation / Test

Không dùng Test để lựa chọn tham số.

Luồng chung:

```text
Train
  ↓
Validation
  ↓
chọn threshold / config
  ↓
FREEZE
  ↓
Test đúng một lượt để báo cáo
```

Nếu sau khi xem Test lại quay về chỉnh tham số thì Test không còn là tập đánh giá cuối độc lập.

---

## 4. Quy tắc với experiment có retrain

Nếu thay một thành phần làm thay đổi feature distribution, ví dụ:

```text
Butterworth order
pre-emphasis
Mel bins
window / hop
dataset composition
```

và mục tiêu là đánh giá ảnh hưởng thực tới model, cần:

```text
generate lại X_train / X_val / X_test
        ↓
retrain cùng kiến trúc V1
        ↓
cùng seed / optimizer / callback / epoch policy
        ↓
so sánh metric
```

Không nên lấy model đã train với baseline feature rồi dùng feature distribution mới để kết luận cấu hình mới tốt/xấu, trừ khi mục tiêu chỉ là **sensitivity test**.

---

## 5. Quy tắc với experiment chỉ để minh họa / phân tích

Không phải mục nào cũng cần retrain.

Ví dụ phân tích cơ sở chọn dải tần `100–2000 Hz` có thể chỉ cần:

```text
raw waveform
frequency spectrum
filter response
filtered spectrum
Mel visualization
```

Nếu mục tiêu chỉ là giải thích lựa chọn kỹ thuật, không cần tạo thêm một model mới.

Khi đó báo cáo phải ghi rõ đây là:

> phân tích / visual justification

không phải:

> chứng minh cấu hình tối ưu bằng metric phân loại.

---

## 6. Cấu trúc khuyến nghị

```text
Experiments_Benchmarking/
└── Patient_Node/
    ├── README.md
    ├── Step_Done_V1.md
    │
    ├── Final_V1_Validation/
    │   ├── README.md
    │   ├── 01_Classification_Threshold/
    │   ├── 02_Quality_Gate/
    │   ├── 03_VAD_Distance/
    │   ├── 04_MAX30102/
    │   ├── 05_End_to_End/
    │   └── 06_Long_Term_Stability/
    │
    └── Extension/
        ├── README.md
        ├── 01_Quantization/
        ├── 02_Model_Architecture/
        ├── 03_DSP_Audio_Frontend/
        ├── 04_Mel_Ablation/
        ├── 05_Dataset_Ablation/
        ├── 06_RealWorld_Challenge/
        └── ...
```

---

## 7. Quy tắc đặt trạng thái

Dùng thống nhất:

```text
TODO
RUNNING
DONE
FROZEN
FUTURE
```

| Trạng thái | Ý nghĩa |
|---|---|
| `TODO` | chưa thực hiện |
| `RUNNING` | đang chạy / đang thu dữ liệu |
| `DONE` | đã có kết quả và kết luận |
| `FROZEN` | đã được chấp nhận làm baseline chính thức |
| `FUTURE` | chỉ giữ làm hướng phát triển |

`DONE` chưa chắc đồng nghĩa `FROZEN`.

Một experiment có thể hoàn thành nhưng không được chọn làm baseline mới.

---

## 8. Quy tắc cuối

Mỗi thay đổi phải trả lời được ba câu:

```text
1. Thay cái gì?
2. Giữ cố định cái gì?
3. Kết quả có đủ bằng chứng để thay baseline không?
```

Nếu không trả lời được ba câu này thì experiment chưa đủ rõ để dùng trong báo cáo hoặc để thay cấu hình FINAL.
