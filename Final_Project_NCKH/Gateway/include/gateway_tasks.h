#ifndef GATEWAY_TASKS_H
#define GATEWAY_TASKS_H

#include <Arduino.h>

// ============================================================
// FreeRTOS Tasks
// ============================================================

void TaskEspNow(void *parameter);

void TaskGatewayManager(void *parameter);

void TaskSensor(void *parameter);

void TaskNetwork(void *parameter);


// ============================================================
// ESP-NOW
// ============================================================

bool initEspNow();

#endif