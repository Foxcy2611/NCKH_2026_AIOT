#include <Arduino.h>

#include "Config/gateway_config.h"
#include "Config/gateway_types.h"
#include "System/gateway_queue.h"
#include "Task/gateway_tasks.h"


// ============================================================
// Convert classification -> text
// ============================================================

static const char* classificationToString(
    uint8_t classification)
{
    switch (classification)
    {
        case CLASS_ASTHMA_LIKE:
            return "ASTHMA_LIKE";

        case CLASS_NON_ASTHMA:
            return "NON_ASTHMA";

        default:
            return "UNKNOWN";
    }
}


// ============================================================
// TaskGatewayManager
//
// Nhận PatientEventPacket từ Queue.
//
// Phase 10:
//     chỉ nhận + log.
//
// Phase 12:
//     sẽ aggregation.
//
// Phase 13+:
//     CompleteRecord -> Network.
// ============================================================

void TaskGatewayManager(void *parameter)
{
    Serial.println(
        "[TaskGatewayManager] Started"
    );

    PatientEventPacket event;

    while (true)
    {
        if (xQueueReceive(
                patientEventQueue,
                &event,
                portMAX_DELAY) == pdTRUE)
        {
            Serial.println();
            Serial.println(
                "================================"
            );

            Serial.println(
                "[Gateway] Patient Event Received"
            );

            Serial.print("Device ID       : ");
            Serial.println(event.device_id);

            Serial.print("Sequence        : ");
            Serial.println(event.sequence);

            Serial.print("Session ID      : ");
            Serial.println(event.session_id);

            Serial.print("Timestamp       : ");
            Serial.println(
                static_cast<unsigned long long>(
                    event.timestamp
                )
            );

            Serial.print("Event Type      : ");
            Serial.println(event.event_type);

            Serial.print("Classification   : ");
            Serial.println(
                classificationToString(
                    event.classification
                )
            );

            Serial.print("Model Score     : ");
            Serial.println(event.model_score, 4);

            Serial.print("Asthma Votes    : ");
            Serial.println(event.asthma_votes);

            Serial.print("Non-Asthma Votes: ");
            Serial.println(event.non_asthma_votes);

            Serial.print("Audio Quality   : ");
            Serial.println(event.audio_quality);

            Serial.print("Vitals Valid    : ");
            Serial.println(
                event.vitals_valid ? "YES" : "NO"
            );

            if (event.vitals_valid)
            {
                Serial.print("Heart Rate      : ");
                Serial.println(event.heart_rate);

                Serial.print("SpO2            : ");
                Serial.println(event.spo2);
            }

            Serial.print("Battery         : ");
            Serial.print(event.battery_percent);
            Serial.println("%");

            Serial.println(
                "================================"
            );
            Serial.println();
        }
    }
}