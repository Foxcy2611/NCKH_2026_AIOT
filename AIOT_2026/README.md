# ESP32 FreeRTOS Sensor Node

Firmware PlatformIO/Arduino cho ESP32, sử dụng năm module:

| Module | Giao tiếp | Kết nối |
|---|---|---|
| DHT22 | GPIO một dây | DATA GPIO25 |
| BMP280 | I2C | `0x76` hoặc `0x77` |
| SGP30 | I2C | `0x58` |
| MAX30102 | I2C + ngắt | `0x57`, INT GPIO27 |
| SSD1306 128x64 | I2C | `0x3C` |

Bus I2C dùng SDA GPIO21 và SCL GPIO22.

## Kiến trúc

- `EnvironmentTask`, priority 1: DHT22, BMP280, SGP30, SSD1306.
- `MAX30102Task`, priority 2: thu FIFO, tính nhịp tim và SpO2.
- Hai task chạy trên core 1.
- Mutex bảo vệ toàn bộ giao dịch I2C dùng chung.
- Queue một phần tử giữ kết quả MAX30102 mới nhất.
- SGP30 được đọc mỗi 1 giây để duy trì thuật toán baseline.
- DHT22, BMP280, MAX30102 và OLED được cập nhật mỗi 2 giây.
- Cảm biến lỗi được thử khởi tạo lại sau 5 giây.

MAX30102 dùng trung bình phần cứng bốn mẫu: 100 SPS / 4 = 25 SPS, phù hợp với thuật toán BPM/SpO2 tích hợp trong driver.

## Cấu trúc chính

```text
include/
  ESP32_DHT22_Lib.h
  ESP32_BMP280_Lib.h
  ESP32_SGP30_Lib.h
  ESP32_MAX30102_Lib.h
  ESP32_SSD1306_Display.h
src/
  ESP32_DHT22_Lib.cpp
  ESP32_BMP280_Lib.cpp
  ESP32_SGP30_Lib.cpp
  ESP32_MAX30102_Lib.cpp
  ESP32_SSD1306_Display.cpp
  main.cpp
platformio.ini
```

Các driver thử nghiệm A7680C, NEO-M8N và MLX90614 vẫn được giữ trong repository nhưng bị loại khỏi bản build hiện tại bằng `build_src_filter`.

## Build

```powershell
C:\Users\Mr T\.platformio\penv\Scripts\pio.exe run
```

Firmware không phụ thuộc thư viện cảm biến bên ngoài. `Wire` và FreeRTOS được cung cấp bởi Arduino-ESP32.

## Lưu ý phần cứng

- Dùng điện trở pull-up phù hợp cho SDA, SCL, DHT22 DATA và MAX30102 INT.
- Địa chỉ BMP280 được tự dò giữa `0x76` và `0x77`.
- Giá trị độ cao phụ thuộc áp suất mực nước biển cấu hình tại vị trí đo.
- BPM và SpO2 từ thuật toán tham khảo MAXREFDES117 không phải thiết bị y tế được chứng nhận.
- Build thành công không thay thế kiểm tra trực tiếp trên bo mạch và cảm biến.
