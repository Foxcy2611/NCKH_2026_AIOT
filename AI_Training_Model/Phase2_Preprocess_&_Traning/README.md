# Phase 2 - Tiền xử lý và huấn luyện model

Phase 2 có hai entry point chính và chạy độc lập với `Frontend_Benchmarking`:

1. `Preprocess_Audio.py`: chuyển WAV thành tensor Log-Mel;
2. `Training_Model.py`: chuẩn hóa, huấn luyện và đánh giá các kiến trúc.

Không script nào yêu cầu config SHA. Metadata chỉ ghi lại tham số thực sự đã dùng
để truy vết kết quả.

## 1. Đầu vào

```text
AI_Training_Model/Dataset_Chia_V2/
├── Asthma/{train,val,test}/*.wav
└── Non_Asthma_Disease/{train,val,test}/*.wav
```

Phase 2 không chia lại bệnh nhân/session và không tạo augmentation mới.

## 2. Preprocess

Chạy từ root repository:

```powershell
py -3.11 "AI_Training_Model/Phase2_Preprocess_&_Traning/Preprocess_Audio.py"
```

Pipeline mặc định:

```text
WAV -> mono/resample 16 kHz -> crop/pad 5 giây
    -> peak normalization -> Butterworth band-pass
    -> pre-emphasis nếu PRE_EMPHASIS != 0
    -> Mel power -> Log-Mel dB -> thêm channel dimension
```

Các tham số nằm ở đầu script và có thể chỉnh trực tiếp. Với mặc định hiện tại:

| Thông số | Giá trị |
|---|---:|
| Band-pass / order | 100-2.000 Hz / 5 |
| Pre-emphasis | 0.0 |
| Mel / FFT / hop | 40 / 2048 / 625 |
| Output shape | 40 x 129 x 1 |

Playback có hậu tố `__take01`/`__take02` được crop từ giây `1,0`; các WAV khác
bắt đầu từ giây `0,0`.

Đầu ra:

```text
Output_Preprocess/
├── X_train_mel.npy / Y_train_mel.npy / Files_train.npy
├── X_val_mel.npy   / Y_val_mel.npy   / Files_val.npy
├── X_test_mel.npy  / Y_test_mel.npy  / Files_test.npy
└── Preprocess_Metadata.json
```

### Vẽ hai ví dụ Asthma core qua pipeline

Script sau lấy hai WAV core ở `Asthma/train` (không phải playback hoặc
augmentation), chạy đúng các hàm DSP của `Preprocess_Audio.py` và tạo hai ảnh
gồm waveform, phổ trước/sau band-pass và Log-Mel:

```powershell
py -3.11 "AI_Training_Model/Phase2_Preprocess_&_Traning/Visualize_Two_Asthma_Core.py"
```

Mặc định trên là preset C4 hiện tại. Khảo sát lại baseline F0 hoặc vẽ cả hai:

```powershell
py -3.11 "AI_Training_Model/Phase2_Preprocess_&_Traning/Visualize_Two_Asthma_Core.py" --preset f0
py -3.11 "AI_Training_Model/Phase2_Preprocess_&_Traning/Visualize_Two_Asthma_Core.py" --preset both
```

| Preset | Band-pass | Order | Pre-emphasis | Mel | FFT | Hop | Shape |
|---|---:|---:|---:|---:|---:|---:|---:|
| `c4` | 100-2.000 Hz | 5 | 0 | 40 | 2048 | 625 | 40 x 129 |
| `f0` | 100-2.000 Hz | 5 | 0,97 | 64 | 1024 | 625 | 64 x 129 |
| `f0_noPre` | 100-2.000 Hz | 5 | 0 | 64 | 1024 | 625 | 64 x 129 |

Có thể truyền hai core khác và override từng tham số:

```powershell
py -3.11 "AI_Training_Model/Phase2_Preprocess_&_Traning/Visualize_Two_Asthma_Core.py" `
  --preset f0 `
  --files P12WheezingRS_56.wav P19WheezingIE_93.wav `
  --pre-emphasis 0.95 --n-mels 80 --n-fft 2048 --tag f0_custom
```

Các tùy chọn gồm `--low-cut`, `--high-cut`, `--order`, `--pre-emphasis`,
`--n-mels`, `--hop-length`, `--n-fft`, `--tag` và `--output-dir`. Tên ảnh chứa
preset/tag nên F0 không ghi đè C4. Script chỉ trực quan hóa, không ghi đè các
tensor `X/Y/Files_*.npy`.

## 3. Huấn luyện

```powershell
py -3.11 "AI_Training_Model/Phase2_Preprocess_&_Traning/Training_Model.py"
```

Seed mặc định là `42`. Có thể tạo một lần chạy độc lập với seed khác:

```powershell
$env:TRAIN_SEED = "44"
py -3.11 "AI_Training_Model/Phase2_Preprocess_&_Traning/Training_Model.py"
```

Script tự lấy `input_shape` từ `X_train_mel.npy`, sau đó xác minh Validation và
Test có cùng shape. Không có giả định khóa cứng `40 x 129 x 1` trong code train.

Danh sách `MODEL_ARCHITECTURES_TO_TRAIN` ở đầu file quyết định model cần chạy:

- `V1_SepConv2D_Flatten`
- `V2_SepConv2D_GAP`
- `V3_HelloEdge`
- `V4_0_MobileNet`
- `V4_1_MobileNet`
- `V5_ERespiNet`
- `V6_Azizi_SepCNN_Adapted`

Muốn chỉ train một model:

```python
MODEL_ARCHITECTURES_TO_TRAIN = ["V1_SepConv2D_Flatten"]
```

## 4. Quy tắc đánh giá

- Min/max chỉ tính từ Train.
- Train, Validation và Test dùng cùng min/max của Train.
- Tensor được cast `float32` sau min-max normalization.
- Validation điều khiển early stopping, giảm learning rate và checkpoint tốt nhất.
- Test không cập nhật trọng số; chỉ đánh giá checkpoint đã chọn.
- Ngưỡng báo cáo mặc định: `p_non_asthma >= 0.5`.

Mỗi thư mục `Output_Train_<version>/` chứa checkpoint Keras, normalization,
training log, biểu đồ lịch sử, Test report và metadata. Bảng tổng hợp của lần chạy
mới được ghi tại `Architecture_Training_Summary.csv`.

`C4_Architecture_Training_Summary.csv` và các output đã có vẫn được giữ nguyên
như bằng chứng của lần thí nghiệm trước; script generic không xóa chúng.
