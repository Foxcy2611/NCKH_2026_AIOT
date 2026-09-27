#include "System/gateway_state.h"
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>

namespace {
SemaphoreHandle_t stateMutex = nullptr;
GatewayStateSnapshot state{};
constexpr uint32_t LOCK_TIMEOUT_MS = 20;
bool lockState() {
    return stateMutex &&
        xSemaphoreTake(stateMutex, pdMS_TO_TICKS(LOCK_TIMEOUT_MS)) == pdTRUE;
}
void unlockState() { xSemaphoreGive(stateMutex); }
}

bool GatewayState_Init() {
    if (stateMutex) return true;
    state = GatewayStateSnapshot{};
    stateMutex = xSemaphoreCreateMutex();
    return stateMutex != nullptr;
}

bool GatewayState_UpdateNode(const PatientEventEnvelope &event) {
    if (!lockState()) return false;
    state.current_node = event;
    state.current_node_valid = true;
    state.node_dirty = true;
    ++state.node_revision;
    unlockState();
    return true;
}

bool GatewayState_UpdateGate(const Gate_Payload_t &gate) {
    if (!lockState()) return false;
    state.current_gate = gate;
    state.current_gate_valid = true;
    unlockState();
    return true;
}

bool GatewayState_GetSnapshot(GatewayStateSnapshot *out) {
    if (!out || !lockState()) return false;
    *out = state;
    unlockState();
    return true;
}

bool GatewayState_MarkPublished(uint64_t published_revision) {
    if (!lockState()) return false;
    if (state.current_node_valid && state.node_dirty &&
        state.node_revision == published_revision) {
        state.node_dirty = false;
    }
    unlockState();
    return true;
}
