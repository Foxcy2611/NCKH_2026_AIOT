#pragma once
#include <Arduino.h>
#include "Config/gateway_network_config.h"
bool MQTT_WIFI_Init();
bool MQTT_WIFI_Connect();
bool MQTT_WIFI_IsConnected();
bool MQTT_WIFI_Loop();
void MQTT_WIFI_Disconnect();
bool MQTT_WIFI_Publish(const char *topic, const char *payload);
