#include <cassert>
#include <cstdio>
#include "System/gateway_sms.h"

int main() {
    Node_Payload_t payload{};
    assert(!GatewaySmsQualifies(payload));                     // no session/event
    payload.session_id = 42;
    payload.classification = 0;
    assert(!GatewaySmsQualifies(payload));                     // ASTHMA
    payload.classification = 2;
    assert(!GatewaySmsQualifies(payload));                     // UNSURE
    payload.classification = 1;
    assert(GatewaySmsQualifies(payload));                      // NON-ASTHMA

    GatewaySmsSessionHistory history{};
    assert(!history.contains(100, 42));
    history.remember(100, 42);
    assert(history.contains(100, 42));
    assert(!history.contains(101, 42));                        // device ID part of key
    assert(!history.contains(100, 43));                        // distinct session
    history.remember(101, 42);
    assert(history.contains(101, 42));

    // Bounded cache is documented and never touches modem/telemetry state.
    for (uint32_t i = 0; i < GATEWAY_SMS_SESSION_HISTORY + 2; ++i) {
        history.remember(200, 1000 + i);
    }
    assert(!history.contains(100, 42));
    assert(history.contains(200, 1001 + GATEWAY_SMS_SESSION_HISTORY));

    std::puts("PASS: SMS only NON-ASTHMA with session; duplicate session cache/device isolation");
}
