#pragma once
using SemaphoreHandle_t = void*;
inline SemaphoreHandle_t xSemaphoreCreateMutex() { static int token; return &token; }
inline int xSemaphoreTake(SemaphoreHandle_t, unsigned) { return 1; }
inline void xSemaphoreGive(SemaphoreHandle_t) {}
