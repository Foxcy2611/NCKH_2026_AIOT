#include <Arduino.h>
#include <PubSubClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <esp_system.h>

#include "json_serializer.h"
#include "packet.h"
#include "test_config.h"

namespace {

WiFiClientSecure tlsClient;
PubSubClient mqttClient(tlsClient);

uint32_t publishCount = 0;
uint32_t sessionId = 1000;
unsigned long lastWifiAttempt = 0;
unsigned long lastMqttAttempt = 0;
unsigned long lastPublish = 0;
bool autoPublish = true;

const char *ClassificationName(uint8_t classification) {
    switch (classification) {
        case CLASS_ASTHMA: return "ASTHMA";
        case CLASS_NON_ASTHMA: return "NON-ASTHMA";
        default: return "UNSURE";
    }
}

float RandomFloat(float minimum, float maximum) {
    const long value = random(0, 10001);
    return minimum + (maximum - minimum) * (static_cast<float>(value) / 10000.0f);
}

void ConnectWifi() {
    if (WiFi.status() == WL_CONNECTED || millis() - lastWifiAttempt < 5000UL) {
        return;
    }

    lastWifiAttempt = millis();
    Serial.printf("[WiFi] Dang ket noi den %s ...\n", TEST_WIFI_SSID);
    WiFi.disconnect();
    WiFi.begin(TEST_WIFI_SSID, TEST_WIFI_PASSWORD);
}

void ConnectMqtt() {
    if (WiFi.status() != WL_CONNECTED || mqttClient.connected() ||
        millis() - lastMqttAttempt < 5000UL) {
        return;
    }

    lastMqttAttempt = millis();
    char clientId[40];
    snprintf(clientId, sizeof(clientId), "qt6-packet-test-%08lX",
             static_cast<unsigned long>(ESP.getEfuseMac()));

    Serial.printf("[MQTT] Dang ket noi broker %s ...\n", TEST_MQTT_BROKER);
    if (mqttClient.connect(clientId, TEST_MQTT_USERNAME, TEST_MQTT_PASSWORD)) {
        Serial.printf("[MQTT] Da ket noi. Topic: %s\n", TEST_MQTT_TOPIC);
    } else {
        Serial.printf("[MQTT] Ket noi that bai, state=%d\n", mqttClient.state());
    }
}

Gateway_Payload_t BuildGatewayPayload() {
    Gateway_Payload_t gate{};
    gate.gateway_id = 0x20260001UL;
    gate.timestamp = static_cast<uint64_t>(millis());
    gate.operating_mode = GATE_MODE_HOME;
    gate.uplink_type = GATE_UPLINK_WIFI;

    // Du lieu cam bien gia lap, khong doc bat ky module phan cung nao.
    gate.temperature = RandomFloat(24.0f, 34.0f);
    gate.humidity = RandomFloat(40.0f, 90.0f);
    gate.pressure = RandomFloat(990.0f, 1035.0f);
    gate.tvoc = static_cast<uint16_t>(random(20, 501));
    gate.eco2 = static_cast<uint16_t>(random(400, 1501));
    gate.sensor_valid_mask = SENSOR_DHT22_VALID |
                             SENSOR_BMP280_VALID |
                             SENSOR_SGP30_VALID |
                             SENSOR_GPS_VALID;

    gate.wifi_connected = WiFi.status() == WL_CONNECTED;
    gate.wifi_rssi_dbm = gate.wifi_connected ? static_cast<int16_t>(WiFi.RSSI()) : -127;
    gate.lte_registered = 0;
    gate.lte_rssi_dbm = -127;
    gate.mqtt_connected = mqttClient.connected();

    gate.latitude = 21.028511 + static_cast<double>(random(-500, 501)) / 1000000.0;
    gate.longitude = 105.804817 + static_cast<double>(random(-500, 501)) / 1000000.0;
    gate.gps_timestamp = gate.timestamp;
    gate.battery_gate = static_cast<uint8_t>(random(40, 101));
    return gate;
}

Node_Payload_t BuildNodePayload(uint8_t classification) {
    Node_Payload_t node{};
    node.session_id = ++sessionId;
    node.event_type = static_cast<uint8_t>(random(EVENT_MANUAL_CHECK, EVENT_MONITOR + 1));
    node.classification = classification;
    node.audio_quality = (random(0, 10) == 0)
                             ? static_cast<uint8_t>(random(AUDIO_TOO_WEAK, AUDIO_INACTIVE + 1))
                             : AUDIO_OK;
    node.vitals_valid = random(0, 10) < 8;
    node.battery_node = static_cast<uint8_t>(random(35, 101));

    switch (classification) {
        case CLASS_ASTHMA:
            node.model_score = RandomFloat(0.65f, 0.99f);
            node.heart_rate = static_cast<uint16_t>(random(88, 126));
            node.spo2 = static_cast<uint8_t>(random(88, 96));
            break;
        case CLASS_NON_ASTHMA:
            node.model_score = RandomFloat(0.65f, 0.99f);
            node.heart_rate = static_cast<uint16_t>(random(60, 101));
            node.spo2 = static_cast<uint8_t>(random(95, 101));
            break;
        default:
            node.model_score = RandomFloat(0.45f, 0.60f);
            node.heart_rate = static_cast<uint16_t>(random(65, 116));
            node.spo2 = static_cast<uint8_t>(random(90, 100));
            break;
    }

    if (!node.vitals_valid) {
        node.heart_rate = 0;
        node.spo2 = 0;
    }
    return node;
}

bool PublishScenario(int scenario) {
    if (!mqttClient.connected()) {
        Serial.println("[TEST] Chua co MQTT, khong the gui packet.");
        return false;
    }

    Complete_Packet_t packet{};
    packet.gateway = BuildGatewayPayload();

    switch (scenario) {
        case 0:
            packet.has_patient_event = 0;
            break;
        case 1:
            packet.has_patient_event = 1;
            packet.node = BuildNodePayload(CLASS_ASTHMA);
            break;
        case 2:
            packet.has_patient_event = 1;
            packet.node = BuildNodePayload(CLASS_NON_ASTHMA);
            break;
        default:
            packet.has_patient_event = 1;
            packet.node = BuildNodePayload(CLASS_UNSURE);
            break;
    }

    char json[1536];
    if (!SerializeCompletePacketJson(packet, json, sizeof(json))) {
        Serial.println("[JSON] Loi: bo dem JSON khong du.");
        return false;
    }

    const bool sent = mqttClient.publish(TEST_MQTT_TOPIC, json, false);
    Serial.printf("\n[MQTT] %s packet #%lu",
                  sent ? "Da gui" : "Gui that bai",
                  static_cast<unsigned long>(publishCount));
    if (!packet.has_patient_event) {
        Serial.println(" | GATE-ONLY");
    } else {
        Serial.printf(" | %s | session=%lu\n",
                      ClassificationName(packet.node.classification),
                      static_cast<unsigned long>(packet.node.session_id));
    }
    Serial.println(json);

    if (sent) {
        ++publishCount;
    }
    return sent;
}

void HandleSerialCommand() {
    if (!Serial.available()) {
        return;
    }

    const char command = static_cast<char>(tolower(Serial.read()));
    switch (command) {
        case 'g': PublishScenario(0); break;
        case 'a': PublishScenario(1); break;
        case 'n': PublishScenario(2); break;
        case 'u': PublishScenario(3); break;
        case 't':
            autoPublish = !autoPublish;
            Serial.printf("[TEST] Tu dong gui: %s\n", autoPublish ? "BAT" : "TAT");
            break;
        default: break;
    }
}

}  // namespace

