#ifndef GATEWAY_MQTT_LTE_H
#define GATEWAY_MQTT_LTE_H

#include <Arduino.h>

// Khởi tạo MQTT qua A7680C
bool MQTT_LTE_Init(void);

// Kết nối MQTT Broker qua LTE
bool MQTT_LTE_Connect(
    const char* broker,
    uint16_t port,
    const char* clientId,
    const char* username,
    const char* password
);

// Kết nối lại MQTT Broker bằng thông tin đã cấu hình trước đó
bool MQTT_LTE_Reconnect(void);

// Publish MQTT message qua LTE
bool MQTT_LTE_Publish(
    const char* topic,
    const char* payload
);

// Kiểm tra trạng thái MQTT
bool MQTT_LTE_IsConnected(void);

// Duy trì MQTT connection
void MQTT_LTE_Loop(void);

// Ngắt kết nối MQTT
bool MQTT_LTE_Disconnect(void);

#endif // GATEWAY_MQTT_LTE_H