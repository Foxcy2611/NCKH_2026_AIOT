#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <esp_system.h>
#include <mbedtls/gcm.h>
#include <string.h>

#include "Secure_Protocol.h"
#include "test_config.h"

namespace {

uint32_t device_id = 0;
uint32_t sequence_counter = 0;
uint32_t session_id = 0x20260916UL;

struct PendingEvent {
    Secure_Packet_t packet{};
    uint32_t session_id = 0;
    bool active = false;
    bool waiting_ack = false;
    uint8_t retry_count = 0;
    uint32_t last_send_ms = 0;
};

PendingEvent pending{};

portMUX_TYPE callback_mux = portMUX_INITIALIZER_UNLOCKED;
volatile bool response_ready = false;
Secure_Packet_t response_packet{};
volatile int8_t send_result = -1; // -1 none, 0 failed, 1 success

uint32_t makeDeviceId() {
    const uint64_t mac = ESP.getEfuseMac();
    uint32_t id = static_cast<uint32_t>(mac) ^ static_cast<uint32_t>(mac >> 32U);
    return id == 0 ? 1U : id;
}

void printMac(const uint8_t *mac) {
    for (int i = 0; i < 6; ++i) {
        if (i) Serial.print(':');
        if (mac[i] < 0x10) Serial.print('0');
        Serial.print(mac[i], HEX);
    }
}

void printPacketHeader(const Secure_Packet_t &p, const char *label) {
    Serial.printf(
        "[%s] magic=0x%04X ver=%u type=%u device=0x%08lX seq=%lu len=%u\n",
        label,
        p.magic,
        p.protocol_version,
        p.message_type,
        static_cast<unsigned long>(p.device_id),
        static_cast<unsigned long>(p.sequence),
        static_cast<unsigned>(sizeof(p))
    );
}

Node_Payload_t makePayload(uint32_t seq) {
    Node_Payload_t p{};
    p.session_id = session_id;
    p.event_type = 1;       // Manual/check event in the Final 2 contract.
    p.classification = 1;   // Fake asthma-like result.
    p.model_score = 0.91f;
    p.audio_quality = 1;    // Valid audio quality value.
    p.vitals_valid = 1;
    p.heart_rate = static_cast<uint16_t>(72 + (seq % 5));
    p.spo2 = 97;
    p.battery_node = 85;
    return p;
}

bool encryptPatientEvent(const Node_Payload_t &payload,
                         uint32_t seq,
                         Secure_Packet_t &out) {
    memset(&out, 0, sizeof(out));

    out.magic = SECURE_PACKET_MAGIC;
    out.protocol_version = SECURE_PROTOCOL_VERSION;
    out.message_type = MSG_PATIENT_EVENT;
    out.device_id = device_id;
    out.sequence = seq;
    esp_fill_random(out.nonce, AES_GCM_NONCE_SIZE);

    mbedtls_gcm_context ctx;
    mbedtls_gcm_init(&ctx);

    int result = mbedtls_gcm_setkey(
        &ctx, MBEDTLS_CIPHER_ID_AES,
        KEY_NODE_TO_GATEWAY,
        AES_128_KEY_SIZE * 8U
    );

    if (result == 0) {
        result = mbedtls_gcm_crypt_and_tag(
            &ctx,
            MBEDTLS_GCM_ENCRYPT,
            SECURE_PAYLOAD_SIZE,
            out.nonce,
            AES_GCM_NONCE_SIZE,
            reinterpret_cast<const uint8_t*>(&out),
            SECURE_AAD_SIZE,
            reinterpret_cast<const uint8_t*>(&payload),
            out.ciphertext,
            AES_GCM_TAG_SIZE,
            out.authentication_tag
        );
    }

    mbedtls_gcm_free(&ctx);
    return result == 0;
}

bool decryptGatewayResponse(const Secure_Packet_t &packet,
                            Response_Payload_t &out) {
    memset(&out, 0, sizeof(out));

    if (packet.magic != SECURE_PACKET_MAGIC ||
        packet.protocol_version != SECURE_PROTOCOL_VERSION ||
        packet.message_type != MSG_GATEWAY_RESPONSE ||
        packet.device_id != GATEWAY_DEVICE_ID ||
        !pending.active ||
        packet.sequence != pending.packet.sequence) {
        return false;
    }

    mbedtls_gcm_context ctx;
    mbedtls_gcm_init(&ctx);

    int result = mbedtls_gcm_setkey(
        &ctx, MBEDTLS_CIPHER_ID_AES,
        KEY_GATEWAY_TO_NODE,
        AES_128_KEY_SIZE * 8U
    );

    if (result == 0) {
        result = mbedtls_gcm_auth_decrypt(
            &ctx,
            SECURE_RESPONSE_SIZE,
            packet.nonce,
            AES_GCM_NONCE_SIZE,
            reinterpret_cast<const uint8_t*>(&packet),
            SECURE_AAD_SIZE,
            packet.authentication_tag,
            AES_GCM_TAG_SIZE,
            packet.ciphertext,
            reinterpret_cast<uint8_t*>(&out)
        );
    }

    mbedtls_gcm_free(&ctx);

    if (result != 0) return false;

    return out.target_device_id == device_id &&
           out.session_id == pending.session_id &&
           out.response_code <= RESPONSE_NACK_INTERNAL;
}

void onSend(const uint8_t *mac, esp_now_send_status_t status) {
    (void)mac;
    portENTER_CRITICAL(&callback_mux);
    send_result = (status == ESP_NOW_SEND_SUCCESS) ? 1 : 0;
    portEXIT_CRITICAL(&callback_mux);
}

void onReceive(const uint8_t *mac, const uint8_t *data, int len) {
    (void)mac;
    if (!data || len != static_cast<int>(SECURE_PACKET_SIZE)) return;

    Secure_Packet_t packet{};
    memcpy(&packet, data, sizeof(packet));

    // Ignore everything except a Gateway response with the expected Gateway ID.
    if (packet.magic != SECURE_PACKET_MAGIC ||
        packet.protocol_version != SECURE_PROTOCOL_VERSION ||
        packet.message_type != MSG_GATEWAY_RESPONSE ||
        packet.device_id != GATEWAY_DEVICE_ID) {
        return;
    }

    portENTER_CRITICAL(&callback_mux);
    memcpy(&response_packet, &packet, sizeof(packet));
    response_ready = true;
    portEXIT_CRITICAL(&callback_mux);
}

bool initEspNow() {
    WiFi.mode(WIFI_STA);
    delay(100);

    const esp_err_t ch = esp_wifi_set_channel(
        ESPNOW_TEST_CHANNEL, WIFI_SECOND_CHAN_NONE
    );
    if (ch != ESP_OK) {
        Serial.printf("[ESP-NOW] WARNING: set channel failed (%d)\n", static_cast<int>(ch));
    }

    if (esp_now_init() != ESP_OK) {
        Serial.println("[ESP-NOW] init FAILED");
        return false;
    }

    if (esp_now_register_send_cb(onSend) != ESP_OK ||
        esp_now_register_recv_cb(onReceive) != ESP_OK) {
        Serial.println("[ESP-NOW] callback registration FAILED");
        esp_now_deinit();
        return false;
    }

    esp_now_peer_info_t peer{};
    memcpy(peer.peer_addr, ESP_NOW_BROADCAST_MAC, 6);
    peer.channel = ESPNOW_TEST_CHANNEL;
    peer.ifidx = WIFI_IF_STA;
    peer.encrypt = false;

    if (!esp_now_is_peer_exist(ESP_NOW_BROADCAST_MAC) &&
        esp_now_add_peer(&peer) != ESP_OK) {
        Serial.println("[ESP-NOW] broadcast peer add FAILED");
        esp_now_deinit();
        return false;
    }

    Serial.print("[ESP-NOW] Ready | Node MAC=");
    Serial.print(WiFi.macAddress());
    Serial.printf(" | channel=%u | packet=%u bytes | GatewayID=0x%08lX\n",
                  ESPNOW_TEST_CHANNEL,
                  static_cast<unsigned>(sizeof(Secure_Packet_t)),
                  static_cast<unsigned long>(GATEWAY_DEVICE_ID));
    Serial.println("[ESP-NOW] Sending to broadcast; Gateway learns this Node MAC in learning mode.");
    return true;
}

bool sendRaw(const Secure_Packet_t &packet, const char *label) {
    portENTER_CRITICAL(&callback_mux);
    send_result = -1;
    portEXIT_CRITICAL(&callback_mux);

    const esp_err_t result = esp_now_send(
        ESP_NOW_BROADCAST_MAC,
        reinterpret_cast<const uint8_t*>(&packet),
        sizeof(packet)
    );

    Serial.printf("[TX] %s | seq=%lu | len=%u | esp_now_send=%s (%d)\n",
                  label,
                  static_cast<unsigned long>(packet.sequence),
                  static_cast<unsigned>(sizeof(packet)),
                  result == ESP_OK ? "OK" : "ERROR",
                  static_cast<int>(result));
    return result == ESP_OK;
}

Secure_Packet_t last_packet{};
bool have_last_packet = false;
uint32_t last_packet_session_id = 0;
Secure_Packet_t previous_packet{};
bool have_previous_packet = false;
uint32_t previous_packet_session_id = 0;

void newEvent() {
    if (pending.active) {
        Serial.println("[TEST] Event trước vẫn đang pending; chờ ACK/retry.");
        return;
    }

    ++sequence_counter;
    if (sequence_counter == 0) sequence_counter = 1;
    Node_Payload_t payload = makePayload(sequence_counter);

    Secure_Packet_t packet{};
    if (!encryptPatientEvent(payload, sequence_counter, packet)) {
        Serial.println("[TX] AES-GCM encryption FAILED");
        return;
    }

    previous_packet = last_packet;
    previous_packet_session_id = last_packet_session_id;
    have_previous_packet = have_last_packet;
    last_packet = packet;
    last_packet_session_id = payload.session_id;
    have_last_packet = true;

    pending = {};
    pending.packet = packet;
    pending.session_id = payload.session_id;
    pending.active = true;
    pending.waiting_ack = false;
    pending.retry_count = 0;
    pending.last_send_ms = millis();

    Serial.printf("\n[EVENT] NEW | session=0x%08lX | seq=%lu | HR=%u | SpO2=%u | score=%.3f\n",
                  static_cast<unsigned long>(payload.session_id),
                  static_cast<unsigned long>(packet.sequence),
                  payload.heart_rate,
                  payload.spo2,
                  payload.model_score);
    printPacketHeader(packet, "SECURE");
    sendRaw(packet, "new event");
}

void armPendingForPacket(const Secure_Packet_t &packet, uint32_t packet_session_id) {
    pending = {};
    pending.packet = packet;
    pending.session_id = packet_session_id;
    pending.active = true;
    pending.waiting_ack = false;
    pending.retry_count = 0;
    pending.last_send_ms = millis();
}

void duplicateLast() {
    if (!have_last_packet) {
        Serial.println("[TEST] Chưa có packet. Bấm n trước.");
        return;
    }
    if (pending.active) {
        Serial.println("[TEST] Đang chờ ACK/NACK cho một packet khác. Hãy chờ xử lý xong.");
        return;
    }

    armPendingForPacket(last_packet, last_packet_session_id);
    Serial.printf("\n[TEST] DUPLICATE | gửi lại y nguyên seq=%lu, nonce/ciphertext/tag không đổi\n",
                  static_cast<unsigned long>(last_packet.sequence));
    sendRaw(last_packet, "duplicate");
}

void tamperLast() {
    if (!have_last_packet) {
        Serial.println("[TEST] Chưa có packet. Bấm n trước.");
        return;
    }

    Secure_Packet_t bad = last_packet;
    bad.ciphertext[0] ^= 0x01;
    Serial.printf("\n[TEST] AUTH FAILURE | seq=%lu | ciphertext modified after AES-GCM\n",
                  static_cast<unsigned long>(bad.sequence));
    sendRaw(bad, "tampered ciphertext");
}

void outOfOrder() {
    if (!have_previous_packet) {
        Serial.println("[TEST] Cần ít nhất 2 packet normal trước.");
        return;
    }
    Serial.printf("\n[TEST] OUT-OF-ORDER | gửi seq cũ=%lu\n",
                  static_cast<unsigned long>(previous_packet.sequence));
    sendRaw(previous_packet, "older sequence");
}

void retrySamePacket() {
    if (!have_last_packet) {
        Serial.println("[TEST] Chưa có packet. Bấm n trước.");
        return;
    }
    if (pending.active) {
        Serial.println("[TEST] Đang chờ ACK/NACK. Không tự retry; hãy chờ ACK hoặc reset nếu muốn mô phỏng mất ACK.");
        return;
    }

    armPendingForPacket(last_packet, last_packet_session_id);
    Serial.println("[TEST] RETRY MANUAL | SAME sequence/nonce/ciphertext/tag");
    sendRaw(last_packet, "manual retry");
}

void printHelp() {
    Serial.println();
    Serial.println("========== PATIENT NODE TEST ==========");
    Serial.println("n = tạo + gửi event AES-GCM mới");
    Serial.println("d = gửi lại packet cuối y nguyên -> Gateway phải ACK_DUPLICATE nếu đã nhận");
    Serial.println("c = sửa ciphertext -> Gateway phải DROP vì AES-GCM auth failed");
    Serial.println("o = gửi sequence cũ -> Gateway phải DROP replay/out-of-order");
    Serial.println("r = gửi lại packet cuối thủ công (retry cùng nonce/sequence)");
    Serial.println("x = clear pending test state (không xóa last packet)");
    Serial.println("h = help");
    Serial.println("========================================");
    Serial.println("MANUAL-ONLY: firmware không tự gửi event và không tự retry.");
    Serial.print("> ");
    Serial.println();
}

void processAck() {
    bool has_response = false;
    Secure_Packet_t packet{};
    int8_t radio_result = -1;

    portENTER_CRITICAL(&callback_mux);
    radio_result = send_result;
    send_result = -1;
    if (response_ready) {
        memcpy(&packet, &response_packet, sizeof(packet));
        response_ready = false;
        has_response = true;
    }
    portEXIT_CRITICAL(&callback_mux);

    if (!pending.active) return;

    if (radio_result == 1) {
        pending.waiting_ack = true;
        Serial.printf("[TX] RF send success | seq=%lu | waiting Gateway ACK/NACK\n",
                      static_cast<unsigned long>(pending.packet.sequence));
    } else if (radio_result == 0) {
        Serial.println("[TX] RF send callback FAILED");
    }

    if (has_response) {
        Response_Payload_t response{};
        if (!decryptGatewayResponse(packet, response)) {
            Serial.println("[ACK] DROP: Gateway response failed AES-GCM/header/session validation");
        } else {
            Serial.printf("[ACK] VALID | code=%u | target=0x%08lX | seq=%lu | session=0x%08lX\n",
                          response.response_code,
                          static_cast<unsigned long>(response.target_device_id),
                          static_cast<unsigned long>(packet.sequence),
                          static_cast<unsigned long>(response.session_id));

            switch (static_cast<Gateway_Response_Code_t>(response.response_code)) {
                case RESPONSE_ACK_ACCEPTED:
                    Serial.println("[ACK] ACK_ACCEPTED -> event completed");
                    pending = {};
                    break;
                case RESPONSE_ACK_DUPLICATE:
                    Serial.println("[ACK] ACK_DUPLICATE -> Gateway already processed this event");
                    pending = {};
                    break;
                case RESPONSE_NACK_BUSY:
                    Serial.println("[ACK] NACK_BUSY -> keep same packet and retry");
                    pending.waiting_ack = false;
                    break;
                case RESPONSE_NACK_UNSUPPORTED:
                    Serial.println("[ACK] NACK_UNSUPPORTED -> stop this event");
                    pending = {};
                    break;
                case RESPONSE_NACK_INTERNAL:
                    Serial.println("[ACK] NACK_INTERNAL -> keep same packet and retry");
                    pending.waiting_ack = false;
                    break;
                default:
                    Serial.println("[ACK] Unknown response code");
                    break;
            }
        }
    }
}

void processPendingTimeoutNotice() {
    if (!pending.active || !pending.waiting_ack) return;

    const uint32_t elapsed = millis() - pending.last_send_ms;
    if (elapsed >= ACK_TIMEOUT_MS) {
        Serial.printf("[TIMEOUT] No Gateway ACK for seq=%lu. Manual-only mode: no automatic retry.\n",
                      static_cast<unsigned long>(pending.packet.sequence));
        Serial.println("[TIMEOUT] Reset the test state with 'x', or use 'r' after state is cleared.");
        // Prevent repeated timeout spam while preserving the packet for inspection.
        pending.waiting_ack = false;
    }
}

void clearPending() {
    pending = {};
    Serial.println("[TEST] Pending state cleared. Last packet is still available for d/c/o/r tests.");
}

} // namespace

