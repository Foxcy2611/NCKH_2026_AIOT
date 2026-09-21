#include "json_serializer.h"

#include <stdarg.h>
#include <stdio.h>

namespace {

struct JsonWriter {
    char *buffer;
    size_t capacity;
    size_t length;
    bool ok;

    void Add(const char *format, ...) {
        if (!ok || length >= capacity) {
            ok = false;
            return;
        }

        va_list args;
        va_start(args, format);
        const int written = vsnprintf(buffer + length, capacity - length, format, args);
        va_end(args);

        if (written < 0 || static_cast<size_t>(written) >= capacity - length) {
            ok = false;
            buffer[0] = '\0';
            return;
        }
        length += static_cast<size_t>(written);
    }
};

void AddNode(JsonWriter &writer, const Complete_Packet_t &packet) {
    if (!packet.has_patient_event) {
        writer.Add("null");
        return;
    }

    const Node_Payload_t &node = packet.node;
    writer.Add(
        "{\"session_id\":%lu,\"event_type\":%u,\"classification\":%u,"
        "\"model_score\":%.6f,\"audio_quality\":%u,\"vitals_valid\":%s,"
        "\"heart_rate\":",
        static_cast<unsigned long>(node.session_id),
        node.event_type,
        node.classification,
        static_cast<double>(node.model_score),
        node.audio_quality,
        node.vitals_valid ? "true" : "false");

    if (node.vitals_valid) {
        writer.Add("%u,\"spo2\":%u", node.heart_rate, node.spo2);
    } else {
        writer.Add("null,\"spo2\":null");
    }

    writer.Add(",\"battery_node\":%u}", node.battery_node);
}

}  // namespace

bool SerializeCompletePacketJson(const Complete_Packet_t &packet,
                                 char *output,
                                 size_t capacity) {
    if (output == nullptr || capacity == 0) {
        return false;
    }

    output[0] = '\0';
    JsonWriter writer{output, capacity, 0, true};
    const Gateway_Payload_t &gate = packet.gateway;

    writer.Add(
        "{\"schema_version\":1,\"message_type\":\"complete_packet\","
        "\"synthetic\":true,\"has_patient_event\":%s,\"gateway\":{"
        "\"gateway_id\":%lu,\"timestamp\":%llu,\"timestamp_basis\":\"uptime_ms\","
        "\"operating_mode\":%u,\"uplink_type\":%u,",
        packet.has_patient_event ? "true" : "false",
        static_cast<unsigned long>(gate.gateway_id),
        static_cast<unsigned long long>(gate.timestamp),
        gate.operating_mode,
        gate.uplink_type);

    if (gate.sensor_valid_mask & SENSOR_DHT22_VALID) {
        writer.Add("\"temperature\":%.2f,\"humidity\":%.2f,",
                   static_cast<double>(gate.temperature),
                   static_cast<double>(gate.humidity));
    } else {
        writer.Add("\"temperature\":null,\"humidity\":null,");
    }

    if (gate.sensor_valid_mask & SENSOR_BMP280_VALID) {
        writer.Add("\"pressure\":%.2f,", static_cast<double>(gate.pressure));
    } else {
        writer.Add("\"pressure\":null,");
    }

    if (gate.sensor_valid_mask & SENSOR_SGP30_VALID) {
        writer.Add("\"tvoc\":%u,\"eco2\":%u,", gate.tvoc, gate.eco2);
    } else {
        writer.Add("\"tvoc\":null,\"eco2\":null,");
    }

    writer.Add(
        "\"sensor_valid_mask\":%u,\"wifi_connected\":%s,\"wifi_rssi_dbm\":%d,"
        "\"lte_registered\":%s,\"lte_rssi_dbm\":%d,\"mqtt_connected\":%s,",
        gate.sensor_valid_mask,
        gate.wifi_connected ? "true" : "false",
        gate.wifi_rssi_dbm,
        gate.lte_registered ? "true" : "false",
        gate.lte_rssi_dbm,
        gate.mqtt_connected ? "true" : "false");

    if (gate.sensor_valid_mask & SENSOR_GPS_VALID) {
        writer.Add(
            "\"latitude\":%.6f,\"longitude\":%.6f,\"gps_timestamp\":%llu,",
            gate.latitude,
            gate.longitude,
            static_cast<unsigned long long>(gate.gps_timestamp));
    } else {
        writer.Add("\"latitude\":null,\"longitude\":null,\"gps_timestamp\":null,");
    }

    writer.Add("\"battery_gate\":%u},\"node\":", gate.battery_gate);
    AddNode(writer, packet);
    writer.Add("}");

    if (!writer.ok) {
        output[0] = '\0';
    }
    return writer.ok;
}
