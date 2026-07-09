# 🚀 Kịch Bản Kiểm Thử AI (TinyML) trên ESP32-S3

Folder này mô tả quy trình 3 giai đoạn để tích hợp và kiểm thử mô hình Depthwise Separable CNN (Phân loại Hen suyễn) trên vi điều khiển ESP32-S3. Mục tiêu là đảm bảo tính chính xác, đo lường hiệu năng và tích hợp hệ thống thời gian thực (Real-time).

---

## 🟢 GIAI ĐOẠN 1: TEST TĨNH (STATIC INFERENCE)
**Project:** 1_Test_Model_Static
**Mục tiêu:** Chứng minh "bộ não" TFLite Micro có thể load thành công trọng số (`.h`) và chạy phép toán chính xác trên cấu trúc phần cứng ESP32-S3.

* **Bước 1 (Khởi động bộ não):** Cho đầu vào toàn rác (Số 0) để ESP32-S3 có thể in ra Serial, nhằm chắc chắn khởi động bộ não thành công mà không gặp các lỗi
* **Bước 2 (Chuẩn bị mồi):** Khi đảm bảo bộ não đã có thể hoạt động, xuất 1 bức ảnh Mel-Spectrogram mẫu (đã Scale Min-Max chuẩn bị từ Python) thành file mảng C (VD: `test_asthma_sample.h`).
* **Bước 3 (Khởi tạo AI):** * Cài đặt `tflite_micro` component.
  * Khai báo `tflite::MicroInterpreter` và cấp phát `tensor_arena` (dự kiến 300 Kb cho rộng rãi).
* **Bước 4 (Thực thi):** Đổ mảng dữ liệu mẫu vào `input_tensor` -> Gọi hàm `Invoke()`.
* **Bước 5 (Nghiệm thu):** In giá trị `output_tensor` ra cổng Serial. Kết quả phải khớp 100% với giá trị dự đoán lúc chạy file `.keras` trên máy tính.

---

## 🟡 GIAI ĐOẠN 2: ÉP XUNG VÀ ĐO LƯỜNG (PROFILING)
**Project:** 2_Test_Model_Profiling
**Mục tiêu:** Đánh giá tốc độ phản hồi (Latency) và giới hạn bộ nhớ SRAM của mạch.

* **Bước 1 (Đo thời gian):** Sử dụng hàm `esp_timer_get_time()` bọc quanh hàm `Invoke()`. Tính toán thời gian suy luận cho 1 khung hình (Inference Time). Yêu cầu: < 100ms.
* **Bước 2 (Tối ưu RAM):** Giảm thiểu `tensor_arena` dần dần cho đến khi báo lỗi. Chốt con số bộ nhớ tối ưu.
* **Bước 3 (Tối ưu CPU):** Đảm bảo project đã bật cấu hình tối ưu hóa phần cứng vector của ESP32-S3 (ESP-NN / DSP instruction set) trong Menuconfig.

---

## 🔴 GIAI ĐOẠN 3: TEST ĐỘNG THỜI GIAN THỰC (REAL-TIME PIPELINE)
**Project:** 3_Test_Model_LiveMic
**Mục tiêu:** Nối thông toàn bộ luồng dữ liệu từ Micro thu âm -> Tiền xử lý -> Trí tuệ nhân tạo.

* **Bước 1 (Giao tiếp phần cứng):** Khởi tạo I2S, đọc dữ liệu luồng từ Micro INMP441 (16kHz, 16-bit).
* **Bước 2 (DSP trên C/C++):** * Chạy bộ lọc Butterworth Bandpass (100Hz - 2000Hz).
  * Tính toán STFT và trích xuất Mel-Spectrogram (sử dụng màng lọc 64 Mels).
* **Bước 3 (Suy luận & Cảnh báo):** Đẩy ma trận Mel-Spectrogram vừa tính vào luồng TFLite. Đọc output liên tục, nếu vượt ngưỡng kích hoạt cảnh báo qua còi bíp, đèn LED hoặc đẩy bản tin MQTT.