#include "Network/gateway_wifi.h"
#include "Config/gateway_config.h"
#include "Config/gateway_network_config.h"
#include <esp_wifi.h>
namespace {
bool connecting = false;
uint32_t started = 0, nextAttempt = 0;
void resetChannel() {
    esp_err_t result = esp_wifi_set_channel(ESPNOW_CHANNEL, WIFI_SECOND_CHAN_NONE);
    if (result != ESP_OK) Serial.printf("[WiFi] channel restore error=%d\n", result);
}
}
void WiFi_Init() {
    connecting = false;
    WiFi.mode(WIFI_STA);
    WiFi.persistent(false);
    WiFi.setAutoReconnect(false);
    WiFi.setSleep(false);
    WiFi.disconnect(false, false);
    resetChannel();
    nextAttempt = millis();
#if !GATEWAY_NETWORK_CONFIGURED
    Serial.println("[WiFi] disabled by GATEWAY_NETWORK_CONFIGURED=0");
#endif
}
bool WiFi_IsConnected() {
    return WiFi.status() == WL_CONNECTED && WiFi.channel() == ESPNOW_CHANNEL;
}
void WiFi_Reconnect() {
#if !GATEWAY_NETWORK_CONFIGURED
    return;
#endif
    if (connecting || WiFi_IsConnected()) return;
    started = millis(); connecting = true;
    Serial.printf("[WiFi] connecting on channel %u\n", ESPNOW_CHANNEL);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD, ESPNOW_CHANNEL);
}
void WiFi_Poll() {
#if !GATEWAY_NETWORK_CONFIGURED
    return;
#endif
    uint32_t now = millis();
    if (WiFi.status() == WL_CONNECTED) {
        if (WiFi.channel() != ESPNOW_CHANNEL) {
            Serial.printf("[WiFi] CHANNEL MISMATCH: AP=%d required=%d; disconnect\n", WiFi.channel(), ESPNOW_CHANNEL);
            WiFi.disconnect(false, false); connecting = false;
            resetChannel(); nextAttempt = now + GATEWAY_WIFI_RETRY_MS;
        } else {
            if (connecting) Serial.printf("[WiFi] connected channel=%d RSSI=%d\n", WiFi.channel(), WiFi.RSSI());
            connecting = false;
        }
        return;
    }
    if (connecting && now - started >= GATEWAY_WIFI_CONNECT_TIMEOUT_MS) {
        WiFi.disconnect(false, false); connecting = false;
        resetChannel(); nextAttempt = now + GATEWAY_WIFI_RETRY_MS;
        Serial.println("[WiFi] timeout; ESP-NOW remains enabled");
    }
    if (!connecting && (int32_t)(now - nextAttempt) >= 0) WiFi_Reconnect();
}
