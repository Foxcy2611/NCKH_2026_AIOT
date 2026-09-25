#ifndef NCKH_GATEWAY_TFT_H
#define NCKH_GATEWAY_TFT_H

#include <Arduino.h>
#include <SPI.h>
#include <TFT_eSPI.h>
#include "Config/gateway_types.h"
#include "System/gateway_state.h"

// ============================================================
//  SƠ ĐỒ NỐI DÂY MÀN HÌNH TFT ST7735 (Cấu hình qua platformio.ini):
//  - VCC   -> 3.3V / 5V
//  - GND   -> GND
//  - CS    -> GPIO 15 (TFT_CS)
//  - RESET -> GPIO 4  (TFT_RST)
//  - A0/DC -> GPIO 27 (TFT_DC)  <-- Chân A0 (Data/Command)
//  - SDA   -> GPIO 23 (TFT_MOSI)
//  - SCK   -> GPIO 18 (TFT_SCLK)
//  - LED   -> 3.3V
// ============================================================

// ============================================================
//  MÃ MÀU RGB565 — Căn theo thiết kế SVG
//  Card: #252632  Stroke: #383A4A
//  Neon: #00FFAA  Cyan: #00D2FF  Red: #FF4B4B  Orange: #FF512F
// ============================================================
#ifndef TFT_RGB565
#define TFT_RGB565(r, g, b) ((uint16_t)(((uint8_t)(r) & 0xF8) << 8) | (((uint8_t)(g) & 0xFC) << 3) | ((uint8_t)(b) >> 3))
#endif

#define C_BG_TOP       TFT_RGB565( 20,  21,  28)
#define C_BG_BOT       TFT_RGB565( 30,  31,  41)
#define C_CARD         TFT_RGB565( 37,  38,  50)  // #252632 mọi card cùng màu
#define C_STROKE       TFT_RGB565( 56,  58,  74)  // #383A4A
#define C_MUTED        TFT_RGB565(139, 141, 155)  // #8B8D9B
#define C_DARK         TFT_RGB565( 96,  98, 117)  // #606275
#define C_NEON         TFT_RGB565(  0, 255, 170)  // #00FFAA
#define C_CYAN         TFT_RGB565(  0, 210, 255)  // #00D2FF
#define C_RED          TFT_RGB565(255,  75,  75)  // #FF4B4B
#define C_ORANGE       TFT_RGB565(255,  81,  47)  // #FF512F
#define C_PTIT         TFT_RGB565(211,  47,  47)  // #D32F2F logo PTIT
#define C_WHITE        TFT_RGB565(255, 255, 255)
#define C_BLUE_DARK    TFT_RGB565(139,  26,  26)  // #8B1A1A đỏ trung - Patient Node
#define C_GREEN_DARK   TFT_RGB565( 15,  75,  35)  // #0F4B23 xanh lá - Env Card
#define C_PURPLE_DARK  TFT_RGB565( 65,  18,  95)  // #41125F tím - Network Card

// Đối tượng màn hình toàn cục
extern TFT_eSPI tft;

// ============================================================
//  CÁC HÀM KHỞI TẠO VÀ VẼ GIAO DIỆN
// ============================================================

/**
 * @brief Khởi tạo phần cứng màn hình TFT, đặt xoay ngang (160x128)
 *        và vẽ toàn bộ giao diện khởi đầu (gradient, header, cards mẫu).
 */
void GatewayTFT_Init();

/**
 * @brief Vẽ nền dải màu gradient từ trên xuống dưới
 */
void GatewayTFT_DrawBackground();

/**
 * @brief Vẽ khung nền của một card
 */
void GatewayTFT_DrawCard(int x, int y, int w, int h);

/**
 * @brief Vẽ thanh tiêu đề Header (Logo PTIT, GATEWAY, trạng thái Online)
 * @param isOnline true nếu kết nối Gateway hoạt động
 */
void GatewayTFT_DrawHeader(bool isOnline = true);

/**
 * @brief Vẽ thẻ thông tin Patient Node (AI result, nhịp tim, SpO2, thanh pin)
 */
void GatewayTFT_DrawPatientCard(const char *aiResult, int hr, int spo2, int bat);
void GatewayTFT_DrawPatientCard(const String &aiResult, int hr, int spo2, int bat);

/**
 * @brief Vẽ thẻ thông tin môi trường (Nhiệt độ, độ ẩm)
 */
void GatewayTFT_DrawEnvironmentCard(float temp, int hum);

/**
 * @brief Vẽ thẻ trạng thái mạng (WiFi, MQTT, LTE)
 */
void GatewayTFT_DrawNetworkCard(bool wifi, bool mqtt, bool lte);

/**
 * @brief Cập nhật nhanh toàn bộ 3 thẻ trên màn hình với dữ liệu tường minh
 */
void GatewayTFT_Update(const char *aiResult, int hr, int spo2, int bat, float temp, int hum, bool wifi, bool mqtt, bool lte);

/**
 * @brief Tự động trích xuất dữ liệu từ GatewayStateSnapshot và cập nhật giao diện
 * @param state Bản chụp trạng thái tức thời của Gateway
 */
/**
 * @brief Đẩy gói tin tổng hợp (trước khi gửi Cloud) vào hàng đợi hiển thị TFT
 * @param packet Gói tin Complete_Packet_t chứa dữ liệu Gate và Patient Event
 * @return true nếu ghi vào hàng đợi thành công
 */
bool GatewayTFT_PostPacket(const Complete_Packet_t &packet);

/**
 * @brief Trích xuất dữ liệu từ gói packet gửi lên cloud và cập nhật lên màn hình TFT
 * @param packet Gói tin Complete_Packet_t hoàn chỉnh
 */
void GatewayTFT_UpdateFromPacket(const Complete_Packet_t &packet);

/**
 * @brief FreeRTOS task tùy chọn chạy nền định kỳ lấy snapshot và cập nhật TFT
 */
void TaskDisplayTFT(void *parameter);

#endif // NCKH_GATEWAY_TFT_H
