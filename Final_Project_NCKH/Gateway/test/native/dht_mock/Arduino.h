#pragma once
#include <stdint.h>
#define LOW 0
#define HIGH 1
#define OUTPUT 1
#define INPUT_PULLUP 2
using portMUX_TYPE = int;
#define portMUX_INITIALIZER_UNLOCKED 0
extern int mockCriticalDepth;
#define portENTER_CRITICAL(m) ((void)(m), ++mockCriticalDepth)
#define portEXIT_CRITICAL(m) ((void)(m), --mockCriticalDepth)
extern int mockLevel;
inline int digitalRead(int) { return mockLevel; }
inline void digitalWrite(int,int) {}
inline void pinMode(int,int) {}
inline void delay(unsigned) {}
inline void delayMicroseconds(unsigned) {}
struct MockSerial {
    template<class... Args> void printf(const char*,Args...) {}
    void println(const char*) {}
};
extern MockSerial Serial;
