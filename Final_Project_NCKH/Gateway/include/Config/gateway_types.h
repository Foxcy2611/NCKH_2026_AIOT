#ifndef NCKH_GATEWAY_TYPES_H
#define NCKH_GATEWAY_TYPES_H

#include <Arduino.h>
#include <stdint.h>
#include <string.h>
#include "Secure_Protocol.h"

// Internal Gateway representation of an authenticated Patient Event.
// The payload itself is the canonical 24-byte struct from Secure_Protocol.h.
struct PatientEventEnvelope {
    Node_Payload_t payload;
    uint32_t device_id;
    uint32_t sequence;
    uint8_t mac[6];
    uint64_t received_timestamp_ms;
};

// Raw item copied by the ESP-NOW callback.
struct EspNowRawPacket {
    uint8_t data[SECURE_PACKET_SIZE];
    uint16_t length;
    uint8_t mac[6];
};

struct EnvironmentSnapshot {
    uint64_t gateway_timestamp_ms;
    bool temperature_valid;
    float temperature_c;
    bool humidity_valid;
    float humidity_percent;
    bool pressure_valid;
    float pressure_hpa;
    bool eco2_valid;
    uint16_t eco2_ppm;
    bool tvoc_valid;
    uint16_t tvoc_ppb;
};

typedef enum : uint8_t {
    GATE_MODE_HOME = 0,
    GATE_MODE_OFFLINE,
    GATE_MODE_MOBILE
} Gate_Operating_Mode_t;

typedef enum : uint8_t {
    GATE_UPLINK_NONE = 0,
    GATE_UPLINK_WIFI,
    GATE_UPLINK_LTE
} Gate_Uplink_Type_t;

typedef enum : uint8_t {
    SENSOR_DHT22_VALID  = 1 << 0,
    SENSOR_BMP280_VALID = 1 << 1,
    SENSOR_SGP30_VALID  = 1 << 2,
    SENSOR_GPS_VALID    = 1 << 3
} Gate_Sensor_Valid_Bit_t;

// Cloud/internal Gateway payload defined by GATE_PAYLOAD_COMPLETE_PACKET_DESIGN.md.
struct Gateway_Payload_t {
    uint32_t gateway_id;
    uint64_t timestamp;
    uint8_t operating_mode;
    uint8_t uplink_type;
    float temperature;
    float humidity;
    float pressure;
    uint16_t tvoc;
    uint16_t eco2;
    uint8_t sensor_valid_mask;
    uint8_t wifi_connected;
    int16_t wifi_rssi_dbm;
    uint8_t lte_registered;
    int16_t lte_rssi_dbm;
    uint8_t mqtt_connected;
    double latitude;
    double longitude;
    uint64_t gps_timestamp;
};

struct Complete_Packet_t {
    uint8_t has_patient_event;
    Gateway_Payload_t gate;
    Node_Payload_t patient_event;
};

// Compatibility name used in the M4 task/aggregator roadmap.
using CompleteRecord = Complete_Packet_t;

struct GatewayStats {
    volatile uint32_t espnow_received;
    volatile uint32_t espnow_valid;
    volatile uint32_t espnow_invalid;
    volatile uint32_t auth_failed;
    volatile uint32_t duplicates;
    volatile uint32_t replay_rejected;
    volatile uint32_t ack_sent;
    volatile uint32_t nack_sent;
    volatile uint32_t queue_dropped;
    volatile uint32_t complete_records;
    volatile uint32_t mqtt_published;
    volatile uint32_t mqtt_failed;
};

extern GatewayStats gatewayStats;

#endif
