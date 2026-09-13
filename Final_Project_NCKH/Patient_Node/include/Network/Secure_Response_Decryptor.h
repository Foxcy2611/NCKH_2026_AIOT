#ifndef NCKH_SECURE_RESPONSE_DECRYPTOR_H
#define NCKH_SECURE_RESPONSE_DECRYPTOR_H

#include <stdint.h>

#include "Secure_Protocol.h"

// Kết quả giải mã từ PACKET của Gateway (RESPONSE)
typedef enum {
    SECURE_RESPONSE_DECRYPT_OK = 0,

    SECURE_RESPONSE_NOT_INITIALIZED,    // Chưa được khởi tạo
    SECURE_RESPONSE_INVALID_ARGUMENT,   // Tham số không hợp lệ
    SECURE_RESPONSE_INVALID_HEADER,     // Tiêu đề không hợp lệ
    SECURE_RESPONSE_UNEXPECTED_PACKET,  // Gói tin bất thường
    SECURE_RESPONSE_CRYPTO_ERROR,       // Lỗi mã hóa
    SECURE_RESPONSE_AUTH_FAILED,        // Xác thực thất bại
    SECURE_RESPONSE_INVALID_PAYLOAD     // Dữ liệu trong Payload không hợp lệ

} Secure_Response_Decrypt_Result_t;

/*
- Khởi tạo bộ giải mã
+ node_device_id: ID của chính Patient Node
+ gateway_device_id: ID của Gateway hợp lệ
+ key: KEY_GATEWAY_TO_NODE dài 16 byte
*/

bool SecureResponse_Init(
    uint32_t node_device_id,
    uint32_t gateway_device_id,
    const uint8_t key[AES_128_KEY_SIZE]
);

/*
- Xác thực và giải mã phản hồi từ Gateway.
+ expected_sequence: Sequence của Event đang nằm trong Pending Queue.
+ expected_session_id: Session ID của Event đang chờ ACK/NACK.
 
- Thành công:
-> out_response chứa Gateway_Response_Payload_t hợp lệ.
- Thất bại:
-> out_response được xóa về 0 và không được sử dụng.
*/
Secure_Response_Decrypt_Result_t SecureResponseDecryptor_Decrypt(
    const Secure_EspNow_Packet_t* packet,
    uint32_t expected_sequence,
    uint32_t expected_session_id,
    Gateway_Response_Payload_t* out_response
);



#endif /* NCKH_SECURE_RESPONSE_DECRYPTOR_H */