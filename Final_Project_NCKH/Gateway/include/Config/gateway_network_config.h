#pragma once

// Copy file này thành gateway_network_config.local.h rồi điền cấu hình thật.
// Không commit file .local.h.
#define LTE_SIM_APN "v-internet"

#define GATEWAY_NETWORK_CONFIGURED 1
#define WIFI_SSID "Thawngspt"
#define WIFI_PASSWORD "21022006"
#define MQTT_BROKER "6ff32dfda1cd49c49496e5b35f957f87.s1.eu.hivemq.cloud"
#define MQTT_PORT 8883
#define MQTT_USERNAME "AIOT_2026"
#define MQTT_PASSWORD "12345678"
#define MQTT_CLIENT_ID "nckh-gateway"

// Chỉ dùng 1 khi thử nghiệm. Bản triển khai thật nên xác thực CA và đặt bằng 0.
#define GATEWAY_TLS_INSECURE 1
static const char GATEWAY_MQTT_CA[] = "";

#define GATEWAY_WIFI_CONNECT_TIMEOUT_MS 12000UL
#define GATEWAY_WIFI_RETRY_MS 5000UL
#define GATEWAY_MQTT_RETRY_MS 5000UL
#define GATEWAY_JSON_CAPACITY 2048
#define GATEWAY_MQTT_BUFFER_SIZE 2304
