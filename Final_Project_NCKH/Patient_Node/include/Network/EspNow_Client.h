#ifndef NCKH_ESPNOW_CLIENT_H
#define NCKH_ESPNOW_CLIENT_H

#include <stdint.h>

#include "Secure_Protocol.h"

// =====================================================
// Trạng thái tổng thể khi gửi 1 packet qua ESP-NOW
// =====================================================
typedef enum {
    STATUS_IDLE = 0,          // Không có packet cần gửi
    STATUS_QUEUED,            // Packet đã nằm trong hàng đợi
    STATUS_SENDING,           // Đã gọi esp_now_send()
    STATUS_ACK_PENDING,       // ESP-NOW báo gửi được, đang chờ Gateway phản hồi
    STATUS_RETRY_WAIT,        // Đang chờ đến thời điểm gửi lại
    STATUS_ACK_CONFIRMED,     // Gateway xác nhận packet hợp lệ
    STATUS_NACK_RECEIVED,     // Gateway từ chối packet
    STATUS_RETRY_EXCEEDED,    // Đã vượt số lần gửi lại
    STATUS_SEND_ERROR         // Không thể gửi ở mức ESP-NOW
} Event_Send_Status_t;

// Setup cho esp-now
bool EspNow_Setup(void);

// Kiểm tra ESP-NOW sẵn sàng hay chưa
bool EspNow_IsReady(void);

// Đưa sự kiện vào vùng chờ
bool EspNow_QueuePatientEvent(const Patient_Event_Payload_t* payload);

// Hàm xử lý định kỳ
void EspNow_Process(void);

// True khi vẫn còn packet đang chờ gửi, retry hoặc chờ ACK/NACK.
bool EspNow_HasPendingEvent(void);

// Lấy trạng thái gửi hiện tại
Event_Send_Status_t EspNow_GetStatus(void);

#endif /* NCKH_ESPNOW_CLIENT_H */
