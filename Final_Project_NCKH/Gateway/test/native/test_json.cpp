#include <cassert>
#include <cstdio>
#include <cstring>
#include <limits>
#include "System/gateway_json.h"
#include "System/gateway_record.h"
#include "Config/gateway_network_config.h"
int main() {
    UplinkRecord item{};
    item.boot_id = 0x12345678; item.record_sequence = 1;
    EnvironmentSnapshot env{};
    item.record.gate = GatewayBuildPayload(env, 0x100000001ULL);
    char json[GATEWAY_JSON_CAPACITY];
    assert(GatewaySerializeJson(item, json, sizeof(json)));
    assert(!GatewaySerializeJson(item, nullptr, 100));
    char tiny[8] = "before";
    assert(!GatewaySerializeJson(item, tiny, sizeof(tiny)) && tiny[0] == '\0');
    size_t length = strlen(json);
    char exact[GATEWAY_JSON_CAPACITY];
    assert(GatewaySerializeJson(item, exact, length + 1));
    assert(!GatewaySerializeJson(item, exact, length) && exact[0] == '\0');
    puts(json);
    item.record.has_patient_event = 1;
    item.source_device_id = UINT32_MAX; item.source_sequence = UINT32_MAX;
    item.received_uptime_ms = UINT64_MAX;
    item.record_sequence = 2;
    auto &g = item.record.gate;
    g.sensor_valid_mask = 7; g.temperature = 25; g.humidity = 60;
    g.pressure = 1013.25f; g.tvoc = 0; g.eco2 = 500;
    g.wifi_connected = g.mqtt_connected = 1; g.wifi_rssi_dbm = -65;
    g.operating_mode = GATE_MODE_HOME; g.uplink_type = GATE_UPLINK_WIFI;
    auto &p = item.record.patient_event;
    p.session_id = UINT32_MAX;
    p.event_type = 2; p.classification = 2; p.model_score = .875f;
    p.audio_quality = 3; p.vitals_valid = 1; p.heart_rate = 72; p.spo2 = 98; p.battery_node = 100;
    assert(GatewaySerializeJson(item, json, sizeof(json))); puts(json);
    char retry[GATEWAY_JSON_CAPACITY];
    assert(GatewaySerializeJson(item, retry, sizeof(retry)) && strcmp(json, retry) == 0);
    g.temperature = std::numeric_limits<float>::infinity(); g.pressure = NAN;
    p.vitals_valid = 0;
    assert(GatewaySerializeJson(item, json, sizeof(json))); puts(json);
    char auxiliary[GATEWAY_JSON_CAPACITY];
    NetworkSnapshot network{true, true, -55};
    assert(GatewaySerializeStatusJson(network, true, true, 3, 123456, 180000, auxiliary, sizeof(auxiliary)));
    assert(strstr(auxiliary, "\"message_type\":\"gateway_status\"") != nullptr);
    assert(strstr(auxiliary, "\"node_revision\":3") != nullptr);
    assert(GatewaySerializeAlertJson(item, auxiliary, sizeof(auxiliary)));
    assert(strstr(auxiliary, "\"message_type\":\"patient_alert\"") != nullptr);
    assert(!GatewaySerializeAlertJson(UplinkRecord{}, auxiliary, sizeof(auxiliary)));
    const size_t longestTopic = strlen(MQTT_TOPIC_PATIENT_EVENT) > strlen(MQTT_TOPIC_GATEWAY_STATUS)
        ? strlen(MQTT_TOPIC_PATIENT_EVENT) : strlen(MQTT_TOPIC_GATEWAY_STATUS);
    assert(strlen(json) + longestTopic + 7 < GATEWAY_MQTT_BUFFER_SIZE);
}
