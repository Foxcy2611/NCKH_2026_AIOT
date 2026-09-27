#include <Arduino.h>
#include "Task/gateway_tasks.h"
#include "System/gateway_sensor.h"
#include "System/gateway_network.h"
#include "System/gateway_record.h"
#include "System/gateway_runtime.h"
#include "System/gateway_state.h"

void TaskGatewayManager(void *) {
    GatewayWatchdogJoin();
    Serial.println("[Manager] latest Gateway snapshot; no NVS/FIFO");
    for (;;) {
        GatewayWatchdogFeed();
        EnvironmentSnapshot env{};
        GatewaySensor_GetLatest(&env);
        NetworkSnapshot net{};
        GatewayNetwork_GetLatest(&net);
        Gate_Payload_t gate = GatewayBuildPayload(env, GatewayNowMs());
        GatewayApplyNetwork(gate, net);
        if (!GatewayState_UpdateGate(gate)) {
            // The next iteration retries with fresh data, without blocking RX.
            Serial.println("[Manager] state busy; refresh next cycle");
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}
