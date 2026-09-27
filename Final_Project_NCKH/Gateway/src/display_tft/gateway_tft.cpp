#include "Display_TFT/gateway_tft.h"
#include "System/gateway_queue.h"
#include "System/gateway_runtime.h"
#include "Config/gateway_config.h"

// Khởi tạo đối tượng màn hình TFT_eSPI
TFT_eSPI tft = TFT_eSPI();

void GatewayTFT_DrawBackground() {
    for (int y = 0; y < 128; y++) {
        uint8_t r = 20 + (uint8_t)((uint32_t)10 * y / 128);
        uint8_t g = 21 + (uint8_t)((uint32_t)10 * y / 128);
        uint8_t b = 28 + (uint8_t)((uint32_t)13 * y / 128);
        tft.drawFastHLine(0, y, 160, tft.color565(r, g, b));
    }
}

void GatewayTFT_DrawCard(int x, int y, int w, int h) {
    tft.fillRoundRect(x, y, w, h, 5, C_CARD);
    tft.drawRoundRect(x, y, w, h, 5, C_STROKE);
}

void GatewayTFT_DrawHeader(bool isOnline) {
    tft.fillRect(0, 0, 160, 14, tft.color565(14, 15, 22));

    // Logo PTIT
    tft.setTextDatum(TL_DATUM);
    tft.setTextColor(C_WHITE);
    tft.drawString("PTIT", 10, 4, 1);

    // GATEWAY
    tft.drawString("GATEWAY", 70, 4, 1);

    // Trạng thái ONLINE / OFF
    if (isOnline) {
        tft.fillCircle(138, 7, 3, C_NEON);
        tft.setTextColor(C_NEON);
        tft.drawString("ON", 145, 4, 1);
    } else {
        tft.fillCircle(138, 7, 3, C_RED);
        tft.setTextColor(C_RED);
        tft.drawString("OFF", 143, 4, 1);
    }

    // Divider
    tft.drawFastHLine(5, 14, 150, C_STROKE);
}

void GatewayTFT_DrawPatientCard(const char *aiResult, int hr, int spo2, int bat) {
    const int cx = 2, cy = 18, cw = 88, ch = 106;
    
    // Nền card riêng cho Patient Node
    tft.fillRoundRect(cx, cy, cw, ch, 5, C_BLUE_DARK);
    tft.drawRoundRect(cx, cy, cw, ch, 5, C_STROKE);

    // Tiêu đề card + chấm tín hiệu kết nối
    tft.setTextDatum(TL_DATUM);
    tft.setTextColor(C_WHITE);
    tft.drawString("NODE", cx + 32, cy + 5, 1);
    tft.fillCircle(cx + cw - 9, cy + 9, 3, C_NEON);

    tft.drawFastHLine(cx + 3, cy + 16, cw - 6, C_STROKE);

    // Kết quả phân loại AI
    bool isAsthma = (aiResult != nullptr && strcmp(aiResult, "ASTHMA") == 0);
    tft.setTextDatum(TC_DATUM);
    tft.setTextColor(isAsthma ? C_NEON : C_CYAN);
    tft.drawString(aiResult ? aiResult : "--", cx + cw / 2, cy + 23, 2);

    // Nhịp tim Heart Rate
    tft.setTextDatum(TL_DATUM);
    tft.setTextColor(C_WHITE);
    tft.drawString("HR:", cx + 4, cy + 45, 1);
    tft.setTextDatum(TR_DATUM);
    if (hr > 0) {
        tft.drawString(String(hr) + " bpm", cx + cw - 3, cy + 45, 1);
    } else {
        tft.drawString("--", cx + cw - 3, cy + 45, 1);
    }

    // Nồng độ Oxy SpO2
    tft.setTextDatum(TL_DATUM);
    tft.setTextColor(C_WHITE);
    tft.drawString("SpO2:", cx + 4, cy + 59, 1);
    tft.setTextDatum(TR_DATUM);
    if (spo2 > 0) {
        tft.drawString(String(spo2) + "%", cx + cw - 3, cy + 59, 1);
    } else {
        tft.drawString("--", cx + cw - 3, cy + 59, 1);
    }

    // Nhãn cập nhật & pin
    tft.setTextDatum(TL_DATUM);
    tft.setTextColor(C_WHITE);
    tft.drawString("Updated:", cx + 4, cy + 73, 1);

    uint16_t bc = (bat >= 50) ? C_WHITE
                : (bat >= 20) ? tft.color565(255, 220, 30)
                              : C_RED;
    tft.drawString("Bat: ", cx + 4, cy + 85, 1);
    tft.setTextColor(bc);
    tft.drawString(String(bat) + "%", cx + 28, cy + 85, 1);

    // Thanh đo pin đồ họa
    int bx = cx + 4, by = cy + 96, bw = cw - 10, bh = 6;
    int clampedBat = constrain(bat, 0, 100);
    int fw = (int)((long)bw * clampedBat / 100);
    tft.fillRect(bx, by, bw, bh, tft.color565(28, 30, 42));
    if (fw > 0) {
        tft.fillRect(bx, by, fw, bh, bc);
    }
    tft.drawRect(bx, by, bw, bh, C_STROKE);
    tft.fillRect(bx + bw, by + 2, 2, bh - 4, C_STROKE);
}

