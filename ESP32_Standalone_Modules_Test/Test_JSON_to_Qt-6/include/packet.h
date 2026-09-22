#ifndef PACKET_H
#define PACKET_H

#include <stdint.h>

// Quy uoc chung voi Patient Node:
// 0 = ASTHMA, 1 = NON-ASTHMA, 2 = UNSURE.
typedef enum : uint8_t {
    CLASS_ASTHMA = 0,
    CLASS_NON_ASTHMA,
    CLASS_UNSURE
} Classification_t;

typedef enum : uint8_t {
    EVENT_MANUAL_CHECK = 0,
    EVENT_MONITOR
} Event_Type_t;

typedef enum : uint8_t {
    AUDIO_OK = 0,
    AUDIO_TOO_WEAK,
    AUDIO_TOO_LOUD,
    AUDIO_INACTIVE
} Audio_Quality_t;

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

#pragma pack(push, 1)
typedef struct {
    uint32_t session_id;
    uint8_t event_type;
    uint8_t classification;
    float model_score;
    uint8_t audio_quality;
    uint8_t vitals_valid;
    uint16_t heart_rate;
    uint8_t spo2;
    uint8_t battery_node;
} Node_Payload_t;
#pragma pack(pop)

static_assert(sizeof(Node_Payload_t) == 16, "Node_Payload_t phai co kich thuoc 16 byte");

typedef struct {
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
    uint8_t battery_gate;
} Gateway_Payload_t;

typedef struct {
    uint8_t has_patient_event;
    Gateway_Payload_t gateway;
    Node_Payload_t node;
} Complete_Packet_t;

#endif
