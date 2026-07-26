# 🩺 ESP32 Low-Level Peripheral Drivers (Datasheet-Based)

Dự án Nghiên cứu khoa học (NCKH) tập trung vào việc tự nghiên cứu, thiết kế và đóng gói toàn bộ driver cho các cảm biến, module ngoại vi trên nền tảng ESP32.

**Đặc điểm cốt lõi:** Toàn bộ mã nguồn driver được viết thủ công từ đầu bằng cách tra cứu **Datasheet / Register Map**, cấu hình trực tiếp qua thanh ghi hoặc các API lớp thấp (I2C, I2S, UART, ADC) của ESP-IDF/Arduino Core, nhằm tối ưu hiệu năng phần cứng, làm chủ luồng dữ liệu và sẵn sàng chuyển đổi lên cấu trúc **ESP32-S3**.

---

## 🏗 Kiến trúc Hệ thống & Quản lý Ngoại vi

### 1. 🖥️ ESP32 #1: Sensor Node (Thu thập & Xử lý Cục bộ)
* 🩸 **MAX30102:** Cấu hình thanh ghi điều khiển LED, chế độ lấy mẫu (SpO2/HR) và đọc mảng dữ liệu qua bộ đệm FIFO bằng giao tiếp **I2C**.
* 🌫️ **SGP30:** Đo chỉ số eCO2, TVOC (qua tập lệnh I2C của SGP30) về chất lượng không khí.
* 🌤️ **DHT11 & BMP280:** Đọc thông số vi khí hậu. Riêng với BMP280, tự viết hàm bóc tách các hệ số bù (Calibration Coefficients) từ bộ nhớ ROM của chip để tính toán nhiệt độ và áp suất chính xác.
* 🤒 **MLX90614:** Đọc thông số nhiệt độ cơ thể con người từ đó theo dõi sát sao cơ thể
* 🚨 **Xử lý cảnh báo tại chỗ:** Tự xây dựng bộ đệm hiển thị đồ họa trên màn hình **OLED (SSD1306)** qua I2C và điều khiển còi **Buzzer** báo động.

### 2. 📡 ESP32 #2: Gateway Node (Định vị & Cảnh báo Khẩn cấp)
* 🛰️ **NEO-M8N:** Cấu hình cổng **UART**, tự viết bộ Parser xử lý chuỗi ký tự thô NMEA để lọc lấy tọa độ GPS (`$GPRMC`, `$GPGGA`).
* 📶 **A7680C (4G LTE):** Đóng gói bộ thư viện gửi nhận tập lệnh **AT Commands** qua UART để điều khiển module di động thực hiện cuộc gọi khẩn cấp (Voice Call) và gửi tin nhắn SMS chứa tọa độ cứu trợ khi `alert_level` vượt ngưỡng an toàn.

### 3. 📋 Danh sách và Chức năng các Module phần cứng

| Module / Cảm biến | Chuẩn giao tiếp | Chức năng chính |
| :--- | :---: | :--- |
| 📶 **A7680C** | UART (115200) | Module viễn thông 4G LTE |
| 🌡️ **BMP280** | I2C (`0x76`) | Đo áp suất khí quyển và nhiệt độ |
| 💧 **DHT11** | 1-Wire (GPIO) | Đo nhiệt độ, độ ẩm môi trường |
| 🎤 **INMP441** | I2S / ADC | Thu thập dữ liệu âm thanh ho / hô hấp / nói chuyện |
| ❤️ **MAX30102** | I2C (`0x57`) | Đo nhịp tim và nồng độ oxy trong máu bệnh nhân |
| 🤒 **MLX90614** | I2C (`0x5A`) | Đo nhiệt độ môi trường xung quanh và đối tượng nhìn thấy | 
| 🛰️ **NEO-M8N** | UART (9600) | Module định vị vệ tinh GPS/GLONASS |
| 🌫️ **SGP30** | I2C (`0x58`) | Cảm biến chất lượng không khí (CO2 và TVOC) |
| 📺 **SSD1306** | I2C (`0x3C`) | Màn hình hiển thị OLED (128x64) |

---

## 🛠 Công cụ & Thiết lập
* ⚙️ **Hardware:** ESP32
* 🧰 **Board:** Espressif ESP32 Dev Module
* 💻 **Framework:** Arduino Core

