#pragma once
#include <math.h>
#include <stdint.h>
#include "Config/gateway_config.h"

// Pure conversion/filter; only TaskSensor owns this state. No network calls.
class GatewayBatteryFilter {
    float filtered_ = NAN;
public:
    float voltage() const { return filtered_; }
    uint8_t update(float adcMv) {
        if (!isfinite(adcMv) || adcMv < 150.0f || adcMv > 3000.0f) {
            filtered_ = NAN;
            return 255;
        }
        const float volts = adcMv * 0.001f * GATEWAY_BATTERY_VBAT_REF / GATEWAY_BATTERY_ADC_REF;
        filtered_ = isfinite(filtered_) ? filtered_ + 0.25f * (volts - filtered_) : volts;
        // Voltage-based estimate only; configurable full/empty pack endpoints.
        float percent = 100.0f * (filtered_ - GATEWAY_BATTERY_EMPTY_V) /
                        (GATEWAY_BATTERY_FULL_V - GATEWAY_BATTERY_EMPTY_V);
        if (percent <= 0) return 0;
        if (percent >= 100) return 100;
        return static_cast<uint8_t>(percent + 0.5f);
    }
};
static_assert(GATEWAY_BATTERY_ADC_REF > 0 && GATEWAY_BATTERY_VBAT_REF > 0,
              "Battery calibration references must be positive");
static_assert(GATEWAY_BATTERY_FULL_V > GATEWAY_BATTERY_EMPTY_V,
              "Battery full voltage must exceed empty voltage");
