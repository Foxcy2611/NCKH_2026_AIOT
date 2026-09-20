#include "Network/gateway_espnow.h"
#include <WiFi.h>
#include <esp_wifi.h>
#include <string.h>
#include "Config/gateway_config.h"
#include "System/gateway_queue.h"
#include "Network/Secure_Event_Decryptor.h"

GatewayStats gatewayStats{};

namespace {
// Arduino-ESP32 2.x callback signature.
// Keep this callback minimal: validate size, copy MAC + 64-byte packet,
// and push it to the FreeRTOS queue. All AES-GCM/decrypt/ACK logic runs
// later in TaskEspNow.
void onReceive(const uint8_t *mac_addr,
               const uint8_t *data,
               int len)
{
    if (!mac_addr || !data || !espNowRxQueue) return;

    gatewayStats.espnow_received++;

    if (len != static_cast<int>(SECURE_PACKET_SIZE)) {
        gatewayStats.espnow_invalid++;
        return;
    }

    EspNowRawPacket raw{};
    memcpy(raw.mac, mac_addr, sizeof(raw.mac));
    memcpy(raw.data, data, SECURE_PACKET_SIZE);
    raw.length = SECURE_PACKET_SIZE;

    BaseType_t hpw = pdFALSE;
    if (xQueueSendFromISR(espNowRxQueue, &raw, &hpw) != pdTRUE) {
        gatewayStats.queue_dropped++;
    }

    if (hpw == pdTRUE) {
        portYIELD_FROM_ISR();
    }
}
}

bool ESPNow_AddPeer(const uint8_t *mac) {
    if (!mac) return false;
    if (esp_now_is_peer_exist(mac)) return true;

    esp_now_peer_info_t peer{};
    memcpy(peer.peer_addr, mac, 6);
    peer.channel = 0;
    peer.encrypt = false;
    return esp_now_add_peer(&peer) == ESP_OK;
}

bool ESPNow_Init() {
    WiFi.mode(WIFI_STA);
    esp_wifi_set_channel(ESPNOW_CHANNEL, WIFI_SECOND_CHAN_NONE);

    Serial.print("[ESP-NOW] Gateway MAC: ");
    Serial.println(WiFi.macAddress());

    if (esp_now_init() != ESP_OK) return false;
    if (esp_now_register_recv_cb(onReceive) != ESP_OK) return false;

    Serial.println("[ESP-NOW] RX callback ready (callback only copy+queue)");
    return true;
}

bool ESPNow_Send(const uint8_t *mac, const uint8_t *data, size_t len) {
    if (!mac || !data || len == 0) return false;
    if (!ESPNow_AddPeer(mac)) return false;
    return esp_now_send(mac, data, len) == ESP_OK;
}

bool ESPNow_SendSecureResponse(const uint8_t *mac,
                               uint32_t target_device_id,
                               uint32_t sequence,
                               uint32_t session_id,
                               Gateway_Response_Code_t response_code) {
    Secure_Packet_t response{};
    if (!SecureGateway_BuildResponse(target_device_id,
                                     sequence,
                                     session_id,
                                     response_code,
                                     KEY_GATEWAY_TO_NODE,
                                     &response)) {
        return false;
    }

    return ESPNow_Send(mac,
                       reinterpret_cast<const uint8_t*>(&response),
                       sizeof(response));
}

void ESPNow_RemovePeer(const uint8_t *mac) {
    if (mac) esp_now_del_peer(mac);
}

void ESPNow_Deinit() {
    esp_now_deinit();
}
