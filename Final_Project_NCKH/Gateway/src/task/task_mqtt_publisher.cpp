#include <Arduino.h>
#include "Task/gateway_tasks.h"
#include <esp_system.h>
#include "System/gateway_state.h"
#include "System/gateway_sensor.h"
#include "System/gateway_record.h"
#include "System/gateway_runtime.h"
#include "System/gateway_json.h"
#include "System/gateway_network.h"
#include "Config/gateway_config.h"
#include "Config/gateway_network_config.h"
#include "Network/gateway_mqtt_wifi.h"
#include "Display_TFT/gateway_tft.h"

#if GATEWAY_LTE_ENABLED
#include "Network/gateway_mqtt_lte.h"
#endif

namespace {
bool MqttPublishUnified(Gate_Uplink_Type_t uplink, const char *topic, const char *payload) {
    if (!topic || !payload) return false;
    if (uplink == GATE_UPLINK_WIFI) {
        return MQTT_WIFI_Publish(topic, payload);
    }
#if GATEWAY_LTE_ENABLED
    else if (uplink == GATE_UPLINK_LTE) {
        return MQTT_LTE_Publish(topic, payload);
    }
#endif
    return false;
}

bool MqttIsConnectedUnified(Gate_Uplink_Type_t uplink) {
    if (uplink == GATE_UPLINK_WIFI) return MQTT_WIFI_IsConnected();
#if GATEWAY_LTE_ENABLED
    if (uplink == GATE_UPLINK_LTE) return MQTT_LTE_IsConnected();
#endif
    return false;
}

bool MqttConnectUnified(Gate_Uplink_Type_t uplink) {
    if (uplink == GATE_UPLINK_WIFI) {
#if GATEWAY_LTE_ENABLED
        if (MQTT_LTE_IsConnected()) MQTT_LTE_Disconnect();
#endif
        return MQTT_WIFI_Connect();
    }
#if GATEWAY_LTE_ENABLED
    else if (uplink == GATE_UPLINK_LTE) {
        if (MQTT_WIFI_IsConnected()) MQTT_WIFI_Disconnect();
        return MQTT_LTE_Connect(MQTT_BROKER, MQTT_PORT, MQTT_CLIENT_ID, MQTT_USERNAME, MQTT_PASSWORD);
    }
#endif
    return false;
}

void MqttLoopUnified(Gate_Uplink_Type_t uplink) {
    if (uplink == GATE_UPLINK_WIFI) MQTT_WIFI_Loop();
#if GATEWAY_LTE_ENABLED
    if (uplink == GATE_UPLINK_LTE) MQTT_LTE_Loop();
#endif
}
}