---

## 📂 Cấu trúc Thư mục Dự án

Toàn bộ Driver tự viết được tổ chức gọn gàng trong thư mục `lib/`:

```text
├── lib/
│   ├── MAX30102/    # Đo SpO2 & Nhịp tim qua thanh ghi (I2C)
│   ├── INMP441/     # [Đã hoàn thiện] Cấu hình thu âm (I2S Native)
│   ├── SGP30/       # Giao tiếp lấy dữ liệu eCO2 & TVOC (I2C)
│   ├── MLX90614/    # Tính toán nhiệt độ cơ thể con người (I2C)
│   ├── DHT11/       # Đọc Nhiệt độ & Độ ẩm (Xử lý xung 1-Wire)
│   ├── BMP280/      # Tính toán Áp suất & Nhiệt độ từ hệ số bù (I2C)
│   ├── OLED/        # Tự build buffer điều khiển màn hình SSD1306 (I2C)
│   ├── NEO_M8N/     # Trích xuất dữ liệu định vị NMEA (UART)
│   └── A7680C/      # Xử lý tập lệnh AT Command gọi & SMS (UART)
├── src/
│   └── main.cpp     # Nơi gọi và điều phối các module độc lập
├── platformio.ini   # Cấu hình board esp32dev, trống lib_deps
└── README.md
```

## 📖 Tóm Tắt Quy Trình Giao Tiếp Phần Cứng (Protocol Reference)

Dự án này tương tác với phần cứng ở tầng Bare-Metal. Dưới đây là tóm tắt quy trình chuẩn (dựa trên Datasheet) để giao tiếp và ép các module/cảm biến trả về dữ liệu.

### 1. 📱 Module 4G LTE (A7680C) - Giao tiếp UART & AT Command
Sử dụng cổng UART (Baudrate mặc định 115200, 8N1). Vi điều khiển đóng vai trò Master, gửi lệnh dạng ASCII và phân tích chuỗi phản hồi.

* **🚀 Khởi động & Cấu hình:**
  1. MCU gửi `AT\r\n` để kiểm tra module thức tỉnh (Chờ phản hồi `OK`).
  2. Gửi `ATE0\r\n` để tắt chế độ nhại lệnh (Echo), giúp buffer nhận về sạch sẽ hơn.
  3. Kiểm tra SIM bằng `AT+CPIN?` (Chờ phản hồi `+CPIN: READY`).
  4. Đọc chất lượng sóng bằng `AT+CSQ` (Trích xuất giá trị dải 0-31, bỏ qua nếu bằng 99).
  5. Đăng ký mạng bằng `AT+CEREG?` (Chờ trạng thái `0,1` hoặc `0,5` là đã vào mạng).
* **🚨 Quy trình Cảnh báo:**
  * **Gọi điện:** Gửi `ATD<Số_điện_thoại>;\r\n` (Bắt buộc có dấu `;`). Đợi người dùng bắt máy (kiểm tra bằng `AT+CLCC`) rồi gửi `ATH\r\n` để cúp máy.
  * **Nhắn tin:** Gửi `AT+CMGF=1` (đưa về Text mode). Gửi `AT+CMGS="Số_điện_thoại"`. Chờ module trả về dấu nhắc `>`. MCU đẩy nội dung tin nhắn và kết thúc bằng mã ASCII `0x1A` (Ctrl+Z).

### 2. 🌤️ Cảm biến Áp suất/Nhiệt độ (BMP280) - Giao tiếp I2C & Memory Map
Giao tiếp qua bus I2C ở địa chỉ `0x76` (khi chân SDO nối GND). Quy trình đọc bắt buộc phải qua bước bù trừ sai số (Calibration) do giới hạn vật lý của cảm biến MEMS.

* **⚙️ Quy trình Khởi tạo (Boot Sequence):**
  1. **Check ID:** MCU đọc 1 byte từ thanh ghi `0xD0`. Nếu trả về `0x58` -> Đúng chip BMP280.
  2. **Soft Reset:** MCU ghi giá trị `0xB6` vào thanh ghi `0xE0` để dọn dẹp cấu hình rác.
  3. **Đọc ROM:** MCU đọc 24 bytes liên tục từ dải địa chỉ `0x88` đến `0xA1`. Đây là các hệ số bù sai số (Calibration Coefficients) được Bosch nạp cứng tại nhà máy.
  4. **Cấu hình:** Ghi vào thanh ghi `0xF5` (Cài Standby time và bộ lọc IIR) và thanh ghi `0xF4` (Cài Oversampling và chọn Normal Mode).
