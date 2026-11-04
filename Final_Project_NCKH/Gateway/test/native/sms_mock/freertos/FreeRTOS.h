#pragma once
#include <stdint.h>
#define pdTRUE 1
#define pdFALSE 0
#define pdPASS 1
#define pdMS_TO_TICKS(ms) (ms)
#define portMAX_DELAY 0xffffffffUL
using BaseType_t = int;
using QueueHandle_t = void*;
