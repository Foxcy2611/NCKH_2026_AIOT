#include "ESP32_SSD1306_Display.h"

void setup() {
    Serial.begin(115200);
    
    // Khởi tạo chân I2C cho mạch ESP32
    Wire.begin(21, 22); 
    
    // Khởi tạo màn hình
    OLED_Init();
}

void loop() {
   // Hiển thị màn hình Unknown
OLED_Show_ReplyOK();
delay(3000); // Giữ màn hình trong 3 giây
// Hoặc kết quả cuối cùng là Unknown
OLED_Show_NoReply(); 
delay(3000); // Giữ màn hình trong 3 giây
    

}
