#include "Network/gateway_wifi.h"
#include "Config/gateway_config.h"
#include "Config/gateway_network_config.h"
#include <esp_wifi.h>

namespace {
bool connecting = false;
uint32_t started = 0, nextAttempt = 0;
#if defined(ARDUINO_ARCH_ESP32)
volatile bool wifiEventConnected = false;
#endif

void resetChannel() {
    esp_err_t result = esp_wifi_set_channel(ESPNOW_CHANNEL, WIFI_SECOND_CHAN_NONE);
    if (result != ESP_OK) Serial.printf("[WiFi] channel restore error=%d\n", result);
}
}

void WiFi_Init() {
    connecting = false;
#if defined(ARDUINO_ARCH_ESP32)
    wifiEventConnected = false;
    static bool eventRegistered = false;
    if (!eventRegistered) {
        eventRegistered = true;
        WiFi.onEvent([](WiFiEvent_t event, WiFiEventInfo_t info) {
            (void)event; (void)info;
            wifiEventConnected = true;
        }, ARDUINO_EVENT_WIFI_STA_GOT_IP);

        WiFi.onEvent([](WiFiEvent_t event, WiFiEventInfo_t info) {
            (void)event;
            wifiEventConnected = false;
            Serial.printf("[WiFi] STA disconnected event (reason=%u)\n", info.wifi_sta_disconnected.reason);
        }, ARDUINO_EVENT_WIFI_STA_DISCONNECTED);
    }
#endif
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
#if defined(ARDUINO_ARCH_ESP32)
    if (!wifiEventConnected) return false;
    wifi_ap_record_t ap_info;
    if (esp_wifi_sta_get_ap_info(&ap_info) != ESP_OK) return false;
#endif
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
#if defined(ARDUINO_ARCH_ESP32)
            wifiEventConnected = false;
#endif
            return;
        }
    }

    if (WiFi_IsConnected()) {
        if (connecting) Serial.printf("[WiFi] connected channel=%d RSSI=%d\n", WiFi.channel(), WiFi.RSSI());
        connecting = false;
        return;
    }

    // Nếu WiFi tầng driver/event đã mất kết nối nhưng WiFi.status() vẫn kẹt ở WL_CONNECTED (do bug AUTH_EXPIRE)
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("[WiFi] Disconnect detected but status stuck; forcing clean disconnect");
        WiFi.disconnect(false, false); connecting = false;
        resetChannel(); nextAttempt = now + GATEWAY_WIFI_RETRY_MS;
        return;
    }

    if (connecting && now - started >= GATEWAY_WIFI_CONNECT_TIMEOUT_MS) {
        WiFi.disconnect(false, false); connecting = false;
        resetChannel(); nextAttempt = now + GATEWAY_WIFI_RETRY_MS;
        Serial.println("[WiFi] timeout; ESP-NOW remains enabled");
    }
    if (!connecting && (int32_t)(now - nextAttempt) >= 0) WiFi_Reconnect();
}
