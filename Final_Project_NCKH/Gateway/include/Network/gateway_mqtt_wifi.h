#ifndef NCKH_GATEWAY_MQTT_H
#define NCKH_GATEWAY_MQTT_H

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>

#define MQTT_BROKER   "6ff32dfda1cd49c49496e5b35f957f87.s1.eu.hivemq.cloud"
#define MQTT_PORT     8883

#define MQTT_USERNAME "AIOT_2026"
#define MQTT_PASSWORD "12345678"

#define MQTT_CLIENT_ID "AIOT_2026"

void MQTT_WIFI_Init();
void MQTT_WIFI_Connect();
bool MQTT_WIFI_IsConnected();
bool MQTT_WIFI_Loop();
void MQTT_WIFI_Disconnect();
void MQTT_WIFI_Reconnect();
bool MQTT_WIFI_Publish(const char* topic, const char* payload);

#endif
