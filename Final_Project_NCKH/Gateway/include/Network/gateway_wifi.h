#ifndef NCKH_GATEWAY_WIFI_H
#define NCKH_GATEWAY_WIFI_H

#include <Arduino.h>
#include <WiFi.h>

void WiFi_Init();
bool WiFi_IsConnected();
void WiFi_Reconnect();
void WiFi_Scan();

#endif