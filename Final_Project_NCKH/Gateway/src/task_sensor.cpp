#include <Arduino.h>

#include "gateway_tasks.h"


void TaskSensor(void *parameter)
{
    Serial.println(
        "[TaskSensor] Started"
    );

    while (true)
    {
        // Phase 10:
        // Chưa đọc DHT22 / BMP280 / SGP30.
        //
        // Phase 11 sẽ triển khai ở đây.

        vTaskDelay(
            pdMS_TO_TICKS(1000)
        );
    }
}