#include "Network/Secure_Response_Decryptor.h"

#include <string.h>
#include <mbedtls/gcm.h>

namespace {
    bool is_initialized = false;

    uint32_t local_node_id = 0;
    uint32_t expected_gateway_id = 0;

    uint8_t gateway_to_node_key[AES_128_KEY_SIZE];

    void SecureResponse_ClearResponse(Response_Payload_t* response){
        if(response != nullptr){
            memset(response, 0, sizeof(*response));
        }
    }
}

bool SecureResponse_Init(
    uint32_t node_device_id,
    uint32_t gateway_device_id,
    const uint8_t key[AES_128_KEY_SIZE]
){
    if(key == nullptr || 
        node_device_id == 0 ||
        gateway_device_id == 0
    ){
        return false;
    }

    local_node_id = node_device_id;
    expected_gateway_id = gateway_device_id;

    memcpy(gateway_to_node_key, key, AES_128_KEY_SIZE);

    is_initialized = true;

    return true;
}

Secure_Response_Decrypt_Result_t SecureResponseDecryptor_Decrypt(
    const Secure_Packet_t* packet,
    uint32_t expected_sequence,
    uint32_t expected_session_id,
    Response_Payload_t* out_response
){
    if(!is_initialized){
        SecureResponse_ClearResponse(out_response);
        return SECURE_RESPONSE_NOT_INITIALIZED;
    }

    if(packet == nullptr || out_response == nullptr){
        SecureResponse_ClearResponse(out_response);
        return SECURE_RESPONSE_INVALID_ARGUMENT;
    }

    // 1. Kiểm tra Header trước khi gọi AES-GCM
    if(packet->magic != SECURE_PACKET_MAGIC ||
        packet->protocol_version != SECURE_PROTOCOL_VERSION ||
        packet->message_type != MSG_GATEWAY_RESPONSE
    ){
        return SECURE_RESPONSE_INVALID_HEADER;
    }

    if(packet->device_id != expected_gateway_id ||
        packet->sequence != expected_sequence
    ){
        return SECURE_RESPONSE_UNEXPECTED_PACKET;
    }

    // 2. Khởi tạo AES-GCM
    mbedtls_gcm_context ctx;
    mbedtls_gcm_init(&ctx);

    int result = mbedtls_gcm_setkey(
        &ctx, MBEDTLS_CIPHER_ID_AES,
        gateway_to_node_key, 128
    );
    if(result != 0){
        mbedtls_gcm_free(&ctx);
        return SECURE_RESPONSE_CRYPTO_ERROR;
    }

    // 3. Xác thực tag và giải mã ciphertext
    result = mbedtls_gcm_auth_decrypt(
        &ctx, 
        SECURE_PAYLOAD_SIZE,

        // NONCE
        packet->nonce, AES_GCM_NONCE_SIZE,

        // AAD là Header 12 byte đầu packet
        reinterpret_cast<const uint8_t*>(packet), SECURE_AAD_SIZE,

        // Authentication TAG
        packet->authentication_tag, AES_GCM_TAG_SIZE,

        // Ciphertext Input
        packet->ciphertext,

        // Plaintext Output
        reinterpret_cast<uint8_t*>(out_response)
    );

    mbedtls_gcm_free(&ctx);

    if(result != 0){
        SecureResponse_ClearResponse(out_response);
        return SECURE_RESPONSE_AUTH_FAILED;
    }

    // 4. Kiểm tra nội dung sau khi tag hợp lệ
    if(out_response->target_device_id != local_node_id ||
        out_response->session_id != expected_session_id ||
        out_response->response_code > static_cast<uint8_t>(RESPONSE_NACK_INTERNAL) ||
        out_response->time_valid > 1
    ){
        SecureResponse_ClearResponse(out_response);
        return SECURE_RESPONSE_INVALID_PAYLOAD;
    }

    return SECURE_RESPONSE_DECRYPT_OK;
}