void setup() {
    Serial.begin(115200);
    delay(1500);

    device_id = makeDeviceId();

    Serial.println();
    Serial.println("============================================");
    Serial.println(" NCKH 2026 - PATIENT NODE TEST");
    Serial.println(" Final 2 M4 / ESP32-S3 / AES-128-GCM");
    Serial.println("============================================");
    Serial.printf("Node Device ID : 0x%08lX\n", static_cast<unsigned long>(device_id));
    Serial.printf("Gateway ID     : 0x%08lX\n", static_cast<unsigned long>(GATEWAY_DEVICE_ID));
    Serial.printf("ESP-NOW channel: %u\n", ESPNOW_TEST_CHANNEL);
    Serial.printf("Secure packet  : %u bytes\n", static_cast<unsigned>(sizeof(Secure_Packet_t)));
    if (!initEspNow()) {
        Serial.println("[FATAL] ESP-NOW init failed");
        while (true) delay(1000);
    }

    Serial.print("Node MAC       : ");
    Serial.println(WiFi.macAddress());

    printHelp();
    Serial.println("[READY] Nhập lệnh n/d/c/o/r/x/h trong Serial Monitor rồi Enter.");
    Serial.print("> ");
}

void loop() {
    if (Serial.available()) {
        const char c = static_cast<char>(Serial.read());
        if (c == '\r' || c == '\n' || c == ' ' || c == '\t') {
            // Ignore terminal line endings/whitespace.
        } else {
            Serial.printf("[CMD] %c\n", c);
            if (c == 'n' || c == 'N') newEvent();
            else if (c == 'd' || c == 'D') duplicateLast();
            else if (c == 'c' || c == 'C') tamperLast();
            else if (c == 'o' || c == 'O') outOfOrder();
            else if (c == 'r' || c == 'R') retrySamePacket();
            else if (c == 'x' || c == 'X') clearPending();
            else if (c == 'h' || c == 'H' || c == '?') printHelp();
            else Serial.println("[CMD] Unknown. Press h for help.");
            Serial.print("> ");
        }
    }

    processAck();
    processPendingTimeoutNotice();
    delay(10);
}
