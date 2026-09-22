#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ESP32_DHT11_Lib.h>
#include <WiFiClientSecure.h>

// ==== WIFI ====
const char* ssid = "VNPT HAI YEN";
const char* password = "haiyen2009";

// ==== HIVE MQ ====
const char* mqtt_server = "964dc275c0db4f789a75a75c92a78a33.s1.eu.hivemq.cloud";
const int mqtt_port    = 8883;
const char* mqtt_user  = "Test_DHT11";
const char* mqtt_pass  = "NCKH_node_2026";

const char* mqtt_topic = "nckh/ngocchien/dht11";

WiFiClientSecure espClient;
PubSubClient client(espClient);

void Setup_WiFi(void){
  WiFi.mode(WIFI_STA);
  WiFi.disconnect(true);
  delay(100);

  delay(10);
  Serial.println();
  Serial.print("Đang kết nối với: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nĐã kết nối WiFi thành công!");
  Serial.print("Địa chỉ IP: ");
  Serial.println(WiFi.localIP());
}

void WiFi_Reconnect(void){
  while(! client.connected()){
    Serial.print("Đang kết nối tới HiveMQ Cloud...");
    
    String clientId = "ESP32Client-";
    clientId += String(random(0xffff), HEX);
    
    if (client.connect(clientId.c_str(), mqtt_user, mqtt_pass)) {
      Serial.println(" Thành công!");
    } else {
      Serial.print(" Thất bại, mã lỗi = ");
      Serial.print(client.state());
      Serial.println(" Thử lại sau 5 giây");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  DHT11_Init();
  Setup_WiFi();
  espClient.setInsecure(); 
  client.setServer(mqtt_server, mqtt_port);
  client.setBufferSize(1024); 
}


void loop() {
  // 1. Kiểm tra phần cứng mạng trước tiên
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\nMất kết nối WiFi! Đang thử lại...");
    Setup_WiFi(); // Gọi lại hàm kết nối
  }

  if (!client.connected()) {
    WiFi_Reconnect();
  }
  client.loop();

  // Chu kỳ lấy mẫu: 2 giây 1 lần
  static unsigned long lastMsg = 0;
  unsigned long now = millis();
  
  if (now - lastMsg > 2000) {
    lastMsg = now;

    float temp, humi;
    
    // Đọc dữ liệu từ hàm custom
    uint8_t err = DHT11_ReadData(&temp, &humi);

    if (err == 0) {
        Serial.printf("[OK] Nhiet do: %.1f *C  |  Do am: %.1f %%\n", temp, humi);
        // {"temp": 25.5, "hum": 60.0}
        
        // Đóng gói data thành chuỗi JSON
        String payload = "{\"temp\":";
        payload += String(temp, 1);
        payload += ",\"hum\":";
        payload += String(humi, 1);
        payload += "}";

        // Publish lên Broker
        client.publish(mqtt_topic, payload.c_str());
        Serial.print("Đã Publish lên HiveMQ: ");
        Serial.println(payload);
    } 
    else if (err == 1) {
        Serial.println("[ERR] Loi Timeout - Kiem tra day DHT11 hoac tro keo pull-up!");
    } 
    else if (err == 2) {
        Serial.println("[ERR] Loi Checksum - Nhieu tin hieu tren day DATA!");
    }
  }
}