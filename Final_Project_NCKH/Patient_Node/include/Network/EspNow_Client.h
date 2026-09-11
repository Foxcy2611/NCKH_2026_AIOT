#ifndef NCKH_ESPNOW_CLIENT_H
#define NCKH_ESPNOW_CLIENT_H

#include <stdint.h>

#include "system_state.h"
#include <esp_now.h>

#define ESP_NOW_CHANNEL 0

void EspNow_OnSent(
    const uint8_t *mac_addr,
    esp_now_send_status_t status
);

// Setup cho esp-now
bool EspNow_Setup(void);

// Kiểm tra ESP-NOW sẵn sàng hay chưa
bool EspNow_IsReady(void);

// Lấy trạng thái gửi hiện tại
Event_Send_Status_t EspNow_GetStatus(void);

#endif /* NCKH_ESPNOW_CLIENT_H */