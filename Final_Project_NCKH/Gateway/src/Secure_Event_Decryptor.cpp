#include "Network/Secure_Event_Decryptor.h"

#include <string.h>

#include <mbedtls/gcm.h>

namespace {

void SecureEvent_ClearPayload(Patient_Event_Payload_t* payload) {
    if (payload != nullptr) {
        memset(payload, 0, sizeof(*payload));
    }
}

bool SecureEvent_IsPayloadValid(const Patient_Event_Payload_t& payload) {
    // Các giá trị enum hiện hành của giao thức:
    // event_type: 0..2, classification: 0..2, audio_quality: 0..3.
    if (payload.session_id == 0U ||
        payload.event_type > 2U ||
        payload.classification > 2U ||
        payload.audio_quality > 3U ||
        payload.vitals_valid > 1U ||
        payload.spo2 > 100U ||
        payload.battery > 100U) {
        return false;
    }

    // Phép so sánh này cũng loại NaN và vô cực.
    if (!(payload.model_score >= 0.0F && payload.model_score <= 1.0F)) {
        return false;
    }

    // Khi cờ không hợp lệ, Node phải gửi các chỉ số sinh tồn bằng 0.
    if (payload.vitals_valid == 0U &&
        (payload.heart_rate != 0U || payload.spo2 != 0U)) {
        return false;
    }

    return true;
}

} // namespace

Secure_Event_Decrypt_Result_t SecureEvent_Decrypt(
    const Secure_EspNow_Packet_t* packet,
    uint32_t expected_node_id,
    const uint8_t key[AES_128_KEY_SIZE],
    Patient_Event_Payload_t* out_payload
) {
    if (packet == nullptr || key == nullptr || out_payload == nullptr ||
        expected_node_id == 0U) {
        SecureEvent_ClearPayload(out_payload);
        return SECURE_EVENT_INVALID_ARGUMENT;
    }

    SecureEvent_ClearPayload(out_payload);

    if (packet->magic != SECURE_PACKET_MAGIC ||
        packet->protocol_version != SECURE_PROTOCOL_VERSION ||
        packet->message_type != MSG_PATIENT_EVENT) {
        return SECURE_EVENT_INVALID_HEADER;
    }

    if (packet->device_id != expected_node_id) {
        return SECURE_EVENT_UNEXPECTED_NODE;
    }

    mbedtls_gcm_context context;
    mbedtls_gcm_init(&context);

    int result = mbedtls_gcm_setkey(
        &context,
        MBEDTLS_CIPHER_ID_AES,
        key,
        AES_128_KEY_SIZE * 8U
    );

    if (result != 0) {
        mbedtls_gcm_free(&context);
        return SECURE_EVENT_CRYPTO_ERROR;
    }

    result = mbedtls_gcm_auth_decrypt(
        &context,
        SECURE_PAYLOAD_SIZE,
        packet->nonce,
        AES_GCM_NONCE_SIZE,
        reinterpret_cast<const uint8_t*>(packet),
        SECURE_AAD_SIZE,
        packet->authentication_tag,
        AES_GCM_TAG_SIZE,
        packet->ciphertext,
        reinterpret_cast<uint8_t*>(out_payload)
    );

    mbedtls_gcm_free(&context);

    if (result != 0) {
        SecureEvent_ClearPayload(out_payload);
        return SECURE_EVENT_AUTH_FAILED;
    }

    if (!SecureEvent_IsPayloadValid(*out_payload)) {
        SecureEvent_ClearPayload(out_payload);
        return SECURE_EVENT_INVALID_PAYLOAD;
    }

    return SECURE_EVENT_DECRYPT_OK;
}
