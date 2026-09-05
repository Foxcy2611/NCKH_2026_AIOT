#ifndef __ST7735_H
#define __ST7735_H

#include <Arduino.h>
#include <SPI.h>

/* ============ Kích thước màn hình ============ */
#define ST7735_WIDTH   160
#define ST7735_HEIGHT  128

/* ============ Registers (giữ nguyên từ bản STM32) ============ */
#define REG_SWRESET 0x01
#define REG_SLPOUT  0x11
#define REG_DISPON  0x29

#define REG_CASET   0x2A
#define REG_RASET   0x2B
#define REG_RAMWR   0x2C

#define REG_MADCTL  0x36
#define REG_COLMOD  0x3A

#define REG_GMCTRP1 0xE0
#define REG_GMCTRN1 0xE1

/* ============ Màu RGB565 ============ */
#define RGB_BLACK   0x0000
#define RGB_BLUE    0x001F
#define RGB_RED     0xF800
#define RGB_GREEN   0x07E0
#define RGB_CYAN    0x07FF
#define RGB_BROWN   0xA145
#define RGB_MAGENTA 0xF81F
#define RGB_PINK    0xFC90
#define RGB_YELLOW  0xFFE0
#define RGB_WHITE   0xFFFF
#define RGB_ORANGE  0xF940

/* ============ Cấu hình chân (đổi theo board của bạn) ============
 * Ví dụ cho ESP32-S3 DevKit — sửa lại theo mạch thực tế.
 * MISO không dùng (màn hình chỉ ghi).
 */
#define TFT_PIN_MOSI   11   // SDA
#define TFT_PIN_SCLK   12   // SCK
#define TFT_PIN_CS     10   // CS
#define TFT_PIN_DC      9   // A0 / DC
#define TFT_PIN_RST     8   // RST

#define TFT_SPI_CLOCK_HZ  20000000UL   // 20MHz, tăng dần nếu dây tốt/ngắn

/* ============ API khởi tạo & SPI low-level ============ */
void ST7735_Init(void);

void SPI_WriteCmd(uint8_t cmd);
void SPI_WriteData(uint8_t data);
void SPI_WriteDataBuf(const uint8_t *data, size_t len);

void SPI_Reset(void);

/* ============ API vẽ cơ bản (giữ tên như bản gốc) ============ */
void ST7735_SetAddressWindow(uint8_t x0, uint8_t y0, uint8_t x1, uint8_t y1);
void ST7735_FillScreen(uint16_t color);
void ST7735_DrawPixel(uint8_t x, uint8_t y, uint16_t color);
void ST7735_DrawImage(uint8_t x, uint8_t y, uint8_t w, uint8_t h, const uint16_t *data);
void ST7735_DrawImageStruct(uint8_t x, uint8_t y, uint8_t w, uint8_t h, const uint8_t *data);

/* ============ API vẽ hình học (bổ sung) ============ */
void ST7735_DrawHLine(uint8_t x, uint8_t y, uint8_t w, uint16_t color);
void ST7735_DrawVLine(uint8_t x, uint8_t y, uint8_t h, uint16_t color);
void ST7735_DrawLine(int16_t x0, int16_t y0, int16_t x1, int16_t y1, uint16_t color);
void ST7735_DrawRect(uint8_t x, uint8_t y, uint8_t w, uint8_t h, uint16_t color);
void ST7735_FillRect(uint8_t x, uint8_t y, uint8_t w, uint8_t h, uint16_t color);
void ST7735_DrawCircle(int16_t x0, int16_t y0, int16_t r, uint16_t color);
void ST7735_FillCircle(int16_t x0, int16_t y0, int16_t r, uint16_t color);

#endif