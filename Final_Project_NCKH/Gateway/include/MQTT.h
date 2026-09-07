#ifndef MQTT_H
#define MQTT_H

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>

#define MQTT_BROKER   "6ff32dfda1cd49c49496e5b35f957f87.s1.eu.hivemq.cloud"
#define MQTT_PORT     8883

#define MQTT_USERNAME "AIOT_2026"
#define MQTT_PASSWORD "12345678"

#define MQTT_CLIENT_ID "AIOT_2026"

void MQTT_Init();
void MQTT_Connect();
bool MQTT_IsConnected();
bool MQTT_Loop();
void MQTT_Disconnect();
void MQTT_Reconnect();
bool MQTT_Publish(const char* topic, const char* payload);

#endif
