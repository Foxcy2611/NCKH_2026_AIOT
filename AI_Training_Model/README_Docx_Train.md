# Training Pipeline README — 5 → 6 → 7 (🎵 Trích xuất → 🧠 Train → ⚡ Quantize)
Tài liệu mô tả cơ chế hoạt động của 3 script Python cốt lõi trong quy trình huấn luyện mô hình AI nhận diện Asthma, dùng để đối chiếu lại khi cần debug hoặc tái tạo pipeline.

---

## 1. `5_Extract_Features.py` — 🎵 Trích xuất Mel-Spectrogram

### Vai trò
📂 Đọc toàn bộ file `.wav` trong `Dataset/0_Asthma` và `Dataset/1_Non_Asthma`, biến mỗi file thành 1 "ảnh" Mel-Spectrogram (ma trận số), gán nhãn, rồi lưu gộp thành 2 file `.npy` để dùng train.

### Tham số cố định
| Tham số | Giá trị | Ghi chú |
|---|---|---|
| `Sr` | 16000 Hz | Sample rate chuẩn hóa mọi file về |
| `Samples` | 80000 (5.0s) | Độ dài cố định, cắt/pad nếu lệch |
| `Low_Cut / High_Cut` | 100 / 2000 Hz | Dải tần bandpass, bao trùm dải wheeze |
| `Order` | 5 | Bậc Butterworth |
| `Pre_Coef` | 0.97 | Hệ số pre-emphasis |
| `N_FFT` | 1024 | Kích thước FFT |
| `Hop_Length` | 625 | Bước nhảy giữa các frame → 129 frame/file |
| `N_Mels` | 64 | Số dải Mel |

### Pipeline `Process_Audio_File()` — 6 bước, thứ tự bắt buộc

1. Load mẫu wav (16kHz, 5s) 
2. Chuẩn hóa biên độ [-1,1] (librosa.util.normalize) 
3. Butterworth Bandpass với tần số Lowcut/Highcut trên (scipy.signal.lfilter)
4. Pre-emphasis (Phương trình: y[n] = x[n] - 0.97·x[n-1]) 
5. STFT + Mel-Spectrogram (librosa.feature.melspectrogram, mặc định htk=False + norm='slaney') 
6. power_to_db (ref=np.max, top_db=80)

**Đây chính là "khuôn mẫu vàng"** mà toàn bộ pipeline C++ trên firmware phải mô phỏng lại y hệt — bất kỳ sai lệch nào ở đây (dù nhỏ như dùng nhầm `htk=True`) sẽ khiến model học tốt trên Python nhưng hoạt động sai trên thiết bị thật.

### Output
- `X_data_mel.npy` — shape `[N, 64, 129, 1]`, giá trị đơn vị dB (luôn `≤ 0`, vì `ref=np.max`).
- `Y_labels_mel.npy` — nhãn `0` = Asthma, `1` = Non-Asthma.

Nhãn được gán theo đúng thứ tự duyệt thư mục: toàn bộ Asthma trước, Non-Asthma sau — nghĩa là trong mảng `X_data`, N file đầu luôn là Asthma. Đây là điều cần nhớ nếu lấy sample theo index thủ công (ví dụ ở bước 7 khi chọn representative dataset).

---

## 2. `6_Train_Model.py` — 🧠 Huấn luyện mô hình DS-CNN

### Vai trò
⚙️ Load `.npy` từ bước 5, chuẩn hóa thêm 1 lớp nữa (min-max global), rồi train mạng CNN nhẹ để phân loại nhị phân Asthma/Non-Asthma.

### Kiểm tra dữ liệu đầu vào (bổ sung, nên luôn làm trước khi train)
```python
print("Check NaN trong X_data:", np.isnan(X_data).any())
print("Check Inf trong X_data:", np.isinf(X_data).any())
print("Số lớp 0 (Asthma):", np.sum(Y_labels == 0))
print("Số lớp 1 (Non-Asthma):", np.sum(Y_labels == 1))
```
Nếu có `NaN`/`Inf`, hoặc 2 lớp lệch số lượng nghiêm trọng, cần quay lại bước 3 (`3_Prep_Asthma.py`) hoặc bước 5 kiểm tra lại trước khi train tiếp — train trên dữ liệu lỗi sẽ cho kết quả đánh giá (accuracy) đẹp giả tạo nhưng model thực chất không đáng tin.

