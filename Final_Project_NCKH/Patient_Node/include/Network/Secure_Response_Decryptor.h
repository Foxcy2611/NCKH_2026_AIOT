#ifndef NCKH_SECURE_RESPONSE_DECRYPTOR_H
#define NCKH_SECURE_RESPONSE_DECRYPTOR_H

#include <stdint.h>

#include "Secure_Protocol.h"

// Kết quả xác thực và giải mã phản hồi Gateway -> Patient Node.
typedef enum {
    SECURE_RESPONSE_DECRYPT_OK = 0,
    SECURE_RESPONSE_NOT_INITIALIZED,
    SECURE_RESPONSE_INVALID_ARGUMENT,
    SECURE_RESPONSE_INVALID_HEADER,
    SECURE_RESPONSE_UNEXPECTED_PACKET,
    SECURE_RESPONSE_CRYPTO_ERROR,
    SECURE_RESPONSE_AUTH_FAILED,
    SECURE_RESPONSE_INVALID_PAYLOAD
} Secure_Response_Decrypt_Result_t;

// Khởi tạo thông tin định danh và khóa riêng cho chiều Gateway -> Node.
bool SecureResponse_Init(
    uint32_t node_device_id,
    uint32_t gateway_device_id,
    const uint8_t key[AES_128_KEY_SIZE]
);

// Xác thực header/tag, giải mã Response_Payload_t và đối chiếu packet đang pending.
Secure_Response_Decrypt_Result_t SecureResponseDecryptor_Decrypt(
    const Secure_Packet_t* packet,
    uint32_t expected_sequence,
    uint32_t expected_session_id,
    Response_Payload_t* out_response
);

#endif /* NCKH_SECURE_RESPONSE_DECRYPTOR_H */
