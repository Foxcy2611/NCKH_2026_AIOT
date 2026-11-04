#pragma once
#include <stdint.h>
#include <stddef.h>
class HardwareSerial;
struct TestSerial {
    template <typename... Args> void printf(const char *, Args...) {}
    void println(const char *) {}
};
extern TestSerial Serial;
uint32_t millis();
