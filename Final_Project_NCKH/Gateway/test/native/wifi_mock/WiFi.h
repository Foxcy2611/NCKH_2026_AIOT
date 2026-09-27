#pragma once
#include "Arduino.h"
#define WIFI_STA 1
#define WL_CONNECTED 3
struct MockWiFi {
    int state = 0, channelValue = 1, begins = 0, disconnects = 0, requestedChannel = 0;
    void mode(int) {}
    void persistent(bool) {}
    void setAutoReconnect(bool) {}
    void setSleep(bool) {}
    void disconnect(bool, bool) { ++disconnects; state = 0; }
    void begin(const char *, const char *, int channel) { ++begins; requestedChannel = channel; }
    int status() { return state; }
    int channel() { return channelValue; }
    int RSSI() { return -60; }
};
extern MockWiFi WiFi;
