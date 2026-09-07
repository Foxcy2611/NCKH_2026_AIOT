#ifndef ESP32_DHT22_LIB_H
#define ESP32_DHT22_LIB_H

#include <Arduino.h>

#define DHT22_PIN 25

#if SENSOR_TIMING_DEBUG
struct DHT22_TimingProfile {
    int64_t responseLowUs;
    int64_t responseHighUs;
    int64_t startLowUs;
    int64_t criticalEnterUs;
    int64_t criticalExitUs;
    const char *timeoutStage;
    int16_t timeoutBit;
};
#endif

void DHT22_Init(void);

// Hàm đọc dữ liệu
// 0: Thành công
// 1: Lỗi (Timeout - Mất kết nối)
// 2: Lỗi checksum
uint8_t DHT22_ReadData(float* temp, float* humi);

#if SENSOR_TIMING_DEBUG
void DHT22_GetTimingProfile(DHT22_TimingProfile *profile);
#endif

void DHT22_TestMain(void);

#endif
