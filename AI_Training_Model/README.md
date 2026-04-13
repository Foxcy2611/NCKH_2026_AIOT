# 🌐 Asthma TinyML: Hệ thống Cảnh báo Hen suyễn tại biên

Dự án nghiên cứu khoa học: Hệ thống cảnh báo hen suyễn sớm sử dụng trí tuệ nhân tạo tại biên (Edge AI), kết hợp phân tích âm thanh hô hấp và các chỉ số sinh tồn/môi trường trên nền tảng vi điều khiển.

## 💻 Cài đặt Môi trường (Setup & Run)
Để chạy các script huấn luyện AI trong thư mục này, vui lòng cài đặt các thư viện Python sau:

    pip install numpy soundfile librosa scikit-learn tensorflow matplotlib

---

## 🚀 Quy trình Huấn luyện AI Model (Training Pipeline)

### 🗂️ Giai đoạn 1: Thu thập & Gán nhãn (Data Collection & Labeling)
> **💡 Lưu ý:** AI không học từ không khí, nó học từ ví dụ. Cần chuẩn bị dữ liệu đầu vào cực kỳ chuẩn.

* **🎤 Với INMP441 (Âm thanh):** Thu thập hàng trăm/ngàn file .wav ngắn (1-2 giây) ở tần số lấy mẫu 16kHz và chia vào các thư mục:
  * 🤧 `Cough_asthma`: Ho do hen suyễn
  * 😮‍💨 `Wheeze`: Tiếng ho do các bệnh khác (Số lượng ít hơn nhiều so với hen suyễn)
  * 🗣️ `Normal_speech`: Tiếng nói chuyện bình thường
  * 🚗 `Background_noise`: Nhiễu môi trường (tiếng quạt, tiếng đường phố)

* **🩸 Với Cảm biến (SpO2, Bụi mịn, Khí độc):** Thu thập các mảng số liệu tương ứng với các trạng thái: Bình thường, Nguy cơ, Đang lên cơn hen.

### ⚙️ Giai đoạn 2: Tiền xử lý (Preprocessing)
> **⚠️ Cảnh báo:** Không đưa nguyên sóng âm thô vào Model. Sử dụng thư viện librosa để biến đổi.

* **🎵 Trích xuất đặc trưng âm thanh:** Chuyển sóng âm thành biểu đồ đặc trưng **MFCC**. Quá trình này biến đổi âm thanh thô thành một ma trận số liệu toán học gọn gàng mà vi điều khiển có thể xử lý được.
* **⚖️ Chuẩn hóa (Normalization):** Đưa tất cả dữ liệu cảm biến (SpO2, AQI...) về cùng một hệ quy chiếu (vd: từ 0 đến 1) bằng Scikit-learn để tránh việc AI bị lệch trọng số.

### 🧠 Giai đoạn 3: Huấn luyện (Training)
> **🏗️ Luyện đan:** Sử dụng TensorFlow/Keras để nhào nặn Mạng Nơ-ron.

* Định nghĩa kiến trúc mô hình (ví dụ: một mạng **CNN 1D** hoặc mạng Dense nhỏ gọn để phân tích MFCC).
* Đưa dữ liệu đã tiền xử lý vào huấn luyện qua nhiều vòng (**Epochs**).
* Quá trình này tối ưu hóa 2 đường cong cốt lõi: **Đường Loss** (Độ lỗi - càng thấp càng tốt) và **Đường Accuracy** (Độ chính xác - càng cao càng tốt).

### 🕵️‍♂️ Giai đoạn 4: Đánh giá & Tinh chỉnh (Evaluation & Tuning)
> **🛑 Kiểm tra:** Dùng bộ dữ liệu "Lạ" (Validation/Test Set) để đánh giá thực tế.

* **Bắt bệnh "Học Vẹt" (Overfitting):** Nếu AI nhận diện đúng 95% dữ liệu học, nhưng chỉ đoán đúng 50% dữ liệu test thực tế -> Mô hình đã bị Overfitting.
* Tiến hành tinh chỉnh: Thêm nhiễu (Data Augmentation), giảm bớt lớp Nơ-ron, hoặc thêm các lớp Dropout.

### 📦 Giai đoạn 5: Triển khai lên ESP32 (Deployment)
> **🚀 Nhét não vào vi điều khiển:** Xử lý file model Keras (.h5) để chạy trên MCU.

1. 🗜️ Dùng **TFLite Converter** ép model từ dạng số thực 32-bit xuống số nguyên 8-bit siêu nhẹ (**Quantization**).
2. 📄 Chuyển đổi file .tflite thành một mảng code C/C++ (Hex array).
3. ⚡ Nạp mảng C++ đó vào bộ nhớ của **ESP32**, gọi hàm Invoke() của thư viện **TensorFlow Lite Micro**.

---
*Trạm AI tại biên (Edge Node) hoàn chỉnh, sẵn sàng hoạt động độc lập và thời gian thực!*
