#include <Arduino.h>
#include <math.h>
#include "Config/gateway_config.h"
#include "System/gateway_sensor.h"
#include "Sensor/gateway_battery.h"
#include "System/gateway_dht22_cache.h"
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
// Written only by TaskSensor; readers use the mutex-protected snapshot.
LatestDht22 latestDht22{};
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
    uint64_t lastProbe = 0, sgpStart = 0, lastDht = GatewayNowMs();
    uint32_t dhtAttempts = 0, dhtSuccesses = 0, dhtTimeouts = 0, dhtChecksums = 0;
#if GATEWAY_GPS_ENABLED
    Serial1.begin(GATEWAY_GPS_BAUD, SERIAL_8N1, GATEWAY_GPS_RX_PIN, GATEWAY_GPS_TX_PIN);
    NEO_M8N_Init(&Serial1);
    uint64_t lastGpsFix = 0;
    NEO_Data_t gps{};
#endif
#endif
#if GATEWAY_SENSOR_MODE == 1 && GATEWAY_BATTERY_ENABLED
    static_assert(GATEWAY_BATTERY_PIN == 34, "Battery wiring is calibrated for GPIO34 / ADC1");
    pinMode(GATEWAY_BATTERY_PIN, INPUT);
    analogSetPinAttenuation(GATEWAY_BATTERY_PIN, ADC_11db);
    GatewayBatteryFilter battery;
    uint64_t lastBatteryLog = 0;
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
        if (now >= lastDht && now - lastDht >= GATEWAY_DHT22_PERIOD_MS) {
            float t = NAN, h = NAN;
            uint8_t dhtErr = DHT22_ReadData(&t, &h);
            const bool ok = latestDht22.update(dhtErr, t, h);
            // Wait from completion, including failed attempts. Also gives the
            // sensor time to settle after initialization before the first read.
            lastDht = GatewayNowMs();
            ++dhtAttempts;
            if (ok) ++dhtSuccesses;
            if (dhtErr == 1) ++dhtTimeouts;
            if (dhtErr == 2) ++dhtChecksums;

            {
                if (ok) {
                    Serial.printf("[Sensor] DHT OK (GPIO %d): Nhiet do=%.1f *C, Do am=%.1f %%\n", GATEWAY_DHT22_PIN, t, h);
                } else {
                    if (dhtErr == 1) {
                        DHT22_TimingProfile timing{};
                        DHT22_GetTimingProfile(&timing);
                        Serial.printf("[Sensor] DHT TIMEOUT GPIO=%d stage=%s bit=%d response_low=%lldus response_high=%lldus\n",
                            GATEWAY_DHT22_PIN, timing.timeoutStage, timing.timeoutBit,
                            (long long)timing.responseLowUs, (long long)timing.responseHighUs);
                    } else if (dhtErr == 2) {
                        Serial.println("[Sensor] DHT LOI 2 (Checksum): Du lieu bi nhieu tren day DATA!");
                    } else {
                        Serial.printf("[Sensor] DHT LOI Pham vi: T=%.1f *C, H=%.1f %% (Gia tri khong hop le)\n", t, h);
                    }
                }
                Serial.printf("[Sensor] DHT attempts=%lu ok=%lu timeout=%lu checksum=%lu cache=%s\n",
                    (unsigned long)dhtAttempts, (unsigned long)dhtSuccesses,
                    (unsigned long)dhtTimeouts, (unsigned long)dhtChecksums,
                    latestDht22.valid ? "available" : "NA");
            }
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
        latestDht22.update(0, 25, 60); s.pressure_hpa = 1013.25f;
        s.eco2_ppm = 500; s.tvoc_ppb = 20;
        s.gps_valid = false; s.latitude = s.longitude = NAN; s.gps_timestamp_ms = 0;
#else
        s = EnvironmentSnapshot{};
#endif
#if GATEWAY_SENSOR_MODE == 1 && GATEWAY_BATTERY_ENABLED
        // Bounded burst (8 samples), no delay, no critical section or radio changes.
        // Trim one minimum and maximum to reduce isolated ADC noise.
        uint32_t totalMv = 0, minMv = UINT32_MAX, maxMv = 0;
        bool adcValid = true;
        for (unsigned i = 0; i < 8; ++i) {
            const uint32_t mv = analogReadMilliVolts(GATEWAY_BATTERY_PIN);
            if (mv < 150 || mv > 3000) adcValid = false;
            totalMv += mv;
            if (mv < minMv) minMv = mv;
            if (mv > maxMv) maxMv = mv;
        }
        const float adcMv = adcValid ? (totalMv - minMv - maxMv) / 6.0f : NAN;
        s.battery_percent = battery.update(adcMv);
        s.battery_valid = s.battery_percent <= 100;
        s.battery_timestamp_ms = GatewayNowMs();
        if (!lastBatteryLog || s.battery_timestamp_ms - lastBatteryLog >= 10000) {
            Serial.printf("[Battery] GPIO34=%.3fV Vbat=%.3fV percent=%u valid=%u\n",
                adcMv * 0.001f, battery.voltage(), s.battery_percent, s.battery_valid);
            lastBatteryLog = s.battery_timestamp_ms;
        }
#endif
        latestDht22.copyTo(s);
        s.gateway_timestamp_ms = now;
        portENTER_CRITICAL(&mux); latest = s; portEXIT_CRITICAL(&mux);
        vTaskDelayUntil(&wake, pdMS_TO_TICKS(GATEWAY_SENSOR_PERIOD_MS));
    }
}
