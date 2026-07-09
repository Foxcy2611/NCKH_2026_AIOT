# 📂 GIAI ĐOẠN 1: `1_Test_Model_Static` (Kiểm Thử Tĩnh)

**Mục tiêu:** Kiểm tra và xác minh độ chính xác của mô hình AI (TinyML) trên vi điều khiển ESP32-S3. Quá trình này sử dụng dữ liệu tĩnh (đã được tiền xử lý và nhúng sẵn vào Flash) để đối chiếu kết quả suy luận của chip phần cứng so với kết quả huấn luyện trên máy tính (Python).

---

## 🧠 Thành phần Cốt lõi (Bộ Não AI)

### `Asthma_Model.h`
- **Vai trò:** Trái tim của toàn bộ dự án. 
- **Nội dung:** Chứa mảng mảng C tĩnh (`unsigned char`) lưu trữ toàn bộ cấu trúc mạng Nơ-ron và trọng số (weights) của mô hình TFLite sau khi convert.
- **Lưu ý:** **TUYỆT ĐỐI KHÔNG XÓA**. Hàm `tflite::GetModel()` sẽ đọc trực tiếp dữ liệu từ file này để khởi tạo bộ nhớ Tensor Arena và thiết lập đồ thị tính toán.

---

## 📊 Dữ Liệu Kiểm Thử (Input Data)

Các file này đóng vai trò là "Đề bài" để đưa vào mô hình đánh giá. Dữ liệu gốc là âm thanh (`.wav`) đã được đi qua đường ống tiền xử lý (Butterworth Filter, Pre-emphasis) và chuyển thành phổ Mel-Spectrogram lượng tử hóa (Int8).

### 1. `Sample_Asthma_1.h` (Dương tính)
- **Vai trò:** Bệnh án mẫu của bệnh nhân mắc Hen suyễn.
- **Nhãn kỳ vọng:** `Label 0` (Đầu ra Int8 sẽ là số âm sâu).

### 2. `Sample_Non_Asthma_1.h` (Âm tính)
- **Vai trò:** Bệnh án mẫu của người hô hấp bình thường (để test đối chứng).
- **Nhãn kỳ vọng:** `Label 1` (Đầu ra Int8 sẽ là số dương).

---

## ⚙️ Khối Điều Khiển (Controller)

### `Test_Asthma_1.h`
- **Vai trò:** Trạm kiểm soát thư viện TensorFlow Lite Micro.
- **Các hàm nòng cốt:**
  - `Setup_TinyML()`: Đọc Model, xin cấp phát RAM ngoài (PSRAM) cho `tensor_arena`, và khởi tạo các toán tử (Ops Resolver).
  - `Predict_Static_Dummy()`: Nhận dữ liệu đầu vào từ các file Sample, đẩy vào Tensor Input, kích hoạt hàm `Invoke()` để phân tích, đo lường thời gian (ms) và nội suy phần trăm (%) chẩn đoán bệnh lý để in ra Serial Monitor.
  - `void Predict_Static_Dummy_0()`: Cũng tương tự hàm trên nhưng đầu vào toàn rác nhằm mục đích kiểm tra bộ não còn sống và khởi tạo thành công

> *Ghi chú: Mã nguồn giao tiếp thu âm trực tiếp (I2S Mic) đã được loại bỏ ở Giai đoạn 1 để đảm bảo tính cô lập và tập trung hoàn toàn vào việc test độ chính xác thuật toán cốt lõi.*