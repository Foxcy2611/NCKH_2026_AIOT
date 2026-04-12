# 🫁 Edge AI & IoT: Hệ Thống Giám Sát, Dự Báo Và Cảnh Báo Sớm Hen Suyễn Đa Yếu Tố

![ESP32](https://img.shields.io/badge/MCU-ESP32%20Dual--Core-red.svg)
![OS](https://img.shields.io/badge/OS-FreeRTOS-blue.svg)
![AI](https://img.shields.io/badge/AI-Edge%20Impulse%20TinyML-orange.svg)
![Network](https://img.shields.io/badge/Network-ESP--NOW%20%7C%204G%20LTE-brightgreen.svg)

> **Đề tài Nghiên cứu:** Nghiên cứu, thiết kế và chế tạo hệ thống IoT ứng dụng TinyML trên vi điều khiển hỗ trợ theo dõi sức khỏe và các yếu tố môi trường kích thích cơn hen suyễn.

## 📝 Giới thiệu
Dự án phát triển một hệ thống nhúng phân tán (Distributed Embedded System) nhằm giám sát toàn diện bệnh nhân hen suyễn. Khác với các hệ thống truyền thống, thiết bị không chỉ đo chỉ số sinh tồn (Nhịp tim, SpO2, Âm thanh hô hấp) mà còn theo dõi liên tục các thông số môi trường xung quanh (CO2, VOC, Nhiệt độ, Độ ẩm) - vốn là các tác nhân chính gây khởi phát cơn hen. 

Trí tuệ nhân tạo (TinyML) được tích hợp trực tiếp trên Node Cảm biến (Edge AI) để phân tích dữ liệu đa kênh theo thời gian thực, đưa ra mức độ cảnh báo trước khi gửi qua Gateway 4G về trung tâm.

## 🚀 Tính năng nổi bật
- **Sensor Fusion & Edge AI:** Xử lý mô hình học máy kết hợp (Audio model + Sensor model) ngay trên ESP32 để xuất ra mức độ cảnh báo (`alert_level`) và độ tin cậy (`confidence %`) với độ trễ siêu thấp.
- **Mạng cục bộ ESP-NOW:** Truyền tải luồng dữ liệu (raw data) và trạng thái khẩn cấp giữa Sensor Node và Gateway ổn định, tiết kiệm năng lượng.
- **Hệ điều hành thời gian thực (FreeRTOS):** Quản lý đồng thời hàng loạt tác vụ đọc cảm biến phức tạp thông qua cơ chế Queue và Task Scheduler.
- **Cảnh báo Đa phương thức:**
  - *Tại chỗ:* Màn hình OLED & Buzzer.
  - *Từ xa:* Gửi tin nhắn SMS và Gọi điện khẩn cấp cho người thân qua module 4G A7680C kèm tọa độ GPS (NEO-M8N).
- **Giám sát Trung tâm:** Dashboard viết bằng QML kết hợp Firebase để lưu trữ lịch sử bệnh án trên nền tảng Cloud.

## ⭐ Sơ đồ hệ thống

<img width="1912" height="914" alt="Sodo" src="https://github.com/user-attachments/assets/474e8be7-f494-443d-b622-f38ea197b361" />

## 🏗 Kiến trúc Hệ thống

Hệ thống được thiết kế theo kiến trúc 2 Node xử lý song song, giao tiếp qua giao thức ESP-NOW:

### 1. ESP32 #1 — Sensor Node (Thu thập & Inference)
Đảm nhiệm việc đọc dữ liệu môi trường và sinh tồn, chạy mô hình AI và cảnh báo tại chỗ.
- **Lớp Cảm biến (FreeRTOS Tasks):**
  - `MAX30102`: Nhịp tim (HR) và Nồng độ Oxy máu (SpO2).
  - `INMP441`: Microphone (I2S) thu âm thanh tiếng ho/khò khè.
  - `SGP30 + MQ135`: Theo dõi nồng độ CO2 và khí gas/VOC.
  - `DHT11 + BMP280`: Theo dõi nhiệt độ, độ ẩm, áp suất khí quyển.
- **Lớp Xử lý AI:** Sử dụng Edge Impulse C++ Library để chạy song song 2 luồng nhận diện (Audio & Sensor), sau đó kết hợp (Fusion) để đưa ra mức độ cảnh báo.
- **Lớp Đầu ra:** Hiển thị OLED, kích hoạt Buzzer và gửi gói tin `{raw_data + alert_level}` qua ESP-NOW.

### 2. ESP32 #2 — Gateway (Xử lý Đám mây & Khẩn cấp)
Đóng vai trò trạm trung chuyển dữ liệu diện rộng và thiết bị cảnh báo khẩn cấp độc lập.
- **Lớp Đầu vào:** Nhận dữ liệu từ ESP-NOW; đọc liên tục tọa độ từ GPS NEO-M8N (Multi-GNSS) qua UART2.
- **Lớp Xử lý (FreeRTOS Tasks):**
  - *Task 1 (Data Logging):* Đóng gói dữ liệu và Publish lên Mosquitto Broker (Local/VPS) thông qua kết nối mạng LTE/WiFi.
  - *Task 2 (Emergency Alert):* Giám sát `alert_level`. Nếu phát hiện cơn hen nguy kịch, tự động kích hoạt module 4G A7680C để gửi SMS tọa độ và gọi điện cho bác sĩ/người nhà (Hoạt động như một Fallback khi mất kết nối Internet).

### 3. Server & Application UI
- **Mosquitto Broker:** Điều phối bản tin MQTT.
- **QML Dashboard:** Giao diện điều khiển trung tâm (C++/Qt) hiển thị Biểu đồ (Charts), Bản đồ vị trí (Map), và Bảng cảnh báo (Alert panel).
- **Firebase:** Đồng bộ và lưu trữ chuỗi dữ liệu lịch sử trên Cloud phục vụ cho việc tái huấn luyện AI sau này.

## 📂 Tổ chức Mã nguồn (Repository Structure)

```text
Asthma_EdgeAI_System/
│
├── 1_ESP32_SensorNode/          # Mã nguồn cho ESP32 #1 (Edge Impulse, Sensors, ESP-NOW TX)
│   ├── lib/edge_impulse/        # Thư viện TinyML Export từ Edge Impulse
│   ├── src/tasks/               # Chứa các FreeRTOS Tasks đọc sensor
│   └── src/main.cpp
│
├── 2_ESP32_Gateway/             # Mã nguồn cho ESP32 #2 (ESP-NOW RX, 4G, GPS, MQTT)
│   ├── src/sim_a7680c/          # Driver tập lệnh AT command cho module 4G
│   ├── src/gps_neo8m/           # Xử lý chuỗi NMEA từ GPS
│   └── src/main.cpp
│
└── 3_QML_Dashboard/             # Mã nguồn giao diện Qt/C++ giám sát trung tâm
    ├── src/mqtt_client/         # Kết nối Backend
    └── qml/views/               # Giao diện Chart, Map, Alert Panel
```

## 🛠 Cài đặt và Phát triển
- **Môi trường:** Dự án được phát triển và biên dịch bằng **PlatformIO** (VS Code) và **Qt Creator**.
- **Cấu hình phần cứng:** Vui lòng kiểm tra kỹ sơ đồ đấu nối chân (Pinout) I2C, SPI, UART, và I2S trong thư mục `docs/schematics`.

---
*Dự án NCKH thực hiện bởi: Nguyen Ngoc Chien (NgocChien Trùm VT01!) - PTIT.*
