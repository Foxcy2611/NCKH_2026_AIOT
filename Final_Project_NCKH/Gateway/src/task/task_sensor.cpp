#include <Arduino.h>
#include <math.h>
#include "Config/gateway_config.h"
#include "System/gateway_sensor.h"
#include "System/gateway_runtime.h"
#include "Task/gateway_tasks.h"
#if GATEWAY_SENSOR_MODE == 1
#include <Wire.h>
#include "Sensor/ESP32_DHT22_Lib.h"
#include "Sensor/ESP32_BMP280_Lib.h"
#include "Sensor/ESP32_SGP30_Lib.h"
#if GATEWAY_GPS_ENABLED
#include "Sensor/ESP32_NEO_M8N_GPS.h"
#endif
static_assert(GATEWAY_DHT22_PIN == DHT22_PIN, "Update the driver pin with gateway config");
#endif
namespace {
EnvironmentSnapshot latest{};
portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;
}
void GatewaySensor_GetLatest(EnvironmentSnapshot *out) {
    if (!out) return;
    portENTER_CRITICAL(&mux);
    *out = latest;
    portEXIT_CRITICAL(&mux);
}
void TaskSensor(void *) {
    GatewayWatchdogJoin();
    Serial.printf("[Sensor] mode=%d (0=missing, 1=hardware, 2=SYNTHETIC)\n", GATEWAY_SENSOR_MODE);
    EnvironmentSnapshot s{};
#if GATEWAY_SENSOR_MODE == 1
    Wire.begin(GATEWAY_I2C_SDA, GATEWAY_I2C_SCL);
    Wire.setTimeOut(50);
    DHT22_Init();
    bool bmpReady = false, sgpReady = false;
    uint64_t lastProbe = 0, sgpStart = 0, lastDht = 0;
#if GATEWAY_GPS_ENABLED
    Serial1.begin(GATEWAY_GPS_BAUD, SERIAL_8N1, GATEWAY_GPS_RX_PIN, GATEWAY_GPS_TX_PIN);
    NEO_M8N_Init(&Serial1);
    uint64_t lastGpsFix = 0;
    NEO_Data_t gps{};
#endif
#endif
    TickType_t wake = xTaskGetTickCount();
    for (;;) {
        GatewayWatchdogFeed();
        const uint64_t now = GatewayNowMs();
#if GATEWAY_TEST_WDT_STALL
        if (now > 15000) {
            Serial.println("[TEST] sensor stops feeding TWDT; expect reset in ~10s");
            for (;;) vTaskDelay(pdMS_TO_TICKS(100));
        }
#endif
#if GATEWAY_SENSOR_MODE == 1
        if (!lastProbe || now - lastProbe >= 5000) {
            if (!bmpReady) bmpReady = BMP280_Init(GATEWAY_BMP280_ADDR);
            if (!sgpReady) { sgpReady = SGP30_Init(); if (sgpReady) sgpStart = now; }
            lastProbe = now;
        }
        if (!lastDht || now - lastDht >= GATEWAY_DHT22_PERIOD_MS) {
            float t = NAN, h = NAN;
            bool ok = DHT22_ReadData(&t, &h) == 0 && isfinite(t) && isfinite(h)
                && t >= -40 && t <= 80 && h >= 0 && h <= 100;
            s.temperature_valid = s.humidity_valid = ok;
            s.temperature_c = ok ? t : NAN; s.humidity_percent = ok ? h : NAN;
            lastDht = now;
        }
        float bt = NAN, bp = NAN;
        s.pressure_valid = bmpReady && BMP280_ReadData(&bt, &bp) && isfinite(bp) && bp >= 300 && bp <= 1100;
        s.pressure_hpa = s.pressure_valid ? bp : NAN;
        if (!s.pressure_valid) bmpReady = false;
        SGP30_Data_t gas{};
        bool gasRead = sgpReady && SGP30_Measure(&gas);
        s.eco2_valid = s.tvoc_valid = gasRead && now - sgpStart >= 15000;
        s.eco2_ppm = s.eco2_valid ? gas.CO2_eq : 0;
        s.tvoc_ppb = s.tvoc_valid ? gas.TVOC : 0;
        if (!gasRead) sgpReady = false;
#if GATEWAY_GPS_ENABLED
        NEO_Data_t candidate{};
        if (NEO_M8N_ReadData(&candidate) && candidate.isValid) {
            gps = candidate;
            lastGpsFix = now;
        }
        s.gps_valid = lastGpsFix && now - lastGpsFix <= GATEWAY_GPS_MAX_AGE_MS;
        s.latitude = s.gps_valid ? gps.latitude : NAN;
        s.longitude = s.gps_valid ? gps.longitude : NAN;
        s.gps_timestamp_ms = s.gps_valid ? NEO_M8N_UnixTimeMs(&gps) : 0;
#else
        s.gps_valid = false; s.latitude = s.longitude = NAN; s.gps_timestamp_ms = 0;
#endif
#elif GATEWAY_SENSOR_MODE == 2
        s.temperature_valid = s.humidity_valid = s.pressure_valid = true;
        s.eco2_valid = s.tvoc_valid = true;
        s.temperature_c = 25; s.humidity_percent = 60; s.pressure_hpa = 1013.25f;
        s.eco2_ppm = 500; s.tvoc_ppb = 20;
        s.gps_valid = false; s.latitude = s.longitude = NAN; s.gps_timestamp_ms = 0;
#else
        s = EnvironmentSnapshot{};
#endif
        s.gateway_timestamp_ms = now;
        portENTER_CRITICAL(&mux); latest = s; portEXIT_CRITICAL(&mux);
        vTaskDelayUntil(&wake, pdMS_TO_TICKS(GATEWAY_SENSOR_PERIOD_MS));
    }
}
