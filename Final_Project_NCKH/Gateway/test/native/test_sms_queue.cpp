#include <cassert>
#include <cstdio>
#include <cstring>
#include <deque>
#include <vector>
#include "System/gateway_sms.h"
#include <freertos/queue.h>

TestSerial Serial;
uint32_t millis() { return 0; }
void vTaskDelay(uint32_t) {}

struct MockQueue {
    unsigned capacity;
    unsigned itemSize;
    std::deque<std::vector<uint8_t>> items;
};
MockQueue q{};
QueueHandle_t xQueueCreate(unsigned count, unsigned size) {
    q.capacity = count;
    q.itemSize = size;
    return &q;
}
BaseType_t xQueueSend(QueueHandle_t handle, const void *item, uint32_t) {
    assert(handle == &q);
    if (q.items.size() == q.capacity) return pdFALSE;
    const auto *bytes = static_cast<const uint8_t*>(item);
    q.items.emplace_back(bytes, bytes + q.itemSize);
    return pdTRUE;
}
BaseType_t xQueueReceive(QueueHandle_t handle, void *item, uint32_t) {
    assert(handle == &q);
    if (q.items.empty()) return pdFALSE;
    std::memcpy(item, q.items.front().data(), q.itemSize);
    q.items.pop_front();
    return pdTRUE;
}

bool A7680C_IsReady() { return true; }
bool A7680C_SendSMS(const char*, const char*) { return true; }

int main() {
    assert(GatewaySms_Init());
    PatientEventEnvelope event{};
    event.device_id = 5;
    event.payload.session_id = 7;
    event.payload.classification = 0;
    assert(GatewaySms_OnPatientEvent(event) == GatewaySmsQueueResult::NotEligible);
    event.payload.classification = 2;
    assert(GatewaySms_OnPatientEvent(event) == GatewaySmsQueueResult::NotEligible);
    event.payload.classification = 1;
    event.payload.session_id = 0;
    assert(GatewaySms_OnPatientEvent(event) == GatewaySmsQueueResult::NotEligible);
    assert(q.items.empty());

    event.payload.session_id = 7;
    assert(GatewaySms_OnPatientEvent(event) == GatewaySmsQueueResult::Queued);
    assert(GatewaySms_OnPatientEvent(event) == GatewaySmsQueueResult::DuplicateSession);
    event.sequence = 800; // new ESP-NOW sequence, same session
    assert(GatewaySms_OnPatientEvent(event) == GatewaySmsQueueResult::DuplicateSession);
    assert(q.items.size() == 1);

    for (unsigned i = 0; i < GATEWAY_SMS_QUEUE_LENGTH - 1; ++i) {
        event.payload.session_id = 100 + i;
        assert(GatewaySms_OnPatientEvent(event) == GatewaySmsQueueResult::Queued);
    }
    assert(q.items.size() == GATEWAY_SMS_QUEUE_LENGTH);
    event.payload.session_id = 900;
    assert(GatewaySms_OnPatientEvent(event) == GatewaySmsQueueResult::QueueFull);
    struct Request { uint32_t device_id; uint32_t session_id; float score; } extracted{};
    assert(xQueueReceive(&q, &extracted, 0) == pdTRUE);
    assert(extracted.device_id == 5 && extracted.session_id == 7);
    assert(GatewaySms_OnPatientEvent(event) == GatewaySmsQueueResult::Queued);
    assert(GatewaySms_OnPatientEvent(event) == GatewaySmsQueueResult::DuplicateSession);
    event.device_id = 6;
    assert(GatewaySms_OnPatientEvent(event) == GatewaySmsQueueResult::QueueFull);

    std::puts("PASS: SMS event queue, at most one per session, no telemetry, overflow retry");
}
