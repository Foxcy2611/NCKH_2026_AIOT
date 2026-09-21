#ifndef NCKH_UI_OLED_H
#define NCKH_UI_OLED_H

#include <Arduino.h>
#include <Wire.h>
#include <stdarg.h>
#include <stdio.h>

constexpr uint8_t OLED_I2C_ADDR = 0x3C;
constexpr uint8_t OLED_WIDTH = 128;
constexpr uint8_t OLED_HEIGHT = 64;

void OLED_Init(void);
void OLED_Clear_Display(void);
void OLED_UpdateScreen(void);

void OLED_Println(const char* str);
void OLED_GotoXY(uint8_t x, uint8_t y);
void OLED_DrawPixel(uint8_t x, uint8_t y, bool color);
void OLED_Printf(const char* format, ...);

void OLED_Show_PlaceNearMouth(void);
void OLED_Show_PlaceFinger(void);
void OLED_Show_Recording(void);
void OLED_Show_QualityError(const char* error_type);
void OLED_Show_AudioOK(void);
void OLED_Show_Processing(void);
void OLED_Show_AI_Result(int ai_status);
void OLED_Show_FinalResult(int ai_status, int hr, int spo2);
void OLED_Show_DataSent(void);
void OLED_Show_Welcome(void);
void OLED_Show_Sleep(void);
void OLED_Show_Standby(void);
void OLED_Show_MonitorPreparing(void);
void OLED_Show_Monitoring(void);
void OLED_Show_SoundDetected(void);
void OLED_Show_ReplyOK(void);
void OLED_Show_NoReply(void);

#endif /* NCKH_UI_OLED_H */
