#ifndef NCKH_BOARD_PINOUT_H
#define NCKH_BOARD_PINOUT_H

#include <stdint.h>

// ------------------- I2C (OLED + MAX30102) ------------------- //

#define PIN_SDA_I2C 8
#define PIN_SCL_I2C 9

// Chân ngắt của MAX30102
#define PIN_INT_MAX 10

// ------------------------------------------------------------- //

// ----------------------- READ BATTERY ------------------------ //

// GPIO7 = ADC1_CH6 tren ESP32-S3 DevKitC-1. Chan nay khong xung dot
// voi I2C, I2S, MAX30102 hay ba nut bam hien tai.
// Chi dua dien ap DA QUA CAU CHIA AP vao chan nay; khong noi truc tiep
// pin 2S (6,4-8,4 V) vao GPIO cua ESP32-S3.
#define PIN_READ_BATTERY 7

// ------------------------------------------------------------- //

// ------------------------- I2S MICRO ------------------------- //

#define PIN_I2S_SCK 14
#define PIN_I2S_WS 15
#define PIN_I2S_SD 16

// ------------------------------------------------------------- //

// ------------------------ BUTTON PIN ------------------------- //

// Cả ba nút active-low, dùng INPUT_PULLUP và đồng thời là wake-source của
// ESP32-S3 khi STATE_STANDBY chuyển sang Light Sleep.
#define PIN_BTN_CHECK   4
#define PIN_BTN_MONITOR 5
#define PIN_BTN_SLEEP   6

// ------------------------------------------------------------- //

#endif /* NCKH_BOARD_PINOUT_H */
