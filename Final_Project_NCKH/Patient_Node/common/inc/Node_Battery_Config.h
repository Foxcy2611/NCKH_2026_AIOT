#ifndef NCKH_NODE_BATTERY_CONFIG_H
#define NCKH_NODE_BATTERY_CONFIG_H

#include "Board_Pinout.h"

// Mach do pin Node dung cau chia ap: 8,39 V tai pin -> 2,56 V tai ADC.
// GPIO dung chung duoc khai bao duy nhat trong Board_Pinout.h.
#define NODE_BATTERY_ENABLED true
#define NODE_BATTERY_ADC_PIN PIN_READ_BATTERY
#define NODE_BATTERY_VBAT_REF_V 8.39f
#define NODE_BATTERY_ADC_REF_V 2.56f
#define NODE_BATTERY_EMPTY_V 6.40f
#define NODE_BATTERY_FULL_V 8.39f
// Reliable ADC input range for the Node chip and attenuation.
#define NODE_BATTERY_ADC_MIN_MV 150.0f
#define NODE_BATTERY_ADC_MAX_MV 3000.0f
#define NODE_BATTERY_ATTENUATION ADC_11db

#endif /* NCKH_NODE_BATTERY_CONFIG_H */
