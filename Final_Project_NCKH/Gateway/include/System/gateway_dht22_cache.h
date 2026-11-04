#pragma once
#include <math.h>
#include "Config/gateway_types.h"

struct LatestDht22 {
    float temperature = NAN;
    float humidity = NAN;
    bool valid = false;

    bool update(uint8_t readError, float t, float h) {
        if (readError != 0 || !isfinite(t) || !isfinite(h)
            || t < -40 || t > 80 || h < 0 || h > 100) return false;
        // Keep temperature and humidity from the same successful reading.
        temperature = t;
        humidity = h;
        valid = true;
        return true;
    }

    void copyTo(EnvironmentSnapshot &snapshot) const {
        snapshot.temperature_valid = snapshot.humidity_valid = valid;
        snapshot.temperature_c = temperature;
        snapshot.humidity_percent = humidity;
    }
};
