#include <cassert>
#include <cstdio>
#include <cstring>

#include "System/gateway_json.h"
#include "System/gateway_record.h"
#include "Config/gateway_dashboard_config.h"

int main() {
    UplinkRecord item{};
    item.boot_id = 1;
    item.record_sequence = 1;
    item.record.gate = GatewayBuildPayload(EnvironmentSnapshot{}, 10000);

    NetworkSnapshot net{true, true, -55};
    net.active_uplink = GATE_UPLINK_WIFI;
    GatewayApplyNetwork(item.record.gate, net);

    char json[GATEWAY_DASHBOARD_JSON_CAPACITY];
    auto emit = [&](bool node_valid, bool dirty, uint64_t now) {
        assert(GatewaySerializeDashboardJson(
            item, net, node_valid, dirty, 9, now, 180000, json, sizeof(json)));
        assert(strlen(json) + strlen(MQTT_TOPIC_DASHBOARD) + 7
               < GATEWAY_DASHBOARD_MQTT_BUFFER_SIZE);
        puts(json);
        ++item.record_sequence;
    };

    // Gateway-only packet: chưa từng nhận Patient Event.
    emit(false, false, 10000);

    // Event A: ASTHMA, đủ ngưỡng cảnh báo.
    item.record.has_patient_event = 1;
    item.source_device_id = 123;
    item.source_sequence = 19;
    item.received_uptime_ms = 9000;
    auto &p = item.record.patient_event;
    p.session_id = 42;
    p.classification = 0;
    p.model_score = 0.90f;
    p.vitals_valid = 1;
    p.heart_rate = 72;
    p.spo2 = 98;
    p.battery_node = 255;
    emit(true, true, 10000);

    // Retry cùng Event A: event_id giữ nguyên, record_id thay đổi.
    emit(true, true, 12000);

    // Event A đã publish: Gateway còn current_node nhưng packet Cloud không đính kèm lại.
    item.record.has_patient_event = 0;
    emit(true, false, 15000);

    // Event B: NON-ASTHMA không được tạo cảnh báo; vitals không hợp lệ phải thành null.
    item.record.has_patient_event = 1;
    item.source_sequence = 20;
    item.received_uptime_ms = 15500;
    p.session_id = 43;
    p.classification = 1;
    p.model_score = 0.95f;
    p.vitals_valid = 0;
    p.heart_rate = 0;
    p.spo2 = 0;
    emit(true, true, 16000);

    // Event C: UNSURE cũng không phải cảnh báo Asthma.
    ++item.source_sequence;
    ++p.session_id;
    p.classification = 2;
    p.model_score = 0.95f;
    emit(true, true, 17000);

    // ASTHMA dưới ngưỡng rồi đúng bằng ngưỡng.
    ++item.source_sequence;
    ++p.session_id;
    p.classification = 0;
    p.model_score = 0.79f;
    emit(true, true, 18000);
    p.model_score = 0.80f;
    emit(true, true, 19000);

    // Thời gian nhận ở tương lai không được gây tràn số patient_age_ms.
    item.received_uptime_ms = 9000;
    emit(true, true, 8000);

    const size_t len = strlen(json);
    char exact[GATEWAY_DASHBOARD_JSON_CAPACITY];
    assert(GatewaySerializeDashboardJson(
        item, net, true, true, 9, 8000, 180000, exact, len + 1));
    assert(!GatewaySerializeDashboardJson(
        item, net, true, true, 9, 8000, 180000, exact, len));
    assert(exact[0] == '\0');
    assert(!GatewaySerializeDashboardJson(
        item, net, true, true, 9, 8000, 180000, nullptr, 0));
}
