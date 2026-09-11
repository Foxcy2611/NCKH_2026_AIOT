#include "ESP32_SSD1306_Display.h"

void setup() {
    Serial.begin(115200);
    
    // Khởi tạo chân I2C cho mạch ESP32
    Wire.begin(21, 22); 
    
    // Khởi tạo màn hình
    OLED_Init();
}

void loop() {
    
   OLED_Show_AI_Result(true);
   delay(1000);
   OLED_Show_PlaceFinger();

}
