#pragma once

// ===================== Cellular / 4G APN =============
// Cấu hình APN nhà mạng cho SIM LTE:
// Viettel:   "v-internet"
// Vinaphone: "m3-world"
// Mobifone:  "m-wap"
#define LTE_SIM_APN "v-internet"

// Private team repository configuration.
#define GATEWAY_NETWORK_CONFIGURED 1
#define WIFI_SSID "VIETTEL_AP_8D8938"
#define WIFI_PASSWORD "1234567890a"
#define MQTT_BROKER "c5fe6f9b3aa34af2a790d0165dcd981c.s1.eu.hivemq.cloud"
//6ff32dfda1cd49c49496e5b35f957f87.s1.eu.hivemq.cloud
#define MQTT_PORT 8883
#define MQTT_USERNAME "thangpt"
#define MQTT_PASSWORD "0919332022"

// Legacy fallback for the excluded LTE source; Wi-Fi uses a MAC-derived ID.
#define MQTT_CLIENT_ID "AIOT_2026"

// Phase 3 bench test only. Set 0 and provide a trusted PEM CA for deployment.
#define GATEWAY_TLS_INSECURE 1
static const char GATEWAY_MQTT_CA[] = "";
#define GATEWAY_WIFI_CONNECT_TIMEOUT_MS 12000UL
#define GATEWAY_WIFI_RETRY_MS 5000UL
#define GATEWAY_MQTT_RETRY_MS 5000UL
#define GATEWAY_JSON_CAPACITY 2048
#define GATEWAY_MQTT_BUFFER_SIZE 2304
// Keep AP 2.4 GHz and Patient Node on ESPNOW_CHANNEL.
// A different AP channel is disconnected rather than silently breaking ESP-NOW.
