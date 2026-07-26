# 🩺 Final Source: TinyML Asthma Detection (ESP32-S3)

Kho lưu trữ này chứa toàn bộ mã nguồn **chính thức (Final)** cho hệ thống nhận diện Hen suyễn (Asthma) chạy trên vi điều khiển ESP32-S3. 

Đây là phiên bản mã nguồn đã được đóng gói gọn gàng trên nền tảng **PlatformIO**, sẵn sàng mang đi deploy và ứng dụng thực tế (Production-ready).

---

## 📌 1. Thông tin phiên bản & Trạng thái dự án

*   **Nguồn gốc:** Source code này được trích xuất và kế thừa trực tiếp từ **Project 3** (Giai đoạn phát triển và thử nghiệm tổng hợp).
*   **Trạng thái Code:** 
    *   **Clean Source:** Toàn bộ các comment nháp, code test, script Python tiền xử lý, và các file dữ liệu thô (Raw Data) đã được dọn sạch bong.
    *   **Sẵn sàng làm việc:** Chỉ giữ lại các module C/C++ cốt lõi nhất. Mô hình AI đã được lượng tử hóa tối ưu và tích hợp sẵn vào mã nguồn.

---

## 📂 2. Cấu trúc Source Code

Dự án được tổ chức theo chuẩn cấu trúc của PlatformIO. Toàn bộ logic chia theo từng module rất rõ ràng:

```text
📦 4_TEST_MODEL_COMPLETE
 ┣ 📂 .pio/                   # ⚙️ Thư mục build tự động của PlatformIO (ẩn)
 ┣ 📂 .vscode/                # ⚙️ Cấu hình môi trường VS Code
 ┣ 📂 include/                # 📁 Chứa các file Header (.h)
 ┃ ┣ 📂 Audio_IO/             
 ┃ ┃ ┗ 📜 I2S_Mic.h           # Cấu hình giao tiếp I2S với Microphone
 ┃ ┣ 📂 DSP_Preprocessing/    
 ┃ ┃ ┣ 📜 DSP_Filter.h        # Khai báo bộ lọc tín hiệu (Butterworth)
 ┃ ┃ ┗ 📜 Mel_Scale.h         # Khai báo biến đổi STFT & Mel-Spectrogram
 ┃ ┣ 📂 Model_AI/             
 ┃ ┃ ┣ 📜 Asthma_Model.h      # Trọng số mạng nơ-ron AI (Mảng C - Định dạng INT8)
 ┃ ┃ ┗ 📜 Interface_Asthma.h  # Giao tiếp với TensorFlow Lite Micro
 ┃ ┗ 📜 README                
 ┣ 📂 lib/                    # 📚 Thư mục chứa thư viện ngoài (Nếu có)
 ┃ ┗ 📜 README                
 ┣ 📂 src/                    # 💻 Chứa các file mã nguồn chính (.cpp)
 ┃ ┣ 📜 DSP_Filter.cpp        # Cài đặt logic bộ lọc tín hiệu số
 ┃ ┣ 📜 I2S_Mic.cpp           # Cài đặt logic đọc dữ liệu I2S Mic & phát hiện VAD
 ┃ ┣ 📜 Interface_Asthma.cpp  # Cài đặt logic chạy suy luận AI
 ┃ ┣ 📜 main.cpp              # Chương trình chính (Chứa FreeRTOS Tasks)
 ┃ ┗ 📜 Mel_Scale.cpp         # Cài đặt logic tính toán phổ Mel
 ┣ 📂 test/                   # 🧪 Thư mục dành riêng cho code Unit Test
 ┣ 📜 .gitignore              # 🚫 Bỏ qua các file không cần đẩy lên Git
 ┣ 📜 platformio.ini          # 🛠️ File cấu hình board, framework & thư viện của PlatformIO
 ┗ 📜 README.md               # 📝 Tài liệu hướng dẫn này

## 🚀 3. Hướng dẫn Build & Deploy (PlatformIO)

Vì dự án dùng hệ thống PlatformIO nên việc biên dịch và nạp code cực kỳ đơn giản, không cần cấu hình phức tạp hay dùng command line.

**Bước 1: Chuẩn bị môi trường 💻**
*   Cài đặt **Visual Studio Code (VS Code)**.
*   Tải và cài đặt Extension **PlatformIO IDE** trong VS Code.

**Bước 2: Build và Nạp Code (Flash) ⚡**
*   Mở thư mục `4_TEST_MODEL_COMPLETE` bằng VS Code.
*   Đợi PlatformIO khởi tạo dự án và tự động tải các thư viện cần thiết (nếu có) dựa trên file `platformio.ini`.
*   Kết nối mạch **ESP32-S3** với máy tính qua cáp USB.
*   Nhấn nút **Upload** (Biểu tượng mũi tên `→` ở thanh trạng thái dưới cùng của VS Code) để tiến hành biên dịch và nạp thẳng xuống board.

**Bước 3: Kiểm tra hoạt động (Monitor) 🔍**
*   Nhấn nút **Serial Monitor** (Biểu tượng phích cắm `🔌` ngay cạnh nút Upload) để mở giao diện Terminal.
*   Theo dõi kết quả chẩn đoán bệnh và log hệ thống in ra từ ESP32-S3 theo thời gian thực.