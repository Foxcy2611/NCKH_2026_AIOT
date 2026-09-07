#include <Arduino.h>

#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include "gateway_config.h"
#include "gateway_types.h"
#include "gateway_queue.h"
#include "gateway_tasks.h"


// ============================================================
// Global statistics
// ============================================================

GatewayStats gatewayStats = {
    0,
    0,
    0,
    0
};


// ============================================================
// ESP-NOW Receive Callback
//
// CỰC KỲ QUAN TRỌNG:
//
// Callback KHÔNG parse.
// Callback KHÔNG aggregate.
// Callback KHÔNG Serial.print nhiều.
// Callback KHÔNG MQTT.
//
// Callback chỉ:
//
//     Receive
//       ↓
//     Copy
//       ↓
//     Queue
//       ↓
//     Return
// ============================================================

static void onEspNowReceive(
    const esp_now_recv_info_t *info,
    const uint8_t *data,
    int len)
{
    if (data == nullptr)
    {
        return;
    }

    if (len <= 0 || len > ESPNOW_MAX_PACKET_SIZE)
    {
        return;
    }

    EspNowRawPacket rawPacket{};

    // Copy payload
    memcpy(
        rawPacket.data,
        data,
        len
    );

    rawPacket.length = static_cast<uint16_t>(len);

    // Copy sender MAC nếu có
    if (info != nullptr)
    {
        memcpy(
            rawPacket.mac,
            info->src_addr,
            6
        );
    }

    gatewayStats.espnow_received++;

    // Gửi raw packet vào queue
    BaseType_t higherPriorityTaskWoken = pdFALSE;

    BaseType_t result = xQueueSendFromISR(
        espNowRxQueue,
        &rawPacket,
        &higherPriorityTaskWoken
    );

    if (result != pdTRUE)
    {
        gatewayStats.queue_dropped++;
    }

    if (higherPriorityTaskWoken == pdTRUE)
    {
        portYIELD_FROM_ISR();
    }
}


// ============================================================
// Initialize ESP-NOW
// ============================================================

bool initEspNow()
{
    Serial.println("[ESP-NOW] Initializing...");

    WiFi.mode(WIFI_STA);

    // Set channel
    esp_wifi_set_channel(
        ESPNOW_CHANNEL,
        WIFI_SECOND_CHAN_NONE
    );

    Serial.print("[ESP-NOW] MAC: ");
    Serial.println(WiFi.macAddress());

    if (esp_now_init() != ESP_OK)
    {
        Serial.println("[ESP-NOW] ERROR: esp_now_init failed");

        return false;
    }

    // Register receive callback
    esp_err_t result = esp_now_register_recv_cb(
        onEspNowReceive
    );

    if (result != ESP_OK)
    {
        Serial.println(
            "[ESP-NOW] ERROR: callback registration failed"
        );

        return false;
    }

    Serial.println("[ESP-NOW] Initialized");

    return true;
}


// ============================================================
// TaskEspNow
//
// Nhiệm vụ:
//
// 1. Lấy raw packet từ espNowRxQueue
// 2. Kiểm tra size
// 3. Parse thành PatientEventPacket
// 4. Đẩy vào PatientEventQueue
//
// Đây mới là nơi được phép parse packet.
// ============================================================

void TaskEspNow(void *parameter)
{
    Serial.println("[TaskEspNow] Started");

    EspNowRawPacket rawPacket;

    while (true)
    {
        if (xQueueReceive(
                espNowRxQueue,
                &rawPacket,
                portMAX_DELAY) == pdTRUE)
        {
            // ------------------------------------------------
            // Validate packet size
            // ------------------------------------------------

            if (rawPacket.length != sizeof(PatientEventPacket))
            {
                gatewayStats.espnow_invalid++;

                Serial.print(
                    "[TaskEspNow] Invalid packet size: "
                );

                Serial.println(rawPacket.length);

                continue;
            }


            // ------------------------------------------------
            // Parse packet
            // ------------------------------------------------

            PatientEventPacket event{};

            memcpy(
                &event,
                rawPacket.data,
                sizeof(PatientEventPacket)
            );


            // ------------------------------------------------
            // Packet basic validation
            // ------------------------------------------------

            if (event.device_id == 0)
            {
                gatewayStats.espnow_invalid++;

                Serial.println(
                    "[TaskEspNow] Invalid device ID"
                );

                continue;
            }


            // ------------------------------------------------
            // Send to PatientEventQueue
            // ------------------------------------------------

            if (xQueueSend(
                    patientEventQueue,
                    &event,
                    pdMS_TO_TICKS(100)) != pdTRUE)
            {
                gatewayStats.queue_dropped++;

                Serial.println(
                    "[TaskEspNow] PatientEventQueue FULL"
                );

                continue;
            }

            gatewayStats.espnow_valid++;

            Serial.println(
                "[TaskEspNow] PatientEvent -> Queue"
            );
        }
    }
}