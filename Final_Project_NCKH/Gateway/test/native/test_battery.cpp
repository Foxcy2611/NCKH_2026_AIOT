#include <cassert>
#include <cmath>
#include <cstring>
#include <cstdio>
#include <string>
#include "Sensor/gateway_battery.h"
#include "System/gateway_record.h"
#include "System/gateway_json.h"
int main() {
    GatewayBatteryFilter b;
    assert(b.update(2560) == 100);
    assert(fabs(b.voltage() - 8.39f) < 0.001f);
    assert(b.update(NAN) == 255 && isnan(b.voltage()));
    assert(b.update(0) == 255 && b.update(3100) == 255);
    const float ratio = GATEWAY_BATTERY_VBAT_REF / GATEWAY_BATTERY_ADC_REF;
    assert(b.update(6400 / ratio) == 0);
    b.update(NAN);
    assert(b.update(7395 / ratio) == 50);
    b.update(NAN);
    assert(b.update(6000 / ratio) == 0); // low pack is empty, not missing
    b.update(NAN);
    assert(b.update(8600 / ratio) == 100);
    const float before = b.voltage();
    b.update(2560);
    assert(b.voltage() < before && b.voltage() > 8.39f);

    EnvironmentSnapshot e{};
    e.gateway_timestamp_ms = e.battery_timestamp_ms = 10000;
    assert(GatewayBuildPayload(e, 10000).battery_gate == 255);
    e.battery_valid = true; e.battery_percent = 73;
    assert(GatewayBuildPayload(e, 15000).battery_gate == 73);
    assert(GatewayBuildPayload(e, 15001).battery_gate == 255);
    assert(GatewayBuildPayload(e, 9999).battery_gate == 255);
    e.battery_percent = 101;
    assert(GatewayBuildPayload(e, 10000).battery_gate == 255);
    e.battery_percent = 73;
    UplinkRecord item{};
    item.record.gate = GatewayBuildPayload(e, 10000);
    item.record.has_patient_event = 1;
    item.record.patient_event.battery_node = 42;
    char withBattery[4096], withoutBattery[4096];
    NetworkSnapshot net{};
    assert(GatewaySerializeDashboardJson(item, net, true, true, 1, 10000, 100000,
                                        withBattery, sizeof(withBattery)));
    item.record.gate.battery_gate = 255;
    assert(GatewaySerializeDashboardJson(item, net, true, true, 1, 10000, 100000,
                                        withoutBattery, sizeof(withoutBattery)));
    std::string actual(withBattery);
    const auto pos = actual.find("\"battery_gate\":73");
    assert(pos != std::string::npos);
    actual.replace(pos, strlen("\"battery_gate\":73"), "\"battery_gate\":null");
    assert(actual == withoutBattery); // every other byte of JSON remains identical
    assert(strstr(withBattery, "\"battery_node\":42"));
    assert(sizeof(Node_Payload_t) == 16 && sizeof(Secure_Packet_t) == 56);
    puts("PASS: measured calibration, bounds, filtering, invalid/recovery, age, JSON isolation, Node ABI");
}
