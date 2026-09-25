#ifndef NCKH_GATEWAY_CONFIG_H
#define NCKH_GATEWAY_CONFIG_H

#include <stdint.h>

#define GATEWAY_SERIAL_BAUD 115200

// ===================== Cellular / LTE SIM A7680C ================
// Chân phần cứng cho module SIM A7680C (UART2).
// Dễ dàng thay đổi chân tại đây nếu cắm sang GPIO khác.
// LƯU Ý: Nếu bật cả GPS phần cứng, hãy đổi chân GPS hoặc LTE để tránh xung đột chân 16/17.
#ifndef GATEWAY_LTE_ENABLED
#define GATEWAY_LTE_ENABLED             1
#endif
#define GATEWAY_LTE_RX_PIN              16
#define GATEWAY_LTE_TX_PIN              26
#define GATEWAY_LTE_BAUD                115200
#define GATEWAY_WIFI_FAILOVER_TIMEOUT_MS 15000UL // Mất Wi-Fi >15s -> chuyển sang LTE
#define GATEWAY_LTE_PROBE_WIFI_MS       30000UL // Chu kỳ thăm dò lại Wi-Fi khi đang chạy LTE (30s)

// ===================== FreeRTOS =====================
#define ESPNOW_RX_QUEUE_LENGTH          10
#define DISPLAY_QUEUE_LENGTH            1

#define TASK_ESPNOW_STACK_SIZE          4096
#define TASK_GATEWAY_STACK_SIZE         4096
#define TASK_SENSOR_STACK_SIZE          4096
#define TASK_NETWORK_STACK_SIZE         8192
#define TASK_DISPLAY_STACK_SIZE         8192

#define TASK_ESPNOW_PRIORITY             4
#define TASK_GATEWAY_PRIORITY            3
#define TASK_SENSOR_PRIORITY             2
#define TASK_DISPLAY_PRIORITY            2
#define TASK_NETWORK_PRIORITY            1

#define GATEWAY_DISPLAY_PERIOD_MS       1000

// ===================== ESP-NOW ======================
// Node và Gateway phải cùng channel.
#define ESPNOW_CHANNEL                   6
#define ESPNOW_MAX_PACKET_SIZE          250
#define SECURE_ESPNOW_PACKET_SIZE        56

// ===================== Gateway identity ============
// Phải trùng GATEWAY_DEVICE_ID ở Patient_Node/src/EspNow_Client.cpp
#define GATEWAY_DEVICE_ID               0x47575431UL

// ===================== Single-node test config =====
// 0x00...00 = learning mode: sau packet AES-GCM hợp lệ đầu tiên,
// Gateway bind device_id <-> MAC đó và chỉ nhận MAC này về sau.
// Để test strict MAC, điền MAC của Patient Node và đặt = 1.
#define GATEWAY_STRICT_NODE_MAC          0
#define GATEWAY_NODE_DEVICE_ID           0UL
#define GATEWAY_NODE_MAC {0x00,0x00,0x00,0x00,0x00,0x00}

// ===================== AES-128-GCM ==================
// Phải trùng KEY_NODE_TO_GATEWAY ở Patient Node.
static const uint8_t KEY_NODE_TO_GATEWAY[16] = {
    0x42, 0x91, 0xD7, 0x2C, 0xA5, 0x68, 0x1B, 0xEF,
    0x30, 0xC4, 0x7A, 0x16, 0x8D, 0x53, 0xB9, 0xE2
};

// Phải trùng KEY_GATEWAY_TO_NODE ở Patient Node.
static const uint8_t KEY_GATEWAY_TO_NODE[16] = {
    0xC8, 0x35, 0x6E, 0xA1, 0x19, 0xF4, 0x82, 0x5B,
    0xD0, 0x27, 0x9C, 0x73, 0x4A, 0xBE, 0x06, 0xE9
};

// ===================== Sensors =====================
#define GATEWAY_I2C_SDA                21
#define GATEWAY_I2C_SCL                22
#define GATEWAY_DHT22_PIN              25
#define GATEWAY_BMP280_ADDR            0x76
#define GATEWAY_GPS_RX_PIN               32
#define GATEWAY_GPS_TX_PIN               33
#define GATEWAY_GPS_BAUD                9600
#define GATEWAY_GPS_MAX_AGE_MS         10000
#ifndef GATEWAY_GPS_ENABLED
#define GATEWAY_GPS_ENABLED                1
#endif
#define GATEWAY_SENSOR_PERIOD_MS       1000
#define GATEWAY_DHT22_PERIOD_MS        2000
#define ENV_SNAPSHOT_MAX_AGE_MS        5000

// ===================== Aggregator ==================
#define PATIENT_HISTORY_SIZE            16

// ===================== Network =====================
#define MQTT_RECONNECT_INTERVAL_MS      5000
#define MQTT_TOPIC_COMPLETE_RECORD      "aiot/2026/complete_record"
#define MQTT_TOPIC_TELEMETRY            "aiot/2026/gateway/telemetry"
#define MQTT_TOPIC_PATIENT_EVENT        "aiot/2026/patient/event"
#define MQTT_TOPIC_GATEWAY_STATUS       "aiot/2026/gateway/status"
#define MQTT_TOPIC_ALERT                "aiot/2026/alert"
#define MQTT_TEST_TOPIC_TELEMETRY       "aiot/2026/test/gateway/telemetry"
#define MQTT_TEST_TOPIC_PATIENT_EVENT   "aiot/2026/test/patient/event"
#define MQTT_TEST_TOPIC_GATEWAY_STATUS  "aiot/2026/test/gateway/status"
#define MQTT_TEST_TOPIC_ALERT           "aiot/2026/test/alert"
#define GATEWAY_ALERT_NORMAL_CLASS       0
#define GATEWAY_ALERT_MIN_SCORE          0.80f

// 0 = no sensors, 1 = real drivers, 2 = synthetic (TEST ONLY).
#ifndef GATEWAY_SENSOR_MODE
#define GATEWAY_SENSOR_MODE 1
#endif
#define GATEWAY_TELEMETRY_PERIOD_MS 5000
#define GATEWAY_STATUS_PERIOD_MS 30000
#define GATEWAY_WDT_TIMEOUT_S 30
#ifndef GATEWAY_TEST_WDT_STALL
#define GATEWAY_TEST_WDT_STALL 0
#endif
#endif
