#ifndef ESP32_SSD1306_DISPLAY_H
#define ESP32_SSD1306_DISPLAY_H

#include <Arduino.h>
#include <Wire.h>
#include <stdio.h>
#include <stdarg.h>

//[Địa chỉ] 7-bit chuẩn cho SSD1306 trên nền tảng Arduino/ESP-IDF
#define OLED_I2C_ADDR 0x3C 
#define OLED_WIDTH 128
#define OLED_HEIGHT 64

bool OLED_Init(void);
void OLED_Clear_Display(void);
bool OLED_UpdateScreen(void);

void OLED_Println(const char* str);
void OLED_GotoXY(uint8_t x, uint8_t y);
void OLED_DrawPixel(uint8_t x, uint8_t y, bool color);

void OLED_Printf(const char* format, ...);

// ==== TEST MAIN ==== 
void OLED_TestSetup(void);

#endif
