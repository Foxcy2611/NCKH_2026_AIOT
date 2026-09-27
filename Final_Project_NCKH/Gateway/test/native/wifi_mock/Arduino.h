#pragma once
#include <stdint.h>
#include <stddef.h>
extern uint32_t mockNow;
inline uint32_t millis() { return mockNow; }
struct MockSerial {
    template<class... Args> void printf(const char *, Args...) {}
    void println(const char *) {}
};
extern MockSerial Serial;
