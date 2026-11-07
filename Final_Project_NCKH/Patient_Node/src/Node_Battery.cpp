#include <Arduino.h>
#include <math.h>

#include "Power/Node_Battery.h"

#include "Node_Battery_Config.h"
namespace {
bool ready = false;
float filtered = NAN;
NodeBatteryReading unavailable() {
    filtered = NAN;
    return {255, NAN, NAN, false};
}
}
void NodeBattery_ResetFilter() { filtered = NAN; }
bool NodeBattery_Begin() {
    ready = false;
    NodeBattery_ResetFilter();
    if (!NODE_BATTERY_ENABLED || NODE_BATTERY_ADC_PIN < 0 || NODE_BATTERY_ADC_PIN > 255 ||
        !isfinite(NODE_BATTERY_VBAT_REF_V) || NODE_BATTERY_VBAT_REF_V <= 0 ||
        !isfinite(NODE_BATTERY_ADC_REF_V) || NODE_BATTERY_ADC_REF_V <= 0 ||
        !isfinite(NODE_BATTERY_EMPTY_V) || NODE_BATTERY_EMPTY_V <= 0 ||
        !isfinite(NODE_BATTERY_FULL_V) || NODE_BATTERY_FULL_V <= NODE_BATTERY_EMPTY_V ||
        !isfinite(NODE_BATTERY_ADC_MIN_MV) || NODE_BATTERY_ADC_MIN_MV <= 0 ||
        !isfinite(NODE_BATTERY_ADC_MAX_MV) || NODE_BATTERY_ADC_MAX_MV <= NODE_BATTERY_ADC_MIN_MV)
        return false;
    pinMode(NODE_BATTERY_ADC_PIN, INPUT);
    analogSetPinAttenuation(NODE_BATTERY_ADC_PIN, NODE_BATTERY_ATTENUATION);
    ready = true;
    return true;
}
NodeBatteryReading NodeBattery_Read() {
    if (!ready) return unavailable();
    uint64_t sum = 0;
    uint32_t minimum = UINT32_MAX, maximum = 0;
    bool valid = true;
    for (unsigned i = 0; i < 8; ++i) {
        const uint32_t mv = analogReadMilliVolts(NODE_BATTERY_ADC_PIN);
        if (mv < NODE_BATTERY_ADC_MIN_MV || mv > NODE_BATTERY_ADC_MAX_MV) valid = false;
        sum += mv;
        if (mv < minimum) minimum = mv;
        if (mv > maximum) maximum = mv;
    }
    if (!valid) return unavailable();
    const float adcMv = (sum - minimum - maximum) / 6.0f;
    const float voltage = adcMv * 0.001f * NODE_BATTERY_VBAT_REF_V / NODE_BATTERY_ADC_REF_V;
    if (!isfinite(voltage)) return unavailable();
    filtered = isfinite(filtered) ? filtered + 0.25f * (voltage - filtered) : voltage;
    const float estimate = 100.0f * (filtered - NODE_BATTERY_EMPTY_V) /
                           (NODE_BATTERY_FULL_V - NODE_BATTERY_EMPTY_V);
    const uint8_t percent = estimate <= 0 ? 0 : estimate >= 100 ? 100 :
                            static_cast<uint8_t>(estimate + 0.5f);
    return {percent, filtered, adcMv, true};
}
