# 🚀 Kịch Bản Kiểm Thử AI (TinyML) trên ESP32-S3

**Mục tiêu dự án:** Xây dựng hệ thống chẩn đoán Hen suyễn (Asthma) dựa trên âm thanh hô hấp, chạy hoàn toàn trên vi điều khiển ESP32-S3 (Edge AI) với độ trễ thấp và độ chính xác cao.

--- 

## 🟢 GIAI ĐOẠN 1: TEST TĨNH (STATIC INFERENCE)

**Project:** `1_Test_Model_Static`

**Mục tiêu:** Chứng minh "bộ não" TFLite Micro có thể load thành công trọng số (`.h`) và chạy phép toán chính xác trên cấu trúc phần cứng ESP32-S3.

*   **Bước 1 (Khởi động bộ não):** Cho đầu vào toàn rác (Số 0) để ESP32-S3 có thể in ra Serial, nhằm chắc chắn khởi động bộ não thành công mà không gặp các lỗi tràn bộ nhớ.
*   **Bước 2 (Chuẩn bị mồi):** Xuất 1 bức ảnh Mel-Spectrogram mẫu (đã Scale Min-Max chuẩn bị từ Python) thành file mảng C (VD: `test_asthma_sample.h`).
*   **Bước 3 (Khởi tạo AI):**
    *   Cài đặt `tflite_micro` component.
    *   Khai báo `tflite::MicroInterpreter` và cấp phát `tensor_arena` (dự kiến 270 KB cho rộng rãi).
*   **Bước 4 (Thực thi):** Đổ mảng dữ liệu mẫu vào `input_tensor` -> Gọi hàm `Invoke()`.
*   **Bước 5 (Nghiệm thu):** In giá trị `output_tensor` ra cổng Serial. Kết quả phải khớp với giá trị dự đoán lúc chạy file `.keras` trên máy tính.

---

## 🟡 GIAI ĐOẠN 2: ÉP XUNG VÀ ĐO LƯỜNG (PROFILING)

**Project:** `2_Test_Model_Profiling`

**Mục tiêu:** Đánh giá tốc độ phản hồi (Latency) và giới hạn bộ nhớ SRAM của mạch.

*   **Bước 1 (Đo thời gian):** Sử dụng hàm `esp_timer_get_time()` bọc quanh hàm `Invoke()`. Tính toán thời gian suy luận cho 1 khung hình (Inference Time).
*   **Bước 2 (Tối ưu RAM):** Giảm thiểu `tensor_arena` dần dần cho đến khi báo lỗi. Chốt con số bộ nhớ tối ưu.
*   **Bước 3 (Tối ưu CPU):** Đảm bảo project đã bật cấu hình tối ưu hóa phần cứng vector của ESP32-S3 (ESP-NN / DSP instruction set) trong Menuconfig.

---

## 🔴 GIAI ĐOẠN 3: KIỂM THỬ TOÀN DIỆN & XỬ LÝ NHIỄU (REAL-TIME PIPELINE)

**Project:** `3_Test_Model_LiveMic`

**Mục tiêu:** Nối thông toàn bộ luồng dữ liệu (Micro -> DSP -> AI) và giải quyết triệt để các sai lệch do nhiễu môi trường thực tế gây ra.

*   **Bước 1 (Kiểm chứng cốt lõi độc lập):** Để loại trừ lỗi do AI, hệ thống được nạp các mẫu mảng C tĩnh với đủ các kỹ thuật mix nhiễu (quạt, podcast, white noise). Kết quả chứng minh model AI dự đoán chính xác hoàn toàn trên mọi mẫu thử nghiệm. (Thư viện AI hoạt động hoàn toàn chính xác).
*   **Bước 2 (Test thực chiến với Micro):** Khởi tạo I2S, đọc dữ liệu luồng từ Micro INMP441. Chạy bộ lọc Butterworth Bandpass và trích xuất Mel-Spectrogram (64 Mels).
*   **Bước 3 (Phát hiện vấn đề phần cứng):** Khi thu bằng Micro, xuất hiện tình trạng dương tính giả (False Positive) với một trường hợp âm thanh bình thường bị cảnh báo Asthma. Nguyên nhân được xác định là do dính tạp âm và nhiễu môi trường, không phải do bug phần mềm.
*   **Bước 4 (Tinh chỉnh Final Tweaks):** Nâng cấp logic ra quyết định của hệ thống để chống nhiễu:
    *   **Phân mảnh ngưỡng (Thresholds):** Thiết lập lại các ngưỡng giới hạn trên và dưới để phân loại rõ ràng Hen suyễn và Bình thường.
    *   **Vùng đệm an toàn:** Khoảng giữa hai ngưỡng được phân loại là "Không chắc chắn" (Unsure), yêu cầu hệ thống bỏ qua và đo lại.
    *   **Voting 3 vòng:** Hệ thống sử dụng VAD (Voice Activity Detection) để bắt âm thanh, yêu cầu đo đủ 3 lần liên tiếp mới đưa ra kết luận cuối cùng nhằm loại bỏ hoàn toàn các khung thời gian bị nhiễu.
    *   **Log thống kê dài hạn:** Tích hợp bộ đếm theo dõi tổng số lần test và số lần cảnh báo để đánh giá tỷ lệ sai số.

**Lưu ý:** Bạn hoàn toàn có thể đọc qua về cách thức xây dựng các hàm tiền xử lý khi Convert từ Python qua C++ tại đây [README HÀM TIỀN XỬ LÝ](doc/)

---

## 🔵 GIAI ĐOẠN 4: ĐÓNG GÓI CHÍNH THỨC (FINAL DEPLOYMENT / NO DEBUG)

**Project:** `4_Test_Model_Official_Final`

**Mục tiêu:** Dọn dẹp mã nguồn (Clean Code), loại bỏ toàn bộ các script test và log debug của Giai đoạn 3 để tạo ra bản Source Code triển khai thực tế (Production) tối ưu và nhẹ nhất.

*   **Bước 1 (Kế thừa tinh hoa):** Chuyển giao toàn bộ bộ mã nguồn xử lý tín hiệu số (Butterworth, Pre-Emphasis, Mel-Spectrogram) và khối lượng tử hóa INT8 chuẩn xác từ Giai đoạn 3 sang.
*   **Bước 2 (Làm sạch hệ thống):**
    *   Loại bỏ hoàn toàn các file `.h` chứa mảng C giả lập (Hardcoded Data) để giải phóng không gian lưu trữ Flash.
    *   Xóa bỏ các đoạn `Serial.print` dư thừa (in ma trận DB, in raw tensor) để tiết kiệm chu kỳ CPU.
*   **Bước 3 (Luồng hoạt động tự động):** Hệ thống giờ đây chỉ chạy một vòng lặp tinh gọn duy nhất:
    *   `STATE_LISTENING`: Chờ VAD kích hoạt khi có tiếng động vượt ngưỡng năng lượng.
    *   `STATE_RECORDING`: Thu thập mảng âm thanh chuẩn 5 giây qua I2S.
    *   `STATE_PROCESSING`: Chạy Pipeline DSP.
    *   `STATE_INTERFACE`: Chạy Invoke AI, lưu kết quả Voting và tự động xuất tín hiệu cảnh báo (Buzzer/LED) nếu phát hiện Hen suyễn, sau đó quay lại trạng thái chờ.
