# Quy trình phân tích lỗi Model Asthma V2

## Mục tiêu

Phân tích mô hình hiện có mà **không huấn luyện lại**, nhằm xác định cụ thể:

- Asthma nào bị bỏ sót.
- Non-Asthma nào bị cảnh báo nhầm thành Asthma.
- Xác suất dự đoán của từng mẫu.
- Lỗi tập trung ở Core, Playback, bệnh lý hay môi trường nào.

## Đầu vào

Script `Analyze_Model_Errors.py` sử dụng:

```text
Output_Train_V1_SepConv2D_Flatten/Model_Asthma.keras
Output_Train_V1_SepConv2D_Flatten/Normalization_Params.txt

Output_Preprocess/X_val_mel.npy
Output_Preprocess/Y_val_mel.npy
Output_Preprocess/Files_val.npy

Output_Preprocess/X_test_mel.npy
Output_Preprocess/Y_test_mel.npy
Output_Preprocess/Files_test.npy
```

Script dùng đúng `TRAIN_MIN/TRAIN_MAX` đã lưu khi huấn luyện và ngưỡng phân
lớp `0.5`.

## Quy ước lỗi

Mô hình dùng `0 = Asthma`, `1 = Non-Asthma`; đầu ra sigmoid là xác suất
Non-Asthma.

- `ASTHMA_FN`: nhãn thật Asthma nhưng dự đoán Non-Asthma.
- `NON_ASTHMA_FP`: nhãn thật Non-Asthma nhưng dự đoán Asthma.

Tên gọi trên ưu tiên ý nghĩa lâm sàng, tránh nhầm do Asthma mang nhãn số 0.

## Cách chạy

Từ thư mục gốc dự án:

```powershell
python "AI_Training_Model/Phase2_Preprocess_&_Traning/Analyze_Model_Errors.py"
```

Script chỉ gọi `model.predict()`, không gọi `fit()` và không sửa model.

## Đầu ra

Kết quả của V1 nằm trong
`Output_Analysis_V1/Output_Analysis_Accu8931/`:

```text
Val_Predictions.csv
Test_Predictions.csv
Val_Errors.csv
Test_Errors.csv
Error_Group_Summary.csv
Analysis_Summary.md
```

Hai file `Val_Predictions.csv` và `Test_Predictions.csv` chứa toàn bộ mẫu,
bao gồm:

- Đường dẫn và tên WAV.
- Nhãn thật và nhãn dự đoán.
- Xác suất Asthma và Non-Asthma.
- Loại nguồn: Core, Playback hoặc Environment.
- Nhóm bệnh/nhóm môi trường.
- Mã bệnh nhân hoặc session.
- Loại lỗi nếu dự đoán sai.
- Cờ cho biết xác suất có nằm trong vùng `UNSURE 0.45-0.65` của thiết bị.

## Thứ tự đánh giá

1. Mở `Analysis_Summary.md` để xác nhận lại ma trận nhầm lẫn.
2. Mở `Test_Errors.csv` và lọc `error_type = ASTHMA_FN`.
3. Nghe lại các WAV Asthma bị bỏ sót, xem xác suất và nguồn Core/Playback.
4. Lọc `error_type = NON_ASTHMA_FP`.
5. Gom lỗi theo `data_group` để xem nhóm COPD, Bronchial, Healthy,
   Pneumonia hay Environment gây nhầm nhiều nhất.
6. Đối chiếu Validation và Test; không chỉnh model chỉ dựa trên riêng Test.
7. Chỉ quyết định huấn luyện lại khi lỗi có quy luật rõ ràng và có phương án
   sửa dữ liệu hợp lệ.

Không đưa trực tiếp các mẫu Test dự đoán sai trở lại Train của cùng phiên bản,
vì thao tác đó làm mất tính độc lập của tập Test.
