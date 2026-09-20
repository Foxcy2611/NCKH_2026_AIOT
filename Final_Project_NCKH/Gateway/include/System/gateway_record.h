#pragma once
#include <math.h>
#include "Config/gateway_config.h"
#include "Config/gateway_types.h"
inline Gateway_Payload_t GatewayBuildPayload(const EnvironmentSnapshot &env, uint64_t now) {
    Gateway_Payload_t g{};
    g.gateway_id = GATEWAY_DEVICE_ID;
    // Monotonic uptime, NOT UTC; M5 must supply a time basis in its JSON schema.
    g.timestamp = now;
    g.operating_mode = GATE_MODE_OFFLINE;
    g.uplink_type = GATE_UPLINK_NONE;
    g.temperature = g.humidity = g.pressure = NAN;
    g.latitude = g.longitude = NAN;
    const bool fresh = env.gateway_timestamp_ms != 0 && now >= env.gateway_timestamp_ms
        && now - env.gateway_timestamp_ms <= ENV_SNAPSHOT_MAX_AGE_MS;
    if (!fresh) return g;
    if (env.temperature_valid && env.humidity_valid && isfinite(env.temperature_c) && isfinite(env.humidity_percent)) {
        g.temperature = env.temperature_c; g.humidity = env.humidity_percent;
        g.sensor_valid_mask |= SENSOR_DHT22_VALID;
    }
    if (env.pressure_valid && isfinite(env.pressure_hpa)) {
        g.pressure = env.pressure_hpa; g.sensor_valid_mask |= SENSOR_BMP280_VALID;
    }
    if (env.eco2_valid && env.tvoc_valid) {
        g.eco2 = env.eco2_ppm; g.tvoc = env.tvoc_ppb; g.sensor_valid_mask |= SENSOR_SGP30_VALID;
    }
    return g;
}
