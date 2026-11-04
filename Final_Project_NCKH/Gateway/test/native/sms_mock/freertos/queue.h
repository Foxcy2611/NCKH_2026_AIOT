#pragma once
#include "FreeRTOS.h"
QueueHandle_t xQueueCreate(unsigned length, unsigned itemSize);
BaseType_t xQueueSend(QueueHandle_t, const void* item, uint32_t);
BaseType_t xQueueReceive(QueueHandle_t, void* item, uint32_t);
