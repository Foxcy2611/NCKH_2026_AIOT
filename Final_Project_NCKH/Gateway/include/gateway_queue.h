#ifndef GATEWAY_QUEUE_H
#define GATEWAY_QUEUE_H

#include <Arduino.h>
#include "gateway_types.h"

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