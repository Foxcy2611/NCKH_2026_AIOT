# Phase 3 - Lượng tử hóa mô hình

Phase này nhận checkpoint Keras và tham số chuẩn hóa do Phase 2 tạo ra, sau đó
chuyển mô hình sang TFLite, lượng tử hóa, đánh giá trên tập test và sinh header C
để chuẩn bị triển khai trên ESP32-S3.

Luồng sử dụng chính được giữ đơn giản:

```text
Sửa Config.py
      ↓
Chạy Quantize_Model.py
      ↓
TFLite + header C + dự đoán + báo cáo
```

## 1. Các phương pháp được tạo

Mỗi lần chạy tạo và đánh giá năm biểu diễn của cùng một checkpoint:

| Biểu diễn | Mục đích |
|---|---|
| Keras FP32 | Baseline checkpoint gốc |
| TFLite FP32 | Kiểm tra sai số do chuyển đổi Keras sang TFLite |
| PTQ INT8 | Lượng tử sau huấn luyện, weights và activations INT8 |
| QAT INT8 | Fine-tune có mô phỏng lượng tử rồi xuất INT8 |
| PTQ INT16x8 | Activations INT16, weights INT8 |

PTQ dùng mẫu đại diện từ tập train để hiệu chuẩn miền số. QAT dùng train để cập
nhật trọng số và validation để theo dõi quá trình fine-tune. Tập test chỉ được dùng
sau khi đã tạo xong các model để tính chỉ số cuối.

## 2. File nào cần giữ?

### Entry point

- `Config.py`: nơi duy nhất người dùng chọn checkpoint và cấu hình lần chạy.
- `Quantize_Model.py`: script duy nhất cần chạy trực tiếp.

### Module lõi được import tự động

- `Data_Utils.py`: đọc `.npy` và chuẩn hóa bằng `TRAIN_MIN`, `TRAIN_MAX` của Phase 2.
- `Quantizers.py`: chuyển FP32, PTQ INT8, QAT INT8, PTQ INT16x8 và sinh header.
- `Inference.py`: chạy suy luận Keras/TFLite, xử lý scale và zero-point.
- `Report_Utils.py`: tính metric, lưu dự đoán và báo cáo.

Không chạy trực tiếp bốn module trên.

Các thư mục `Output_Quantize_*`, `Batch_Logs`, các CSV tổng hợp và báo cáo so sánh
đang có là kết quả lịch sử. Chúng không tham gia vào lần chạy mới và có thể lưu lại
làm bằng chứng thực nghiệm.

## 3. Input bắt buộc từ Phase 2

Ví dụ với V1:

```text
Phase2_Preprocess_&_Traning/
├── Output_Preprocess/
│   ├── X_train_mel.npy
│   ├── Y_train_mel.npy
│   ├── X_val_mel.npy
│   ├── Y_val_mel.npy
│   ├── X_test_mel.npy
│   ├── Y_test_mel.npy
│   └── Files_test.npy
└── Output_Train_V1_SepConv2D_Flatten/
    ├── Model_Asthma.keras
    └── Normalization_Params.txt
```

`Normalization_Params.txt` phải chứa:

```text
TRAIN_MIN=<giá trị>
TRAIN_MAX=<giá trị>
```

Mọi model được so sánh phải dùng đúng bộ đặc trưng `.npy` và đúng normalization
đã dùng khi huấn luyện checkpoint đó.

## 4. Chọn model trong `Config.py`

Chỉ sửa khối **CẤU HÌNH NGƯỜI DÙNG** ở đầu file:

```python
SEED = 42
MODEL_VERSION = "V1"
MODEL_SOURCE_FOLDER = "Output_Train_V1_SepConv2D_Flatten"
OUTPUT_FOLDER = f"Output_Quantize_{MODEL_VERSION}"
```

Ba giá trị liên quan phải đồng bộ:

| Biến | Ý nghĩa | Ví dụ |
|---|---|---|
| `MODEL_VERSION` | Tên ngắn dùng đặt tên TFLite/header | `"V3"` |
| `MODEL_SOURCE_FOLDER` | Folder model tương ứng trong Phase 2 | `"Output_Train_V3_HelloEdge"` |
| `OUTPUT_FOLDER` | Folder nhận output, nên riêng cho từng model | `"Output_Quantize_V3"` |

Các tham số nâng cao cũng nằm trong `Config.py`:

- `REPRESENTATIVE_PER_CLASS`: số mẫu train mỗi lớp dùng cho PTQ.
- `THRESHOLD`: ngưỡng chuyển xác suất thành nhãn.
- `QAT_EPOCHS`, `QAT_BATCH_SIZE`, `QAT_LEARNING_RATE`: cấu hình QAT.
- `QAT_PATIENCE` và nhóm `QAT_REDUCE_LR_*`: early stopping và giảm learning rate.

## 5. Cách chạy

Mở PowerShell tại root repository:

```powershell
py -3.11 "AI_Training_Model/Phase3_Quantization_Model/Quantize_Model.py"
```

Hoặc mở terminal ngay trong `Phase3_Quantization_Model`:

```powershell
py -3.11 .\Quantize_Model.py
```

Script tự động:

1. Kiểm tra và nạp checkpoint Keras.
2. Đọc train, validation, test đã preprocess.
3. Chuẩn hóa bằng tham số từ checkpoint Phase 2.
4. Tạo TFLite FP32.
5. Tạo PTQ INT8.
6. Fine-tune và tạo QAT INT8.
7. Tạo PTQ INT16x8.
8. Chạy cả năm biểu diễn trên tập test.
9. Ghi prediction, metric, model và header C.

## 6. Output

Với `MODEL_VERSION = "V1"`, output mặc định là:

```text
Output_Quantize_V1/
├── models/
│   ├── V1_FP32.tflite
│   ├── V1_PTQ_INT8.tflite
│   ├── V1_QAT_INT8.tflite
│   └── V1_PTQ_INT16x8.tflite
├── headers/
│   ├── V1_PTQ_INT8.h
│   ├── V1_QAT_INT8.h
│   └── V1_PTQ_INT16x8.h
├── qat/
│   ├── V1_QAT.keras
│   └── QAT_Training_Log.csv
├── Quantization_Predictions.csv
└── Quantization_Report.txt
```

## 7. Lưu ý khi chạy lại

- Nếu muốn giữ kết quả cũ, đổi `OUTPUT_FOLDER` trước khi chạy.
- Nếu giữ nguyên `OUTPUT_FOLDER`, các file cùng tên có thể bị ghi đè.
- Không sửa `Data_Utils.py` hoặc `Quantizers.py` chỉ để đổi checkpoint.
- Không dùng test để chọn epoch hoặc cập nhật trọng số.
- Trước khi đưa header vào firmware, đối chiếu input shape, dtype, scale, zero-point
  và preprocessing với Patient Node.

