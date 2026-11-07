# ESP32 Sensor Suite - chạy thử riêng lẻ từng mô-đun

Thư mục này là bộ driver mức thấp và chương trình mẫu để kiểm tra **từng mô-đun
phần cứng độc lập** trước khi tích hợp vào Patient Node hoặc Gateway. Đây không
phải firmware hoàn chỉnh và không mô phỏng luồng Node–Gateway–Dashboard.

Các driver được viết trực tiếp trên API lõi của Arduino-ESP32 (`Wire`, `SPI`,
`HardwareSerial`, GPIO, timer và FreeRTOS). Project không cần cài thư viện cảm
biến bên thứ ba qua `lib_deps`.

## 1. Cách chạy nhanh

Mở [platformio.ini](platformio.ini), sửa đúng một dòng:

```ini
-D SENSOR_SUITE_MODULE=7
```

| Giá trị | Mô-đun được chạy |
|---:|---|
| `1` | BMP280 |
| `2` | DHT22 |
| `3` | MAX30102 |
| `4` | MLX90614 |
| `5` | NEO-M8N |
| `6` | SGP30 |
| `7` | SSD1306 |
| `8` | A7680C |
| `9` | ST7735 |

Sau đó chạy tại thư mục `ESP32_Sensor_Suite`:

```powershell
pio run
pio run --target upload
pio device monitor --baud 115200
```

Trong VS Code có thể dùng nút Build/Upload/Monitor của PlatformIO. Không mở đồng
thời nhiều ví dụ vì một số driver dùng chung I2C hoặc cùng chân UART.

## 2. Tổ chức project

```text
ESP32_Sensor_Suite/
├── include/          # API công khai, thanh ghi, chân mặc định và ghi chú sử dụng
├── src/
│   ├── main.cpp      # chọn đúng một mô-đun để chạy thử
│   └── ESP32_*.cpp   # phần cài đặt driver
├── platformio.ini    # board, baud và SENSOR_SUITE_MODULE
└── README.md
```

`main.cpp` chỉ là ví dụ ghép API. Khi tích hợp vào project khác, sao chép đúng
cặp `.h/.cpp` của mô-đun cần dùng, rồi gọi API khởi tạo/đọc tương ứng; không sao
chép nguyên `main.cpp`.

## 3. Thư viện lõi được sử dụng

| Thư viện/API | Có sẵn từ | Mục đích |
|---|---|---|
| `Arduino.h` | Arduino-ESP32 | GPIO, thời gian, Serial và kiểu dữ liệu nền tảng |
| `Wire.h` | Arduino-ESP32 | I2C cho BMP280, MAX30102, MLX90614, SGP30 và SSD1306 |
| `SPI.h` | Arduino-ESP32 | Giao tiếp ghi màn hình ST7735 |
| `HardwareSerial` | Arduino-ESP32 | UART cho NEO-M8N và A7680C |
| `esp_timer.h` | ESP-IDF trong Arduino Core | Đo timing microsecond của DHT22/MAX30102 |
| FreeRTOS | ESP-IDF trong Arduino Core | Semaphore và nhường CPU trong driver MAX30102/A7680C |
| `math.h` | toolchain C/C++ | Công thức bù, độ cao, HR và SpO2 |

Không cài thêm `Adafruit_*`, `TFT_eSPI`, SparkFun MAX3010x hoặc thư viện BMP280
khác khi dùng các driver này, trừ khi chủ động thay toàn bộ implementation.

## 4. Bảng mô-đun và API tối thiểu

| Mô-đun | Giao tiếp mặc định | API driver chính | Ví dụ độc lập |
|---|---|---|---|
| BMP280 | I2C SDA21/SCL22; thử địa chỉ `0x77` trong ví dụ | `BMP280_Init`, `BMP280_ReadData` | `BMP280_TestSetup/Loop` |
| DHT22 | DATA GPIO25 | `DHT22_Init`, `DHT22_ReadData` | `DHT22_TestMain` mỗi 2,5 s |
| MAX30102 | I2C SDA21/SCL22, INT27, địa chỉ `0x57` | `MAX30102_Init`, `MAX30102_GetHeartRateSpO2` | `MAX30102_TestSetup/Loop` |
| MLX90614 | I2C, địa chỉ `0x5A` | `MLX90614_Read_Object_Temp`, `MLX90614_Read_Ambient_Temp` | `MLX90614_TestSetup/Loop` |
| NEO-M8N | UART1 RX16/TX17, 9600 baud | `NEO_M8N_Init`, `NEO_M8N_ReadData` | `NEO_M8N_TestSetup/Loop` |
| SGP30 | I2C, địa chỉ `0x58` | `SGP30_Init`, `SGP30_Measure` | `SGP30_TestSetup/Loop` |
| SSD1306 | I2C, địa chỉ `0x3C`, 128x64 | `OLED_Init`, `OLED_Println`, `OLED_UpdateScreen` | `OLED_TestSetup` |
| A7680C | UART2 RX16/TX17, 115200 baud trong ví dụ | `A7680C_InitAndDiagnose`, các hàm kiểm tra/SMS | Chẩn đoán lúc setup, kiểm tra mỗi 10 s |
| ST7735 | SPI: MOSI11, SCLK12, CS10, DC9, RST8 | `ST7735_Init`, API `Draw/Fill` | Vẽ khung và hình tròn tĩnh |

