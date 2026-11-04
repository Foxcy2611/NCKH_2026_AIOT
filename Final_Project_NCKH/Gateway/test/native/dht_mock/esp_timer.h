#pragma once
#include <stdint.h>
extern int64_t mockTime;
inline int64_t esp_timer_get_time() { return ++mockTime; }
