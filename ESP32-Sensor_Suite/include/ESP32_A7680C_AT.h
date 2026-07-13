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

bool A7680C_Init(HardwareSerial& serialPort, uint8_t rxPin, uint8_t txPin, uint32_t baudrate);

// Các hàm kiểm tra trạng thái
bool A7680C_CheckAlive();
bool A7680C_CheckSIM();
int  A7680C_GetSignalQuality();
bool A7680C_CheckNetwork();

// Các hàm thực thi cơ bản
bool A7680C_MakeCall(const char* phoneNumber);
bool A7680C_HangUp();
bool A7680C_SendSMS(const char* phoneNumber, const char* message);

// Hàm gọi điện thông minh: Tự động cúp máy sau X giây (Có hỗ trợ ghi chú chuyển đổi RTOS)
bool A7680C_CallWithAutoHangUp(const char* phoneNumber, uint8_t activeDuration_sec, uint8_t maxTimeout_sec);
#endif