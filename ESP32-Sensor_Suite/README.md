# 🩺 ESP32 Low-Level Peripheral Drivers (Datasheet-Based)

Dự án Nghiên cứu khoa học (NCKH) tập trung vào việc tự nghiên cứu, thiết kế và đóng gói toàn bộ driver cho các cảm biến, module ngoại vi trên nền tảng ESP32.

**Đặc điểm cốt lõi:** Toàn bộ mã nguồn driver được viết thủ công từ đầu bằng cách tra cứu **Datasheet / Register Map**, cấu hình trực tiếp qua thanh ghi hoặc các API lớp thấp (I2C, I2S, UART, ADC) của ESP-IDF/Arduino Core, nhằm tối ưu hiệu năng phần cứng, làm chủ luồng dữ liệu và sẵn sàng chuyển đổi lên cấu trúc **ESP32-S3**.

---

## 🏗 Kiến trúc Hệ thống & Quản lý Ngoại vi

### 1. ESP32 #1: Sensor Node (Thu thập & Xử lý Cục bộ)
* **MAX30102:** Cấu hình thanh ghi điều khiển LED, chế độ lấy mẫu (SpO2/HR) và đọc mảng dữ liệu qua bộ đệm FIFO bằng giao tiếp **I2C**.
* **SGP30 & MQ135:** Đo chỉ số eCO2, TVOC (qua tập lệnh I2C của SGP30) và các khí độc hại (qua bộ chuyển đổi **ADC** kết hợp công thức tính điện trở cảm biến).
* **DHT11 & BMP280:** Đọc thông số vi khí hậu. Riêng với BMP280, tự viết hàm bóc tách các hệ số bù (Calibration Coefficients) từ bộ nhớ ROM của chip để tính toán nhiệt độ và áp suất chính xác.
* **Xử lý cảnh báo tại chỗ:** Tự xây dựng bộ đệm hiển thị đồ họa trên màn hình **OLED (SSD1306)** qua I2C và điều khiển còi **Buzzer** báo động.

### 2. ESP32 #2: Gateway Node (Định vị & Cảnh báo Khẩn cấp)
* **NEO-M8N:** Cấu hình cổng **UART**, tự viết bộ Parser xử lý chuỗi ký tự thô NMEA để lọc lấy tọa độ GPS (`$GPRMC`, `$GPGGA`).
* **A7680C (4G LTE):** Đóng gói bộ thư viện gửi nhận tập lệnh **AT Commands** qua UART để điều khiển module di động thực hiện cuộc gọi khẩn cấp (Voice Call) và gửi tin nhắn SMS chứa tọa độ cứu trợ khi `alert_level` vượt ngưỡng an toàn.

---

## 🛠 Công cụ & Thiết lập
* **Hardware:** ESP32
* **Board:** Espressif ESP32 Dev Module
* **Framework:** Arduino Core

---

## 📂 Cấu trúc Thư mục Dự án

Toàn bộ Driver tự viết được tổ chức gọn gàng trong thư mục `lib/`:

```text
├── lib/
│   ├── MAX30102/    # Đo SpO2 & Nhịp tim qua thanh ghi (I2C)
│   ├── INMP441/     # [Đã hoàn thiện] Cấu hình thu âm (I2S Native)
│   ├── SGP30/       # Giao tiếp lấy dữ liệu eCO2 & TVOC (I2C)
│   ├── MQ135/       # Tính toán chất lượng không khí qua điện áp (ADC)
│   ├── DHT11/       # Đọc Nhiệt độ & Độ ẩm (Xử lý xung 1-Wire)
│   ├── BMP280/      # Tính toán Áp suất & Nhiệt độ từ hệ số bù (I2C)
│   ├── OLED/        # Tự build buffer điều khiển màn hình SSD1306 (I2C)
│   ├── NEO_M8N/     # Trích xuất dữ liệu định vị NMEA (UART)
│   └── A7680C/      # Xử lý tập lệnh AT Command gọi & SMS (UART)
├── src/
│   └── main.cpp     # Nơi gọi và điều phối các module độc lập
├── platformio.ini   # Cấu hình board esp32dev, trống lib_deps
└── README.md