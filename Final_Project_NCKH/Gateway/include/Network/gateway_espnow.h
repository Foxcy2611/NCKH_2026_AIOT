#ifndef NCKH_GATEWAY_ESPNOW_H
#define NCKH_GATEWAY_ESPNOW_H

#include <Arduino.h>
#include <esp_now.h>
#include "Config/gateway_types.h"
#include "Secure_Protocol.h"

bool ESPNow_Init();
bool ESPNow_AddPeer(const uint8_t *mac);
bool ESPNow_Send(const uint8_t *mac, const uint8_t *data, size_t len);
bool ESPNow_SendSecureResponse(const uint8_t *mac,
                               uint32_t target_device_id,
                               uint32_t sequence,
                               uint32_t session_id,
                               Gateway_Response_Code_t response_code);
void ESPNow_RemovePeer(const uint8_t *mac);
void ESPNow_Deinit();

#endif
