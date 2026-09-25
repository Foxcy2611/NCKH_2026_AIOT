#pragma once
#include <math.h>
#include "Config/gateway_config.h"
#include "Config/gateway_types.h"
inline Gate_Payload_t GatewayBuildPayload(const EnvironmentSnapshot &env, uint64_t now) {
    Gate_Payload_t g{};
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
    if (env.gps_valid && isfinite(env.latitude) && isfinite(env.longitude)
        && env.latitude >= -90.0 && env.latitude <= 90.0
        && env.longitude >= -180.0 && env.longitude <= 180.0) {
        g.latitude = env.latitude;
        g.longitude = env.longitude;
        g.gps_timestamp = env.gps_timestamp_ms;
        g.sensor_valid_mask |= SENSOR_GPS_VALID;
    }
    return g;
}


// Preserve the current project's mode mapping during this storage-only stage.
// A separate HOME/MOBILE user policy should replace it in the revised stage.
inline void GatewayApplyNetwork(Gate_Payload_t &gate, const NetworkSnapshot &net) {
    gate.wifi_connected = net.wifi_connected;
    gate.wifi_rssi_dbm = net.wifi_rssi_dbm;
    gate.mqtt_connected = net.mqtt_connected;
    gate.lte_registered = net.lte_connected;
    gate.lte_rssi_dbm = net.lte_rssi_dbm;
    gate.uplink_type = net.active_uplink;
    gate.operating_mode = (net.active_uplink == GATE_UPLINK_LTE)
        ? GATE_MODE_MOBILE
        : (net.mqtt_connected ? GATE_MODE_HOME : GATE_MODE_OFFLINE);
}
