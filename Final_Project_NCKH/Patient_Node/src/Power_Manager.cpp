#include "Power/Power_Manager.h"

#include <Arduino.h>

#include <esp_sleep.h>

#include "Board_Pinout.h"

namespace {
    constexpr uint64_t kCheckWakeMask = 1ULL << PIN_BTN_CHECK;
    constexpr uint64_t kMonitorWakeMask = 1ULL << PIN_BTN_MONITOR;
    constexpr uint64_t kSleepWakeMask = 1ULL << PIN_BTN_SLEEP;
    constexpr uint64_t kButtonWakeMask =
        kCheckWakeMask | kMonitorWakeMask | kSleepWakeMask;

    void DisableButtonWakeSource(void) {
        esp_sleep_disable_wakeup_source(ESP_SLEEP_WAKEUP_EXT1);
    }
}

Power_Wake_Source_t PowerManager_EnterLightSleep(void) {
    esp_sleep_disable_wakeup_source(ESP_SLEEP_WAKEUP_ALL);

    // GPIO4/5/6 của ESP32-S3 đều thuộc miền RTC IO. EXT1 hỗ trợ ANY_LOW,
    // phù hợp ba nút INPUT_PULLUP và còn cung cấp đúng bitmask sau khi wake.
    // Giữ RTC peripheral hoạt động để các điện trở kéo lên nội vẫn có hiệu lực.
    if (esp_sleep_pd_config(ESP_PD_DOMAIN_RTC_PERIPH, ESP_PD_OPTION_ON) != ESP_OK
        || esp_sleep_enable_ext1_wakeup(
            kButtonWakeMask,
            ESP_EXT1_WAKEUP_ANY_LOW
        ) != ESP_OK) {
        DisableButtonWakeSource();
        return POWER_WAKE_ERROR;
    }

    Serial.flush();
    const esp_err_t sleep_result = esp_light_sleep_start();
    uint64_t wake_mask = esp_sleep_get_ext1_wakeup_status();
    DisableButtonWakeSource();

    if (sleep_result != ESP_OK) {
        return POWER_WAKE_ERROR;
    }

    // Fallback cho trường hợp SDK không lưu mask nhưng nút vẫn còn được giữ LOW
    // ở thời điểm CPU vừa resume.
    if (wake_mask == 0ULL) {
        if (digitalRead(PIN_BTN_CHECK) == LOW) wake_mask |= kCheckWakeMask;
        if (digitalRead(PIN_BTN_MONITOR) == LOW) wake_mask |= kMonitorWakeMask;
        if (digitalRead(PIN_BTN_SLEEP) == LOW) wake_mask |= kSleepWakeMask;
    }

    // Nếu nhiều nút cùng đánh thức, ưu tiên CHECK rồi MONITOR rồi SLEEP.
    if ((wake_mask & kCheckWakeMask) != 0ULL) return POWER_WAKE_CHECK;
    if ((wake_mask & kMonitorWakeMask) != 0ULL) return POWER_WAKE_MONITOR;
    if ((wake_mask & kSleepWakeMask) != 0ULL) return POWER_WAKE_SLEEP;

    return POWER_WAKE_NONE;
}
