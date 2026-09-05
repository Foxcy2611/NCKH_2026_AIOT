#include "st7735.h"

static SPISettings tftSPISettings(TFT_SPI_CLOCK_HZ, MSBFIRST, SPI_MODE0);

/* ============ Macro điều khiển chân, giữ style code gốc ============ */
#define CS_LOW()    digitalWrite(TFT_PIN_CS, LOW)
#define CS_HIGH()   digitalWrite(TFT_PIN_CS, HIGH)

#define A0_CMD()    digitalWrite(TFT_PIN_DC, LOW)
#define A0_DATA()   digitalWrite(TFT_PIN_DC, HIGH)

#define RST_LOW()   digitalWrite(TFT_PIN_RST, LOW)
#define RST_HIGH()  digitalWrite(TFT_PIN_RST, HIGH)

/* ============ SPI low-level ============ */

static void SPI_Config(void) {
    pinMode(TFT_PIN_CS, OUTPUT);
    pinMode(TFT_PIN_DC, OUTPUT);
    pinMode(TFT_PIN_RST, OUTPUT);

    CS_HIGH();
    RST_HIGH();

    // MISO không dùng -> truyền -1
    SPI.begin(TFT_PIN_SCLK, -1, TFT_PIN_MOSI, TFT_PIN_CS);
}

void SPI_WriteCmd(uint8_t cmd) {
    A0_CMD();
    SPI.beginTransaction(tftSPISettings);
    CS_LOW();

    SPI.transfer(cmd);

    CS_HIGH();
    SPI.endTransaction();
}

void SPI_WriteData(uint8_t data) {
    A0_DATA();
    SPI.beginTransaction(tftSPISettings);
    CS_LOW();

    SPI.transfer(data);

    CS_HIGH();
    SPI.endTransaction();
}

/* Gửi buffer dài trong 1 transaction duy nhất — dùng cho FillScreen/DrawImage,
 * nhanh hơn nhiều so với gọi SPI_WriteData() từng byte. */
void SPI_WriteDataBuf(const uint8_t *data, size_t len) {
    A0_DATA();
    SPI.beginTransaction(tftSPISettings);
    CS_LOW();

    SPI.writeBytes(data, len);

    CS_HIGH();
    SPI.endTransaction();
}

void SPI_Reset(void) {
    RST_HIGH();
    delay(5);

    RST_LOW();
    delay(20);

    RST_HIGH();
    delay(150);
}

/* ============ Khởi tạo controller (giữ nguyên chuỗi lệnh gốc) ============ */

void ST7735_Init(void) {
    SPI_Config();

    SPI_Reset();

    SPI_WriteCmd(REG_SWRESET);
    delay(150);

    SPI_WriteCmd(REG_SLPOUT);
    delay(200);

    SPI_WriteCmd(REG_COLMOD);
    SPI_WriteData(0x05);

    SPI_WriteCmd(REG_MADCTL);
    SPI_WriteData(0xA0);

    SPI_WriteCmd(REG_GMCTRN1);
    SPI_WriteData(0x09);
    SPI_WriteData(0x16);
    SPI_WriteData(0x09); SPI_WriteData(0x20);
    SPI_WriteData(0x21); SPI_WriteData(0x1B);
    SPI_WriteData(0x13); SPI_WriteData(0x19);
    SPI_WriteData(0x17); SPI_WriteData(0x15);
    SPI_WriteData(0x1E); SPI_WriteData(0x2B);
    SPI_WriteData(0x04); SPI_WriteData(0x05);
    SPI_WriteData(0x02); SPI_WriteData(0x0E);

    SPI_WriteCmd(REG_GMCTRN1);
    SPI_WriteData(0x0B);
    SPI_WriteData(0x14);
    SPI_WriteData(0x08); SPI_WriteData(0x1E);
    SPI_WriteData(0x22); SPI_WriteData(0x1D);
    SPI_WriteData(0x18); SPI_WriteData(0x1E);
    SPI_WriteData(0x1B); SPI_WriteData(0x1A);
    SPI_WriteData(0x24); SPI_WriteData(0x2B);
    SPI_WriteData(0x06); SPI_WriteData(0x06);
    SPI_WriteData(0x02); SPI_WriteData(0x0F);

    SPI_WriteCmd(REG_DISPON);
    delay(100);

    ST7735_FillScreen(RGB_BLACK);
}

/* ============ Vẽ cơ bản ============ */

