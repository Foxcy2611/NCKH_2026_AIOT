#ifndef NCKH_SECURE_PROTOCOL_H
#define NCKH_SECURE_PROTOCOL_H

#include <stddef.h>
#include <stdint.h>

// =====================================================
// Hằng số giao thức
// =====================================================

constexpr uint16_t SECURE_PACKET_MAGIC = 0xA57A;

constexpr uint8_t SECURE_PROTOCOL_VERSION = 1;

constexpr size_t AES_128_KEY_SIZE    = 16;
constexpr size_t AES_GCM_NONCE_SIZE = 12;
constexpr size_t AES_GCM_TAG_SIZE   = 16;

constexpr size_t SECURE_PAYLOAD_SIZE = 24;

// =====================================================
// Kiểu tin nhắn
// =====================================================
typedef enum : uint8_t {
    MSG_PATIENT_EVENT = 1,
    MSG_GATEWAY_RESPONSE = 2

} Secure_Message_Type_t;

// =====================================================
// Kiểu phản hồi từ Gateway
// =====================================================
typedef enum : uint8_t {

    RESPONSE_ACK_ACCEPTED = 0,

    RESPONSE_ACK_DUPLICATE,

    RESPONSE_NACK_BUSY,

    RESPONSE_NACK_UNSUPPORTED,

    RESPONSE_NACK_INTERNAL

} Gateway_Response_Code_t;

// =====================================================
// Cấu trúc PAYLOAD và PACKET BẢO MẬT TRYỀN ESP-NOW (TRUYỀN TẢI)
// =====================================================

// /* VÙNG DỮ LIỆU LOGIC */ //
#pragma pack(push, 1)

typedef struct {
    uint32_t session_id;       // ID phiên đo liên kết các tập dữ liệu
    uint64_t timestamp;        // Dấu thời gian lúc đóng gói bản tin

    uint8_t event_type;        // Phân loại mục đích gói tin 

    uint8_t classification;    // Kết quả AI (Sử dụng AiResult ép kiểu uint8_t)
    float model_score;         // Độ tự tin của mô hình AI

    uint8_t audio_quality;     // Tình trạng file âm thanh (Sử dụng AudioQuality ép kiểu uint8_t)

    uint8_t vitals_valid;      // 1 nếu dữ liệu nhịp tim/SpO2 có giá trị
    uint16_t heart_rate;       // Dữ liệu nhịp tim
    uint8_t spo2;              // Dữ liệu SpO2

    uint8_t battery;           // Phần trăm pin hiện hành

} Patient_Event_Payload_t;

#pragma pack(pop)

// /* VÙNG DỮ LIỆU BẢO MẬT - PACKET THẬT SỰ GỬI QUA ESP-NOW */ //
#pragma pack(push, 1)
typedef struct {
    // =============================
    // HEADER + AAD: không mã hóa
    // =============================
    uint16_t magic;
    uint8_t protocol_version;
    uint8_t message_type;

    uint32_t device_id;
    uint32_t sequence;

    // =============================
    // AES-GCM
    // =============================
    uint8_t nonce[AES_GCM_NONCE_SIZE];

    // Một trong hai payload logic 24 byte sau khi mã hóa
    uint8_t ciphertext[SECURE_PAYLOAD_SIZE];

    // Mã xác thực AES-GCM
    uint8_t authentication_tag[AES_GCM_TAG_SIZE];

} Secure_EspNow_Packet_t;
#pragma pack(pop)


// =====================================================
// GATEWAY RESPONSE PLAINTEXT
// =====================================================

#pragma pack(push, 1)

typedef struct {

    uint32_t target_device_id;

    uint32_t session_id;

    uint64_t gateway_timestamp;

    uint8_t response_code;

    uint8_t time_valid;

    uint8_t reserved[6];

} Gateway_Response_Payload_t;

#pragma pack(pop)



constexpr size_t SECURE_AAD_SIZE =
    offsetof(
        Secure_EspNow_Packet_t,
        nonce
    );


// =====================================================
// COMPILE-TIME CHECK
// =====================================================

static_assert(
    sizeof(Patient_Event_Payload_t) == 24,
    "Patient_Event_Payload_t must be 24 bytes"
);

static_assert(
    sizeof(Gateway_Response_Payload_t) == 24,
    "Gateway_Response_Payload_t must be 24 bytes"
);

static_assert(
    SECURE_AAD_SIZE == 12,
    "AAD must be 12 bytes"
);

static_assert(
    sizeof(Secure_EspNow_Packet_t) == 64,
    "Secure_EspNow_Packet_t must be 64 bytes"
);

#endif /* NCKH_SECURE_PROTOCOL_H */
