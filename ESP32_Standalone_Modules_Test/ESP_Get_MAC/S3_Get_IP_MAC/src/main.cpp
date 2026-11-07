#include <WiFi.h>

void setup(){
  Serial0.begin(115200);
  
  // Đợi cổng Serial0 khởi động
  delay(2000);

  // Thiết lập ESP32-S3 ở chế độ Wi-Fi Station
  WiFi.mode(WIFI_STA);
}

void loop(){
  Serial0.println("===================================");
  Serial0.print("Địa chỉ MAC của ESP32-S3 là: ");
  Serial0.println(WiFi.macAddress());
  Serial0.println("===================================");
  
  // Đợi 3 giây rồi in lại
  delay(3000);
}