Chân trong bảng là mặc định của chính folder này, không tự động đồng bộ với
`Final_Project_NCKH`. Trước khi đấu mạch, đối chiếu header của mô-đun và pinout
của board đang sử dụng.

## 5. Cách dùng từng driver

### BMP280

```cpp
Wire.begin(21, 22);
if (BMP280_Init(0x76)) {
    float temperature = 0.0f;
    float pressure = 0.0f;
    BMP280_ReadData(&temperature, &pressure);
}
```

Một số breakout dùng `0x76`, một số dùng `0x77` tùy chân SDO. Ví dụ tích hợp
hiện thử `0x77`; đổi địa chỉ nếu Serial báo không tìm thấy thiết bị.

### DHT22

```cpp
DHT22_Init();
float temperature = 0.0f;
float humidity = 0.0f;
const uint8_t error = DHT22_ReadData(&temperature, &humidity);
```

Không đọc dồn dập. Giữ khoảng cách ít nhất khoảng 2 giây và dùng điện trở kéo
lên chân DATA theo module thực tế.

### MAX30102

```cpp
MAX30102_TestSetup();
// Trong loop:
MAX30102_TestLoop();
```

Ví dụ dùng FIFO và ngắt GPIO27. Đặt ngón tay ổn định, che ánh sáng môi trường và
không coi giá trị chưa có cờ valid là phép đo sinh lý hợp lệ.

### MLX90614

```cpp
Wire.begin();
float objectTemperature = 0.0f;
if (MLX90614_Read_Object_Temp(&objectTemperature)) {
    Serial.println(objectTemperature);
}
```

Driver kiểm tra PEC CRC-8. Khoảng cách, góc nhìn và nhiệt độ môi trường ảnh hưởng
phép đo; ví dụ này chỉ kiểm tra giao tiếp, không phải hiệu chuẩn y tế.

### NEO-M8N

```cpp
Serial1.begin(9600, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
NEO_M8N_Init(&Serial1);
NEO_Data_t data{};
NEO_M8N_ReadData(&data);
```

Driver đọc câu RMC, trả tọa độ thập phân khi dữ liệu hợp lệ. Lần bắt vị trí đầu
có thể kéo dài; thử ngoài trời hoặc gần cửa sổ và bảo đảm anten được gắn đúng.

### SGP30

```cpp
Wire.begin();
SGP30_Init();
SGP30_Data_t data{};
SGP30_Measure(&data);
```

Phải giữ chu kỳ đo đều 1 giây. Các giá trị đầu tiên trong thời gian warm-up chỉ
dùng để quan sát hoạt động, không nên xem là kết quả môi trường ổn định.

### SSD1306

```cpp
Wire.begin();
OLED_Init();
OLED_Clear_Display();
OLED_GotoXY(0, 0);
OLED_Println("ESP32 Sensor Suite");
OLED_UpdateScreen();
```

Các hàm vẽ thay đổi framebuffer RAM. Phải gọi `OLED_UpdateScreen()` để truyền
buffer mới lên màn hình.

### A7680C

```cpp
const bool ready = A7680C_InitAndDiagnose(
    Serial2, SIM_RX_PIN, SIM_TX_PIN, 115200);
```

Module LTE cần nguồn riêng có khả năng chịu dòng đỉnh, GND chung với ESP32, SIM
đã kích hoạt và anten phù hợp. Ví dụ mặc định chỉ chẩn đoán, không tự gửi SMS để
tránh phát sinh thao tác mạng ngoài ý muốn.

### ST7735

```cpp
ST7735_Init();
ST7735_FillScreen(RGB_BLACK);
ST7735_DrawRect(8, 8, 144, 112, RGB_CYAN);
```

Chân mặc định trong header được ghi cho cấu hình ESP32-S3. Nếu build trên
`esp32dev`, phải đổi sang các chân SPI khả dụng trên board thực tế trước khi nối.

## 6. Quy tắc khi đưa driver sang project chính

1. Chốt board và chân trước; không giả định pin của Sensor Suite giống Node/Gateway.
2. Chỉ khởi tạo `Wire`, `SPI` hoặc UART một lần và thống nhất clock/bus dùng chung.
3. Bỏ các hàm `*_TestSetup/Loop` nếu project chính đã có state machine riêng.
4. Không dùng vòng lặp vô hạn trong driver tích hợp; trả mã lỗi cho tầng gọi xử lý.
5. Phân biệt “đọc được thanh ghi” với “số đo hợp lệ”.
6. Kiểm tra timeout, CRC/checksum, mất dây và phục hồi sau lỗi.
7. Đo nguồn và mức logic trước khi cấp điện cho A7680C hoặc module dùng nguồn riêng.

Folder này phục vụ học giao thức và kiểm tra module độc lập. Source tích hợp cuối
cùng vẫn phải được đối chiếu với `Final_Project_NCKH/Patient_Node` hoặc
`Final_Project_NCKH/Gateway` trước khi nghiệm thu.
