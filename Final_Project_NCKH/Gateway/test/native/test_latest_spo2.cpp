#include <cassert>
#include <cstdio>
#include <cstring>
#include <initializer_list>
#include "System/gateway_state.h"
#include "System/gateway_json.h"
#include "Network/gateway_payload_validation.h"

static GatewayStateSnapshot snapshot() {
    GatewayStateSnapshot s{};
    assert(GatewayState_GetSnapshot(&s));
    return s;
}
static void checkJson(const GatewayStateSnapshot &s, bool event, const char *expected) {
    UplinkRecord item{};
    item.record.has_patient_event = event;
    item.record.patient_event = s.current_node.payload;
    item.record.latest_spo2 = s.latest_spo2;
    item.record.latest_spo2_valid = s.latest_spo2_valid;
    char json[4096], needle[64];
    assert(GatewaySerializeJson(item, json, sizeof(json)));
    assert(!strstr(json, "\"latest_spo2\""));
    if (event) {
        snprintf(needle, sizeof(needle), "\"spo2\":%s", expected);
        assert(strstr(json, needle));
    } else assert(strstr(json, "\"patient_event\":null"));
}
int main() {
    assert(GatewayState_Init());
    checkJson(snapshot(), false, "null");
    PatientEventEnvelope e{};
    e.device_id = 1;
    e.payload.session_id = 1;
    assert(GatewayState_UpdateNode(e)); // NA before first measurement
    checkJson(snapshot(), true, "null");
    e.payload.vitals_valid = 1; e.payload.spo2 = 98; e.sequence = 2;
    assert(GatewayState_UpdateNode(e));
    auto first = snapshot(); checkJson(first, true, "98");
    e.payload.vitals_valid = 0; e.payload.spo2 = 0; e.sequence = 3;
    assert(GatewayState_UpdateNode(e));
    auto missing = snapshot();
    assert(missing.current_node.payload.spo2 == 0); // raw event preserved
    assert(missing.current_node.payload.vitals_valid == 0);
    assert(missing.current_node.sequence == 3 && missing.node_dirty);
    checkJson(missing, true, "98");
    assert(GatewayState_MarkPublished(first.node_revision));
    assert(snapshot().node_dirty); // stale publish cannot clear newer event
    assert(GatewayState_MarkPublished(missing.node_revision));
    assert(!snapshot().node_dirty);
    checkJson(snapshot(), false, "98"); // periodic telemetry retains cache
    for (unsigned invalid : {0u, 101u, 255u}) {
        e.payload.vitals_valid = 1; e.payload.spo2 = invalid;
        assert(GatewayNodePayloadValid(e.payload));
        assert(GatewayState_UpdateNode(e)); checkJson(snapshot(), true, "98");
    }
    e.payload.vitals_valid = 0; e.payload.spo2 = 97;
    e.payload.heart_rate = 72; // false flag must not block independent SpO2
    assert(GatewayNodePayloadValid(e.payload));
    assert(GatewayState_UpdateNode(e)); checkJson(snapshot(), true, "97");
    e.payload.spo2 = 255;
    assert(GatewayNodePayloadValid(e.payload));
    assert(GatewayState_UpdateNode(e)); checkJson(snapshot(), true, "97");
    e.payload.session_id = 0;
    assert(!GatewayNodePayloadValid(e.payload));
    e.payload.session_id = 1;
    e.payload.vitals_valid = 2;
    assert(!GatewayNodePayloadValid(e.payload));
    e.payload.vitals_valid = 1; e.payload.spo2 = 96;
    assert(GatewayState_UpdateNode(e)); checkJson(snapshot(), true, "96");
    e.payload.spo2 = 100;
    assert(GatewayState_UpdateNode(e)); checkJson(snapshot(), true, "100");
    puts("PASS: latest SpO2, initial NA, retained NA, zero/range/flag, replacement, telemetry, revision");
}
