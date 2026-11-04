#include <Arduino.h>
#include "System/gateway_runtime.h"
#include "Task/gateway_tasks.h"
#include "System/gateway_network.h"
#include "Config/gateway_config.h"
#include "Config/gateway_network_config.h"
#include "Network/gateway_wifi.h"
#include "Network/gateway_mqtt_wifi.h"

#if GATEWAY_LTE_ENABLED
#include "Network/gateway_lte.h"
#include "Network/gateway_mqtt_lte.h"
#include "Sensor/ESP32_A7680C_AT.h"
#endif

namespace {
NetworkSnapshot latest{};
portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;

void updateSnapshot(Gate_Uplink_Type_t active_uplink, bool lte_connected, int16_t lte_rssi) {
    NetworkSnapshot s{};
    s.wifi_connected = WiFi_IsConnected();
    s.wifi_rssi_dbm = s.wifi_connected ? WiFi.RSSI() : 0;
    s.lte_connected = lte_connected;
    s.lte_rssi_dbm = lte_rssi;
    s.active_uplink = active_uplink;

    if (active_uplink == GATE_UPLINK_WIFI) {
        s.mqtt_connected = s.wifi_connected && MQTT_WIFI_IsConnected();
    }
#if GATEWAY_LTE_ENABLED
    else if (active_uplink == GATE_UPLINK_LTE) {
        s.mqtt_connected = lte_connected && MQTT_LTE_IsConnected();
    }
#endif
    else {
        s.mqtt_connected = false;
    }

    portENTER_CRITICAL(&mux);
    latest = s;
    portEXIT_CRITICAL(&mux);
}
}

void GatewayNetwork_GetLatest(NetworkSnapshot *out) {
    if (!out) return;
    portENTER_CRITICAL(&mux);
    *out = latest;
    portEXIT_CRITICAL(&mux);
}

void TaskConnManager(void *) {
    GatewayWatchdogJoin();
    WiFi_Init();

#if GATEWAY_LTE_ENABLED
    Serial.printf("[ConnManager] Initializing LTE A7680C (RX=%u, TX=%u, baud=%lu, APN=\"%s\")...\n",
                  GATEWAY_LTE_RX_PIN, GATEWAY_LTE_TX_PIN,
                  (unsigned long)GATEWAY_LTE_BAUD, LTE_SIM_APN);
    bool lteDriverReady = LTE_Init(Serial2, GATEWAY_LTE_RX_PIN, GATEWAY_LTE_TX_PIN, GATEWAY_LTE_BAUD);
    if (lteDriverReady) {
        Serial.println("[ConnManager] LTE module A7680C ready (standby)");
    } else {
        Serial.println("[ConnManager] WARNING: LTE A7680C did not respond; failover may be unavailable");
    }
#endif

    uint32_t wifiLostStart = 0;
    uint32_t lastLteAttempt = 0;
    uint32_t lastCsqCheck = 0;
    bool lteConnected = false;
    int16_t lteRssi = -113;
    Gate_Uplink_Type_t currentUplink = GATE_UPLINK_NONE;

    for (;;) {
        GatewayWatchdogFeed();
        WiFi_Poll();

        uint32_t now = millis();
        bool wifiOk = WiFi_IsConnected();

        if (wifiOk) {
            // Wi-Fi đang hoạt động tốt (Ưu tiên số 1)
            if (currentUplink != GATE_UPLINK_WIFI) {
                Serial.printf("[ConnManager] Wi-Fi ACTIVE (RSSI=%d) -> Primary Uplink selected\n", WiFi.RSSI());
#if GATEWAY_LTE_ENABLED
                if (lteConnected) {
                    Serial.println("[ConnManager] Wi-Fi restored; disconnecting LTE data");
                    MQTT_LTE_Disconnect();
                    LTE_Disconnect();
                    lteConnected = false;
                }
#endif
            }
            wifiLostStart = 0;
            currentUplink = GATE_UPLINK_WIFI;
        } else {
            // Wi-Fi mất kết nối
            if (wifiLostStart == 0) {
                wifiLostStart = now;
                Serial.println("[ConnManager] Wi-Fi connection lost; starting failover timer...");
            }

#if GATEWAY_LTE_ENABLED
            if (now - wifiLostStart >= GATEWAY_WIFI_FAILOVER_TIMEOUT_MS) {
                // Đã quá thời gian chờ -> Chuyển sang kết nối dự phòng LTE
                if (!lteConnected && (int32_t)(now - lastLteAttempt) >= 0) {
                    Serial.printf("[ConnManager] FAILOVER: Connecting 4G LTE with APN \"%s\"...\n", LTE_SIM_APN);
                    ESP_ERROR_CHECK(esp_task_wdt_delete(nullptr));
                    lteConnected = LTE_Connect(LTE_SIM_APN);
                    GatewayWatchdogJoin();
                    GatewayWatchdogFeed();
                    lastLteAttempt = now + 10000UL;
                    if (lteConnected) {
                        Serial.println("[ConnManager] LTE connected; switching uplink to LTE");
                    } else {
                        Serial.println("[ConnManager] LTE connect attempt failed; will retry");
                    }
                }

                if (lteConnected) {
                    currentUplink = GATE_UPLINK_LTE;
                    if ((int32_t)(now - lastCsqCheck) >= 0) {
                        int csq = A7680C_GetSignalQuality();
                        lteRssi = (csq >= 0 && csq <= 31) ? static_cast<int16_t>(2 * csq - 113) : -113;
                        lastCsqCheck = now + 15000UL;
                    }
                } else {
                    currentUplink = GATE_UPLINK_NONE;
                }
            } else {
                currentUplink = GATE_UPLINK_NONE;
            }
#else
            currentUplink = GATE_UPLINK_NONE;
#endif
        }

        updateSnapshot(currentUplink, lteConnected, lteRssi);
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}