void setup() {
    Serial.begin(115200);
    delay(500);

    Serial.println("\n=== TEST COMPLETE PACKET -> JSON -> MQTT -> QT6 ===");
    Serial.println("Lenh Serial: a=ASTHMA, n=NON-ASTHMA, u=UNSURE, g=GATE-ONLY, t=bat/tat tu dong");

    WiFi.mode(WIFI_STA);
    randomSeed(esp_random());
    tlsClient.setInsecure();  // Chi dung cho ban thu nghiem; ban chinh nen gan CA.
    mqttClient.setServer(TEST_MQTT_BROKER, TEST_MQTT_PORT);
    mqttClient.setBufferSize(2048);

    // Cho phep lan thu ket noi dau tien chay ngay.
    lastWifiAttempt = millis() - 5000UL;
    lastMqttAttempt = millis() - 5000UL;
    lastPublish = millis();
}

void loop() {
    ConnectWifi();
    ConnectMqtt();

    if (mqttClient.connected()) {
        mqttClient.loop();
    }

    HandleSerialCommand();

    if (autoPublish && mqttClient.connected() &&
        millis() - lastPublish >= TEST_PUBLISH_INTERVAL_MS) {
        lastPublish = millis();
        PublishScenario(publishCount % 4);
    }

    delay(5);
}
