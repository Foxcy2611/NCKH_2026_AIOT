#ifndef NCKH_GATEWAY_TYPES_H
#define NCKH_GATEWAY_TYPES_H

#include <Arduino.h>

// ============================================================
// Patient Event types
// ============================================================

enum PatientEventType : uint8_t
{
    EVENT_MANUAL_CHECK = 0,
    EVENT_MONITOR      = 1,
    EVENT_STATUS       = 2
};

// Classification của AI
enum PatientClassification : uint8_t
{
    CLASS_NON_ASTHMA = 0,
    CLASS_ASTHMA_LIKE = 1
};

// ============================================================
// Packet gửi từ Patient Node -> Gateway
//
// Giữ đúng concept trong Final Project:
// device_id
// sequence
// session_id
// timestamp
// event_type
// classification
// model_score
// asthma_votes
// non_asthma_votes
// audio_quality
// vitals_valid
// heart_rate
// spo2
// battery_percent
// ============================================================

struct PatientEventPacket
{
    uint32_t device_id;

    uint32_t sequence;
    uint32_t session_id;

    uint64_t timestamp;

    uint8_t event_type;

    uint8_t classification;
    float model_score;

    uint8_t asthma_votes;
    uint8_t non_asthma_votes;

    uint8_t audio_quality;

    bool vitals_valid;
    uint16_t heart_rate;
    uint8_t spo2;

    uint8_t battery_percent;
};

// ============================================================
// Raw packet dùng giữa ESP-NOW callback và TaskEspNow
//
// Callback KHÔNG parse PatientEventPacket.
// Nó chỉ copy raw bytes vào queue.
// ============================================================

#define ESPNOW_MAX_PACKET_SIZE 250

struct EspNowRawPacket
{
    uint8_t data[ESPNOW_MAX_PACKET_SIZE];

    uint16_t length;

    uint8_t mac[6];
};

// ============================================================
// Gateway statistics
// ============================================================

struct GatewayStats
{
    uint32_t espnow_received;
    uint32_t espnow_valid;
    uint32_t espnow_invalid;
    uint32_t queue_dropped;
};

#endif