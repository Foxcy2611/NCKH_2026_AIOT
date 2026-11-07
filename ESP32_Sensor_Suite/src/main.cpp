/*
 * Chương trình chạy thử RIÊNG LẺ từng mô-đun trong ESP32_Sensor_Suite.
 *
 * Chọn đúng một mô-đun bằng SENSOR_SUITE_MODULE trong platformio.ini, sau đó
 * build/upload và mở Serial Monitor 115200 baud. Driver cảm biến vẫn nằm trong
 * include/ và src/; file này chỉ ghép API của driver thành ví dụ sử dụng tối thiểu.
 */

#include <Arduino.h>

#define MODULE_BMP280    1
#define MODULE_DHT22     2
#define MODULE_MAX30102  3
#define MODULE_MLX90614  4
#define MODULE_NEO_M8N   5
#define MODULE_SGP30     6
#define MODULE_SSD1306   7
#define MODULE_A7680C    8
#define MODULE_ST7735    9

#ifndef SENSOR_SUITE_MODULE
#define SENSOR_SUITE_MODULE MODULE_SSD1306
#endif

#if SENSOR_SUITE_MODULE == MODULE_BMP280
#include <ESP32_BMP280_Lib.h>
#elif SENSOR_SUITE_MODULE == MODULE_DHT22
#include <ESP32_DHT22_Lib.h>
#elif SENSOR_SUITE_MODULE == MODULE_MAX30102
#include <ESP32_MAX30102_Lib.h>
#elif SENSOR_SUITE_MODULE == MODULE_MLX90614
#include <ESP32_MLX90614_Driver.h>
#include <Wire.h>
#elif SENSOR_SUITE_MODULE == MODULE_NEO_M8N
#include <ESP32_NEO_M8N_GPS.h>
#elif SENSOR_SUITE_MODULE == MODULE_SGP30
#include <ESP32_SGP30_Lib.h>
#include <Wire.h>
#elif SENSOR_SUITE_MODULE == MODULE_SSD1306
#include <ESP32_SSD1306_Display.h>
#include <Wire.h>
#elif SENSOR_SUITE_MODULE == MODULE_A7680C
#include <ESP32_A7680C_AT.h>
#elif SENSOR_SUITE_MODULE == MODULE_ST7735
#include <ESP32_ST7735.h>
#else
#error "SENSOR_SUITE_MODULE không hợp lệ; chọn giá trị từ 1 đến 9."
#endif

namespace {

const char *ModuleName() {
#if SENSOR_SUITE_MODULE == MODULE_BMP280
    return "BMP280";
#elif SENSOR_SUITE_MODULE == MODULE_DHT22
    return "DHT22";
#elif SENSOR_SUITE_MODULE == MODULE_MAX30102
    return "MAX30102";
#elif SENSOR_SUITE_MODULE == MODULE_MLX90614
    return "MLX90614";
#elif SENSOR_SUITE_MODULE == MODULE_NEO_M8N
    return "NEO-M8N";
#elif SENSOR_SUITE_MODULE == MODULE_SGP30
    return "SGP30";
#elif SENSOR_SUITE_MODULE == MODULE_SSD1306
    return "SSD1306";
#elif SENSOR_SUITE_MODULE == MODULE_A7680C
    return "A7680C";
#else
    return "ST7735";
#endif
}

#if SENSOR_SUITE_MODULE == MODULE_A7680C
uint32_t lastA7680CheckMs = 0;
#endif

}  // namespace

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.printf("\n[SUITE] Chạy thử độc lập: %s\n", ModuleName());

#if SENSOR_SUITE_MODULE == MODULE_BMP280
    BMP280_TestSetup();
#elif SENSOR_SUITE_MODULE == MODULE_DHT22
    DHT22_Init();
    Serial.println("[DHT22] Đã cấu hình chân DATA; bắt đầu đọc mỗi 2,5 giây.");
#elif SENSOR_SUITE_MODULE == MODULE_MAX30102
    MAX30102_TestSetup();
#elif SENSOR_SUITE_MODULE == MODULE_MLX90614
    Wire.begin();
    MLX90614_TestSetup();
#elif SENSOR_SUITE_MODULE == MODULE_NEO_M8N
    NEO_M8N_TestSetup();
#elif SENSOR_SUITE_MODULE == MODULE_SGP30
    Wire.begin();
    SGP30_TestSetup();
#elif SENSOR_SUITE_MODULE == MODULE_SSD1306
    Wire.begin();
    OLED_TestSetup();
#elif SENSOR_SUITE_MODULE == MODULE_A7680C
    const bool ok = A7680C_InitAndDiagnose(
        Serial2, SIM_RX_PIN, SIM_TX_PIN, 115200);
    Serial.println(ok
        ? "[A7680C] Khởi tạo và chẩn đoán thành công."
        : "[A7680C] Khởi tạo thất bại; kiểm tra nguồn, UART, SIM và anten.");
#elif SENSOR_SUITE_MODULE == MODULE_ST7735
    ST7735_Init();
    ST7735_FillScreen(RGB_BLACK);
    ST7735_DrawRect(8, 8, 144, 112, RGB_CYAN);
    ST7735_FillCircle(80, 64, 24, RGB_GREEN);
    Serial.println("[ST7735] Đã vẽ khung và hình tròn kiểm tra.");
#endif
}

void loop() {
#if SENSOR_SUITE_MODULE == MODULE_BMP280
    BMP280_TestLoop();
    delay(1000);
#elif SENSOR_SUITE_MODULE == MODULE_DHT22
    DHT22_TestMain();
    delay(2500);  // DHT22 không nên được đọc dồn dập.
#elif SENSOR_SUITE_MODULE == MODULE_MAX30102
    MAX30102_TestLoop();
#elif SENSOR_SUITE_MODULE == MODULE_MLX90614
    MLX90614_TestLoop();
#elif SENSOR_SUITE_MODULE == MODULE_NEO_M8N
    NEO_M8N_TestLoop();
#elif SENSOR_SUITE_MODULE == MODULE_SGP30
    SGP30_TestLoop();  // Driver tự giữ chu kỳ đo đúng 1 giây.
#elif SENSOR_SUITE_MODULE == MODULE_SSD1306
    delay(1000);  // Ảnh kiểm tra tĩnh đã được vẽ trong setup().
#elif SENSOR_SUITE_MODULE == MODULE_A7680C
    if (millis() - lastA7680CheckMs >= 10000U) {
        lastA7680CheckMs = millis();
        const bool alive = A7680C_CheckAlive();
        const bool simReady = alive && A7680C_CheckSIM();
        const bool network = simReady && A7680C_CheckNetwork();
        const int signal = alive ? A7680C_GetSignalQuality() : -1;
        Serial.printf(
            "[A7680C] AT=%s | SIM=%s | NET=%s | CSQ=%d\n",
            alive ? "OK" : "FAIL",
            simReady ? "READY" : "FAIL",
            network ? "REGISTERED" : "WAIT",
            signal);
    }
    delay(10);
#elif SENSOR_SUITE_MODULE == MODULE_ST7735
    delay(1000);  // Hình kiểm tra tĩnh đã được vẽ trong setup().
#endif
}