void TaskMqttPublisher(void *) {
    GatewayWatchdogJoin();
    if (!MQTT_WIFI_Init()) {
        Serial.println("[MQTT] Wi-Fi MQTT configuration error");
    }
    static char json[GATEWAY_JSON_CAPACITY];
    static char secondaryJson[GATEWAY_JSON_CAPACITY];
    const uint32_t bootId = esp_random();
    uint32_t recordSequence = 0;
    uint64_t lastEventRevision = 0;
    uint32_t lastEventRecordSequence = 0;
    uint64_t nextConnect = 0, nextPublish = 0, nextTelemetry = 0, nextStatus = 0;
    bool wasConnected = false;
    Gate_Uplink_Type_t previousUplink = GATE_UPLINK_NONE;

#if GATEWAY_SENSOR_MODE == 2
    const char *telemetryTopic = MQTT_TEST_TOPIC_TELEMETRY;
    const char *eventTopic = MQTT_TEST_TOPIC_PATIENT_EVENT;
    const char *statusTopic = MQTT_TEST_TOPIC_GATEWAY_STATUS;
    const char *alertTopic = MQTT_TEST_TOPIC_ALERT;
#else
    const char *telemetryTopic = MQTT_TOPIC_TELEMETRY;
    const char *eventTopic = MQTT_TOPIC_PATIENT_EVENT;
    const char *statusTopic = MQTT_TOPIC_GATEWAY_STATUS;
    const char *alertTopic = MQTT_TOPIC_ALERT;
#endif
    Serial.println("[MQTT] Latest-state publisher started");
    for (;;) {
        GatewayWatchdogFeed();
        NetworkSnapshot net{};
        GatewayNetwork_GetLatest(&net);
        const auto uplink = net.active_uplink;
        uint64_t now = GatewayNowMs();
        if (uplink != previousUplink) {
            previousUplink = uplink;
            wasConnected = false;
            nextConnect = 0;
        }
        const bool uplinkReady =
            (uplink == GATE_UPLINK_WIFI && net.wifi_connected) ||
            (uplink == GATE_UPLINK_LTE && net.lte_connected);

        if (!uplinkReady) {
            if (MQTT_WIFI_IsConnected()) MQTT_WIFI_Disconnect();
#if GATEWAY_LTE_ENABLED
            if (MQTT_LTE_IsConnected()) MQTT_LTE_Disconnect();
#endif
        } else if (!MqttIsConnectedUnified(uplink) && now >= nextConnect) {
            // Existing transport connection behavior retained in this stage.
            ESP_ERROR_CHECK(esp_task_wdt_delete(nullptr));
            MqttConnectUnified(uplink);
            GatewayWatchdogJoin();
            GatewayWatchdogFeed();
            nextConnect = GatewayNowMs() + GATEWAY_MQTT_RETRY_MS;
        }
        if (uplinkReady && MqttIsConnectedUnified(uplink)) MqttLoopUnified(uplink);
        const bool connected = uplinkReady && MqttIsConnectedUnified(uplink);
        now = GatewayNowMs();
        if (connected && !wasConnected) {
            nextPublish = 0;
            nextTelemetry = 0; // send current state even if node is already clean
            nextStatus = 0;
            Serial.println("[MQTT] connected -> send latest snapshot");
        }
        wasConnected = connected;
        if (!connected) {
            vTaskDelay(pdMS_TO_TICKS(50));
            continue;
        }
        // This task knows the actual MQTT status at this instant.
        net.mqtt_connected = true;
        GatewayStateSnapshot snapshot{};
        if (!GatewayState_GetSnapshot(&snapshot)) {
            vTaskDelay(pdMS_TO_TICKS(50));
            continue;
        }
        const bool dirty = snapshot.current_node_valid && snapshot.node_dirty;
        if (snapshot.current_gate_valid && now >= nextPublish &&
            (dirty || now >= nextTelemetry)) {
            // Temporary for ONE send attempt. Never retain this packet on failure.
            UplinkRecord item{};
            item.boot_id = bootId;
            item.record.gate = snapshot.current_gate;
            // Refresh environment age + network immediately before serialization.
            EnvironmentSnapshot env{};
            GatewaySensor_GetLatest(&env);
            item.record.gate = GatewayBuildPayload(env, GatewayNowMs());
            GatewayApplyNetwork(item.record.gate, net);
            item.record.has_patient_event = dirty ? 1 : 0;
            if (dirty) {
                item.record.patient_event = snapshot.current_node.payload;
                item.source_device_id = snapshot.current_node.device_id;
                item.source_sequence = snapshot.current_node.sequence;
                item.received_uptime_ms = snapshot.current_node.received_timestamp_ms;
                // Same Event retry keeps its record_id even with a fresher gate.
                if (lastEventRevision != snapshot.node_revision) {
                    lastEventRevision = snapshot.node_revision;
                    lastEventRecordSequence = ++recordSequence;
                }
                item.record_sequence = lastEventRecordSequence;
            } else {
                item.record_sequence = ++recordSequence;
            }
            gatewayStats.complete_records++;
            // Chuyển gói tin tổng hợp sang Task Display trước khi gửi lên Cloud
            GatewayTFT_PostPacket(item.record);

            const bool serialized = GatewaySerializeJson(item, json, sizeof(json));
            const char *topic = dirty ? eventTopic : telemetryTopic;
            const bool sent = serialized && MqttPublishUnified(uplink, topic, json);
            if (sent) {
                gatewayStats.mqtt_published++;
                if (dirty && !GatewayState_MarkPublished(snapshot.node_revision)) {
                    // Conservative: keep dirty, backend may see a retry.
                    Serial.println("[MQTT] state busy after send; duplicate retry possible");
                }
                Serial.printf("[MQTT] transport_send_ok patient=%u source=%lu seq=%lu revision=%llu via=%s\n",
                    item.record.has_patient_event,
                    (unsigned long)item.source_device_id,
                    (unsigned long)item.source_sequence,
                    (unsigned long long)(dirty ? snapshot.node_revision : 0),
                    uplink == GATE_UPLINK_LTE ? "LTE" : "Wi-Fi");
                nextPublish = GatewayNowMs() + 20;
                nextTelemetry = GatewayNowMs() + GATEWAY_TELEMETRY_PERIOD_MS;
                // Auxiliary alert is best effort. Do not resend an accepted Event
                // solely because this second publication fails. Backend can derive
                // the alert from the canonical Patient Event.
                const auto &event = item.record.patient_event;
                if (dirty && event.classification != GATEWAY_ALERT_NORMAL_CLASS &&
                    event.model_score >= GATEWAY_ALERT_MIN_SCORE) {
                    const bool alertOk =
                        GatewaySerializeAlertJson(item, secondaryJson, sizeof(secondaryJson)) &&
                        MqttPublishUnified(uplink, alertTopic, secondaryJson);
                    if (!alertOk) {
                        gatewayStats.mqtt_failed++;
                        Serial.println("[MQTT] auxiliary alert failed; no alert backlog");
                    }
                }
            } else {
                gatewayStats.mqtt_failed++;
                Serial.println(serialized
                    ? "[MQTT] send failed; next attempt rebuilds latest state"
                    : "[MQTT] JSON overflow; state kept, bounded retry (check capacity)");
                nextPublish = GatewayNowMs() + GATEWAY_MQTT_RETRY_MS;
            }
        }
        // Low priority status follows data, so reconnect sends latest data first.
        now = GatewayNowMs();
        if (now >= nextStatus && MqttIsConnectedUnified(uplink)) {
            GatewayStateSnapshot status{};
            if (GatewayState_GetSnapshot(&status) &&
                GatewaySerializeStatusJson(net, status.current_node_valid,
                    status.node_dirty, status.node_revision, now,
                    ESP.getFreeHeap(), secondaryJson, sizeof(secondaryJson))) {
                if (!MqttPublishUnified(uplink, statusTopic, secondaryJson)) {
                    gatewayStats.mqtt_failed++;
                }
            }
            nextStatus = GatewayNowMs() + GATEWAY_STATUS_PERIOD_MS;
        }
        vTaskDelay(pdMS_TO_TICKS(50));
    }
}
