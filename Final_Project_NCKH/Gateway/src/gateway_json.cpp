#include "System/gateway_json.h"
#include "Config/gateway_config.h"
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include <math.h>
namespace {
struct Writer {
    char *out; size_t capacity, used; bool ok;
    void add(const char *fmt, ...) {
        if (!ok) return;
        va_list args; va_start(args, fmt);
        int n = vsnprintf(out + used, capacity - used, fmt, args);
        va_end(args);
        if (n < 0 || (size_t)n >= capacity - used) { ok = false; return; }
        used += (size_t)n;
    }
    void number(double value, bool valid) {
        if (valid && isfinite(value)) add("%.6f", value); else add("null");
    }
};
}
bool GatewaySerializeJson(const UplinkRecord &item, char *out, size_t capacity) {
    if (!out || !capacity) return false;
    out[0] = '\0'; Writer w{out, capacity, 0, true};
    const auto &r = item.record; const auto &g = r.gate; const auto &p = r.patient_event;
    w.add("{\"schema_version\":1,\"record_id\":\"%08lx-%08lx-%08lx\",\"synthetic\":%s,\"has_patient_event\":%s,",
        (unsigned long)g.gateway_id, (unsigned long)item.boot_id, (unsigned long)item.record_sequence,
        GATEWAY_SENSOR_MODE == 2 ? "true" : "false", r.has_patient_event ? "true" : "false");
    if (r.has_patient_event) {
        w.add("\"source\":{\"device_id\":%lu,\"sequence\":%lu,\"received_uptime_ms\":%llu},",
            (unsigned long)item.source_device_id, (unsigned long)item.source_sequence,
            (unsigned long long)item.received_uptime_ms);
    } else w.add("\"source\":null,");
    w.add("\"gate\":{\"gateway_id\":%lu,\"timestamp\":%llu,\"time_basis\":\"uptime_ms\",\"operating_mode\":%u,\"uplink_type\":%u,\"sensor_valid_mask\":%u,",
        (unsigned long)g.gateway_id, (unsigned long long)g.timestamp, g.operating_mode, g.uplink_type, g.sensor_valid_mask);
    bool dht = (g.sensor_valid_mask & SENSOR_DHT22_VALID) != 0;
    bool bmp = (g.sensor_valid_mask & SENSOR_BMP280_VALID) != 0;
    bool sgp = (g.sensor_valid_mask & SENSOR_SGP30_VALID) != 0;
    bool gps = (g.sensor_valid_mask & SENSOR_GPS_VALID) != 0;
    w.add("\"temperature\":"); w.number(g.temperature, dht);
    w.add(",\"humidity\":"); w.number(g.humidity, dht);
    w.add(",\"pressure\":"); w.number(g.pressure, bmp);
    if (sgp) w.add(",\"tvoc\":%u,\"eco2\":%u", g.tvoc, g.eco2);
    else w.add(",\"tvoc\":null,\"eco2\":null");
    w.add(",\"wifi_connected\":%s,\"wifi_rssi_dbm\":", g.wifi_connected ? "true" : "false");
    if (g.wifi_connected) w.add("%d", g.wifi_rssi_dbm); else w.add("null");
    w.add(",\"lte_registered\":%s,\"lte_rssi_dbm\":", g.lte_registered ? "true" : "false");
    if (g.lte_registered) w.add("%d", g.lte_rssi_dbm); else w.add("null");
    w.add(",\"mqtt_connected\":%s,\"latitude\":", g.mqtt_connected ? "true" : "false");
    w.number(g.latitude, gps); w.add(",\"longitude\":"); w.number(g.longitude, gps);
    if (gps && g.gps_timestamp) w.add(",\"gps_timestamp\":%llu", (unsigned long long)g.gps_timestamp);
    else w.add(",\"gps_timestamp\":null");
    w.add("},\"patient_event\":");
    if (!r.has_patient_event) w.add("null");
    else {
        w.add("{\"session_id\":%lu,\"timestamp\":null,\"time_basis\":\"unsynced\",\"event_type\":%u,\"classification\":%u,\"model_score\":",
            (unsigned long)p.session_id, p.event_type, p.classification);
        w.number(p.model_score, true);
        w.add(",\"audio_quality\":%u,\"vitals_valid\":%s,\"heart_rate\":", p.audio_quality, p.vitals_valid ? "true" : "false");
        if (p.vitals_valid) w.add("%u", p.heart_rate); else w.add("null");
        w.add(",\"spo2\":"); if (p.vitals_valid) w.add("%u", p.spo2); else w.add("null");
        w.add(",\"battery_node\":%u}", p.battery_node);
    }
    // gate network fields refer to capture time; this field describes the publish route.
    const char *transportStr = (g.uplink_type == GATE_UPLINK_LTE) ? "lte" :
        (g.uplink_type == GATE_UPLINK_WIFI) ? "wifi" : "none";
    w.add(",\"transport\":\"%s\"}", transportStr);
    if (!w.ok) out[0] = '\0';
    return w.ok;
}

