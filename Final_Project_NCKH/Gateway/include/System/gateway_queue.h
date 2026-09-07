#ifndef NCKH_GATEWAY_QUEUE_H
#define NCKH_GATEWAY_QUEUE_H

#include <Arduino.h>
#include "Config/gateway_types.h"

// ============================================================
// Global queues
// ============================================================

// Raw packet từ ESP-NOW callback
extern QueueHandle_t espNowRxQueue;

// Packet đã parse
extern QueueHandle_t patientEventQueue;


// ============================================================
// Queue initialization
// ============================================================

bool initGatewayQueues();

#endif