### Chia tập dữ liệu
```text
100% → 80% Train / 20% Temp
Temp → 50% Validation / 50% Test
```
**Tổng kết:** Toàn bộ tập dataset được chia theo tỉ lệ cuối cùng như sau:
- 80% Train
- 10% Validation
- 10% Test

Dùng `stratify=` ở cả 2 lần chia để đảm bảo tỷ lệ 2 lớp giữ nguyên đồng đều trong mọi tập con.

### Chuẩn hóa Min-Max **toàn cục** (quan trọng nhất trong file này)
```python
min_val = np.min(X_train_np)   # chỉ tính trên tập TRAIN
max_val = np.max(X_train_np)

X_train_np = (X_train_np - min_val) / (max_val - min_val)
X_valid_np = (X_valid_np - min_val) / (max_val - min_val)   
# dùng LẠI đúng min_val/max_val
X_test_np  = (X_test_np  - min_val) / (max_val - min_val)
```
**Đây là điểm mấu chốt phải nhớ:** `min_val` và `max_val` là **2 hằng số cố định duy nhất**, tính 1 lần trên tập train, rồi áp dụng y hệt cho valid/test — **không tính lại riêng cho từng tập**, càng không tính lại theo từng mẫu đơn lẻ. Giá trị thực tế đo được: **`min_val = -80.0, max_val = 0.0`** (khớp với `top_db=80` từ bước 5). Hai con số này phải được hardcode y hệt vào code C++ khi suy luận trên firmware.

### Kiến trúc DS-CNN
1. Input (64, 129, 1)
2. SeparableConv2D(16,3×3) → BatchNorm → MaxPool2D
3. SeparableConv2D(32,3×3) → BatchNorm → MaxPool2D
4. SeparableConv2D(64,3×3) → BatchNorm → MaxPool2D (output 8×16×64)
5. Flatten (8192) → Dense(64, relu) → Dropout(0.3)
6. Dense(1, sigmoid)

`SeparableConv2D` (Depthwise + Pointwise) được chọn thay `Conv2D` thường để giảm số tham số đáng kể — phù hợp mục tiêu triển khai trên MCU (RAM/Flash hạn chế).

### Callbacks
| Callback | Vai trò |
|---|---|
| ⏹ `EarlyStopping(patience=10)` | Dừng sớm nếu `val_loss` không cải thiện |
| 📉 `ReduceLROnPlateau` | Giảm nửa learning rate nếu chững |
| 💾 `ModelCheckpoint(save_best_only=True)` | Chỉ lưu bản có `val_loss` thấp nhất |
| 🚨 `TerminateOnNaN` | Dừng ngay nếu loss NaN, tránh lãng phí thời gian train hỏng |
| 📊 `CSVLogger` | Xuất toàn bộ log (loss, metric) theo từng epoch ra file CSV để tiện phân tích sau này |
| 🌐 `TensorBoard` | Ghi log chi tiết (scalars, histogram, graph…) để trực quan hóa quá trình train trực tuyến trên trình duyệt |


`class_weight='balanced'` được thêm vào `model.fit()` — với dataset đã cân bằng sẵn 1:1 thì ảnh hưởng không đáng kể, nhưng là biện pháp an toàn nếu tỷ lệ lớp lệch nhẹ ở vòng chia tập ngẫu nhiên.

`tf.random.set_seed(42)` + `np.random.seed(42)` đặt ở đầu file — đảm bảo kết quả train **tái lập được** giữa các lần chạy khác nhau (cùng seed → cùng khởi tạo trọng số → kết quả gần giống nhau, dù không tuyệt đối 100% do 1 số phép tính GPU không xác định).

### Kết quả 2 lần train (tham khảo)
| | Phase gốc | Phase 2 (đã cải thiện data augmentation) |
|---|---|---|
| Test Accuracy | 89.00% | **96.00%** |
| Test Loss | 0.4031 | 0.1507 |
| Đỉnh Validation Loss | Vọt chạm mốc > 5.0 ở Epoch 4-5 | Bị dội nhẹ nhưng kiểm soát ổn định không bị dội |
| Validation Accuracy | Đường Valid Loss đi ngang nhưng cách 1 khoảng so với Train Loss | Valid Loss bám sát và dìm xuống sâu, tiệm cận Train Loss

