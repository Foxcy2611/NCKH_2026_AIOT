#ifndef ESP32_SGP30_LIB_H
#define ESP32_SGP30_LIB_H

#include <Arduino.h>
#include <Wire.h>

/*
- Bảng 10 trang 9 Measurement duration
Lệnh đo khí cần tối đa 12ms để chip tính toán

- Luật 1s và 15s
+ Bắt buộc phải gửi lệnh đo đều đặn mỗi 1 giây để thuật toán 
bù đường nền hoạt động đúng
+ Trong 15 giây đầu tiên, cảm biến chỉ trả về các giá trị cố định 
là 400 ppm CO2eq và 0 ppb TVOC

- SGP30 liên tục trả về 3 data lần lượt C02 (msb) - C02 (lsb) - CRC của CO2
+ 1. Khởi tạo vs 0xFF
+ 2. XOR 0xFF vs byte đầu tiên
+ 3. Kiểm tra vs chu kỳ 8 lần, nếu bit ngoài cùng là 
    0: Chỉ dịch trái 1 lần
    1: Dịch trái vầ XOR vs 0x31
+ Được 1 byte kết quả đem XOR vs byte 2 (lsb) như bước 2
*/

// Địa chỉ
#define SGP30_I2C_ADDR 0x58

// Danh sách thanh ghi 16-bit
// Khởi tạo thuật toán đo chất lượng KK
// MAX: 10ms
#define SGP30_CMD_INIT_AIR_QUALITY 0x2003

// Yêu cầu cảm biến đo chất lượng KK
// Khi request thì trả về 6 byte
// MAX: 12ms
#define SGP30_CMD_MEASURE_AIR_QUALITY 0x2008

// Đọc phiên bản: Trả về 3 byte
// 0: SGP30
// 1: SGPC3
// MAX: 2ms
#define SGP30_CMD_GET_FEATURE_SET 0x202F

// Struct lưu data
typedef struct {
    uint16_t CO2_eq;
    uint16_t TVOC;
} SGP30_Data_t;

bool SGP30_Init();
bool SGP30_Measure(SGP30_Data_t* data);

// ==== TEST MAIN ====
void SGP30_TestSetup(void);
void SGP30_TestLoop(void);

#endif