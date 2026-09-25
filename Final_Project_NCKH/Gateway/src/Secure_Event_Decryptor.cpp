#include "Network/Secure_Event_Decryptor.h"
#include <string.h>
#include <mbedtls/gcm.h>
#include <esp_system.h>
#include "Config/gateway_config.h"
#include <Arduino.h>
namespace {
void clearPayload(Node_Payload_t *p) {
    if (p) memset(p, 0, sizeof(*p));
}

bool validPayload(const Node_Payload_t &p) {
    if (p.session_id == 0 || p.event_type > 2 || p.classification > 2 ||
        p.audio_quality > 3 || p.vitals_valid > 1 || p.spo2 > 100 ||
        p.battery_node > 100) return false;
    if (!(p.model_score >= 0.0f && p.model_score <= 1.0f)) return false;
    if (!p.vitals_valid && (p.heart_rate != 0 || p.spo2 != 0)) return false;
    return true;
}
}

Secure_Event_Decrypt_Result_t SecureEvent_Decrypt(
    const Secure_Packet_t* packet,
    uint32_t expected_node_id,
    const uint8_t key[AES_128_KEY_SIZE],
    Node_Payload_t* out_payload) {
    clearPayload(out_payload);
    if (!packet || !key || !out_payload || expected_node_id == 0) return SECURE_EVENT_INVALID_ARGUMENT;
    if (packet->magic != SECURE_PACKET_MAGIC ||
        packet->protocol_version != SECURE_PROTOCOL_VERSION ||
        packet->message_type != MSG_PATIENT_EVENT ||
        packet->device_id != expected_node_id ||
        packet->sequence == 0) return SECURE_EVENT_INVALID_HEADER;

    mbedtls_gcm_context ctx;
    mbedtls_gcm_init(&ctx);
    int r = mbedtls_gcm_setkey(&ctx, MBEDTLS_CIPHER_ID_AES, key, AES_128_KEY_SIZE * 8U);
    if (r == 0) {
        r = mbedtls_gcm_auth_decrypt(
            &ctx, SECURE_PAYLOAD_SIZE,
            packet->nonce, AES_GCM_NONCE_SIZE,
            reinterpret_cast<const uint8_t*>(packet), SECURE_AAD_SIZE,
            packet->authentication_tag, AES_GCM_TAG_SIZE,
            packet->ciphertext, reinterpret_cast<uint8_t*>(out_payload));
    }
    mbedtls_gcm_free(&ctx);
    if (r != 0) {
        clearPayload(out_payload);
        return (r == MBEDTLS_ERR_GCM_AUTH_FAILED) ? SECURE_EVENT_AUTH_FAILED : SECURE_EVENT_CRYPTO_ERROR;
    }
    if (!validPayload(*out_payload)) {
        clearPayload(out_payload);
        return SECURE_EVENT_INVALID_PAYLOAD;
    }
    return SECURE_EVENT_DECRYPT_OK;
}

bool SecureGateway_BuildResponse(
    uint32_t target_device_id,
    uint32_t sequence,
    uint32_t session_id,
    Gateway_Response_Code_t response_code,
    const uint8_t key[AES_128_KEY_SIZE],
    Secure_Packet_t* out_packet) {
    if (!key || !out_packet || target_device_id == 0 || sequence == 0) return false;
    Response_Payload_t payload{};
    payload.target_device_id = target_device_id;
    payload.session_id = session_id;
    payload.response_code = static_cast<uint8_t>(response_code);

    memset(out_packet, 0, sizeof(*out_packet));
    out_packet->magic = SECURE_PACKET_MAGIC;
    out_packet->protocol_version = SECURE_PROTOCOL_VERSION;
    out_packet->message_type = MSG_GATEWAY_RESPONSE;
    out_packet->device_id = GATEWAY_DEVICE_ID;
    out_packet->sequence = sequence;
    esp_fill_random(out_packet->nonce, AES_GCM_NONCE_SIZE);

    mbedtls_gcm_context ctx;
    mbedtls_gcm_init(&ctx);
    int r = mbedtls_gcm_setkey(&ctx, MBEDTLS_CIPHER_ID_AES, key, AES_128_KEY_SIZE * 8U);
    if (r == 0) {
        r = mbedtls_gcm_crypt_and_tag(
            &ctx, MBEDTLS_GCM_ENCRYPT, SECURE_RESPONSE_SIZE,
            out_packet->nonce, AES_GCM_NONCE_SIZE,
            reinterpret_cast<const uint8_t*>(out_packet), SECURE_AAD_SIZE,
            reinterpret_cast<const uint8_t*>(&payload), out_packet->ciphertext,
            AES_GCM_TAG_SIZE, out_packet->authentication_tag);
    }
    mbedtls_gcm_free(&ctx);
    if (r != 0) {
        memset(out_packet, 0, sizeof(*out_packet));
        return false;
    }
    return true;
}
