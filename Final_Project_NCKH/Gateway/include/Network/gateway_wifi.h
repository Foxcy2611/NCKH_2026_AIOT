#pragma once
#include <Arduino.h>
#include <WiFi.h>
void WiFi_Init();
void WiFi_Poll();
bool WiFi_IsConnected();
void WiFi_Reconnect();
