#include "Network/gateway_espnow.h"

void ESPNow_Init()
{
    if (esp_now_init() != ESP_OK)
    {
        Serial.println("[ESPNow] Init failed");
        return;
    }
    esp_now_register_recv_cb(ESPNow_OnReceive);
    Serial.println("[ESPNow] Initialized");
}

void ESPNow_AddPeer(const uint8_t *mac)
{
    esp_now_peer_info_t peerInfo = {};

    memcpy(peerInfo.peer_addr, mac, 6);

    peerInfo.channel = 0;
    peerInfo.encrypt = false;

    if (esp_now_add_peer(&peerInfo) != ESP_OK)
    {
        Serial.println("Failed to add ESP-NOW peer!");
        return;
    }

    Serial.println("ESP-NOW peer added!");
}

void ESPNow_RemovePeer(const uint8_t *mac)
{
    if (esp_now_del_peer(mac) != ESP_OK)
    {
        Serial.println("Failed to remove ESP-NOW peer!");
        return;
    }

    Serial.println("ESP-NOW peer removed!");
}

void ESPNow_Send(const uint8_t *mac,
                 const uint8_t *data,
                 size_t len)
{
    esp_err_t result = esp_now_send(mac, data, len);

    if (result != ESP_OK)
    {
        Serial.println("ESP-NOW send failed!");
        return;
    }

    Serial.println("ESP-NOW data sent!");
}

void ESPNow_Deinit()
{
    if (esp_now_deinit() != ESP_OK)
    {
        Serial.println("ESP-NOW deinit failed!");
        return;
    }

    Serial.println("ESP-NOW deinitialized!");
}

void ESPNow_OnReceive(const uint8_t *mac,
                      const uint8_t *data,
                      int len)
{
    Serial.println("=== ESP-NOW Data Received ===");

    Serial.print("From: ");

    for (int i = 0; i < 6; i++)
    {
        Serial.printf("%02X", mac[i]);

        if (i < 5)
        {
            Serial.print(":");
        }
    }

    Serial.println();

    Serial.print("Length: ");
    Serial.println(len);

    Serial.print("Data: ");

    for (int i = 0; i < len; i++)
    {
        Serial.printf("%02X ", data[i]);
    }

    Serial.println();
}