# 🫁 IoT-TinyML Asthma Monitor: Hệ Thống Theo Dõi và Cảnh Báo Sớm Hen Suyễn

![TinyML](https://img.shields.io/badge/AI-TinyML-blueviolet.svg)
![IoT](https://img.shields.io/badge/Platform-IoT-blue.svg)
![EdgeImpulse](https://img.shields.io/badge/Training-Edge%20Impulse-orange.svg)
![Status](https://img.shields.io/badge/Status-Research--in--Progress-yellow.svg)

> **Đề tài:** Nghiên cứu, thiết kế và chế tạo hệ thống IoT ứng dụng TinyML hỗ trợ theo dõi và cảnh báo sớm cho bệnh nhân hen suyễn.

## 📝 Giới thiệu
Dự án này tập trung vào việc xây dựng một thiết bị đeo thông minh (Wearable Device) tích hợp trí tuệ nhân tạo tại biên (TinyML). Hệ thống có khả năng thu thập dữ liệu sinh học thời gian thực (nhịp tim, nồng độ oxy trong máu) và tín hiệu âm thanh (tiếng ho, tiếng thở khò khè) để đưa ra dự báo sớm về các cơn hen suyễn tiềm ẩn, giúp bệnh nhân can thiệp kịp thời.

## 🚀 Tính năng chính
- **Thu thập dữ liệu đa kênh:** Cảm biến MAX30102 thu thập nhịp tim/SpO2 và Microphone thu thập âm thanh hô hấp.
- **Xử lý AI tại biên (Edge AI):** Chạy model suy luận (Inference) trực tiếp trên Raspberry Pi để giảm độ trễ và tăng tính bảo mật dữ liệu.
- **Cảnh báo thông minh:** Phân loại trạng thái sức khỏe (Bình thường vs. Cảnh báo cơn hen) dựa trên dữ liệu cảm biến và âm thanh.
- **Giao diện Giám sát:** Dashboard trực quan hóa dữ liệu thời gian thực được viết bằng ngôn ngữ QML (Qt Framework).

## 🏗 Kiến trúc hệ thống
Hệ thống được thiết kế theo mô hình 3 tầng:

1.  **End-Node (STM32):** Thu thập dữ liệu thô (Raw data) từ cảm biến MAX30102 và Microphone.
2.  **Gateway (ESP32):** Trung chuyển dữ liệu từ End-node về Server qua giao thức không dây.
3.  **Local Server & Inference (Raspberry Pi):** Nhận dữ liệu, thực hiện suy luận TinyML và hiển thị Dashboard QML.

```text
Project_Structure/
├── 1_STM32_Firmware/        # Mã nguồn thu thập dữ liệu (C/SPL)
├── 2_ESP32_Gateway/         # Mã nguồn trung chuyển dữ liệu (WiFi/UART)
├── 3_ML_Models/             # File model .tflite và header từ Edge Impulse
├── 4_RPi_Dashboard/         # Giao diện giám sát (C++/QML)
└── 5_Data_Collector/        # Scripts Python hỗ trợ thu thập Dataset để train AI
```

## 🛠 Công nghệ & Phần cứng
- **Vi điều khiển:** STM32F103 (End-Node), ESP32-S3 (Gateway).
- **Xử lý trung tâm:** Raspberry Pi 4.
- **Cảm biến:** MAX30102 (PPG), Microphone I2S/Analog.
- **Phần mềm/Công cụ:**
  - **AI:** Edge Impulse (DSP & Training).
  - **UI:** Qt 6 (QML/C++).
  - **IDE:** Keil C, VS Code.

## 📊 Quy trình triển khai TinyML
1.  **Thu thập dữ liệu (Data Acquisition):** Ghi lại các mẫu nhịp tim và âm thanh hô hấp thực tế thông qua thiết bị.
2.  **Huấn luyện (Training):** Sử dụng Edge Impulse để trích xuất đặc trưng (DSP) và huấn luyện mô hình Neural Network.
3.  **Triển khai (Deployment):** Tối ưu hóa mô hình bằng TensorFlow Lite for Microcontrollers và tích hợp vào mã nguồn Raspberry Pi.

## 🛠 Cài đặt & Chạy thử
### Yêu cầu:
- Đã cài đặt Qt 6.x trên Raspberry Pi.
- Đã nạp Firmware cho STM32 và ESP32.

### Các bước:
1.  **Khởi động Server trên Pi:**
    ```bash
    cd 4_RPi_Dashboard
    mkdir build && cd build
    cmake ..
    make
    ./AsthmaMonitor
    ```
2.  **Kết nối thiết bị:** Đảm bảo End-node đã được cấp nguồn và kết nối cùng mạng nội bộ với Raspberry Pi.

## 📜 Giấy phép & Liên hệ
Dự án được thực hiện phục vụ mục đích nghiên cứu khoa học.
- **Người thực hiện:** Nguyen Ngoc Chien (NgocChien Trùm VT01!)
- **Đơn vị:** Khoa Điện tử Viễn thông - Học viện Công nghệ Bưu chính Viễn thông (PTIT).
