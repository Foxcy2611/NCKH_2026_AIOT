#pragma once
#include "Secure_Protocol.h"

// Called only after AES-GCM authentication. Unavailable SpO2 is a missing
// measurement, not a reason to discard an otherwise valid event.
inline bool GatewayNodePayloadValid(const Node_Payload_t &p) {
    if (p.session_id == 0 || p.event_type > 2 || p.classification > 2 ||
        p.audio_quality > 3 || p.vitals_valid > 1 ||
        (p.battery_node > 100 && p.battery_node != 255)) return false;
    if (!(p.model_score >= 0.0f && p.model_score <= 1.0f)) return false;
    // vitals_valid controls heart-rate JSON output, not SpO2 acceptance.
    // Stale vital bytes with a false flag must not discard the entire event.
    return true;
}
