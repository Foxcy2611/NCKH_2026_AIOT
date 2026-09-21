#ifndef NCKH_SECURE_SENDER_H
#define NCKH_SECURE_SENDER_H

#include <stdint.h>
#include <stddef.h>

#include "Secure_Protocol.h"

// =====================================================
// Kết quả đóng gói bảo mật
// =====================================================
typedef enum {
    SECURE_SENDER_OK = 0,
    SECURE_SENDER_NOT_INITIALIZED,  // Chưa đc khởi tạo
    SECURE_SENDER_INVALID_ARGUMENT, // Tham số không hợp lệ
    SECURE_SENDER_CRYPTO_ERROR      // Lỗi mã hóa

} Secure_Sender_Result_t;

/*
- Khởi tạo
+ Device id: ID của Patient Node
+ Key: KEY_NODE_TO_GATEWAY 16 byte
*/ 
bool SecureSender_Init(
    uint32_t device_id, 
    const uint8_t key[AES_128_KEY_SIZE]
);

/*
- Mã hóa
INPUT: + payload = plaintext Patient Event
       + sequence = sequence của Event mới

Output: out_packet = packet 56 byte hoàn chỉnh
*/

Secure_Sender_Result_t SecureSender_BuildPatientEvent(
    const Node_Payload_t* payload,
    uint32_t sequence,
    Secure_Packet_t* out_packet
);

#endif /* NCKH_SECURE_SENDER_H */
