#include <WiFi.h>

void setup(){
  Serial.begin(115200);
  
  // Đợi cổng Serial0 khởi động
  delay(2000);

  // Thiết lập ESP32-S3 ở chế độ Wi-Fi Station
  WiFi.mode(WIFI_STA);
}

void loop(){
  Serial.println("===================================");
  Serial.print("Địa chỉ MAC của ESP32-S3 là: ");
  Serial.println(WiFi.macAddress());
  Serial.println("===================================");
  
  // Đợi 3 giây rồi in lại
  delay(3000);
}