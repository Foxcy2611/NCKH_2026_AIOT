#include <cassert>
#include <cstring>
#include <cstdio>
#include "Sensor/ESP32_DHT22_Lib.h"
int mockCriticalDepth=0, mockLevel=HIGH;
int64_t mockTime=0;
MockSerial Serial;
int main() {
    DHT22_Init();
    float t=25,h=60;
    assert(DHT22_ReadData(&t,&h)==1);
    DHT22_TimingProfile profile{};
    DHT22_GetTimingProfile(&profile);
    assert(!strcmp(profile.timeoutStage,"response_low_wait"));
    assert(profile.timeoutBit==-1 && mockCriticalDepth==0);
    assert(t==25 && h==60);
    mockLevel=LOW;
    assert(DHT22_ReadData(&t,&h)==1);
    DHT22_GetTimingProfile(&profile);
    assert(!strcmp(profile.timeoutStage,"response_low_pulse"));
    assert(mockCriticalDepth==0);
    assert(DHT22_ReadData(nullptr,&h)==1);
    DHT22_GetTimingProfile(&profile);
    assert(!strcmp(profile.timeoutStage,"argument"));
    puts("PASS: DHT driver diagnostics, stuck HIGH/LOW, timeout cleanup, argument");
}
