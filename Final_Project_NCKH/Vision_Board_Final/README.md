# 🏥 Qt Health Monitoring Dashboard - ESP32 & MQTT

[![Qt Version](https://img.shields.io/badge/Qt-6.x-green.svg)](https://www.qt.io/)
[![MQTT](https://img.shields.io/badge/Protocol-MQTT-blue.svg)](https://mqtt.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

Dự án phát triển giao diện phần mềm giám sát sức khỏe bệnh nhân từ xa. Hệ thống thu thập dữ liệu cảm biến (Nhịp tim, SpO2, Nhiệt độ, Vị trí) từ vi điều khiển **ESP32**, truyền qua giao thức **MQTT** và hiển thị trực quan theo thời gian thực trên **Qt Dashboard**.

---

## 🌟 Các tính năng chính (Features)

### 1. 👤 Quản lý thông tin bệnh nhân (Patient Profile)
* Hiển thị thông tin cá nhân: Họ tên, Tuổi, Giới tính, Nhóm máu, Tiền sử bệnh lý.
* Gắn định danh ID cho từng bệnh nhân để dễ dàng quản lý nhiều Node thiết bị cùng lúc.
### 2. 📊 Giám sát Sinh tồn & Môi trường bệnh phòng (Vital & Environmental Monitoring)
Hệ thống thu thập đồng bộ mạng lưới cảm biến đa điểm, cung cấp cái nhìn toàn diện về thể trạng bệnh nhân và chất lượng không gian điều trị:

* **Chỉ số sinh tồn (Vital Signs):**
  * **MAX30102:** Cảm biến quang học đo nhịp tim **(BPM)** và nồng độ oxy trong máu **(SpO2)** liên tục. Phát tín hiệu cảnh báo khẩn cấp khi có dấu hiệu suy hô hấp hoặc rối loạn nhịp tim.
  * **MLX90614:** Cảm biến thân nhiệt đo nhiệt độ cơ thể bệnh nhân **(°C)** không tiếp xúc. Đảm bảo giám sát nhiệt độ cơ thể liên tục, phát hiện sớm nguy cơ sốt.

* **Chỉ số môi trường phòng bệnh (Indoor Environment):**
  * **BMP280:** Đo áp suất khí quyển và nhiệt độ môi trường với độ chính xác cao. Dữ liệu áp suất hỗ trợ đánh giá các yếu tố tác động đến bệnh nhân có bệnh lý nền về đường hô hấp.
  * **DHT11:** Chuyên trách giám sát độ ẩm không khí (%), đảm bảo không gian lưu trú của bệnh nhân luôn ở mức tiêu chuẩn, tránh tác nhân gây nấm mốc.
  * **SGP30 (Indoor Air Quality):** Giám sát chất lượng không khí thông qua việc đo lường nồng độ **eCO2** (Carbon Dioxide tương đương) và **TVOC** (Hợp chất hữu cơ dễ bay hơi), giúp cảnh báo khi phòng bệnh quá ngột ngạt hoặc có mùi hóa chất y tế độc hại.

### 3. 📍 Theo dõi vị trí (GPS Tracking)
* Tích hợp dữ liệu từ module định vị vệ tinh **NEO-M8N**.
* Hiển thị tọa độ (Vĩ độ, Kinh độ) hiện tại của bệnh nhân với độ trễ thấp và độ chính xác cao.
* Cảnh báo địa lý (Geofencing) nếu bệnh nhân di chuyển ra khỏi khu vực an toàn (Tùy chọn mở rộng).

### 4. 🚨 Hệ thống cảnh báo & Thông báo khẩn cấp (Alert & SOS System)
* **Cảnh báo lâm sàng (Clinical Alerts):** Giao diện tự động nhấp nháy đỏ/phát âm thanh khi các chỉ số sinh tồn vượt ngưỡng an toàn (VD: Nhịp tim > 100 bpm, SpO2 < 90%).
* **Cảnh báo SOS (Emergency Notifications):** Nhận tín hiệu từ nút nhấn SOS cứng trên thiết bị đeo.
* **Tích hợp viễn thông (Thông qua A7680C 4G LTE):** Tự động thực hiện cuộc gọi khẩn cấp hoặc gửi tin nhắn SMS chứa dữ liệu sinh tồn và tọa độ GPS đến người nhà/bác sĩ khi có sự cố nghiêm trọng, đảm bảo kết nối liên tục độc lập với Wi-Fi.

### 5. 💾 Lưu trữ & Xuất dữ liệu (Data Logging - *Dự kiến*)
* Lưu trữ lịch sử đo đạc vào CSDL cục bộ (SQLite) hoặc file JSON.
* Hỗ trợ xuất báo cáo định kỳ dưới dạng file CSV/PDF.

---

## 🛠 Công nghệ & Thư viện sử dụng (Tech Stack)

* **Frontend:** QML, Qt Quick Controls (Thiết kế UI/UX hiện đại, hỗ trợ Dark/Light Theme).
* **Backend:** C++17, Qt Core.
* **Networking/IoT:** Thư viện `QtMqtt` (Giao tiếp với HiveMQ Broker qua cổng 8883/SSL).
* **Phần cứng tương thích:** Thiết bị Node chạy ESP32, lập trình bằng C/C++ (FreeRTOS/Arduino framework).

---

## 🚀 Hướng dẫn cài đặt & Build (Getting Started)

### Yêu cầu hệ thống (Prerequisites)
1. Cài đặt [Qt Creator](https://www.qt.io/download) với framework Qt 6.x trở lên.
2. Cài đặt C++ Compiler (MinGW 11.2+ hoặc MSVC 2019+).
3. Đã biên dịch và cài đặt thư viện `qtmqtt` vào thư mục Qt (Tham khảo hướng dẫn build qtmqtt).

### Các bước chạy dự án
1. Clone repository này về máy.
2. Mở file `Dashboard_NCKH.pro` hoặc `CMakeLists.txt` bằng Qt Creator.
3. Cập nhật thông tin kết nối MQTT Broker (Host, Port, Username, Password) trong file `MqttHandler.cpp`.
4. Nhấn **Run (Ctrl + R)** để biên dịch và chạy Dashboard.

---

## 📝 Kiến trúc luồng dữ liệu (Data Flow)
`[Cảm biến MAX30102, GPS, DHT11]` ➡️ `[ESP32 Node]` ➡️ *(Publish JSON via WiFi)* ➡️ `[HiveMQ Cloud Broker]` ➡️ *(Subscribe)* ➡️ `[Qt C++ Backend]` ➡️ *(Data Binding)* ➡️ `[QML Dashboard]`

---

## 👨‍💻 Tác giả (Author)
* **NgocChien Trùm VT01** 
* Viện Công nghệ Bưu chính Viễn thông (PTIT)
* Liên hệ: foeveralone2611@gmail.com