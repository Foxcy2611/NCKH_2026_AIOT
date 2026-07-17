#ifndef ESP32_DHT11_LIB_H
#define ESP32_DHT11_LIB_H

#include <Arduino.h>

#define DHT11_PIN 12

void DHT11_Init(void);

// Hàm đọc dữ liệu
// 0: Thành công
// 1: Lỗi (Timeout - Mất kết nối)
// 2: Lỗi checksum
uint8_t DHT11_ReadData(float* temp, float* humi);

void DHT11_TestMain(void);

#endif