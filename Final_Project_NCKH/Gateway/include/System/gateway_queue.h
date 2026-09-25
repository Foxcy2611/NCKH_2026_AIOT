#pragma once
#include <Arduino.h>
#include "Config/gateway_types.h"
extern QueueHandle_t espNowRxQueue;
extern QueueHandle_t displayQueue;
bool initGatewayQueues();
