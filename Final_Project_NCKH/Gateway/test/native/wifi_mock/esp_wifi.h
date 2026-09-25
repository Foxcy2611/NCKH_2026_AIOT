#pragma once
#include "WiFi.h"
using esp_err_t = int;
#define ESP_OK 0
#define WIFI_SECOND_CHAN_NONE 0
inline int esp_wifi_set_channel(int channel, int) { WiFi.channelValue = channel; return ESP_OK; }
