#ifndef NCKH_BOARD_PINOUT_H
#define NCKH_BOARD_PINOUT_H

#include <stdint.h>

// ------------------- I2C (OLED + MAX30102) ------------------- //

#define PIN_SCL_I2C 7
#define PIN_SDA_I2C 8

// Chân ngắt của MAX30102
#define PIN_INT_MAX 9

// ------------------------------------------------------------ //


// ------------------------ I2S MICRO ------------------------ //

#define PIN_I2S_WS 15
#define PIN_I2S_SD 16
#define PIN_I2S_SCK 14

// ------------------------------------------------------------ //

// ------------------------ BUTTON PIN ------------------------ //
#define PIN_BTN_SLEEP   6
#define PIN_BTN_CHECK   4
#define PIN_BTN_MONITOR 5

// ------------------------------------------------------------ //

#endif /* NCKH_PINOUT_H */