* **📥 Quy trình Lấy mẫu (Burst Read):**
  1. MCU gửi yêu cầu đọc 6 bytes liên tục bắt đầu từ thanh ghi `0xF7`.
  2. Cảm biến trả về lần lượt: Áp suất (MSB, LSB, XLSB) và Nhiệt độ (MSB, LSB, XLSB).
  3. MCU ghép các byte thành dữ liệu thô (20-bit), sau đó đưa vào công thức Double Precision cùng với 24 bytes ROM ở bước 3 để tính ra giá trị thực (Độ C và hPa).

### 3. 💧 Cảm biến Nhiệt ẩm (DHT11) - Giao tiếp 1-Wire vi giây
Giao tiếp qua một dây tín hiệu duy nhất (Half-duplex) yêu cầu trở kéo lên (Pull-up). Mọi bit dữ liệu (0 hoặc 1) đều được định nghĩa bằng **độ rộng xung** tính bằng micro-giây.

* **🤝 Quy trình Bắt tay (Handshake):**
  1. **MCU Start:** MCU đổi chân tín hiệu thành Output Open-Drain, kéo xuống mức LOW tối thiểu 18ms để đánh thức DHT11. Sau đó MCU nhả ra (mức HIGH) trong 20-40µs và chuyển chân sang Input.
  2. **DHT11 ACK:** DHT11 phản hồi bằng cách kéo LOW 80µs, sau đó kéo HIGH 80µs.
* **⏱️ Quy trình Đọc Dữ liệu (40 bits):**
  1. DHT11 bơm ra 40 bits, tương đương 5 Bytes (Độ ẩm phần nguyên, độ ẩm thập phân, nhiệt độ nguyên, nhiệt độ thập phân, Checksum).
  2. **Phân biệt logic:** Mỗi bit đều bắt đầu bằng 50µs mức LOW.
     * Nếu mức HIGH tiếp theo kéo dài **~26-28µs** -> Bit 0.
     * Nếu mức HIGH tiếp theo kéo dài **~70µs** -> Bit 1.
  3. *(Lưu ý HĐH: Trên ESP32, quá trình đo các vi giây này bắt buộc phải khóa ngắt phần cứng (Disable Interrupts) để tránh HĐH FreeRTOS làm sai lệch thời gian).*
* **✅ Xác thực:** Tổng của 4 bytes đầu phải bằng đúng byte thứ 5 (Checksum).

### 4. ❤️ Cảm biến Nhịp tim/SpO2 (MAX30102) - Giao tiếp I2C & Quản lý FIFO/Ngắt
Giao tiếp qua bus I2C (địa chỉ `0x57`). Đây là cảm biến quang học hoạt động ở chế độ đo ngầm. Nó tự động chớp LED, lấy mẫu và đẩy dữ liệu vào bộ nhớ đệm vòng (FIFO 32 mẫu) tích hợp sẵn trong chip. Vi điều khiển không cần lấy mẫu liên tục mà chỉ việc chờ tín hiệu Ngắt (Interrupt) để vào lấy dữ liệu, giải phóng hoàn toàn CPU.

* **⚙️ Quy trình Khởi tạo & Cấu hình:**
  1. **Xác thực (Part ID):** Đọc thanh ghi `0xFF`. Bắt buộc phải trả về `0x15` để đảm bảo kết nối đúng chip.
  2. **Reset:** Ghi bit 6 vào thanh ghi `0x09` để reset toàn bộ phần cứng về trạng thái gốc.
  3. **Cấu hình Ngắt:** Ghi vào thanh ghi `0x02` (INT_ENABLE_1) giá trị `0x40` để bật cờ `PPG_RDY`. Khi có 1 mẫu data mới được đo xong, cảm biến sẽ kéo chân `INT` xuống mức LOW.
  4. **Cấu hình FIFO & Lấy mẫu:** * `0x08` (FIFO Config): Bật chế độ tự động ghi đè khi đầy (Rollover) và lấy trung bình 4 mẫu phần cứng để giảm nhiễu.
     * `0x09` (Mode Config): Bật chế độ SpO2 (Kích hoạt cả 2 LED Đỏ và Hồng ngoại).
     * `0x0A` (SpO2 Config): Cài dải đo ADC lớn nhất, tốc độ 100Hz, độ rộng xung 411µs (để lấy độ phân giải tối đa 18-bit).
     * `0x0C` & `0x0D`: Cài đặt dòng điện cho 2 LED ở mức vừa phải (~7mA) để tối ưu công suất và tránh bão hòa ánh sáng.
