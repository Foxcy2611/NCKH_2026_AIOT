#ifndef NCKH_GATEWAY_LTE_H
#define NCKH_GATEWAY_LTE_H

#include <Arduino.h>
#include "ESP32_A7680C_AT.h"

bool LTE_Init(
    HardwareSerial& serialPort,
    uint8_t rxPin,
    uint8_t txPin,
    uint32_t baudrate
);
bool LTE_Connect(const char* apn);
bool LTE_IsConnected(void);
bool LTE_Reconnect(const char* apn);
bool LTE_Disconnect(void);

#endif