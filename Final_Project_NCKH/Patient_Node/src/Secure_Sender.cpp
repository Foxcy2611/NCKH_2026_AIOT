#include "Network/Secure_Sender.h"

#include <string.h>

#include <esp_system.h>
#include <mbedtls/gcm.h>

namespace {
    // Khởi tạo packet được chưa ?
    bool is_initialized = false;

    uint32_t dvc_id = 0;

    uint8_t node_to_gateway_key[AES_128_KEY_SIZE];
}

bool SecureSender_Init(
    uint32_t device_id, 
    const uint8_t key[AES_128_KEY_SIZE]
){
    if(key == nullptr){
        return false;
    }

    dvc_id = device_id;
    memcpy(node_to_gateway_key, key, AES_128_KEY_SIZE);

    is_initialized = true;

    return true;
}

Secure_Sender_Result_t SecureSender_BuildPatientEvent(
    const Patient_Event_Payload_t* payload,
    uint32_t sequence,
    Secure_EspNow_Packet_t* out_packet
){
    if(!is_initialized){
        return SECURE_SENDER_NOT_INITIALIZED;
    }

    if(payload == nullptr || out_packet == nullptr){
        return SECURE_SENDER_INVALID_ARGUMENT;
    }

    // Clean packet
    memset(out_packet, 0, SECURE_PACKET_SIZE);

    // 1. Build HEADER / AAD
    out_packet->magic = SECURE_PACKET_MAGIC;                // MAGIC
    out_packet->protocol_version = SECURE_PROTOCOL_VERSION; // VERSION
    out_packet->message_type = MSG_PATIENT_EVENT;           // MESSAGE_TYPE
    out_packet->device_id = dvc_id;                         // DEVICE_ID
    out_packet->sequence = sequence;                        // SEQUENCE

    // 2. Sinh ra 12 byte NONCE
    // Chỉ sinh ra 1 lần khi tạo event mới
    // Khi retry phải gửi lại nguyên packet cũ
    esp_fill_random(out_packet->nonce, AES_GCM_NONCE_SIZE);

    // 3. Tạo context nội bộ
    mbedtls_gcm_context ctx;
    mbedtls_gcm_init(&ctx);

    // 4. Set AES-128 KEY
    int result = mbedtls_gcm_setkey(
        &ctx, MBEDTLS_CIPHER_ID_AES,
        node_to_gateway_key, 128
    );

    /*
    5. ENCRYPT + AUTHENTICATE
    
    plaintext:
        Patient_Event_Payload_t
    AAD:
        12-byte Header
    
    output:
        ciphertext[24]
        authentication_tag[16]
    */
    if(result == 0){
        result = mbedtls_gcm_crypt_and_tag(
            &ctx, MBEDTLS_GCM_ENCRYPT,

            // Plaintext size
            SECURE_PAYLOAD_SIZE, 
            
            // Nonce
            out_packet->nonce, AES_GCM_NONCE_SIZE,

            // AAD: 12 byte, ép kiểu về dạng mảng byte 8 bit
            reinterpret_cast<const uint8_t*>(out_packet), SECURE_AAD_SIZE,

            // Plaintext Input
            reinterpret_cast<const uint8_t*>(payload),

            // Ciphertext Output
            out_packet->ciphertext,

            // TAG
            AES_GCM_TAG_SIZE, out_packet->authentication_tag
        );
    }

    // 6. Clean GCM context
    mbedtls_gcm_free(&ctx);

    // 7. If Fail
    if(result != 0){
        memset(out_packet, 0, SECURE_PACKET_SIZE);

        return SECURE_SENDER_CRYPTO_ERROR;
    }

    // 8. SUCESS
    return SECURE_SENDER_OK;    
}