* **⚡ Quy trình Đọc dữ liệu (Hardware Interrupt):**
  1. **Bắt Ngắt (Trigger):** ESP32 cấu hình ngắt sườn xuống (FALLING) trên chân GPIO nối với `INT`. Khi cờ ngắt phần cứng bật lên, MCU tạm dừng các việc khác để ưu tiên lấy dữ liệu.
  2. **Kiểm tra Pointer:** Đọc con trỏ ghi `0x04` (wrPtr) và con trỏ đọc `0x06` (rdPtr). Nếu hai con trỏ khác nhau tức là có dữ liệu mới.
  3. **Burst Read:** MCU yêu cầu đọc liên tục 6 bytes từ thanh ghi `0x07` (FIFO Data). 3 bytes đầu chứa dữ liệu LED Đỏ, 3 bytes sau chứa dữ liệu LED Hồng ngoại (IR).
  4. **Giải mã 18-bit:** Dữ liệu bị phân mảnh trong 3 bytes. MCU sử dụng phép dịch bit (`<<`) và mặt nạ bit (`& 0x03FFFF`) để ép khối dữ liệu này về đúng số nguyên 18-bit chuẩn, loại bỏ các bit rác.
  5. **Xóa Ngắt (Clear Interrupt):** Bắt buộc phải thực hiện lệnh đọc thanh ghi trạng thái ngắt `0x00` (INT_STAT_1). Việc đọc này đóng vai trò reset mạch ngắt nội bộ, MAX30102 sẽ tự động thả chân `INT` lên lại mức HIGH để chuẩn bị cho chu kỳ nhịp tim tiếp theo.

### 5. 🌡️ Cảm biến Thân nhiệt Hồng ngoại (MLX90614) - Giao tiếp SMBus/I2C & Xử lý CRC-8
MLX90614 là cảm biến đo nhiệt độ hồng ngoại không tiếp xúc. Nó không cần mạch phân áp hay hàm toán học phức tạp mà giao tiếp trực tiếp qua chuẩn số SMBus (tương thích I2C).

* **🔌 Đấu nối (Giao tiếp I2C Chuẩn):**
  * `VDD` và `VSS` (GND): Tùy thuộc vào phiên bản phần cứng, dòng MLX90614Bxx (phiên bản 3V) đặc biệt phù hợp để cấp nguồn 3.3V trực tiếp từ vi điều khiển.
  * `PWM/SDA` và `SCL/Vz`: Nối trực tiếp vào bus I2C của MCU. Hệ thống bắt buộc phải có điện trở kéo lên (pull-up resistors) trên cả hai đường tín hiệu này để đảm bảo giao tiếp SMBus ổn định, do chân SDA của cảm biến hoạt động ở chế độ Open Drain NMOS.
* **🚀 Quy trình Khởi động (Plug & Play):**
  * Không giống cảm biến nung nóng, MLX90614 đã được hiệu chuẩn sẵn (factory calibrated) từ nhà máy. Cảm biến hỗ trợ dải đo nhiệt độ môi trường từ **-40°C** đến **125°C**, và nhiệt độ đối tượng từ **-70°C** đến **380°C**. Không cần thời gian nung nóng (pre-heating) hay tự hiệu chuẩn (calibration).
  * Địa chỉ Slave mặc định trên đường truyền là `0x5A` (Hex).
