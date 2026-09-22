# ESP32-Qt-Telemetry 🌡️📊

Project này kiểm chứng (Test) sử dụng board ESP32 tiêu chuẩn để thu thập dữ liệu (Nhiệt độ & Độ ẩm) và đẩy lên MQTT Broker thông qua kết nối Wi-Fi. Một ứng dụng desktop tùy chỉnh được xây dựng bằng Qt Creator 6 sẽ đăng ký (subscribe) các topic MQTT này và trực quan hóa dữ liệu lên đồ thị theo thời gian thực.

## 🏗️ Kiến trúc hệ thống

1. **Edge Node (Phần cứng):** ESP32 (Bản thường) + Cảm biến (ví dụ: DHT11/BME280).
2. **Kết nối:** Wi-Fi (802.11 b/g/n) -> Giao thức MQTT.
3. **Message Broker:** HiveMQ (Public Cloud Broker).
4. **Client/GUI:** Desktop Dashboard được phát triển bằng Qt Creator 6 (C++ / QML) và module `Qt MQTT`.

## 🚀 Tính năng nổi bật

- **Thu thập dữ liệu thời gian thực:** Đọc dữ liệu nhiệt độ, độ ẩm và các thông số môi trường định kỳ.
- **Truyền dẫn tin cậy:** Gửi dữ liệu từ xa (telemetry) cực nhanh thông qua giao thức MQTT siêu nhẹ.
- **Dashboard tương tác:** Giao diện đẹp mắt được thiết kế trên Qt 6 (QML) để theo dõi biểu đồ và dữ liệu mượt mà.
- **Hoạt động độc lập:** Node ESP32 kết nối thẳng vào mạng Wi-Fi nội bộ hoặc internet, dễ dàng mở rộng quy mô.

## 🛠️ Công nghệ sử dụng

- **Firmware:** Arduino Core cho ESP32 (C/C++).
- **Software:** Qt Creator 6, MinGW 64-bit, C++, QML, HiveMQ.
- **Thư viện/Dependencies:**
  - `PubSubClient` (cho ESP32).
  - `qtmqtt` (module cho ứng dụng Qt 6).

## 📂 Cấu trúc thư mục

    ESP32-Qt-Telemetry/
    │
    ├── firmware/                 # Source code cho ESP32
    │   ├── platformio.ini        # File cấu hình thư viện (PlatformIO)
    │   └── src/
    │       └── main.cpp          # Logic đọc cảm biến và publish bản tin MQTT
    │
    ├── software/                 # Source code ứng dụng Qt 6
    │   ├── CMakeLists.txt        # File cấu hình build CMake
    │   ├── main.cpp              # Core C++ và Backend
    │   └── Main.qml              # Giao diện UI Dark Mode
    │
    └── README.md                 # Tài liệu dự án

## ⚙️ Luồng triển khai & Cài đặt (Workflow)

### Giai đoạn 1: Cấu hình Phần cứng ESP32
1. **Đấu nối:** Kết nối chân tín hiệu (DATA) của cảm biến DHT11 vào chân GPIO (mặc định là GPIO4) trên ESP32.
2. **Môi trường:** Mở mã nguồn phần cứng bằng **VS Code** (sử dụng PlatformIO IDE).
3. **Cài đặt:** Điền thông tin mạng Wi-Fi (SSID, Password) và thiết lập Topic MQTT trong mã nguồn. Khai báo Broker là `broker.hivemq.com`.
4. **Nạp Firmware:** Compile và nạp code xuống board mạch.

### Giai đoạn 2: Cấu hình Phần mềm Qt 6
1. **Môi trường:** Mở dự án bằng phần mềm **Qt Creator**. Hệ thống sử dụng bộ công cụ hiện đại **CMake** để quản lý tiến trình biên dịch thay vì `.pro` (qmake) cũ.
2. **Chọn Kit:** Lựa chọn trình biên dịch `Desktop Qt 6.x.x MinGW 64-bit`.
3. **Thư viện:** Đảm bảo hệ thống đã cài đặt và cấu hình thành công module `Qt MQTT`.
4. **Khởi chạy:** Nhấn `Ctrl + R` (Run) hoặc biểu tượng tam giác xanh để phần mềm tự động biên dịch, liên kết đến Broker và hiển thị Dashboard.

## 🔄 Cơ chế Hoạt động

### 1. Trạm phát:
**ESP32 đọc dữ liệu:** ESP32 giao tiếp với DHT11 rồi ➡️ data lên Broker

### 2. Broker:
**Điểm trung chuyển:** Dùng HiveMQ làm bưu điện, ESP32 cứ push data liên tục lên đây 

### 3. Trạm thu:
**Qt thu dữ liệu:** Thay vì dùng web, sử dụng phần mềm t 6 (C++/QML) lấy data về vẽ lên giao diện Desptop (file `.exe`)

## 💡 Các Lưu ý Quan trọng

Trong quá trình thiết kế và vận hành hệ thống IoT này, có 3 điểm cốt lõi về kiến trúc mạng và phần mềm cần nắm rõ:

### 1. Broker HiveMQ có cần treo 24/24 không?
**Không cần tự thiết lập server!** Hệ thống sử dụng Public Cloud Broker (`broker.hivemq.com`). Đây là máy chủ đám mây quốc tế luôn hoạt động 24/7. 
* Nhiệm vụ của phần cứng ESP32 là chỉ cần có nguồn điện và kết nối Wi-Fi, nó sẽ tự động đẩy (Publish) gói tin lên server này một cách độc lập.
* **Lưu ý cực kỳ quan trọng:** Vì sử dụng bưu điện công cộng (ai cũng có thể truy cập), bắt buộc phải đặt tên Topic MQTT thật "độc lạ" (Ví dụ: `ngocchien/vt01/nckh2026/dht11_data`) để dữ liệu không bị xung đột với các sinh viên hoặc thiết bị của người khác.

