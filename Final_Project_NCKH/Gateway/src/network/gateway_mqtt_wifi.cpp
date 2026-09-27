#include "Network/gateway_mqtt_wifi.h"
#include "Network/gateway_wifi.h"
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <time.h>
namespace {
WiFiClientSecure tlsClient;
PubSubClient mqttClient(tlsClient);
char clientId[40];
}
bool MQTT_WIFI_Init() {
#if !GATEWAY_NETWORK_CONFIGURED
    Serial.println("[MQTT] disabled: network credentials are not configured");
    return false;
#endif
#if GATEWAY_TLS_INSECURE
    tlsClient.setInsecure();
    Serial.println("[MQTT] TEST TLS: server certificate verification disabled");
#else
    if (!GATEWAY_MQTT_CA[0]) { Serial.println("[MQTT] missing CA certificate"); return false; }
    tlsClient.setCACert(GATEWAY_MQTT_CA);
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");
#endif
    tlsClient.setHandshakeTimeout(5);
    tlsClient.setTimeout(3); // Arduino-ESP32 2.0.17 takes SECONDS here.
    mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
    mqttClient.setSocketTimeout(3);
    mqttClient.setKeepAlive(30);
    snprintf(clientId, sizeof(clientId), "gateway-%012llx", (unsigned long long)ESP.getEfuseMac());
    return mqttClient.setBufferSize(GATEWAY_MQTT_BUFFER_SIZE);
}
bool MQTT_WIFI_Connect() {
    if (!WiFi_IsConnected()) return false;
#if !GATEWAY_TLS_INSECURE
    if (time(nullptr) < 1700000000) return false;
#endif
    bool ok = mqttClient.connect(clientId, MQTT_USERNAME, MQTT_PASSWORD);
    Serial.printf("[MQTT] connected=%u state=%d client=%s\n", ok, mqttClient.state(), clientId);
    return ok;
}
bool MQTT_WIFI_IsConnected() { return mqttClient.connected(); }
bool MQTT_WIFI_Loop() { return mqttClient.loop(); }
void MQTT_WIFI_Disconnect() { mqttClient.disconnect(); tlsClient.stop(); }
bool MQTT_WIFI_Publish(const char *topic, const char *payload) {
    return topic && payload && mqttClient.connected() && mqttClient.publish(topic, payload, false);
}
