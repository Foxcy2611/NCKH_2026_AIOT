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

void OLED_Init(void);
void OLED_Clear_Display(void);
void OLED_UpdateScreen();

void OLED_Println(const char* str);
void OLED_GotoXY(uint8_t x, uint8_t y);
void OLED_DrawPixel(uint8_t x, uint8_t y, bool color);

void OLED_Printf(const char* format, ...);

// ==== TEST MAIN ==== 
void OLED_TestSetup(void);

// === APP UI FUNCTIONS ===
void OLED_Show_PlaceNearMouth();
void OLED_Show_PlaceFinger();
void OLED_Show_Recording();
void OLED_Show_QualityError(const char* error_type);
void OLED_Show_AudioOK();
void OLED_Show_Processing();
void OLED_Show_AI_Result(bool isAsthma);
void OLED_Show_FinalResult(bool isAsthma, int hr, int spo2);
void OLED_Show_DataSent();
void OLED_Show_Welcome();
void OLED_Show_Sleep();
void OLED_Show_Standby();
void OLED_Show_Monitoring();
void OLED_Show_SoundDetected();

#endif