Phase 2 cải thiện nhờ điều chỉnh tham số augmentation trong `3_Prep_Asthma.py` (giảm mức trộn nhiễu, tăng độ dài đoạn lõi wheeze được giữ lại) — chi tiết xem README của bước chuẩn bị dữ liệu tại đây [Prepare Dataset](Dataset/README.md).

---

## 3. `7_Quantize_Export.py` — ⚡ Lượng tử hóa INT8 & Xuất C Header

### Vai trò
📦 Nén mô hình `.keras` (float32, ~6.4MB) xuống `.tflite` int8 (~544KB, giảm ~91.5%) để vừa với bộ nhớ ESP32-S3, sau đó chuyển thành mảng C (`Asthma_Model.h`) nhúng thẳng vào firmware.

### Chuẩn bị dữ liệu (khớp đúng cách chuẩn hóa lúc train)
```python
X_min = np.min(X_train)
X_max = np.max(X_train)
X_train = (X_train - X_min) / (X_max - X_min)
```
Phải dùng **đúng công thức và tinh thần min-max toàn cục** như bước 6 — nếu lệch, quá trình hiệu chỉnh (calibration) ở bước tiếp theo sẽ tính sai khoảng giá trị thực tế của activation.

### Representative Dataset — bước dễ sai nhất, đã từng gây bug nghiêm trọng
```python
idx_class0 = np.where(Y_labels == 0)[0]
idx_class1 = np.where(Y_labels == 1)[0]

sample_idx = np.concatenate([
    np.random.choice(idx_class0, 50, replace=False),
    np.random.choice(idx_class1, 50, replace=False)
])
np.random.shuffle(sample_idx)

def Rep_Data_Gen():
    for i in sample_idx:
        yield [X_train[i:i+1]]
```
**Nguyên tắc bắt buộc:** representative dataset phải lấy đều mẫu từ **cả 2 lớp**, không được chỉ lấy từ 1 lớp (ví dụ `X_train[0:100]` — vì dữ liệu được sắp theo khối, 100 mẫu đầu toàn là Asthma do cách lưu ở bước 5). Nếu vi phạm, TFLite Converter sẽ hiệu chỉnh sai khoảng giá trị (`scale`/`zero_point`) cho các activation layer trung gian, khiến model sau khi quantize **suy biến** — luôn dự đoán về 1 phía bất kể input là gì, dù model gốc `.keras` hoạt động hoàn toàn bình thường.

### Cấu hình Converter — ép cứng toàn bộ về INT8
```python
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.representative_dataset = Rep_Data_Gen
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type = tf.int8
converter.inference_output_type = tf.int8
```
`supported_ops = TFLITE_BUILTINS_INT8` bắt buộc mọi phép toán (Conv2D, BatchNorm, Dense...) đều chạy dạng int8, không rơi về float32 lai tạp — giúp tối ưu tốc độ và kích thước tối đa trên MCU.

### Xuất C Header
```python
const int model_data_len = {len(bytedata)};
const unsigned char model_data[] __attribute__((aligned(4))) = { ... };
```
`aligned(4)` đảm bảo mảng byte căn chỉnh bộ nhớ đúng 4-byte, cần thiết cho `tflite::GetModel()` đọc đúng cấu trúc FlatBuffer bên trong.

### Kết quả quantize thực tế
- Input: `scale ≈ 0.003922, zero_point = -128`
- Output: `scale ≈ 0.003906, zero_point = -128`
- Kích thước: `6,402,662 bytes → 543,976 bytes` (giảm 91.5%)

Hai cặp `scale/zero_point` này **không cố định giữa các lần train khác nhau** — mỗi lần train lại + quantize lại sẽ cho ra số hơi khác, do đó code C++ (`Interface_Asthma.cpp`) luôn đọc động qua `input_tensor->params.scale/zero_point`, không hardcode.

---

## 4. Checklist đối chiếu bắt buộc trước khi build firmware ✅

Sau khi có `Asthma_Model.h` mới, luôn kiểm tra theo đúng thứ tự sau trước khi đưa vào ESP32:

1. 🧪 Chạy `12_Test_TF_Int8.py` — xác nhận model không suy biến  
2. 🔍 Chạy `13_Test_TF_Quantize.py` — xác nhận model phân biệt đúng vài mẫu Asthma/Non-Asthma thật  
3. 🚀 Chỉ khi cả 2 bước trên đạt, mới copy `Asthma_Model.h` vào project ESP32 và build lại firmware