void GatewayTFT_DrawPatientCard(const String &aiResult, int hr, int spo2, int bat) {
    GatewayTFT_DrawPatientCard(aiResult.c_str(), hr, spo2, bat);
}

void GatewayTFT_DrawEnvironmentCard(float temp, int hum) {
    const int cx = 92, cy = 18, cw = 66, ch = 51;
    
    // Nền card riêng cho môi trường
    tft.fillRoundRect(cx, cy, cw, ch, 5, C_GREEN_DARK);
    tft.drawRoundRect(cx, cy, cw, ch, 5, C_STROKE);

    // Nhãn ENV
    tft.setTextDatum(TC_DATUM);
    tft.setTextColor(C_WHITE);
    tft.drawString("ENV", cx + cw / 2, cy + 3, 1);

    tft.drawFastVLine(cx + cw / 2 + 3, cy + 13, ch - 15, C_STROKE);

    // Nhiệt độ bên trái
    tft.setTextDatum(TC_DATUM);
    tft.setTextColor(C_CYAN);
    tft.drawString(String(temp, 1), cx + cw / 4 - 1, cy + 24, 2);

    // Ký hiệu °C
    int degX = cx + cw / 2 - 8;
    int degY = cy + 17;
    tft.drawCircle(degX, degY, 2, C_CYAN);
    tft.setTextDatum(TL_DATUM);
    tft.setTextColor(C_CYAN);
    tft.drawString("C", degX + 5, degY - 1, 1);

    tft.setTextDatum(TC_DATUM);
    tft.setTextColor(C_WHITE);
    tft.drawString("TEMP", cx + cw / 4, cy + 40, 1);

    // Độ ẩm bên phải
    tft.setTextColor(C_CYAN);
    tft.drawString(String(hum) + "%", cx + cw * 3 / 4, cy + 24, 2);
    tft.setTextColor(C_WHITE);
    tft.drawString("HUM", cx + cw * 3 / 4, cy + 40, 1);
}

void GatewayTFT_DrawNetworkCard(bool wifi, bool mqtt, bool lte) {
    const int cx = 92, cy = 73, cw = 66, ch = 63;
    
    // Nền tím đậm riêng cho Network card
    tft.fillRoundRect(cx, cy, cw, ch, 5, C_PURPLE_DARK);
    tft.drawRoundRect(cx, cy, cw, ch, 5, C_STROKE);

    // Tiêu đề NETWORK
    tft.setTextDatum(TL_DATUM);
    tft.setTextColor(C_WHITE);
    tft.drawString("NETWORK", cx + 12, cy + 3, 1);
    tft.drawFastHLine(cx + 3, cy + 12, cw - 6, C_STROKE);

    // Dòng 1: WiFi
    const int r1y = cy + 22;
    if (wifi) tft.fillCircle(cx + 8, r1y, 4, C_NEON);
    else      tft.drawCircle(cx + 8, r1y, 4, C_DARK);
    tft.setTextDatum(TL_DATUM);
    tft.setTextColor(C_WHITE);
    tft.drawString("WiFi", cx + 17, r1y - 4, 1);

    // Dòng 2: MQTT
    const int r2y = cy + 37;
    if (mqtt) tft.fillCircle(cx + 8, r2y - 2, 4, C_NEON);
    else      tft.drawCircle(cx + 8, r2y - 2, 4, C_DARK);
    tft.setTextColor(C_WHITE);
    tft.drawString("MQTT", cx + 17, r2y - 6, 1);

    // Dòng 3: LTE
    const int r3y = cy + 52;
    if (lte) tft.fillCircle(cx + 8, r3y - 4, 4, C_NEON);
    else     tft.drawCircle(cx + 8, r3y - 4, 3, C_DARK);
    tft.setTextColor(C_WHITE);
    tft.drawString("LTE", cx + 17, r3y - 8, 1);
}

void GatewayTFT_Init() {
    tft.init();
    tft.setRotation(1);  // Landscape 160x128
    
    GatewayTFT_DrawBackground();
    GatewayTFT_DrawHeader(true);
    GatewayTFT_DrawPatientCard("NO NODE", 0, 0, 0);
    GatewayTFT_DrawEnvironmentCard(0.0f, 0);
    GatewayTFT_DrawNetworkCard(false, false, false);
}

// Lưu trữ dữ liệu bệnh nhân gần nhất để duy trì hiển thị khi gói tin telemetry định kỳ không chứa sự kiện bệnh nhân
static char s_lastAiResult[16] = "WAITING";
static int s_lastHr = 0;
static int s_lastSpo2 = 0;
static int s_lastBat = 0;
static bool s_hasPatientData = false;

