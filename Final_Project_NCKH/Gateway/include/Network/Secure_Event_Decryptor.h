#ifndef NCKH_SECURE_EVENT_DECRYPTOR_H
#define NCKH_SECURE_EVENT_DECRYPTOR_H

#include <stdint.h>

#include "Secure_Protocol.h"

/**
 * Kết quả giải mã Patient Event tại Gateway.
 *
 * Lưu ý:
 * - Sai authentication tag được coi là gói không hợp lệ và không được sử dụng.
 * - Kiểm tra MAC nguồn, sequence trùng/lùi và tạo ACK/NACK không nằm trong thư viện này.
 */
typedef enum {
    SECURE_EVENT_DECRYPT_OK = 0,
    SECURE_EVENT_INVALID_ARGUMENT,
    SECURE_EVENT_INVALID_HEADER,
    SECURE_EVENT_UNEXPECTED_NODE,
    SECURE_EVENT_CRYPTO_ERROR,
    SECURE_EVENT_AUTH_FAILED,
    SECURE_EVENT_INVALID_PAYLOAD
} Secure_Event_Decrypt_Result_t;

/**
 * Xác thực và giải mã một gói MSG_PATIENT_EVENT tại Gateway.
 *
 * @param packet            Gói bảo mật 64 byte nhận từ ESP-NOW.
 * @param expected_node_id  device_id của Node đã được Gateway xác định từ MAC nguồn.
 * @param key               Khóa AES-128 dài đúng 16 byte của Node đó.
 * @param out_payload       Nơi nhận Patient_Event_Payload_t sau khi giải mã thành công.
 *
 * @return SECURE_EVENT_DECRYPT_OK khi gói hợp lệ. Với mọi lỗi, out_payload được xóa về 0.
 */
Secure_Event_Decrypt_Result_t SecureEvent_Decrypt(
    const Secure_EspNow_Packet_t* packet,
    uint32_t expected_node_id,
    const uint8_t key[AES_128_KEY_SIZE],
    Patient_Event_Payload_t* out_payload
);

#endif /* NCKH_SECURE_EVENT_DECRYPTOR_H */
