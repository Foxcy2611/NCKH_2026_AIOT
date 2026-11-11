# Danh sách mô-đun phần cứng

Đây là nguồn mô tả tập trung cho danh sách mô-đun, chân giao tiếp và vai trò phần
cứng của Patient Node và Gateway. README ở root chỉ dẫn tới tài liệu này để tránh
lặp lại thông số ở nhiều nơi. Khi thay board, chân hoặc mô-đun, cập nhật tài liệu
này cùng `Board_Pinout.h` và cấu hình Gateway tương ứng.

## Danh sách tổng quát

```text
PATIENT NODE
│
├── ESP32-S3-N16R8
├── INMP441
├── MAX30102
├── SSD1306 OLED 0.96"
├── 3 × Push Button
├── Buzzer
├── LED
├── Battery
├── Battery Charging Module
└── Power Management / Regulator

GATEWAY
│
├── ESP32
│
├── ST7735 1.8" TFT 128×160
│
├── DHT22
├── BMP280
├── SGP30
│
├── A7680C
├── NEO-M8N GPS
│
├── LTE Antenna
├── GPS Antenna
│
├── Battery / Power Supply
└── Power Management

PC
└── Qt6 + QML
```

## Danh mục đánh số

01. ESP32-S3-N16R8
02. ESP32
03. INMP441
04. MAX30102
05. SSD1306 OLED
06. ST7735 1.8" TFT
07. DHT22
08. BMP280
09. SGP30
10. A7680C
11. NEO-M8N
12. 3 × Push Button
13. Buzzer
14. LED
15. Patient Battery
16. Gateway Power Supply / Battery
17. Battery Charging Module
18. Voltage Regulator / Power Management
19. LTE Antenna
20. GPS Antenna


## Cấu hình tích hợp hiện hành

Danh sách dưới đây phản ánh cấu hình và source tích hợp hiện tại. Một mô-đun đã có
trình điều khiển trong source không đồng nghĩa đã hoàn tất kiểm thử thực địa; đặc biệt,
GPS, LTE và các cảm biến của Gateway vẫn cần được nghiệm thu trên bộ phần cứng cuối.

### Patient Node

| Mô-đun | Giao tiếp / chân chính | Tác dụng trong hệ thống |
|---|---|---|
| **ESP32-S3-N16R8V** | MCU chính, có PSRAM | Điều khiển Patient Node; thu âm, tiền xử lý Mel-spectrogram, chạy DS-CNN INT8 bằng TensorFlow Lite Micro, quản lý máy trạng thái, màn hình và truyền dữ liệu bảo mật. |
| **INMP441** | I2S: SCK `GPIO14`, WS `GPIO15`, SD `GPIO16` | Thu âm thanh hô hấp ở 16 kHz để kiểm tra chất lượng, phát hiện âm thanh, suy luận CHECK và MONITOR. |
| **MAX30102** | I2C: SDA `GPIO8`, SCL `GPIO9`; INT `GPIO10` | Đo nhịp tim và SpO₂ theo từng phiên CHECK. Khi không hợp lệ, payload dùng `vitals_valid=false`, HR/SpO₂ bằng `0`. |
| **OLED SSD1306 128×64** | I2C: SDA `GPIO8`, SCL `GPIO9`; địa chỉ `0x3C` | Hiển thị hướng dẫn thao tác, trạng thái thu âm/xử lý, kết quả AI, chỉ số sinh tồn và trạng thái gửi dữ liệu. |
| **Ba nút nhấn CHECK, MONITOR, SLEEP/STOP** | Lần lượt `GPIO4`, `GPIO5`, `GPIO6` | Bắt đầu CHECK, bắt đầu/dừng MONITOR hoặc hủy/bỏ qua theo state. Tại STANDBY, `SLEEP` yêu cầu Light Sleep; không dùng Deep Sleep. |
| **Đo điện áp pin Patient Node** | ADC tại `GPIO12` (`ADC2_CH1`), qua cầu chia áp | Đo điện áp và ước lượng phần trăm pin. Không được nối trực tiếp pin 2S vào GPIO; hệ số cầu chia áp phải được hiệu chuẩn trên mạch thật. |
| **Wi-Fi 2.4 GHz / ESP-NOW tích hợp** | Bộ thu phát có sẵn trong ESP32-S3 | Gửi `Secure_Packet_t` đã mã hóa AES-128-GCM đến Gateway và nhận phản hồi ACK/NACK; không phải mô-đun rời. |

OLED và MAX30102 dùng chung bus I2C của Patient Node. Phần thu phát ESP-NOW sử dụng
phần cứng vô tuyến tích hợp trên ESP32-S3, vì vậy Patient Node không cần thêm mô-đun
Wi-Fi ngoài.

### Gateway

| Mô-đun | Giao tiếp / chân chính | Tác dụng trong hệ thống |
|---|---|---|
| **ESP32 Dev Module** | MCU chính | Chạy các tác vụ FreeRTOS; nhận ESP-NOW, xác thực/giải mã sự kiện, gửi ACK/NACK, ghép dữ liệu cảm biến và quản lý đường truyền MQTT. |
| **DHT22** | Một dây dữ liệu tại `GPIO25` | Đo nhiệt độ và độ ẩm môi trường gần Gateway. |
| **BMP280** | I2C: SDA `GPIO21`, SCL `GPIO22`; địa chỉ `0x76` | Đo áp suất khí quyển, bổ sung bối cảnh môi trường cho bản ghi tổng hợp. |
| **SGP30** | I2C: SDA `GPIO21`, SCL `GPIO22` | Đo TVOC và ước lượng eCO₂. Giá trị eCO₂ là chỉ số tương đương, không phải phép đo CO₂ trực tiếp. |
| **NEO-M8N** | UART: RX `GPIO32`, TX `GPIO33`, 9600 baud | Cung cấp tọa độ GPS và thời gian UTC khi có vị trí hợp lệ; tọa độ được chuyển sang độ thập phân có dấu trước khi đóng gói. |
| **SIMCom A7680C** | UART: RX `GPIO16`, TX `GPIO26` | Cung cấp đường truyền LTE dự phòng khi Wi-Fi không khả dụng; cần SIM, APN và kiểm thử mạng thực tế. |
| **TFT ST7735 128×160** | SPI: SCLK `GPIO18`, MOSI `GPIO23`, CS `GPIO15`, DC `GPIO27`, RST `GPIO4` | Hiển thị nhanh kết quả Patient Node, chỉ số sinh tồn, dữ liệu môi trường và trạng thái Wi-Fi/MQTT/LTE tại Gateway. |
| **Wi-Fi 2.4 GHz / ESP-NOW tích hợp** | Bộ thu phát có sẵn trong ESP32 | Nhận sự kiện từ Patient Node qua ESP-NOW và dùng Wi-Fi làm đường MQTT chính; không phải mô-đun rời. |

BMP280 và SGP30 dùng chung bus I2C của Gateway. Mỗi giá trị cảm biến chỉ được đánh
dấu hợp lệ trong `sensor_valid_mask` khi phép đọc tương ứng thành công; Dashboard
không nên coi giá trị mặc định bằng `0` là một phép đo thật.