### 2. Ứng dụng Desktop Qt có cần bật 24/24 để nhận data?
**Không! Chỉ cần khởi chạy khi có nhu cầu giám sát.**
* Giao thức MQTT hoạt động giống như nguyên lý phát sóng truyền hình: ESP32 (Đài phát) liên tục đẩy gói tin lên Broker. Ứng dụng Qt `.exe` (Tivi) đóng vai trò là Subscriber.
* Khi bật phần mềm, nó sẽ ngay lập tức "bắt sóng" và hiển thị các thông số ở đúng thời điểm hiện tại. Khi tắt ứng dụng, ESP32 vẫn gửi data lên mạng bình thường. *(Lưu ý: Với mô hình Pub/Sub tiêu chuẩn này, nếu muốn xem lại lịch sử dữ liệu trong lúc app tắt, hệ thống sẽ cần mở rộng thêm Cơ sở dữ liệu - Database ở giai đoạn sau).*

### 3. Giao tiếp giữa Backend C++ và Giao diện QML
Sự kết hợp giữa nhân C++ và đồ họa QML diễn ra cực kỳ tối ưu theo 3 bước:
* **Thu thập (C++ `QMqttClient`):** Chạy ngầm, kết nối với Broker qua TCP/IP và Subscribe topic để hứng các gói tin định dạng JSON.
* **Bóc tách (C++ JSON Parser):** Phân tích chuỗi dữ liệu đầu vào (VD: `{"temp": 25.5}`) để trích xuất các giá trị số thực.
* **Tương tác UI (Signals/Slots):** C++ sử dụng cơ chế phát tín hiệu (`Signals`) hoặc thuộc tính `Q_PROPERTY` để truyền data lên QML. Nhờ đó, các biến trên UI nhận được dữ liệu sẽ tự động nội suy (binding), giúp các thành phần đồ họa nảy số mượt mà không cần tải lại toàn bộ khung hình.

---

## 📸 Hướng dẫn Setting Hive MQ và Library trên ESP32

### Bước 1: Setup bưu điện HiveMQ
Ấn vào `Create New Cluster` để tạo 1 tài khoản, thực hiện các bước theo các tab sau
* **Overview:** Có 2 thông tin cần lưu ý là `URL` và `Port`
* **Getting Started:** Tạo 1 thông tin đăng nhập bằng cách nhập vào Username và Password
* **Web Cilent:** Nhập user và pass để tiến hành kết nối ESP32 gửi data

### Bước 2: Setup Môi trường phần cứng (ESP32)
Để ESP32 có thể giao tiếp MQTT và đọc cảm biến, cần cài đặt các thư viện `PubSubClient` và `DHT sensor library` (Hoặc sử dụng trực tiếp thư viện mà tôi đã viết lại).

> **[📸 CHÈN ẢNH HƯỚNG DẪN SETUP THƯ VIỆN CHO ESP32 TẠI ĐÂY (PlatformIO / Arduino IDE)]**

---

## ⚙️ Hướng dẫn cài đặt và cấu hình thư viện Qt MQTT

Dự án này sử dụng module `Qt6::Mqtt` để giao tiếp với MQTT Broker. Vì `qtmqtt` không có sẵn trong bộ cài mặc định của Qt, bạn cần tự build và tích hợp nó vào lõi Qt theo các bước sau:

### 1. Build và Install thư viện `qtmqtt`
* Clone mã nguồn `qtmqtt` tương ứng với phiên bản Qt đang sử dụng (VD: Qt 6.11.0).
* Sử dụng `qt-cmake` để cấu hình và build (Lưu ý ép dùng MinGW để tránh lỗi NMake trên Windows):
  ```bash
  qt-cmake -G "MinGW Makefiles" ..
  cmake --build .
  cmake --install .
  ```
* Sau khi install thành công, module sẽ tự động được thêm vào thư mục lõi của Qt (VD: `D:\Qt_Path\6.11.0\mingw_64`).

### 2. Cấu hình `CMakeLists.txt` trong Project
Đảm bảo file `CMakeLists.txt` của project đã nạp đủ các module cần thiết, đặc biệt là `Mqtt`:

```cmake
# Nạp module Mqtt cùng với Core, Gui, Qml, Quick
find_package(Qt6 REQUIRED COMPONENTS Core Gui Qml Quick Mqtt)

# Link thư viện vào target của ứng dụng
target_link_libraries(appDashboard_DHT11
    PRIVATE Qt6::Quick Qt6::Mqtt
)
```

### 3. Xử lý lỗi CMake Cache (Rất quan trọng)
Nếu vừa cài đặt thư viện xong mà Qt Creator báo lỗi đỏ `Target not found` ở file CMake:
1. Mở Qt Creator, trên thanh menu chọn **Build** -> **Clear CMake Configuration**.
2. Chuột phải vào tên Project ở cột bên trái -> Chọn **Run CMake** để ép hệ thống quét và nhận diện lại thư viện mới nạp.
3. Nhấn Run (Ctrl + R) để tận hưởng thành quả!

## 👤 Thông tin Dự án
- **Dự án:** Nghiên cứu Khoa học (NCKH) AIoT - 2026.
- **Phát triển bởi:** **NgocChien Trùm VT01** (SV: B23DCVT061 - Ngành Điện tử Viễn thông, Học viện Công nghệ Bưu chính Viễn thông PTIT).