* **📡 Quy trình Lấy mẫu và Tính toán (Giao thức Read Word & Mã PEC):**
  * **Đọc RAM:** Gửi lệnh đọc tới thanh ghi `0x07` để truy xuất nhiệt độ đối tượng (T_OBJ1) hoặc thanh ghi `0x06` để truy xuất nhiệt độ môi trường (T_A).
  * **Kiểm tra Toàn vẹn Dữ liệu (PEC - Packet Error Code):** Cảm biến sẽ trả về 3 byte liên tiếp gồm: Byte Thấp (LSB), Byte Cao (MSB) và Byte Mã Lỗi (PEC). MCU cần thực hiện thuật toán CRC-8 (sử dụng đa thức X^8+X^2+X^1+1) quét qua toàn bộ 5 byte của khung truyền (bao gồm cả địa chỉ Slave và mã thanh ghi) để so khớp với byte PEC. Nếu sai lệch, gói tin bị loại bỏ để chống nhiễu tín hiệu.
  * **Quy đổi Nhiệt độ:** Dữ liệu thô (16-bit) thu được từ RAM đại diện cho nhiệt độ tuyệt đối với độ phân giải siêu nhỏ là 0.02°K/LSB. Áp dụng công thức tuyến tính đơn giản sau để có kết quả cuối cùng:
    `T[°C] = (RAM_Value * 0.02) - 273.15`

### 6. 📍 Module Định vị Toàn cầu (NEO-M8N) - Giao tiếp UART & Parsing NMEA
NEO-M8N là module GNSS đồng thời, có khả năng bắt sóng vệ tinh GPS, GLONASS và BeiDou cùng lúc để đạt độ chính xác cao. Module tự động phát luồng dữ liệu (streaming) theo chuẩn ASCII NMEA 0183 ngay khi được cấp nguồn.

* **🔌 Đấu nối:**
  * `RX_GPS` nối với chân TX chỉ định của ESP32.
  * `TX_GPS` nối với chân RX chỉ định của ESP32 (VD: Chân 32).
  * `VCC/GND` cấp nguồn 3.3V hoặc 5V (tùy mạch tích hợp LDO).
* **🔄 Quy trình Giao tiếp (Data Streaming & Parsing):**
  1. **Khởi tạo UART:** MCU mở cổng Serial ở tốc độ mặc định `9600 Baud` theo quy định của nhà sản xuất u-blox. Không cần gửi lệnh cấu hình.
  2. **Bắt luồng (Buffer Polling):** MCU liên tục đọc từng ký tự (char) từ bộ đệm UART, ghép thành các chuỗi văn bản hoàn chỉnh dựa trên ký tự kết thúc dòng `\n`.
  3. **Lọc dữ liệu (Pattern Matching):** Bộ Parser quét các chuỗi văn bản, chỉ giữ lại các dòng có Header là `$GNRMC` (hoặc `$GPRMC`), đây là gói dữ liệu chứa Tọa độ, Trạng thái và Tốc độ.
  4. **Giải mã (Tokenizing & Math):** * Phân tách chuỗi bằng dấu phẩy `,`. Kiểm tra cờ trạng thái (Ký tự `A` = Đã fix được vệ tinh, `V` = Đang tìm kiếm).
     * Bóc tách các trường Vĩ độ, Kinh độ ở định dạng thô `ddmm.mmmm` (Độ, Phút).
     * Áp dụng toán học quy đổi về Độ thập phân chuẩn quốc tế: `Decimal = dd + (mm.mmmm / 60)`. Thêm dấu âm (-) nếu hướng là W (Tây) hoặc S (Nam).

### 7. 🌫️ Cảm biến Chất lượng Không khí (SGP30) - Giao tiếp I2C & Đa pixel

SGP30 là cảm biến khí đa điểm (multi-pixel) của Sensirion, sử dụng công nghệ CMOSens để đo đồng thời TVOC (Tổng hợp hợp chất hữu cơ dễ bay hơi) và eCO2 (Carbon Dioxide tương đương). Đây là cảm biến kỹ thuật số thông minh có thuật toán bù nền tích hợp.

* **🔌 Đấu nối:**
    * Giao tiếp qua bus I2C (Địa chỉ cố định `0x58`).
    * Lưu ý: Chip hoạt động ở mức 1.8V, các module trên thị trường đã tích hợp sẵn mạch hạ áp và chuyển đổi mức logic (Level Shifter) nên có thể cắm trực tiếp vào ESP32 (3.3V).

