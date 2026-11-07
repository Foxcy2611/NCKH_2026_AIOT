#ifndef NCKH_NODE_BATTERY_H
#define NCKH_NODE_BATTERY_H

#include <stdint.h>

struct NodeBatteryReading {
    uint8_t percent; // 0..100; 255 = unavailable
    float voltage;  // Filtered pack voltage; NAN = unavailable
    float adcMv;    // Trimmed ADC average; NAN = unavailable
    bool valid;
};

// Once from setup. False = disabled or invalid configuration.
bool NodeBattery_Begin();

// Single caller only; outside ISR, ESP-NOW callbacks and audio capture.
NodeBatteryReading NodeBattery_Read();

// Call after long sleep or battery replacement to discard EMA history.
void NodeBattery_ResetFilter();

#endif /* NCKH_NODE_BATTERY_H */