#pragma once
#include <math.h>
#include <stdio.h>
#include "Config/gateway_types.h"

inline void GatewayEnvironmentValues(const Gateway_Payload_t &gate, float &t, float &h) {
    const bool valid = (gate.sensor_valid_mask & SENSOR_DHT22_VALID) != 0;
    t = valid ? gate.temperature : NAN;
    h = valid ? gate.humidity : NAN;
}

inline void GatewayFormatEnvironment(float t, float h, char (&temperature)[16], char (&humidity)[16]) {
    if (isfinite(t) && t >= -40 && t <= 80) snprintf(temperature, sizeof(temperature), "%.1f", t);
    else snprintf(temperature, sizeof(temperature), "N/A");
    if (isfinite(h) && h >= 0 && h <= 100) snprintf(humidity, sizeof(humidity), "%.0f%%", h);
    else snprintf(humidity, sizeof(humidity), "N/A");
}
