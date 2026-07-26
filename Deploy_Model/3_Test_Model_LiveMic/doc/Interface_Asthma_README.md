# Interface_Asthma — Giao tiếp với mô hình TFLite Micro

Thư viện chịu trách nhiệm nạp model đã lượng tử hóa (`.h` xuất từ `7_Quantize_Export.py`), đưa dữ liệu Mel-Spectrogram vào đúng định dạng input tensor, chạy suy luận (inference), và diễn giải kết quả.

## Tương ứng bước Python ↔ C++

| Python (lúc quantize/test) | C++ | Vai trò |
|---|---|---|
| `tf.lite.Interpreter(model_path=...)` | `tflite::MicroInterpreter` | Nạp và chạy model |
| `interpreter.allocate_tensors()` | `interpreter->AllocateTensors()` | Cấp phát bộ nhớ cho tensor |
| Chuẩn hóa `(X - min_val)/(max_val - min_val)` rồi quantize `*255-128` (trong `7_Quantize_Export.py` / `13_Test_TF_Quantize.py`) | Công thức `normalized` + `quantized` trong `Run_Asthma_Interface()` | Chuyển đổi input float → int8 |
| `interpreter.invoke()` | `interpreter->Invoke()` | Chạy suy luận |
| Đọc `output_details[0]` | Đọc `output_tensor->data.int8[0]` | Lấy kết quả |

---

## 1. `Init_Asthma_Model()` — Khởi tạo model

**Cấp phát Tensor Arena trên PSRAM** (không dùng SRAM nội bộ vì model + activation cần ~270KB, SRAM nội bộ ESP32-S3 không đủ):
```cpp
tensor_arena = (uint8_t*)heap_caps_aligned_alloc(
    16, kTensorArenaSize, 
    MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT
);
```
`aligned(16)` đảm bảo vùng nhớ căn theo 16-byte, cần thiết để các kernel TFLite Micro (vector hóa SIMD) hoạt động tối ưu.

**Kiểm tra phiên bản schema model** — đảm bảo file `.tflite` được convert bằng đúng version TFLite tương thích với thư viện runtime trên ESP32.

**`AllocateTensors()`** — bước quan trọng nhất: TFLite Micro tự tính toán cần bao nhiêu byte cho mỗi tensor trung gian (activation giữa các layer Conv2D/BatchNorm/Dense), rồi "cắt" vùng nhớ tương ứng từ `tensor_arena`. Nếu `kTensorArenaSize` không đủ, bước này thất bại.

---

## 2. Quy trình quantize input — bước dễ sai nhất

Model được train với **input đã chuẩn hóa min-max toàn cục về [0,1]**, KHÔNG PHẢI nhận thẳng giá trị dB thô. Đây là 2 bước bắt buộc phải làm đúng thứ tự:

**Bước 1 — Chuẩn hóa [0,1] bằng hằng số cố định từ lúc train:**
```cpp
// = min_val khi train 
const float TRAIN_MIN_VAL = -80.0f;   
// = max_val khi train
const float TRAIN_MAX_VAL = 0.0f;    
 
float normalized = (val - TRAIN_MIN_VAL) / TRAIN_RANGE;
(Các giá trị max min lấy từ 6_Train_Model.py)
```
**Quan trọng:** đây phải là **2 hằng số cố định**, KHÔNG được tính động theo min/max của riêng từng mẫu đưa vào lúc inference. Nếu tính động, mỗi file sẽ bị co giãn theo tỷ lệ khác nhau, không khớp với cách model đã học — đây từng là nguồn gốc 1 bug nghiêm trọng khiến model luôn dự đoán sai.

**Bước 2 — Quantize sang int8 theo scale/zero_point của chính model:**
```cpp
float quantized = normalized / input_tensor->params.scale 
                + input_tensor->params.zero_point;
```
`scale` và `zero_point` không phải số cố định do người viết code chọn — chúng được TFLite Converter **tự tính** lúc quantize (`7_Quantize_Export.py`) dựa trên representative dataset, và được nhúng sẵn trong file `.tflite`. Code C++ chỉ đọc lại 2 giá trị này qua `input_tensor->params.scale/zero_point`, không hardcode.

**Bước 3 — Clamp trước khi ép kiểu:**
```cpp
if (quantized > 127.0f) quantized = 127.0f;
if (quantized < -128.0f) quantized = -128.0f;
input_tensor->data.int8[idx] = (int8_t)quantized;
```
Bắt buộc clamp trước khi ép `(int8_t)` — nếu giá trị tính ra vượt khoảng `[-128, 127]` mà không clamp, phép ép kiểu sẽ gây tràn số (undefined behavior), làm input trở thành rác.

**Thứ tự flatten mảng 2D → 1D:**
```cpp
int idx = m * MAX_FRAMES + f;   
// duyệt mel (m) bên ngoài, frame (f) bên trong
```
Khớp đúng shape input tensor `[1, 64, 129, 1]` (64=N_MELS, 129=MAX_FRAMES) mà TFLite Converter đã ghi nhận từ lúc train — nếu đảo thứ tự (`f * N_MELS + m`), toàn bộ input sẽ bị xáo trộn dù giá trị từng phần tử đúng.

---

## 3. Đọc kết quả — Sigmoid 1 giá trị

Model dùng `Dense(1, activation='sigmoid')` ở lớp cuối — chỉ **1 giá trị output duy nhất**, không phải Softmax 2 lớp.

```cpp
int8_t raw = output_tensor->data.int8[0];
probability = (raw - zero_point) * scale;   // giải lượng tử về khoảng [0, 1]
```

**Quy ước nhãn (theo `Y_labels_mel.npy` lúc train):** `probability` gần **0** → Asthma (nhãn 0); gần **1** → Non-Asthma (nhãn 1).

---

## 4. Ngưỡng quyết định 3 mức

Thay vì chốt cứng ở `0.5`, dùng vùng "không chắc chắn" để tránh báo động giả ở các trường hợp mấp mé ranh giới:

```cpp
const float LOW_THRESHOLD = 0.35f;
const float HIGH_THRESHOLD = 0.65f;

if (probability < LOW_THRESHOLD)       → Predicted_Class = 0  (Asthma)
else if (probability > HIGH_THRESHOLD) → Predicted_Class = 1  (Normal)
else                                → Predicted_Class = -1 (Không chắc chắn)
```

Kết quả `-1` được xử lý ở tầng gọi (`I2S_Mic.cpp`) như 1 "phiếu trắng" trong cơ chế voting 3 lần đo, không tính vào cả 2 phe Asthma/Normal.