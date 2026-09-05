#ifndef ESP32_NEO_M8N_GPS_H
#define ESP32_NEO_M8N_GPS_H

#include <Arduino.h>
#include <string.h>
#include <stdlib.h>

// UART INPUT
// 9600 Baud, 8 bits, no parity bit, 1 stop bit, Autobauding disabled

/*
$GNRMC,hhmmss.ss,A,llll.ll,a,yyyyy.yy,a,x.x,x.x,ddmmyy,x.x,a*hh

+ 1. $GNRMC: Tên gói tin (GN = Đa hệ vệ tinh, RMC = Thông tin định vị tối thiểu).
+ 2. hhmmss.ss: Giờ phút giây (Chuẩn giờ UTC, muốn ra giờ Việt Nam phải +7).
+ 3. A: Cờ trạng thái (A = Active / Đã có sóng vệ tinh; V = Void / Mất sóng).
+ 4. llll.ll: Vĩ độ (Định dạng: Độ và Phút).
+ 5. a: Hướng Vĩ độ (N = Bắc, S = Nam).
+ 6. yyyyy.yy: Kinh độ (Định dạng: Độ và Phút).
+ 7. a: Hướng Kinh độ (E = Đông, W = Tây).
+ 8. x.x: Tốc độ di chuyển (Đơn vị: Knot/Hải lý trên giờ. Nhân với 1.852 sẽ ra km/h).
+ 9. x.x: Góc hướng di chuyển (Course - La bàn) tính bằng độ.
+ 10. ddmmyy: Ngày tháng năm.
+ 11. Hai trường cuối thường trống (Từ thiên) và kết thúc bằng Checksum (ví dụ *57) 
để xác minh gói tin không bị lỗi trong quá trình truyền tải.

Kinh độ, vĩ độ thường sẽ theo định dạng sau (đvi: độ phút)
    ddmm.mmmm
*/

/* TIPS: 
- Sử dụng Serial1 9600 để giao tiếp
Serial0 115200 hiện data
- Nó là 1 bộ RTC chính xác nhất
=> Sử dụng nó để update thời gian vào trong bộ RTC có sẵn trong ESP32
*/

#define GPS_RX_PIN 32
#define GPS_TX_PIN 33

// Struct bóc tách gói tin 
typedef struct {
    float latitude;   // Vĩ độ 
    float longitude;  // Kinh độ 
    float speed_kmh;  // Tốc độ 
    bool isValid;     // Trạng thái chốt vệ tinh
    
    // Thêm các biến thời gian (Chuẩn UTC)
    uint8_t hour;
    uint8_t minute;
    uint8_t second;

    uint8_t day;
    uint8_t month;
    uint16_t year;
} NEO_Data_t;

void NEO_M8N_Init(HardwareSerial* serialPort);
bool NEO_M8N_ReadData(NEO_Data_t* gpsData);

// ==== TEST MAIN ====
void NEO_M8N_TestSetup(void);
void NEO_M8N_TestLoop(void);

#endif