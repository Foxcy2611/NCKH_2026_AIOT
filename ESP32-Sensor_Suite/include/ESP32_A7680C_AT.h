#ifndef ESP32_A7680C_AT
#define ESP32_A7680C_AT

#include <Arduino.h>

/* Nhiệm vụ của A7680C
- data module: bình thường
- AI kết luận có bệnh 
=> Gửi tin nhắn kèm nội dung khuyên người dùng 
đi khám bệnh
(SMS)

- data module: nguy hiểm
- AI kết luận có bệnh 
=> Gửi tin nhắn kèm nội dung cấp bách, nháy 1 cuộc gọi sẽ 
tự động tắt sau bắt máy 5-10s 
(SNS + Call)
*/

/*
- Bảng lệnh
Lệnh   |     Chức năng        | Phản hồi mong đợi
+ AT - Ping kiểm tra kết nối - OK
+ ATE0 - Tắt chế độ nhại lệnh - OK
+ AT+CPIN? - Kiểm tra SIM sẵn sàng hay khóa - +CPIN: READY ... OK
+ AT+CSQ - Đọc chất lượng sóng ăng-ten - +CSQ: ...
+ AT+CEREG? - Kiểm tra đăng ký mạng / sim phù hợp vs nhà mạng chưa - OK
-> 1: Đã đki, mạng nhà ; 5: đã đăng ký
+ ATD<số> - Gọi điện thoại - OK
+ ATH - Cúp máy - OK
+ AT+CMGF=1 - Đưa tin nhắn về chế độ text mode - OK
+ AT+CMGS="..." - Bắt đầu gửi tin nhắn - >(Dấu đợi nhập nội dung)

*/

#define SIM_RX_PIN 16
#define SIM_TX_PIN 17

bool A7680C_Init(HardwareSerial& serialPort, uint8_t rxPin, uint8_t txPin, uint32_t baudrate);

// Các hàm kiểm tra trạng thái
int A7680C_GetSignalQuality();
bool A7680C_CheckAlive();
bool A7680C_CheckSIM();
bool A7680C_CheckNetwork();

// Các hàm thực thi cơ bản
bool A7680C_MakeCall(const char* phoneNumber);
bool A7680C_HangUp();
bool A7680C_SendSMS(const char* phoneNumber, const char* message);

// Hàm gọi điện thông minh: Tự động cúp máy sau X giây (Có hỗ trợ ghi chú chuyển đổi RTOS)
bool A7680C_CallWithAutoHangUp(const char* phoneNumber, uint8_t activeDuration_sec, uint8_t maxTimeout_sec);

// Hàm test trong main gồm setup, loop để delay treo
void A7680C_TestMain();

#endif