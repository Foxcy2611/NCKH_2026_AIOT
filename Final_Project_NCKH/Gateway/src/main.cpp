#include <Arduino.h>
#include "System/gateway_runtime.h"
#include <esp_system.h>
#include <soc/soc.h>
#include <soc/rtc_cntl_reg.h>
#include "Config/gateway_config.h"
#include "System/gateway_queue.h"
#include "System/gateway_state.h"
#include "Task/gateway_tasks.h"
#include "Network/gateway_espnow.h"
#include "Display_TFT/gateway_tft.h"

static void startTask(TaskFunction_t fn, const char *name, uint32_t stack, UBaseType_t priority) {
    if (xTaskCreate(fn, name, stack, nullptr, priority, nullptr) != pdPASS) {
        Serial.printf("[FATAL] task creation failed: %s\n", name);
        abort();
    }
}
void setup() {
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); // Vô hiệu hóa Brownout Detector của ESP32
    Serial.begin(GATEWAY_SERIAL_BAUD);
    delay(1000);
    Serial.println();
    Serial.println("========================================");
    Serial.println(" NCKH 2026 - GATEWAY / M4 + M5 Wi-Fi");
    Serial.println(" Latest-state RAM: ESP-NOW + AES-GCM");
    Serial.println("========================================");

    Serial.printf("[Boot] reset_reason=%d\n", (int)esp_reset_reason());
    GatewayTFT_Init();
    Serial.println("[Display] TFT initialized in setup");
    GatewayWatchdogInit();
    if (!initGatewayQueues()) while (true) delay(1000);
    if (!GatewayState_Init()) {
        Serial.println("[FATAL] latest-state init failed");
        while (true) delay(1000);
    }
    if (!ESPNow_Init()) {
        Serial.println("[FATAL] ESP-NOW init failed");
        while (true) delay(1000);
    }

    Serial.println("[Gateway] RX path ready: callback -> RawSecurePacketQueue -> AES-GCM -> current_node -> ACK");
    Serial.println("[Gateway] Starting tasks...");

    startTask(TaskEspNow, "TaskEspNow", TASK_ESPNOW_STACK_SIZE, TASK_ESPNOW_PRIORITY);
    startTask(TaskGatewayManager, "TaskGatewayManager", TASK_GATEWAY_STACK_SIZE, TASK_GATEWAY_PRIORITY);
    startTask(TaskSensor, "TaskSensor", TASK_SENSOR_STACK_SIZE, TASK_SENSOR_PRIORITY);
    startTask(TaskConnManager, "TaskConnManager", TASK_NETWORK_STACK_SIZE/2, TASK_NETWORK_PRIORITY);
    startTask(TaskMqttPublisher, "TaskMqttPublisher", TASK_NETWORK_STACK_SIZE, TASK_NETWORK_PRIORITY);
    startTask(TaskDisplayTFT, "TaskDisplayTFT", TASK_DISPLAY_STACK_SIZE, TASK_DISPLAY_PRIORITY);
}


void loop() {
    GatewayStateSnapshot state{};
    if (GatewayState_GetSnapshot(&state)) {
        Serial.printf("[State] node_valid=%u gate_valid=%u dirty=%u revision=%llu session=%lu seq=%lu\n",
            (unsigned)state.current_node_valid, (unsigned)state.current_gate_valid,
            (unsigned)state.node_dirty, (unsigned long long)state.node_revision,
            (unsigned long)state.current_node.payload.session_id,
            (unsigned long)state.current_node.sequence);
    }
    Serial.printf("[Stats] rx=%lu accepted=%lu duplicate=%lu replay=%lu raw_dropped=%lu state_busy=%lu records=%lu mqtt_send_ok=%lu mqtt_failed=%lu heap=%u\n",
        (unsigned long)gatewayStats.espnow_received,
        (unsigned long)gatewayStats.espnow_valid,
        (unsigned long)gatewayStats.duplicates,
        (unsigned long)gatewayStats.replay_rejected,
        (unsigned long)gatewayStats.queue_dropped,
        (unsigned long)gatewayStats.state_update_failed,
        (unsigned long)gatewayStats.complete_records,
        (unsigned long)gatewayStats.mqtt_published,
        (unsigned long)gatewayStats.mqtt_failed,
        ESP.getFreeHeap());
    vTaskDelay(pdMS_TO_TICKS(5000));
}