void ST7735_SetAddressWindow(uint8_t x0, uint8_t y0, uint8_t x1, uint8_t y1) {
    SPI_WriteCmd(REG_CASET);
    SPI_WriteData(0x00); SPI_WriteData(x0);
    SPI_WriteData(0x00); SPI_WriteData(x1);

    SPI_WriteCmd(REG_RASET);
    SPI_WriteData(0x00); SPI_WriteData(y0);
    SPI_WriteData(0x00); SPI_WriteData(y1);

    SPI_WriteCmd(REG_RAMWR);
}

void ST7735_FillScreen(uint16_t color) {
    ST7735_SetAddressWindow(0, 0, ST7735_WIDTH - 1, ST7735_HEIGHT - 1);

    uint8_t hi = color >> 8;
    uint8_t lo = color & 0xFF;

    // Buffer nhỏ để hạn chế RAM, gửi theo từng dòng
    static uint8_t line[ST7735_WIDTH * 2];
    for (uint16_t i = 0; i < ST7735_WIDTH; i++) {
        line[2 * i]     = hi;
        line[2 * i + 1] = lo;
    }

    A0_DATA();
    SPI.beginTransaction(tftSPISettings);
    CS_LOW();
    for (uint16_t j = 0; j < ST7735_HEIGHT; j++) {
        SPI.writeBytes(line, sizeof(line));
    }
    CS_HIGH();
    SPI.endTransaction();
}

void ST7735_DrawPixel(uint8_t x, uint8_t y, uint16_t color) {
    if (x >= ST7735_WIDTH || y >= ST7735_HEIGHT) return;

    ST7735_SetAddressWindow(x, y, x + 1, y + 1);

    uint8_t buf[2] = { (uint8_t)(color >> 8), (uint8_t)(color & 0xFF) };
    SPI_WriteDataBuf(buf, 2);
}

void ST7735_DrawImage(uint8_t x, uint8_t y, uint8_t w, uint8_t h, const uint16_t *data) {
    if ((x >= ST7735_WIDTH) || (y >= ST7735_HEIGHT)) return;

    ST7735_SetAddressWindow(x, y, x + w - 1, y + h - 1);

    A0_DATA();
    SPI.beginTransaction(tftSPISettings);
    CS_LOW();
    for (uint32_t i = 0; i < (uint32_t)w * h; i++) {
        uint16_t c = data[i];
        SPI.transfer(c >> 8);
        SPI.transfer(c & 0xFF);
    }
    CS_HIGH();
    SPI.endTransaction();
}

void ST7735_DrawImageStruct(uint8_t x, uint8_t y, uint8_t w, uint8_t h, const uint8_t *data) {
    if ((x >= ST7735_WIDTH) || (y >= ST7735_HEIGHT)) return;

    ST7735_SetAddressWindow(x, y, x + w - 1, y + h - 1);

    // Dữ liệu GIMP đã ở dạng byte, đảo thứ tự [lo, hi] -> [hi, lo] giống bản gốc,
    // gửi thẳng cả block bằng writeBytes cho nhanh nếu buffer đã đúng thứ tự.
    A0_DATA();
    SPI.beginTransaction(tftSPISettings);
    CS_LOW();
    for (uint32_t i = 0; i < (uint32_t)w * h * 2; i += 2) {
        SPI.transfer(data[i + 1]);
        SPI.transfer(data[i]);
    }
    CS_HIGH();
    SPI.endTransaction();
}

/* ============ Vẽ hình học (bổ sung) ============ */

void ST7735_DrawHLine(uint8_t x, uint8_t y, uint8_t w, uint16_t color) {
    if (y >= ST7735_HEIGHT) return;
    if (x + w > ST7735_WIDTH) w = ST7735_WIDTH - x;

    ST7735_SetAddressWindow(x, y, x + w - 1, y);

    uint8_t hi = color >> 8, lo = color & 0xFF;
    A0_DATA();
    SPI.beginTransaction(tftSPISettings);
    CS_LOW();
    for (uint8_t i = 0; i < w; i++) {
        SPI.transfer(hi);
        SPI.transfer(lo);
    }
    CS_HIGH();
    SPI.endTransaction();
}

void ST7735_DrawVLine(uint8_t x, uint8_t y, uint8_t h, uint16_t color) {
    if (x >= ST7735_WIDTH) return;
    if (y + h > ST7735_HEIGHT) h = ST7735_HEIGHT - y;

    ST7735_SetAddressWindow(x, y, x, y + h - 1);

    uint8_t hi = color >> 8, lo = color & 0xFF;
    A0_DATA();
    SPI.beginTransaction(tftSPISettings);
    CS_LOW();
    for (uint8_t i = 0; i < h; i++) {
        SPI.transfer(hi);
        SPI.transfer(lo);
    }
    CS_HIGH();
    SPI.endTransaction();
}

