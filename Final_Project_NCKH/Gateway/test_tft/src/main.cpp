#include <Arduino.h>
#include <SPI.h>
#include <TFT_eSPI.h>

TFT_eSPI tft = TFT_eSPI();

// ============================================================
//  MÃ MÀU — căn theo SVG gốc (#14151C → #1E1F29 gradient)
//  Card: #252632  Stroke: #383A4A  (tất cả card cùng màu)
//  Neon: #00FFAA  Cyan: #00D2FF  Red: #FF4B4B  Orange: #FF512F
// ============================================================
#define C_BG_TOP  tft.color565( 20,  21,  28)
#define C_BG_BOT  tft.color565( 30,  31,  41)
#define C_CARD    tft.color565( 37,  38,  50)  // #252632 mọi card cùng màu
#define C_STROKE  tft.color565( 56,  58,  74)  // #383A4A
#define C_MUTED   tft.color565(139, 141, 155)  // #8B8D9B
#define C_DARK    tft.color565( 96,  98, 117)  // #606275
#define C_NEON    tft.color565(  0, 255, 170)  // #00FFAA
#define C_CYAN    tft.color565(  0, 210, 255)  // #00D2FF
#define C_RED     tft.color565(255,  75,  75)  // #FF4B4B
#define C_ORANGE  tft.color565(255,  81,  47)  // #FF512F
#define C_PTIT    tft.color565(211,  47,  47)  // #D32F2F logo PTIT
#define C_WHITE       tft.color565(255, 255, 255)
#define C_BLUE_DARK   tft.color565(139,  26,  26)  // #8B1A1A đỏ trung        – Patient Node
#define C_GREEN_DARK  tft.color565( 15,  75,  35)  // #0F4B23 xanh lá        – Env Card
#define C_PURPLE_DARK tft.color565( 65,  18,  95)  // #41125F tím             – Network Card

unsigned long lastUpdate    = 0;
const unsigned long UPD_INT = 5000;

// ──────────────────────────────────────────────────────────
//  Gradient nền (SVG: #14151C to #1E1F29)
// ──────────────────────────────────────────────────────────
void drawBackgroundGradient() {
  for (int y = 0; y < 128; y++) {
    uint8_t r = 20 + (uint8_t)((uint32_t)10 * y / 128);
    uint8_t g = 21 + (uint8_t)((uint32_t)10 * y / 128);
    uint8_t b = 28 + (uint8_t)((uint32_t)13 * y / 128);
    tft.drawFastHLine(0, y, 160, tft.color565(r, g, b));
  }
}

// ──────────────────────────────────────────────────────────
//  Vẽ card (tất cả cùng 1 màu nền theo SVG)
// ──────────────────────────────────────────────────────────
void drawCard(int x, int y, int w, int h) {
  tft.fillRoundRect(x, y, w, h, 5, C_CARD);
  tft.drawRoundRect(x, y, w, h, 5, C_STROKE);
}

// ──────────────────────────────────────────────────────────
//  HEADER  (SVG: PTIT red circle, GATEWAY text, ONLINE dot)
//  Scale 320→160: circle cx=22→11  GATEWAY x=180→44  ONLINE cx=255→128
// ──────────────────────────────────────────────────────────
void drawHeader() {
  tft.fillRect(0, 0, 160, 14, tft.color565(14, 15, 22));

  // PTIT logo: vòng tròn đỏ + chữ PTIT (SVG: circle cx=22 cy=15 r=11)
  
  tft.setTextColor(C_WHITE);
  tft.drawString("PTIT", 10, 4, 1);

  // GATEWAY (dịch phải gần ONLINE hơn)
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(C_WHITE);
  tft.drawString("GATEWAY", 70, 4, 1);

  // ONLINE: chấm neon + chữ (SVG: circle cx=255→128, text x=265→133)
  tft.fillCircle(138, 7, 3, C_NEON);
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(C_NEON);
  tft.drawString("ON", 145, 4, 1);

  // Divider (SVG: line y=28 → scale y=14)
  tft.drawFastHLine(5, 14, 150, C_STROKE);
}

