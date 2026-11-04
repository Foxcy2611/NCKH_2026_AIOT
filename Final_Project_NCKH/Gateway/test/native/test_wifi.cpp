#include <cassert>
#include <cstdio>
#include "Network/gateway_wifi.h"
#include "Config/gateway_config.h"
#include "Config/gateway_network_config.h"
uint32_t mockNow = 0;
MockSerial Serial;
MockWiFi WiFi;
int main() {
    WiFi_Init(); // Must return with no AP present.
    assert(!WiFi_IsConnected());
    WiFi_Poll(); assert(WiFi.begins == 1 && WiFi.requestedChannel == ESPNOW_CHANNEL);
    mockNow = GATEWAY_WIFI_CONNECT_TIMEOUT_MS - 1;
    WiFi_Poll(); assert(WiFi.begins == 1);
    mockNow++;
    WiFi_Poll(); assert(WiFi.begins == 1 && WiFi.disconnects == 2);
    mockNow += GATEWAY_WIFI_RETRY_MS - 1;
    WiFi_Poll(); assert(WiFi.begins == 1);
    mockNow++;
    WiFi_Poll(); assert(WiFi.begins == 2);
    WiFi.state = WL_CONNECTED; WiFi.channelValue = ESPNOW_CHANNEL;
    WiFi_Poll(); assert(WiFi_IsConnected() && WiFi.disconnects == 2);
    WiFi.channelValue = ESPNOW_CHANNEL + 1;
    WiFi_Poll(); assert(!WiFi_IsConnected() && WiFi.channelValue == ESPNOW_CHANNEL);
    assert(WiFi.disconnects == 3);
    // Backoff still works across millis() rollover.
    mockNow = UINT32_MAX - 100;
    WiFi_Init(); WiFi_Poll(); int attempts = WiFi.begins;
    mockNow += GATEWAY_WIFI_CONNECT_TIMEOUT_MS;
    WiFi_Poll(); assert(WiFi.begins == attempts);
    mockNow += GATEWAY_WIFI_RETRY_MS;
    WiFi_Poll(); assert(WiFi.begins == attempts + 1);
    puts("PASS: Wi-Fi mock no-AP timeout/backoff/channel mismatch/millis rollover");
}
