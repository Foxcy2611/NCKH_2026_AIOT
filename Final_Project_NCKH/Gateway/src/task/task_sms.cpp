#include <Arduino.h>
#include "System/gateway_sms.h"

#if GATEWAY_LTE_ENABLED && GATEWAY_SMS_ENABLED
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/task.h>
#include <stdio.h>
#include "Sensor/ESP32_A7680C_AT.h"

namespace {
struct SmsRequest {
    uint32_t device_id;
    uint32_t session_id;
    float model_score;
};

QueueHandle_t smsQueue = nullptr;
GatewaySmsSessionHistory acceptedSessions{};
}

bool GatewaySms_Init() {
    if (smsQueue) return true;
    smsQueue = xQueueCreate(GATEWAY_SMS_QUEUE_LENGTH, sizeof(SmsRequest));
    return smsQueue != nullptr;
}

// Single producer: only TaskEspNow calls this method. Remember after enqueue success.
GatewaySmsQueueResult GatewaySms_OnPatientEvent(const PatientEventEnvelope &event) {
    if (!GatewaySmsQualifies(event.payload)) return GatewaySmsQueueResult::NotEligible;
    if (acceptedSessions.contains(event.device_id, event.payload.session_id)) {
        return GatewaySmsQueueResult::DuplicateSession;
    }
    if (!smsQueue) return GatewaySmsQueueResult::QueueFull;
    const SmsRequest request{event.device_id, event.payload.session_id, event.payload.model_score};
    if (xQueueSend(smsQueue, &request, 0) != pdTRUE) {
        return GatewaySmsQueueResult::QueueFull;
    }
    acceptedSessions.remember(event.device_id, event.payload.session_id);
    return GatewaySmsQueueResult::Queued;
}

void TaskSms(void *) {
    Serial.printf("[SMS] Worker running; destination=%s\n", GATEWAY_SMS_PHONE);
    // Do not register with task WDT: a cellular AT+CMGS may block for many seconds.
    SmsRequest request{};
    for (;;) {
        if (xQueueReceive(smsQueue, &request, portMAX_DELAY) != pdTRUE) continue;

        // ConnManager initializes the modem independently. Never reinitialize Serial2
        // here: that would race against LTE MQTT / the modem owner.
        const uint32_t waitingSince = millis();
        while (!A7680C_IsReady() &&
               (uint32_t)(millis() - waitingSince) < GATEWAY_SMS_MODEM_READY_WAIT_MS) {
            vTaskDelay(pdMS_TO_TICKS(250));
        }
        if (!A7680C_IsReady()) {
            Serial.printf("[SMS] FAILED session=%lu: A7680C not initialized\n",
                          (unsigned long)request.session_id);
            continue;
        }

        // Plain ASCII so the modem's GSM text mode handles the contents safely.
        char message[180];
        const int length = snprintf(message, sizeof(message),
            "NCKH AIoT: Phien %lu duoc phan loai NON-ASTHMA (%.1f%%). Ket qua chi mang tinh tham khao.",
            (unsigned long)request.session_id, (double)(request.model_score * 100.0f));
        if (length <= 0 || (size_t)length >= sizeof(message)) {
            Serial.println("[SMS] FAILED: message too long");
            continue;
        }

        Serial.printf("[SMS] Sending session=%lu device=%lu -> %s\n",
                      (unsigned long)request.session_id,
                      (unsigned long)request.device_id, GATEWAY_SMS_PHONE);
        const bool success = A7680C_SendSMS(GATEWAY_SMS_PHONE, message);
        Serial.printf("[SMS] %s session=%lu\n", success ? "SENT" : "FAILED",
                      (unsigned long)request.session_id);
        // At-most-once submission per observed session: do not automatically retry
        // after an ambiguous modem/network failure (which might duplicate SMS).
    }
}

#else
bool GatewaySms_Init() { return true; }
GatewaySmsQueueResult GatewaySms_OnPatientEvent(const PatientEventEnvelope &) {
    return GatewaySmsQueueResult::Disabled;
}
void TaskSms(void *) {}
#endif
