
#include <cassert>
#include <cstdio>
#include <cstring>
#include "System/gateway_json.h"
#include "System/gateway_record.h"
#include "Config/gateway_dashboard_config.h"
int main() {
    UplinkRecord item{};
    item.boot_id=1; item.record_sequence=1;
    item.record.gate=GatewayBuildPayload(EnvironmentSnapshot{},10000);
    NetworkSnapshot net{true,true,-55}; net.active_uplink=GATE_UPLINK_WIFI;
    GatewayApplyNetwork(item.record.gate,net);
    char json[GATEWAY_DASHBOARD_JSON_CAPACITY];
    auto emit=[&](bool dirty, uint64_t now) {
        assert(GatewaySerializeDashboardJson(item,net,dirty,9,now,180000,json,sizeof(json)));
        assert(strlen(json)+strlen(MQTT_TOPIC_DASHBOARD)+7<GATEWAY_DASHBOARD_MQTT_BUFFER_SIZE);
        puts(json);
    };
    emit(false,10000);
    item.record.has_patient_event=1; item.source_device_id=123; item.source_sequence=19;
    item.received_uptime_ms=9000;
    auto &p=item.record.patient_event;
    p.session_id=42;p.classification=2;p.model_score=0.9f;p.vitals_valid=1;p.heart_rate=72;p.spo2=98;
    emit(true,10000);
    ++item.record_sequence;
    emit(false,15000); // clean node still present, same event ID and older age
    p.classification=0; p.vitals_valid=0;
    emit(true,16000);
    p.classification=2;p.model_score=0.79f;
    emit(true,17000);
    p.model_score=0.80f;
    emit(true,18000);
    emit(false,8000); // future receive time must not underflow
    const size_t len=strlen(json);
    char exact[GATEWAY_DASHBOARD_JSON_CAPACITY];
    assert(GatewaySerializeDashboardJson(item,net,false,9,8000,180000,exact,len+1));
    assert(!GatewaySerializeDashboardJson(item,net,false,9,8000,180000,exact,len));
    assert(exact[0]=='\0');
    assert(!GatewaySerializeDashboardJson(item,net,false,9,8000,180000,nullptr,0));
}

