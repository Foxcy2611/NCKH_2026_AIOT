#pragma once
#include "Config/gateway_types.h"

struct GatewayStateSnapshot {
    PatientEventEnvelope current_node{};
    Gateway_Payload_t current_gate{};
    bool current_node_valid = false;
    bool current_gate_valid = false;
    bool node_dirty = false;
    uint64_t node_revision = 0;
    // Last usable SpO2 for the configured Node, retained until Gateway restart.
    uint8_t latest_spo2 = 0;
    bool latest_spo2_valid = false;
};

// Call once in setup(), before starting tasks or ESP-NOW.
bool GatewayState_Init();
// Caller must authenticate, validate and reject duplicate/replay BEFORE this.
bool GatewayState_UpdateNode(const PatientEventEnvelope &event);
bool GatewayState_UpdateGate(const Gateway_Payload_t &gate);
bool GatewayState_GetSnapshot(GatewayStateSnapshot *out);
// true means lock acquired; an older revision is a successful no-op.
bool GatewayState_MarkPublished(uint64_t published_revision);
