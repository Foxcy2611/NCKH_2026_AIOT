#include <Arduino.h>
#include <ESP32_BMP280_Lib.h>
#include <ESP32_SSD1306_Display.h>

void setup(){
  Wire.begin();
  
  OLED_TestSetup();
}

void loop(){
  
}