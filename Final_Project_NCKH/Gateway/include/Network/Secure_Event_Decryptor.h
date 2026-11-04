#ifndef NCKH_SECURE_EVENT_DECRYPTOR_H
#define NCKH_SECURE_EVENT_DECRYPTOR_H

#include <stdint.h>
#include "Secure_Protocol.h"

typedef enum {
    SECURE_EVENT_DECRYPT_OK = 0,
    SECURE_EVENT_INVALID_ARGUMENT,
    SECURE_EVENT_INVALID_HEADER,
    SECURE_EVENT_UNEXPECTED_NODE,
    SECURE_EVENT_CRYPTO_ERROR,
    SECURE_EVENT_AUTH_FAILED,
    SECURE_EVENT_INVALID_PAYLOAD
} Secure_Event_Decrypt_Result_t;

Secure_Event_Decrypt_Result_t SecureEvent_Decrypt(
    const Secure_Packet_t* packet,
    uint32_t expected_node_id,
    const uint8_t key[AES_128_KEY_SIZE],
    Node_Payload_t* out_payload
);

bool SecureGateway_BuildResponse(
    uint32_t target_device_id,
    uint32_t sequence,
    uint32_t session_id,
    Gateway_Response_Code_t response_code,
    const uint8_t key[AES_128_KEY_SIZE],
    Secure_Packet_t* out_packet
);

#endif
