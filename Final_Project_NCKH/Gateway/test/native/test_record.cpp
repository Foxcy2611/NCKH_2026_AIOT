#include <cassert>
#include <cstdio>
#include "System/gateway_record.h"
int main() {
    EnvironmentSnapshot e{};
    auto p=GatewayBuildPayload(e,10000); assert(p.sensor_valid_mask==0 && isnan(p.temperature));
    e.gateway_timestamp_ms=10000; e.temperature_valid=e.humidity_valid=e.pressure_valid=true;
    e.eco2_valid=e.tvoc_valid=true; e.temperature_c=25; e.humidity_percent=60;
    e.pressure_hpa=1013.25; e.eco2_ppm=500; e.tvoc_ppb=20;
    p=GatewayBuildPayload(e,10001); assert(p.sensor_valid_mask==7 && p.eco2==500 && p.temperature==25);
    p=GatewayBuildPayload(e,15000); assert(p.sensor_valid_mask==7);
    p=GatewayBuildPayload(e,15001); assert(p.sensor_valid_mask==0 && isnan(p.pressure));
    p=GatewayBuildPayload(e,9999); assert(p.sensor_valid_mask==0);
    e.humidity_valid=false; p=GatewayBuildPayload(e,10001); assert(p.sensor_valid_mask==6 && isnan(p.humidity));
    e.pressure_hpa=NAN; p=GatewayBuildPayload(e,10001); assert(p.sensor_valid_mask==4);
    e.tvoc_valid=false; p=GatewayBuildPayload(e,10001); assert(p.sensor_valid_mask==0);
    e.gateway_timestamp_ms=0x100000000ULL+100; e.humidity_valid=true; e.pressure_hpa=1013.25; e.tvoc_valid=true;
    p=GatewayBuildPayload(e,e.gateway_timestamp_ms+1); assert(p.sensor_valid_mask==7 && p.timestamp>0xffffffffULL);
    CompleteRecord rec{}; rec.gate=p; assert(!rec.has_patient_event && rec.patient_event.session_id==0);
    assert(sizeof(Patient_Event_Payload_t)==24 && sizeof(Gateway_Response_Payload_t)==24 && sizeof(Secure_EspNow_Packet_t)==64);
    puts("PASS: missing/fresh/stale/boundary/future/partial/nonfinite/gas/64-bit-time/telemetry/protocol");
}