* **🔄 Quy trình Giao tiếp (Communication Protocol):**
    1. **Khởi tạo (Init):** Gửi lệnh `0x2003` (Init_air_quality) để bắt đầu thuật toán đo đạc.
    2. **Đọc dữ liệu (Measurement):**
        * Gửi lệnh `0x2008` (Measure_air_quality).
        * Đợi tối thiểu 12ms để chip xử lý.
        * Đọc 6 byte phản hồi từ cảm biến.

* **📦 Cấu trúc gói tin 6-byte:**
    * Dữ liệu trả về chia làm 2 cụm độc lập: [CO2_MSB, CO2_LSB, CO2_CRC] và [TVOC_MSB, TVOC_LSB, TVOC_CRC].
    * Mỗi cụm dữ liệu (2 byte) luôn kèm theo 1 byte `CRC-8` để kiểm tra tính toàn vẹn.

* **⚠️ Lưu ý kỹ thuật quan trọng:**
    * Chu kỳ đo 1s: Bắt buộc gửi lệnh đo đều đặn mỗi 1 giây để thuật toán bù đường nền (Baseline compensation) hoạt động chính xác.
    * Giai đoạn Warm-up: Trong 15 giây đầu sau khi khởi tạo, cảm biến sẽ trả về giá trị mặc định (400ppm eCO2, 0ppb TVOC) để làm nóng lõi gốm.
    * Bảo mật dữ liệu (CRC-8): Mọi giao tiếp đều phải kiểm tra mã CRC (Đa thức `0x31`, khởi tạo `0xFF`) để đảm bảo dữ liệu không bị nhiễu do môi trường.

### 8. 📺 Màn hình OLED (SSD1306) - Giao tiếp I2C & Frame Buffer

Màn hình OLED đơn sắc kích thước 128x64 pixel, sử dụng IC điều khiển SSD1306. Thư viện hiển thị được lập trình từ mức thanh ghi (Register-level) kết hợp bộ đệm khung hình (Frame Buffer), hoạt động hoàn toàn độc lập mà không cần phụ thuộc vào các thư viện cồng kềnh như Adafruit_GFX hay U8g2.

* **🔌 Đấu nối:**
    * **Giao tiếp:** Qua bus I2C (Địa chỉ 7-bit chuẩn: `0x3C`).
    * **Nguồn cấp:** 3.3V hoặc 5V (tùy mạch) kết nối trực tiếp với nguồn của ESP32.

* **⚙️ Cơ chế hoạt động (Frame Buffer & Rendering):**
    * **Cấp phát bộ đệm:** Sử dụng một mảng tĩnh 1024 bytes (128x64/8) trên RAM của ESP32 để lưu trữ toàn bộ trạng thái điểm ảnh.
    * **Xử lý ngoại tuyến (Offline Rendering):** Mọi thao tác tính toán tọa độ, vẽ điểm ảnh (`OLED_DrawPixel`) hoặc ghi đè font chữ đều thao tác trực tiếp trên mảng RAM cục bộ. Điều này giúp hệ thống không bị thắt cổ chai ở đường truyền I2C.
    * **Đồng bộ hóa (Flush):** Gọi hàm `OLED_UpdateScreen()` để đẩy toàn bộ 1024 bytes từ RAM nội bộ xuống IC SSD1306 trong một vòng lặp tối ưu nhất.

* **✨ Tính năng nổi bật của Thư viện:**
    * **Tích hợp sẵn bộ Font 5x7:** Bao phủ toàn bộ bảng mã ASCII chuẩn (từ 32 đến 126).
    * **Logic tự động ngắt dòng (Word Wrap):** Tự động tính toán đẩy con trỏ xuống hàng dưới khi gặp ký tự `\n` hoặc khi chuỗi văn bản vượt quá chiều ngang 128 pixel.
    * **Hỗ trợ định dạng chuỗi động (Variadic Format):** Khai thác `stdarg.h` để xây dựng hàm `OLED_Printf`, cho phép in trực tiếp biến số nguyên (`%d`), số thực (`%.2f`), chuỗi (`%s`) ra màn hình với cú pháp chuẩn C/C++, giải quyết triệt để vấn đề tràn bộ nhớ (Memory Fragmentation) so với việc dùng class `String` của Arduino.