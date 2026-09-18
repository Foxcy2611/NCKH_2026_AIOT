#pragma once
#include <Arduino.h>
#include <esp_timer.h>
#include <esp_task_wdt.h>
#include <esp_idf_version.h>
#include "Config/gateway_config.h"
inline uint64_t GatewayNowMs() { return (uint64_t)esp_timer_get_time() / 1000ULL; }
inline void GatewayWatchdogInit() {
#if ESP_IDF_VERSION_MAJOR >= 5
    esp_task_wdt_config_t config{};
    config.timeout_ms = GATEWAY_WDT_TIMEOUT_S * 1000;
    config.idle_core_mask = 0;
    config.trigger_panic = true;
    esp_err_t result = esp_task_wdt_init(&config);
    if (result == ESP_ERR_INVALID_STATE) result = esp_task_wdt_reconfigure(&config);
    ESP_ERROR_CHECK(result);
#else
    ESP_ERROR_CHECK(esp_task_wdt_init(GATEWAY_WDT_TIMEOUT_S, true));
#endif
}
inline void GatewayWatchdogJoin() { ESP_ERROR_CHECK(esp_task_wdt_add(nullptr)); }
inline void GatewayWatchdogFeed() { ESP_ERROR_CHECK(esp_task_wdt_reset()); }
