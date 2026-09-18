#include <Arduino.h>
#include "System/gateway_runtime.h"
#include <esp_system.h>
#include "Config/gateway_config.h"
#include "System/gateway_queue.h"
#include "Task/gateway_tasks.h"
#include "Network/gateway_espnow.h"

static void startTask(TaskFunction_t fn, const char *name, uint32_t stack, UBaseType_t priority) {
    if (xTaskCreate(fn, name, stack, nullptr, priority, nullptr) != pdPASS) {
        Serial.printf("[FATAL] task creation failed: %s\n", name);
        abort();
    }
}
void setup() {
    Serial.begin(GATEWAY_SERIAL_BAUD);
    delay(1000);
    Serial.println();
    Serial.println("========================================");
    Serial.println(" NCKH 2026 - GATEWAY / M4");
    Serial.println(" Final 2 architecture: ESP-NOW + AES-GCM");
    Serial.println("========================================");

    Serial.printf("[Boot] reset_reason=%d\n", (int)esp_reset_reason());
    GatewayWatchdogInit();
    if (!initGatewayQueues()) while (true) delay(1000);
    if (!ESPNow_Init()) {
        Serial.println("[FATAL] ESP-NOW init failed");
        while (true) delay(1000);
    }

    startTask(TaskEspNow, "TaskEspNow", TASK_ESPNOW_STACK_SIZE, TASK_ESPNOW_PRIORITY);
    startTask(TaskGatewayManager, "TaskGatewayManager", TASK_GATEWAY_STACK_SIZE, TASK_GATEWAY_PRIORITY);
    startTask(TaskSensor, "TaskSensor", TASK_SENSOR_STACK_SIZE, TASK_SENSOR_PRIORITY);
    startTask(TaskNetwork, "TaskNetwork", TASK_NETWORK_STACK_SIZE, TASK_NETWORK_PRIORITY);

    Serial.println("[Gateway] Tasks created");
    Serial.println("[Gateway] RX path ready: callback -> RawSecurePacketQueue -> AES-GCM -> ACK -> PatientEventQueue");
}

void loop() {
    Serial.printf("[Stats] rx=%lu accepted=%lu invalid=%lu auth_failed=%lu duplicate=%lu replay=%lu ack_queued=%lu nack_queued=%lu dropped=%lu records=%lu heap=%u\n",
        (unsigned long)gatewayStats.espnow_received, (unsigned long)gatewayStats.espnow_valid,
        (unsigned long)gatewayStats.espnow_invalid, (unsigned long)gatewayStats.auth_failed,
        (unsigned long)gatewayStats.duplicates, (unsigned long)gatewayStats.replay_rejected,
        (unsigned long)gatewayStats.ack_sent, (unsigned long)gatewayStats.nack_sent,
        (unsigned long)gatewayStats.queue_dropped, (unsigned long)gatewayStats.complete_records, ESP.getFreeHeap());
    vTaskDelay(pdMS_TO_TICKS(5000));
}