void GatewayTFT_Update(const char *aiResult, int hr, int spo2, int bat, float temp, int hum, bool wifi, bool mqtt, bool lte) {
    static int s_lastOnline = -1;
    int currentOnline = (wifi || lte) ? 1 : 0;
    if (currentOnline != s_lastOnline) {
        GatewayTFT_DrawHeader(currentOnline == 1);
        s_lastOnline = currentOnline;
    }
    GatewayTFT_DrawPatientCard(aiResult, hr, spo2, bat);
    GatewayTFT_DrawEnvironmentCard(temp, hum);
    GatewayTFT_DrawNetworkCard(wifi, mqtt, lte);
}

bool GatewayTFT_PostPacket(const Complete_Packet_t &packet) {
    if (!displayQueue) return false;
    return (xQueueOverwrite(displayQueue, &packet) == pdPASS);
}

void GatewayTFT_UpdateFromPacket(const Complete_Packet_t &packet) {
    if (packet.has_patient_event) {
        s_lastHr = packet.patient_event.heart_rate;
        s_lastSpo2 = packet.patient_event.spo2;
        s_lastBat = packet.patient_event.battery_node;
        if (packet.patient_event.classification == 1) {
            strncpy(s_lastAiResult, "ASTHMA", sizeof(s_lastAiResult) - 1);
        } else {
            strncpy(s_lastAiResult, "NON-ASTHMA", sizeof(s_lastAiResult) - 1);
        }
        s_lastAiResult[sizeof(s_lastAiResult) - 1] = '\0';
        s_hasPatientData = true;
    }

    float temp = packet.gate.temperature;
    int hum = (int)packet.gate.humidity;

    bool wifi = (packet.gate.wifi_connected != 0);
    bool mqtt = (packet.gate.mqtt_connected != 0);
    bool lte = (packet.gate.lte_registered != 0) || 
               (packet.gate.uplink_type == GATE_UPLINK_LTE);

    GatewayTFT_Update(s_hasPatientData ? s_lastAiResult : "WAITING",
                      s_lastHr, s_lastSpo2, s_lastBat,
                      temp, hum, wifi, mqtt, lte);
}

void GatewayTFT_UpdateFromSnapshot(const GatewayStateSnapshot &state) {
    // Trích xuất dữ liệu bệnh nhân nếu có
    if (state.current_node_valid) {
        s_lastHr = state.current_node.payload.heart_rate;
        s_lastSpo2 = state.current_node.payload.spo2;
        s_lastBat = state.current_node.payload.battery_node;
        if (state.current_node.payload.classification == 1) {
            strncpy(s_lastAiResult, "ASTHMA", sizeof(s_lastAiResult) - 1);
        } else {
            strncpy(s_lastAiResult, "NON-ASTHMA", sizeof(s_lastAiResult) - 1);
        }
        s_lastAiResult[sizeof(s_lastAiResult) - 1] = '\0';
        s_hasPatientData = true;
    }

    // Trích xuất dữ liệu môi trường từ Gateway
    float temp = 0.0f;
    int hum = 0;
    if (state.current_gate_valid) {
        temp = state.current_gate.temperature;
        hum = (int)state.current_gate.humidity;
    }

    // Trích xuất trạng thái kết nối mạng
    bool wifi = false;
    bool mqtt = false;
    bool lte = false;
    if (state.current_gate_valid) {
        wifi = (state.current_gate.wifi_connected != 0);
        mqtt = (state.current_gate.mqtt_connected != 0);
        lte = (state.current_gate.lte_registered != 0) || 
              (state.current_gate.uplink_type == GATE_UPLINK_LTE);
    }

    // Cập nhật lên màn hình
    GatewayTFT_Update(s_hasPatientData ? s_lastAiResult : "WAITING",
                      s_lastHr, s_lastSpo2, s_lastBat,
                      temp, hum, wifi, mqtt, lte);
}

void TaskDisplayTFT(void *parameter) {
    (void)parameter;
    GatewayWatchdogJoin();
    GatewayTFT_Init();
    Serial.println("[Display] TaskDisplayTFT started, waiting for cloud packets...");

    Complete_Packet_t packet{};
    for (;;) {
        GatewayWatchdogFeed();
        // Nhận gói tin Complete_Packet_t từ TaskMqttPublisher (được gửi ngay trước khi tuần tự hóa JSON và gửi MQTT)
        if (displayQueue && xQueueReceive(displayQueue, &packet, pdMS_TO_TICKS(GATEWAY_DISPLAY_PERIOD_MS)) == pdTRUE) {
            GatewayTFT_UpdateFromPacket(packet);
        } else {
            // Fallback: Khi chưa có gói cloud (lúc khởi động hoặc khi mất kết nối mạng), cập nhật từ snapshot
            GatewayStateSnapshot snapshot{};
            if (GatewayState_GetSnapshot(&snapshot)) {
                GatewayTFT_UpdateFromSnapshot(snapshot);
            }
        }
    }
}
