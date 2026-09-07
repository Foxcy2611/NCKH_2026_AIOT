#include <Arduino.h>

#include "gateway_config.h"
#include "gateway_queue.h"
#include "gateway_tasks.h"


// ============================================================
// Setup
// ============================================================

void setup()
{
    Serial.begin(
        GATEWAY_SERIAL_BAUD
    );

    delay(1000);

    Serial.println();
    Serial.println(
        "========================================"
    );
    Serial.println(
        "       NCKH 2026 - GATEWAY"
    );
    Serial.println(
        "       M4 - PHASE 10"
    );
    Serial.println(
        "========================================"
    );


    // --------------------------------------------------------
    // 1. Create FreeRTOS queues
    // --------------------------------------------------------

    if (!initGatewayQueues())
    {
        Serial.println(
            "[FATAL] Queue initialization failed"
        );

        while (true)
        {
            delay(1000);
        }
    }


    // --------------------------------------------------------
    // 2. Initialize ESP-NOW
    // --------------------------------------------------------

    if (!initEspNow())
    {
        Serial.println(
            "[FATAL] ESP-NOW initialization failed"
        );

        while (true)
        {
            delay(1000);
        }
    }


    // --------------------------------------------------------
    // 3. Create FreeRTOS Tasks
    // --------------------------------------------------------

    xTaskCreate(
        TaskEspNow,
        "TaskEspNow",
        TASK_ESPNOW_STACK_SIZE,
        nullptr,
        TASK_ESPNOW_PRIORITY,
        nullptr
    );


    xTaskCreate(
        TaskGatewayManager,
        "TaskGatewayManager",
        TASK_GATEWAY_STACK_SIZE,
        nullptr,
        TASK_GATEWAY_PRIORITY,
        nullptr
    );


    xTaskCreate(
        TaskSensor,
        "TaskSensor",
        TASK_SENSOR_STACK_SIZE,
        nullptr,
        TASK_SENSOR_PRIORITY,
        nullptr
    );


    xTaskCreate(
        TaskNetwork,
        "TaskNetwork",
        TASK_NETWORK_STACK_SIZE,
        nullptr,
        TASK_NETWORK_PRIORITY,
        nullptr
    );


    Serial.println(
        "[Gateway] All tasks created"
    );

    Serial.println(
        "[Gateway] Phase 10 ready"
    );
}


// ============================================================
// Loop
// ============================================================

void loop()
{
    // Gateway hoạt động bằng FreeRTOS Tasks.
    //
    // Không xử lý logic chính ở loop().

    vTaskDelay(
        pdMS_TO_TICKS(1000)
    );
}