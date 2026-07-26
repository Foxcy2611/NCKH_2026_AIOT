# 📂 Cấu Trúc Thư Mục Header & Dữ Liệu Test (Include)

Thư mục này chứa toàn bộ các file header (`.h`) khai báo thư viện tự viết cho phần cứng, thuật toán xử lý tín hiệu (DSP) và mô hình AI, cùng với các tập dữ liệu mảng C giả lập để phục vụ kiểm thử.

## 1. 📁 `include/` - Cốt lõi hệ thống
Được chia thành 3 module chính tương ứng với 3 giai đoạn của luồng xử lý:

*   **`Audio_IO/`**
    *   `I2S_Mic.h`: Khai báo các hàm giao tiếp phần cứng với Micro I2S (INMP441). Quản lý luồng đọc DMA, cấu hình I2S, thuật toán VAD (nhận diện tiếng động) và máy trạng thái (State Machine) để ghi đủ 5 giây âm thanh chuẩn PCM 16-bit.
*   **`DSP_Preprocessing/`** 
    *   `DSP_Filter.h`: Chứa các hàm tiền xử lý tín hiệu miền thời gian, bao gồm bộ lọc khuếch đại tần số cao (Pre-Emphasis) và bộ lọc Butterworth Bandpass (100Hz - 2000Hz) bậc 5 (dạng SOS/Cascade Biquad) để lọc nhiễu môi trường.
    *   `Mel_Scale.h`: Trái tim của quá trình trích xuất đặc trưng. Chứa các hàm tính toán STFT (cửa sổ Hann), khởi tạo Mel Filterbank (64 dải Mel chuẩn Slaney), và thuật toán chuyển đổi năng lượng sang thang đo decibel (Power to dB) với cơ chế chặn ngưỡng dưới (Top DB).
*   **`Model_AI/`**
    *   `Interface_Asthma.h`: Giao diện lập trình AI (TFLite Micro). Quản lý việc cấp phát bộ nhớ Tensor Arena trên PSRAM, chuẩn hóa đầu vào, chạy suy luận (`Invoke`) và phân loại kết quả Hen suyễn dựa trên ngưỡng quyết định (0.35 và 0.65).
    *   `Asthma_Model.h`: Trọng số của mô hình AI phiên bản cũ.
    *   `Asthma_Model_2.h`: Trọng số của mô hình AI phiên bản mới nhất (đã được train lại và lượng tử hóa Int8). 
    > ⚠️ **Lưu ý quan trọng về Model:** Khi xuất từ script Python, mô hình mới mặc định vẫn sinh ra file tên là `Asthma_Model.h`. Để giữ lại bản cũ đối chứng mà vẫn dùng được bản mới, file đã được đổi tên thủ công thành `Asthma_Model_2.h`. Hãy xem thư mục `Training` để hiểu rõ sự khác biệt giữa hai phiên bản.

## 2. 📁 Các thư mục `Raw_Include_Phase_...` (Dữ liệu giả lập)
Các thư mục này chứa các file `.h` lưu trữ mảng C (mảng số thô của âm thanh) dùng để nạp trực tiếp vào RAM, giúp test độ chính xác của AI và DSP mà không cần Micro thực tế. Được chia làm 3 giai đoạn:

*   **`Raw_Include_Phase_1/`**: Tập dữ liệu (nhãn `0_Asthma`) được mix thêm các loại nhiễu với biên độ rất cao (ví dụ: `level = 0.005`). Đây là tập dữ liệu ban đầu, chưa được tinh chỉnh giảm nhiễu.
*   **`Raw_Include_Phase_2/`**: Tập dữ liệu đã được điều chỉnh lại hệ số mix nhiễu xuống mức hợp lý hơn. Kết quả test trên tập này đã đạt yêu cầu (OK).
*   **`Raw_Include_Phase_3/`**: Tập dữ liệu toàn diện và "hardcore" nhất. Chứa đầy đủ tất cả các thể loại Data Augmentation (White noise, Podcast, tiếng quạt/bàn phím, thay đổi cao độ Pitch, kéo giãn thời gian Time-stretch, và cả dữ liệu thực tế từ Kaggle).

```text
Các tập Raw data trên trừ Phase 1 ra, thì đều được gent từ tập dataset hoàn toàn mới
```