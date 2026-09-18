#include <Arduino.h>
#include "System/gateway_runtime.h"
#include <string.h>
#include "Config/gateway_config.h"
#include "Config/gateway_types.h"
#include "System/gateway_queue.h"
#include "Task/gateway_tasks.h"
#include "Network/Secure_Event_Decryptor.h"
#include "Network/gateway_espnow.h"

namespace {
uint8_t boundMac[6] = GATEWAY_NODE_MAC;
uint32_t boundDeviceId = GATEWAY_NODE_DEVICE_ID;
bool learned = (GATEWAY_STRICT_NODE_MAC == 0 && GATEWAY_NODE_DEVICE_ID == 0UL);

bool macIsZero(const uint8_t *m) { for (int i=0;i<6;i++) if (m[i]) return false; return true; }
bool macEqual(const uint8_t *a, const uint8_t *b) { return memcmp(a,b,6)==0; }
bool macAllowed(const uint8_t *mac) {
    if (!mac || macIsZero(mac)) return false;
    if (GATEWAY_STRICT_NODE_MAC) {
        return !macIsZero(boundMac) && macEqual(mac, boundMac);
    }
    // Learning mode: before the first authenticated packet, accept any source.
    // After binding, enforce the learned MAC to prevent another sender from
    // using the same device_id/key accidentally or maliciously.
    if (boundDeviceId == 0) return true;
    return macEqual(mac, boundMac);
}

struct SeenEntry { bool valid; uint32_t device_id; uint32_t sequence; };
SeenEntry seen[PATIENT_HISTORY_SIZE]{};
size_t seenIndex = 0;

bool isSeen(uint32_t device, uint32_t seq) {
    for (const auto &e : seen) if (e.valid && e.device_id == device && e.sequence == seq) return true;
    return false;
}

uint32_t highestSeen(uint32_t device) {
    uint32_t high = 0;
    for (const auto &e : seen) if (e.valid && e.device_id == device && e.sequence > high) high = e.sequence;
    return high;
}

void markSeen(uint32_t device, uint32_t seq) {
    seen[seenIndex] = {true, device, seq};
    seenIndex = (seenIndex + 1) % PATIENT_HISTORY_SIZE;
}

bool configuredNodeId(uint32_t packetId) {
    if (GATEWAY_STRICT_NODE_MAC || GATEWAY_NODE_DEVICE_ID != 0UL) return packetId == GATEWAY_NODE_DEVICE_ID;
    return learned ? (boundDeviceId == 0 || packetId == boundDeviceId) : true;
}

void sendResponse(const EspNowRawPacket &raw, const Secure_EspNow_Packet_t &packet,
                 uint32_t session_id, Gateway_Response_Code_t code) {
    if (ESPNow_SendSecureResponse(raw.mac, packet.device_id, packet.sequence,
                                   session_id, code)) {
        if (code == RESPONSE_ACK_ACCEPTED || code == RESPONSE_ACK_DUPLICATE) gatewayStats.ack_sent++;
        else gatewayStats.nack_sent++;
    }
}
}

void TaskEspNow(void *parameter) {
    (void)parameter;
    Serial.println("[TaskEspNow] Started");
    GatewayWatchdogJoin();
    EspNowRawPacket raw{};

    for (;;) {
        GatewayWatchdogFeed();
        if (xQueueReceive(espNowRxQueue, &raw, pdMS_TO_TICKS(500)) != pdTRUE) continue;
        if (raw.length != SECURE_PACKET_SIZE) { gatewayStats.espnow_invalid++; continue; }

        Secure_EspNow_Packet_t packet{};
        memcpy(&packet, raw.data, sizeof(packet));

        if (packet.magic != SECURE_PACKET_MAGIC ||
            packet.protocol_version != SECURE_PROTOCOL_VERSION ||
            packet.message_type != MSG_PATIENT_EVENT ||
            packet.sequence == 0) {
            gatewayStats.espnow_invalid++;
            Serial.println("[RX] DROP: invalid header");
            continue;
        }

        if (!macAllowed(raw.mac)) {
            gatewayStats.espnow_invalid++;
            Serial.println("[RX] DROP: source MAC is not allowed");
            continue;
        }

        if (!configuredNodeId(packet.device_id)) {
            gatewayStats.espnow_invalid++;
            Serial.println("[RX] DROP: unexpected device_id");
            continue;
        }

        Patient_Event_Payload_t payload{};
        auto result = SecureEvent_Decrypt(&packet, packet.device_id,
                                          KEY_NODE_TO_GATEWAY, &payload);
        if (result != SECURE_EVENT_DECRYPT_OK) {
            gatewayStats.espnow_invalid++;
            if (result == SECURE_EVENT_AUTH_FAILED) gatewayStats.auth_failed++;
            Serial.printf("[RX] DROP: AES-GCM verify/decrypt failed (%d)\n", static_cast<int>(result));
            continue;
        }

        if (learned && boundDeviceId == 0) {
            boundDeviceId = packet.device_id;
            memcpy(boundMac, raw.mac, 6);
            Serial.printf("[Security] Learned Node device_id=%lu MAC=%02X:%02X:%02X:%02X:%02X:%02X\n",
                          static_cast<unsigned long>(boundDeviceId), boundMac[0],boundMac[1],boundMac[2],boundMac[3],boundMac[4],boundMac[5]);
        }

        uint32_t high = highestSeen(packet.device_id);
        if (isSeen(packet.device_id, packet.sequence)) {
            gatewayStats.duplicates++;
            sendResponse(raw, packet, payload.session_id, RESPONSE_ACK_DUPLICATE);
            Serial.printf("[RX] DUPLICATE seq=%lu -> ACK_DUPLICATE\n", static_cast<unsigned long>(packet.sequence));
            continue;
        }
        if (high != 0 && packet.sequence < high) {
            gatewayStats.replay_rejected++;
            Serial.printf("[RX] DROP: replay/out-of-order seq=%lu < highest=%lu\n",
                          static_cast<unsigned long>(packet.sequence), static_cast<unsigned long>(high));
            continue;
        }

        PatientEventEnvelope event{};
        event.payload = payload;
        event.device_id = packet.device_id;
        event.sequence = packet.sequence;
        memcpy(event.mac, raw.mac, 6);
        event.received_timestamp_ms = GatewayNowMs();

        if (xQueueSend(patientEventQueue, &event, pdMS_TO_TICKS(50)) != pdTRUE) {
            gatewayStats.queue_dropped++;
            sendResponse(raw, packet, payload.session_id, RESPONSE_NACK_BUSY);
            Serial.println("[RX] PatientEventQueue FULL -> NACK_BUSY");
            continue;
        }

        markSeen(packet.device_id, packet.sequence);
        gatewayStats.espnow_valid++;
        sendResponse(raw, packet, payload.session_id, RESPONSE_ACK_ACCEPTED);
        Serial.printf("[RX] ACCEPT seq=%lu session=%lu -> PatientEventQueue\n",
                      static_cast<unsigned long>(packet.sequence),
                      static_cast<unsigned long>(payload.session_id));
    }
}