bool GatewaySerializeStatusJson(const NetworkSnapshot &network, bool node_valid,
                                bool node_dirty, uint64_t node_revision,
                                uint64_t uptime_ms, uint32_t free_heap,
                                char *out, size_t capacity) {
    if (!out || !capacity) return false;
    out[0] = '\0'; Writer w{out, capacity, 0, true};
    w.add("{\"schema_version\":1,\"message_type\":\"gateway_status\",\"gateway_id\":%lu,"
          "\"uptime_ms\":%llu,\"wifi_connected\":%s,\"mqtt_connected\":%s,"
          "\"wifi_rssi_dbm\":",
          (unsigned long)GATEWAY_DEVICE_ID, (unsigned long long)uptime_ms,
          network.wifi_connected ? "true" : "false",
          network.mqtt_connected ? "true" : "false");
    if (network.wifi_connected) w.add("%d", network.wifi_rssi_dbm); else w.add("null");
    w.add(",\"lte_enabled\":%s,\"gps_enabled\":%s,\"node_valid\":%s,\"node_dirty\":%s,\"node_revision\":%llu,"
          "\"free_heap_bytes\":%lu,\"synthetic\":%s}",
          GATEWAY_LTE_ENABLED ? "true" : "false",
          GATEWAY_GPS_ENABLED ? "true" : "false",
          node_valid ? "true" : "false", node_dirty ? "true" : "false",
          (unsigned long long)node_revision,
          (unsigned long)free_heap, GATEWAY_SENSOR_MODE == 2 ? "true" : "false");
    if (!w.ok) out[0] = '\0';
    return w.ok;
}

bool GatewaySerializeAlertJson(const UplinkRecord &item, char *out, size_t capacity) {
    if (!out || !capacity || !item.record.has_patient_event) return false;
    out[0] = '\0'; Writer w{out, capacity, 0, true};
    const auto &g = item.record.gate;
    const auto &p = item.record.patient_event;
    w.add("{\"schema_version\":1,\"message_type\":\"patient_alert\","
          "\"alert_type\":\"abnormal_classification\",\"severity\":\"warning\","
          "\"record_id\":\"%08lx-%08lx-%08lx\",\"gateway_id\":%lu,"
          "\"source_device_id\":%lu,\"source_sequence\":%lu,\"session_id\":%lu,"
          "\"classification\":%u,\"model_score\":",
          (unsigned long)g.gateway_id, (unsigned long)item.boot_id,
          (unsigned long)item.record_sequence, (unsigned long)g.gateway_id,
          (unsigned long)item.source_device_id, (unsigned long)item.source_sequence,
          (unsigned long)p.session_id, p.classification);
    w.number(p.model_score, true);
    w.add(",\"event_timestamp\":null,\"heart_rate\":");
    if (p.vitals_valid) w.add("%u", p.heart_rate); else w.add("null");
    w.add(",\"spo2\":");
    if (p.vitals_valid) w.add("%u", p.spo2); else w.add("null");
    w.add("}");
    if (!w.ok) out[0] = '\0';
    return w.ok;
}


bool GatewaySerializeDashboardJson(const UplinkRecord &item,
    const NetworkSnapshot &network, bool node_valid, bool node_dirty,
    uint64_t node_revision,
    uint64_t uptime_ms, uint32_t free_heap, char *out, size_t capacity) {
    if (!GatewaySerializeJson(item, out, capacity)) return false;
    size_t used = 0;
    while (out[used]) ++used;
    Writer w{out, capacity, used - 1, true}; // replace the closing brace
    w.add(",\"message_type\":\"complete_packet\",\"event_id\":");
    const bool includesPatientEvent = item.record.has_patient_event != 0;
    const auto &p = item.record.patient_event;
    if (includesPatientEvent) w.add("\"%08lx-%08lx-%08lx\"", (unsigned long)item.source_device_id,
        (unsigned long)p.session_id, (unsigned long)item.source_sequence);
    else w.add("null");
    w.add(",\"patient_age_ms\":");
    if (includesPatientEvent && uptime_ms >= item.received_uptime_ms)
        w.add("%llu", (unsigned long long)(uptime_ms - item.received_uptime_ms));
    else w.add("null");
    w.add(",\"status\":");
    if (!w.ok || !GatewaySerializeStatusJson(network, node_valid, node_dirty,
            node_revision, uptime_ms, free_heap, out + w.used, capacity - w.used)) {
        out[0] = '\0'; return false;
    }
    while (out[w.used]) ++w.used;
    const bool active = includesPatientEvent
        && p.classification != GATEWAY_ALERT_NORMAL_CLASS
        && p.model_score >= GATEWAY_ALERT_MIN_SCORE;
    w.add(",\"alert\":{\"active\":%s,\"event_id\":", active ? "true" : "false");
    if (active) w.add("\"%08lx-%08lx-%08lx\"", (unsigned long)item.source_device_id,
        (unsigned long)p.session_id, (unsigned long)item.source_sequence);
    else w.add("null");
    w.add(",\"severity\":%s,\"alert_type\":%s}}",
        active ? "\"warning\"" : "null",
        active ? "\"abnormal_classification\"" : "null");
    if (!w.ok) out[0] = '\0';
    return w.ok;
}
