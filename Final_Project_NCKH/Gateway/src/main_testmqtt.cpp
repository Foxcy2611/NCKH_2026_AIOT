#include <Arduino.h>
#include "gateway_wifi.h"
#include "MQTT.h"

void setup()
{
    Serial.begin(9600);
    delay(1000);

    Serial.println("=== Gateway start ===");

    WiFi_Scan();

    WiFi_Init();

    if (!WiFi_IsConnected())
    {
        Serial.println("WiFi not connected after init.");
    }

    MQTT_Init();

    if (WiFi_IsConnected())
    {
        MQTT_Connect();
    }
    else
    {
        Serial.println("MQTT skipped because WiFi is not connected.");
    }
}

void loop()
{
    if (!WiFi_IsConnected())
    {
        Serial.println("WiFi disconnected. Reconnecting...");
        WiFi_Reconnect();
        delay(1000);
        return;
    }

    if (!MQTT_IsConnected())
    {
        Serial.println("MQTT disconnected. Reconnecting...");
        MQTT_Reconnect();
        delay(1000);
        return;
    }

    MQTT_Loop();

    static unsigned long lastPublish = 0;
    if (millis() - lastPublish > 5000)
    {
        const char* topic = "nckh/gateway/status";
        const char* payload = "Gateway online";

        if (MQTT_Publish(topic, payload))
        {
            Serial.println("Published status to MQTT");
        }
        else
        {
            Serial.println("MQTT publish failed");
        }

        lastPublish = millis();
    }

    delay(200);
}