// ──────────────────────────────────────────────────────────
//  PATIENT CARD  x=2, y=18, w=88, h=106
//  SVG: "PATIENT NODE" + CONN dot, AI result centered,
//       Heart Rate, SpO2, Updated / Bat
// ──────────────────────────────────────────────────────────
void drawPatientCard(String aiResult, int hr, int spo2, int bat) {
  const int cx = 2, cy = 18, cw = 88, ch = 106;
  // Nền xanh navy đậm riêng cho Patient Node card
  tft.fillRoundRect(cx, cy, cw, ch, 5, C_BLUE_DARK);
  tft.drawRoundRect(cx, cy, cw, ch, 5, C_STROKE);

  // "PATIENT NODE" label + chấm CONN (SVG: text x=22, circle cx=115)
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(C_WHITE);
  tft.drawString("NODE", cx + 32, cy + 5, 1);
  tft.fillCircle(cx + cw - 9, cy + 9, 3, C_NEON);

  tft.drawFastHLine(cx + 3, cy + 16, cw - 6, C_STROKE);

  // Kết quả AI — Font 2, nét chuẩn, KHÔNG vẽ đè, KHÔNG in đậm
  bool asthma = (aiResult == "ASTHMA");
  tft.setTextDatum(TC_DATUM);
  tft.setTextColor(asthma ? C_NEON : C_CYAN);
  tft.drawString(aiResult, cx + cw / 2, cy + 23, 2);


  // Heart Rate (SVG: "Heart Rate:" muted + "82 bpm" red)
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(C_WHITE);
  tft.drawString("HR:", cx + 4, cy + 45, 1);
  tft.setTextDatum(TR_DATUM);
  tft.setTextColor(C_WHITE);
  tft.drawString(String(hr) + " bpm", cx + cw - 3, cy + 45, 1);


  // SpO2 
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(C_WHITE);
  tft.drawString("SpO2:", cx + 4, cy + 59, 1);
  tft.setTextDatum(TR_DATUM);
  tft.setTextColor(C_WHITE);
  tft.drawString(String(spo2) + "%", cx + cw - 3, cy + 59, 1);


  // Updated — dòng 1
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(C_WHITE);
  tft.drawString("Updated:", cx + 4, cy + 73, 1);

  // Bat — dòng 2 (tách riêng để không đè lên Updated)
  uint16_t bc = (bat >= 50) ? C_WHITE
              : (bat >= 20) ? tft.color565(255, 220, 30)
                            : C_RED;
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(C_WHITE);
  tft.drawString("Bat: ", cx + 4, cy + 85, 1);
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(bc);
  tft.drawString(String(bat) + "%", cx + 28, cy + 85, 1);  // giá trị pin giữ màu theo mức

  // Thanh pin đồ họa — dịch xuống theo chữ Bat
  int bx = cx + 4, by = cy + 96, bw = cw - 10, bh = 6;
  int fw = (int)((long)bw * bat / 100);
  tft.fillRect(bx, by, bw, bh, tft.color565(28, 30, 42));
  tft.fillRect(bx, by, fw,  bh, bc);
  tft.drawRect(bx, by, bw, bh, C_STROKE);
  tft.fillRect(bx + bw, by + 2, 2, bh - 4, C_STROKE);  // chóp pin
}

// ──────────────────────────────────────────────────────────
//  ENVIRONMENT CARD  x=92, y=18, w=66, h=51
//  SVG: "ENVIRONMENT", temp °C (orange) | vertical | hum% (cyan)
// ──────────────────────────────────────────────────────────
void drawEnvironmentCard(float temp, int hum) {
  const int cx = 92, cy = 18, cw = 66, ch = 51;
  // Nền xanh lá đậm riêng cho Environment card
  tft.fillRoundRect(cx, cy, cw, ch, 5, C_GREEN_DARK);
  tft.drawRoundRect(cx, cy, cw, ch, 5, C_STROKE);

  // "ENV" label
  tft.setTextDatum(TC_DATUM);
  tft.setTextColor(C_WHITE);
  tft.drawString("ENV", cx + cw / 2, cy + 3, 1);

  tft.drawFastVLine(cx + cw / 2 + 3, cy + 13, ch - 15, C_STROKE);

  // Nhiệt độ (trái) — Font 2, cam (SVG: #FF512F)
  tft.setTextDatum(TC_DATUM);
  tft.setTextColor(C_CYAN);
  tft.drawString(String(temp, 1), cx + cw / 4 -1, cy + 24, 2);

  // Ký hiệu °C — X cách xa số để KHÔNG dính vào số
  int degX = cx + cw / 2 - 8;  // offset đủ xa
  int degY = cy + 17;
  tft.drawCircle(degX, degY, 2, C_CYAN);       // vòng tròn °
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(C_CYAN);
  tft.drawString("C", degX + 5, degY - 1, 1);   // chữ C cách °

  tft.setTextDatum(TC_DATUM);
  tft.setTextColor(C_WHITE);
  tft.drawString("TEMP", cx + cw / 4, cy + 40, 1);

  // Độ ẩm (phải) — Font 2, cyan (SVG: #00D2FF)
  tft.setTextColor(C_CYAN);
  tft.drawString(String(hum) + "%", cx + cw * 3 / 4, cy + 24, 2);
  tft.setTextColor(C_WHITE);
  tft.drawString("HUM", cx + cw * 3 / 4, cy + 40, 1);
}

