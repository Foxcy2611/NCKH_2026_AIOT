#pragma once

// Copy file này thành gateway_network_config.local.h rồi điền cấu hình thật.
// Không commit file .local.h.
#define LTE_SIM_APN "v-internet"

#define GATEWAY_NETWORK_CONFIGURED 1
#define WIFI_SSID "iPhone"
#define WIFI_PASSWORD "09092005"
#define MQTT_BROKER "c5fe6f9b3aa34af2a790d0165dcd981c.s1.eu.hivemq.cloud"
#define MQTT_PORT 8883
#define MQTT_USERNAME "thangpt"
#define MQTT_PASSWORD "0919332022"
#define MQTT_CLIENT_ID "nckh-gateway"

// Chỉ dùng 1 khi thử nghiệm. Bản triển khai thật nên xác thực CA và đặt bằng 0.
#define GATEWAY_TLS_INSECURE 1
static const char GATEWAY_MQTT_CA[] = "";

#define GATEWAY_WIFI_CONNECT_TIMEOUT_MS 12000UL
#define GATEWAY_WIFI_RETRY_MS 5000UL
#define GATEWAY_MQTT_RETRY_MS 5000UL
#define GATEWAY_JSON_CAPACITY 2048
#define GATEWAY_MQTT_BUFFER_SIZE 2304
