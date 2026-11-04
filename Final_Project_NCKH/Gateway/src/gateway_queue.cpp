#include "System/gateway_queue.h"
#include "Config/gateway_config.h"
QueueHandle_t espNowRxQueue = nullptr;
QueueHandle_t displayQueue = nullptr;

bool initGatewayQueues() {
    espNowRxQueue = xQueueCreate(ESPNOW_RX_QUEUE_LENGTH, sizeof(EspNowRawPacket));
    if (!espNowRxQueue) {
        Serial.println("[Queue] FATAL: raw RX queue creation failed");
        return false;
    }
    displayQueue = xQueueCreate(DISPLAY_QUEUE_LENGTH, sizeof(Complete_Packet_t));
    if (!displayQueue) {
        Serial.println("[Queue] FATAL: display queue creation failed");
        return false;
    }
    Serial.println("[Queue] Raw ESP-NOW RX & Display queues ready");
    return true;
}