// ──────────────────────────────────────────────────────────
//  NETWORK CARD  x=92, y=73, w=66, h=51
//  SVG: WiFi(trái) + MQTT(phải) cùng hàng, LTE hàng 2
//       WiFi filled=neon, MQTT filled=neon, LTE outline=gray khi off
// ──────────────────────────────────────────────────────────
void drawNetworkCard(bool wifi, bool mqtt, bool lte) {
  const int cx = 92, cy = 73, cw = 66, ch = 63;
  // Nền tím đậm riêng cho Network card
  tft.fillRoundRect(cx, cy, cw, ch, 5, C_PURPLE_DARK);
  tft.drawRoundRect(cx, cy, cw, ch, 5, C_STROKE);

  // "NETWORK"
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(C_WHITE);
  tft.drawString("NETWORK", cx + 12, cy + 3, 1);
  tft.drawFastHLine(cx + 3, cy + 12, cw - 6, C_STROKE);

  // Hàng 1: WiFi
  const int r1y = cy + 22;
  if (wifi) tft.fillCircle(cx + 8, r1y, 4, C_NEON);
  else      tft.drawCircle(cx + 8, r1y, 4, C_DARK);
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(C_WHITE);
  tft.drawString("WiFi", cx + 17, r1y - 4, 1);

  // Hàng 2: MQTT
  const int r2y = cy + 37;
  if (mqtt) tft.fillCircle(cx + 8, r2y - 2, 4, C_NEON);
  else      tft.drawCircle(cx + 8, r2y - 2, 4, C_DARK);
  tft.setTextColor(C_WHITE);
  tft.drawString("MQTT", cx + 17, r2y - 6, 1);

  // Hàng 3: LTE
  const int r3y = cy + 52;
  if (lte) tft.fillCircle(cx + 8, r3y-4, 4, C_NEON);
  else     tft.drawCircle(cx + 8, r3y-4, 3, C_DARK);
  tft.setTextColor(C_WHITE);
  tft.drawString("LTE", cx + 17, r3y - 8, 1);
}

// ──────────────────────────────────────────────────────────
//  SETUP
// ──────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  tft.init();
  tft.setRotation(1);  // Landscape 160x128

  drawBackgroundGradient();
  drawHeader();
  drawPatientCard("NON-ASTHMA", 82, 98, 85);
  drawEnvironmentCard(28.4, 71);
  drawNetworkCard(true, true, false);
}

// ──────────────────────────────────────────────────────────
//  LOOP
// ──────────────────────────────────────────────────────────
void loop() {
  unsigned long now = millis();
  if (now - lastUpdate >= UPD_INT) {
    lastUpdate = now;

    static bool isAsthma = false;
    isAsthma = !isAsthma;

    // Patient Card
    tft.fillRoundRect(2,  18, 88, 106, 5, C_BLUE_DARK);  // giữ màu navy cho Patient Node
    if (isAsthma) drawPatientCard("ASTHMA",     112, 90, 84);
    else          drawPatientCard("NON-ASTHMA",  82, 98, 85);

    // Environment Card
    tft.fillRoundRect(92, 18, 66, 51, 5, C_GREEN_DARK);
    drawEnvironmentCard(28.4, 71);

    // Network Card
    tft.fillRoundRect(92, 73, 66, 63, 5, C_PURPLE_DARK);
    drawNetworkCard(true, true, false);
  }
}
