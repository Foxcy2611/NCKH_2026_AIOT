#ifndef NCKH_POWER_MANAGER_H
#define NCKH_POWER_MANAGER_H

#include <Arduino.h>

// Nguồn đánh thức sau khi ESP32-S3 trở về từ Light Sleep.
enum Power_Wake_Source_t {
    POWER_WAKE_NONE = 0,
    POWER_WAKE_CHECK,
    POWER_WAKE_MONITOR,
    POWER_WAKE_SLEEP,
    POWER_WAKE_ERROR
};

// Cấu hình GPIO4/5/6 làm nguồn EXT1 ANY_LOW rồi đưa CPU vào Light Sleep.
// Hàm chỉ quản lý cơ chế ngủ/wake của ESP32-S3; việc tắt/bật ngoại vi được
// State Machine thực hiện trước/sau lời gọi này.
Power_Wake_Source_t PowerManager_EnterLightSleep(void);

#endif /* NCKH_POWER_MANAGER_H */
