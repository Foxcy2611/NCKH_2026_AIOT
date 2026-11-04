#pragma once

#include <stdint.h>
#include "Config/gateway_config.h"
#include "Config/gateway_types.h"

// Pure policy used by the ESP-NOW RX task; no SMS on telemetry or asthma/unsure.
inline bool GatewaySmsQualifies(const Node_Payload_t &p) {
    return p.session_id != 0 && p.classification == GATEWAY_SMS_NON_ASTHMA_CLASS;
}

// Deduplicate across different ESP-NOW sequences within the same patient session.
// Kept in RAM, bounded by the last GATEWAY_SMS_SESSION_HISTORY unique sessions.
class GatewaySmsSessionHistory {
public:
    bool contains(uint32_t deviceId, uint32_t sessionId) const {
        for (const auto &entry : entries_) {
            if (entry.valid && entry.device_id == deviceId && entry.session_id == sessionId) {
                return true;
            }
        }
        return false;
    }

    void remember(uint32_t deviceId, uint32_t sessionId) {
        entries_[next_] = {true, deviceId, sessionId};
        next_ = (next_ + 1) % GATEWAY_SMS_SESSION_HISTORY;
    }

private:
    struct Entry { bool valid; uint32_t device_id; uint32_t session_id; };
    Entry entries_[GATEWAY_SMS_SESSION_HISTORY]{};
    uint32_t next_ = 0;
};

enum class GatewaySmsQueueResult : uint8_t {
    NotEligible,
    DuplicateSession,
    Queued,
    QueueFull,
    Disabled
};

// Call during setup before starting TaskEspNow / TaskSms.
bool GatewaySms_Init();
// Call only from TaskEspNow after authentication, payload validation and state update.
GatewaySmsQueueResult GatewaySms_OnPatientEvent(const PatientEventEnvelope &event);
void TaskSms(void *parameter);