void ST7735_DrawRect(uint8_t x, uint8_t y, uint8_t w, uint8_t h, uint16_t color) {
    ST7735_DrawHLine(x, y, w, color);
    ST7735_DrawHLine(x, y + h - 1, w, color);
    ST7735_DrawVLine(x, y, h, color);
    ST7735_DrawVLine(x + w - 1, y, h, color);
}

void ST7735_FillRect(uint8_t x, uint8_t y, uint8_t w, uint8_t h, uint16_t color) {
    if (x + w > ST7735_WIDTH)  w = ST7735_WIDTH - x;
    if (y + h > ST7735_HEIGHT) h = ST7735_HEIGHT - y;

    ST7735_SetAddressWindow(x, y, x + w - 1, y + h - 1);

    uint8_t hi = color >> 8, lo = color & 0xFF;
    A0_DATA();
    SPI.beginTransaction(tftSPISettings);
    CS_LOW();
    for (uint32_t i = 0; i < (uint32_t)w * h; i++) {
        SPI.transfer(hi);
        SPI.transfer(lo);
    }
    CS_HIGH();
    SPI.endTransaction();
}

/* Bresenham line — hỗ trợ toạ độ âm/ngoài biên, tự clip qua ST7735_DrawPixel */
void ST7735_DrawLine(int16_t x0, int16_t y0, int16_t x1, int16_t y1, uint16_t color) {
    int16_t dx = abs(x1 - x0), sx = x0 < x1 ? 1 : -1;
    int16_t dy = -abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
    int16_t err = dx + dy, e2;

    while (true) {
        if (x0 >= 0 && x0 < ST7735_WIDTH && y0 >= 0 && y0 < ST7735_HEIGHT) {
            ST7735_DrawPixel((uint8_t)x0, (uint8_t)y0, color);
        }
        if (x0 == x1 && y0 == y1) break;
        e2 = 2 * err;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
    }
}

/* Midpoint circle algorithm */
void ST7735_DrawCircle(int16_t x0, int16_t y0, int16_t r, uint16_t color) {
    int16_t f = 1 - r;
    int16_t ddF_x = 1;
    int16_t ddF_y = -2 * r;
    int16_t x = 0;
    int16_t y = r;

    ST7735_DrawPixel(x0, y0 + r, color);
    ST7735_DrawPixel(x0, y0 - r, color);
    ST7735_DrawPixel(x0 + r, y0, color);
    ST7735_DrawPixel(x0 - r, y0, color);

    while (x < y) {
        if (f >= 0) { y--; ddF_y += 2; f += ddF_y; }
        x++;
        ddF_x += 2;
        f += ddF_x;

        ST7735_DrawPixel(x0 + x, y0 + y, color);
        ST7735_DrawPixel(x0 - x, y0 + y, color);
        ST7735_DrawPixel(x0 + x, y0 - y, color);
        ST7735_DrawPixel(x0 - x, y0 - y, color);
        ST7735_DrawPixel(x0 + y, y0 + x, color);
        ST7735_DrawPixel(x0 - y, y0 + x, color);
        ST7735_DrawPixel(x0 + y, y0 - x, color);
        ST7735_DrawPixel(x0 - y, y0 - x, color);
    }
}

void ST7735_FillCircle(int16_t x0, int16_t y0, int16_t r, uint16_t color) {
    ST7735_DrawVLine(x0, y0 - r, 2 * r + 1, color);

    int16_t f = 1 - r;
    int16_t ddF_x = 1;
    int16_t ddF_y = -2 * r;
    int16_t x = 0;
    int16_t y = r;

    while (x < y) {
        if (f >= 0) { y--; ddF_y += 2; f += ddF_y; }
        x++;
        ddF_x += 2;
        f += ddF_x;

        ST7735_DrawVLine(x0 + x, y0 - y, 2 * y + 1, color);
        ST7735_DrawVLine(x0 - x, y0 - y, 2 * y + 1, color);
        ST7735_DrawVLine(x0 + y, y0 - x, 2 * x + 1, color);
        ST7735_DrawVLine(x0 - y, y0 - x, 2 * x + 1, color);
    }
}