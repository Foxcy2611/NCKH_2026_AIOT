#include <Arduino.h>

#include "Config/gateway_config.h"
#include "System/gateway_queue.h"


// ============================================================
// Global queues
// ============================================================

QueueHandle_t espNowRxQueue = nullptr;

QueueHandle_t patientEventQueue = nullptr;


// ============================================================
// Initialize queues
// ============================================================

bool initGatewayQueues()
{
    // Queue raw ESP-NOW packet

    espNowRxQueue = xQueueCreate(
        ESPNOW_RX_QUEUE_LENGTH,
        sizeof(EspNowRawPacket)
    );

    if (espNowRxQueue == nullptr)
    {
        Serial.println(
            "[Queue] ERROR: espNowRxQueue creation failed"
        );

        return false;
    }


    // Queue PatientEventPacket

    patientEventQueue = xQueueCreate(
        PATIENT_EVENT_QUEUE_LENGTH,
        sizeof(PatientEventPacket)
    );

    if (patientEventQueue == nullptr)
    {
        Serial.println(
            "[Queue] ERROR: patientEventQueue creation failed"
        );

        return false;
    }


    Serial.println(
        "[Queue] All queues created"
    );

    return true;
}