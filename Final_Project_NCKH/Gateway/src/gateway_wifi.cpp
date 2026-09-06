#include <gateway_wifi.h>

#define WIFI_SSID     "VIETTEL_AP_8D8938"
#define WIFI_PASSWORD "1234567890a"

void WiFi_Init()
{
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    Serial.println("Connecting to WiFi...");

    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        Serial.print(".");
    }

    Serial.println();
    Serial.println("WiFi connected!");

    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
}

bool WiFi_IsConnected()
{
    return WiFi.status() == WL_CONNECTED;
}

void WiFi_Reconnect()
{
    if (WiFi_IsConnected())
    {
        return;
    }

    Serial.println("WiFi disconnected. Reconnecting...");

    WiFi.disconnect();
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void WiFi_Scan()
{
    Serial.println("=== WiFi Scan Start ===");

    int numberOfNetworks = WiFi.scanNetworks();

    if (numberOfNetworks == 0)
    {
        Serial.println("No WiFi networks found.");
    }
    else
    {
        Serial.print("Found ");
        Serial.print(numberOfNetworks);
        Serial.println(" networks:");

        for (int i = 0; i < numberOfNetworks; i++)
        {
            Serial.print(i);
            Serial.print(": ");

            Serial.print(WiFi.SSID(i));

            Serial.print(" | RSSI: ");
            Serial.print(WiFi.RSSI(i));

            Serial.print(" | Channel: ");
            Serial.println(WiFi.channel(i));
        }
    }

    WiFi.scanDelete();

    Serial.println("=== WiFi Scan End ===");
}