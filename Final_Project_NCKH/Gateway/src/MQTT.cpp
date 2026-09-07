#include "MQTT.h"

#include <WiFiClientSecure.h>
#include <PubSubClient.h>

// =============================
// MQTT objects
// =============================

WiFiClientSecure espClient;
PubSubClient mqttClient(espClient);

void MQTT_Init()
{
    // TLS client
    espClient.setInsecure();

    // MQTT broker
    mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
    mqttClient.setBufferSize(1024);     // lựa chọn kích thước phù hợp cho dữ liệu cần gửi
}

void MQTT_Connect()
{
    Serial.println("Connecting to MQTT broker...");

    if (mqttClient.connect(MQTT_CLIENT_ID,
                           MQTT_USERNAME,
                           MQTT_PASSWORD))
    {
        Serial.println("MQTT connected!");
    }
    else
    {
        Serial.print("MQTT connection failed, state = ");
        Serial.println(mqttClient.state());
    }
}

bool MQTT_IsConnected()
{
    return mqttClient.connected();
}

bool MQTT_Loop()
{
    return mqttClient.loop();
}

void MQTT_Disconnect()
{
    mqttClient.disconnect();
}

void MQTT_Reconnect()
{
    static unsigned long lastAttempt = 0;

    // Chỉ thử reconnect mỗi 5 giây
    if (millis() - lastAttempt < 5000)
    {
        return;
    }

    lastAttempt = millis();

    Serial.println("MQTT disconnected. Trying to reconnect...");

    if (mqttClient.connect(MQTT_CLIENT_ID,
                           MQTT_USERNAME,
                           MQTT_PASSWORD))
    {
        Serial.println("MQTT reconnected!");
    }
    else
    {
        Serial.print("MQTT reconnect failed, state = ");
        Serial.println(mqttClient.state());
    }
}

bool MQTT_Publish(const char* topic, const char* payload)
{
    if (!mqttClient.connected())
    {
        return false;
    }

    return mqttClient.publish(topic, payload);
}