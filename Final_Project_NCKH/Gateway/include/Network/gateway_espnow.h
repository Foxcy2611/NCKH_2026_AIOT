#ifndef NCKH_GATEWAY_ESPNOW_H
#define NCKH_GATEWAY_ESPNOW_H

#include <Arduino.h>
#include <esp_now.h>

// Config
void ESPNow_Init();

void ESPNow_AddPeer(const uint8_t *mac);

void ESPNow_RemovePeer(const uint8_t *mac);

// Truyền dữ liệu
void ESPNow_Send(const uint8_t *mac,
                 const uint8_t *data,
                 size_t len);

void ESPNow_Deinit();
void ESPNow_OnReceive(const uint8_t *mac,
                      const uint8_t *data,
                      int len);

#endif