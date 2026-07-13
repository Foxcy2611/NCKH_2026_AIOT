# QtEnvDash-ESP32 🌡️📊

Project này sử dụng board ESP32 tiêu chuẩn để thu thập dữ liệu (Nhiệt độ & Độ ẩm) và đẩy lên MQTT Broker thông qua kết nối Wi-Fi. Một ứng dụng desktop tùy chỉnh được xây dựng bằng Qt Creator 5 sẽ đăng ký (subscribe) các topic MQTT này và trực quan hóa dữ liệu lên đồ thị theo thời gian thực.

## 🏗️ Kiến trúc hệ thống

1. **Edge Node (Phần cứng):** ESP32 (Bản thường) + Cảm biến (ví dụ: BME280/DHT22).
2. **Kết nối:** Wi-Fi (802.11 b/g/n) -> Giao thức MQTT.
3. **Message Broker:** HiveMQ.
4. **Client/GUI:** Desktop Dashboard được phát triển bằng Qt Creator 5 (C++ / QML) và module `Qt MQTT`.

## 🚀 Tính năng nổi bật

- **Thu thập dữ liệu thời gian thực:** Đọc dữ liệu nhiệt độ, độ ẩm và các thông số môi trường khác định kỳ.
- **Truyền dẫn tin cậy:** Gửi dữ liệu từ xa (telemetry) cực nhanh thông qua giao thức MQTT siêu nhẹ.
- **Dashboard tương tác:** Giao diện đẹp mắt được thiết kế trên Qt5 (hỗ trợ tốt UI/QML) để theo dõi biểu đồ và đồng hồ đo (gauge).
- **Hoạt động độc lập:** Node ESP32 kết nối thẳng vào mạng Wi-Fi nội bộ hoặc internet, dễ dàng mở rộng quy mô.

## 🛠️ Công nghệ sử dụng

- **Firmware:** Arduino Core cho ESP32 (C/C++).
- **Software:** Qt Creator 5, C++, QML.
- **Thư viện/Dependencies:**
  - `PubSubClient`.
  - `qtmqtt` (module cho ứng dụng Qt5).

## 📂 Cấu trúc thư mục

    QtEnvDash-ESP32/
    │
    ├── firmware/                 # Source code cho ESP32
    │   ├── CMakeLists.txt        # File cấu hình build (Dùng VS Code + CMake/Makefile)
    │   └── main/
    │       └── main.c            # Logic đọc cảm biến và publish bản tin MQTT
    │
    ├── software/                 # Source code ứng dụng Qt5
    │   ├── src/
    │   │   ├── main.cpp
    │   │   ├── mainwindow.cpp
    │   │   └── mainwindow.ui     # Form giao diện (hoặc file .qml nếu code Qt Quick)
    │   └── QtEnvDash.pro         # File project của Qt
    │
    └── README.md                 # Tài liệu dự án

## ⚙️ Hướng dẫn Cài đặt và Chạy

### 1. Node ESP32
1. Mở thư mục `firmware/` trong IDE của bạn (Khuyên dùng VS Code).
2. Cập nhật thông tin cấu hình mạng Wi-Fi (`SSID` & `PASSWORD`) và địa chỉ IP của MQTT Broker vào code.
3. Build (biên dịch) và flash firmware nạp thẳng xuống board ESP32.

### 2. Qt Dashboard
1. Đảm bảo máy tính của bạn đã cài đặt module `Qt MQTT` trong môi trường Qt5.
2. Mở file `software/QtEnvDash.pro` bằng phần mềm Qt Creator 5.
3. Cấu hình các thông số kết nối MQTT (IP Broker, Port, Topic) trong source code ứng dụng để khớp với phần cứng truyền lên.
4. Build và Run ứng dụng desktop.

## 👤 Tác giả
- **NgocChien Trùm VT01**