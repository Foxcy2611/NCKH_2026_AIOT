#include "Network/EspNow_Client.h"

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <string.h>

#include "Network/Secure_Response_Decryptor.h"
#include "Network/Secure_Sender.h"
#include "Packet_Metadata.h"

namespace {

// /** Cấu hình tạm; thay bằng thông tin Gateway thật khi ghép hai bo mạch. */
constexpr uint8_t ESP_NOW_CHANNEL = 0;
constexpr uint32_t GATEWAY_DEVICE_ID = 0x47575431UL;

const uint8_t GATEWAY_MAC[6] = {
    0x02, 0x00, 0x00, 0x00, 0x00, 0x01
};

const uint8_t KEY_NODE_TO_GATEWAY[AES_128_KEY_SIZE] = {
    0x42, 0x91, 0xD7, 0x2C, 0xA5, 0x68, 0x1B, 0xEF,
    0x30, 0xC4, 0x7A, 0x16, 0x8D, 0x53, 0xB9, 0xE2
};

const uint8_t KEY_GATEWAY_TO_NODE[AES_128_KEY_SIZE] = {
    0xC8, 0x35, 0x6E, 0xA1, 0x19, 0xF4, 0x82, 0x5B,
    0xD0, 0x27, 0x9C, 0x73, 0x4A, 0xBE, 0x06, 0xE9
};

constexpr uint32_t SEND_CALLBACK_TIMEOUT_MS = 1000U;
constexpr uint32_t ACK_TIMEOUT_MS = 2000U;
constexpr uint32_t RETRY_DELAY_MS = 1000U;
constexpr uint8_t MAX_RETRY_COUNT = 3U;

// Chỉ giữ một sự kiện đang chờ Gateway xác nhận.
struct Pending_Event_t {
    Secure_Packet_t packet;
    uint32_t session_id;
    uint32_t last_sent_ms;
    uint8_t retry_count;
};

bool espnow_ready = false;
volatile bool pending_active = false;
volatile Event_Send_Status_t send_status = STATUS_IDLE;
Pending_Event_t pending{};

// Hai callback Wi-Fi chỉ ghi dữ liệu ngắn vào mailbox này.
constexpr int8_t CALLBACK_NONE = -1;
constexpr int8_t CALLBACK_FAILED = 0;
constexpr int8_t CALLBACK_SUCCESS = 1;

portMUX_TYPE callback_mux = portMUX_INITIALIZER_UNLOCKED;
volatile int8_t send_callback_result = CALLBACK_NONE;
volatile bool response_ready = false;
Secure_Packet_t response_packet{};

bool IsGatewayMac(const uint8_t* mac) {
    return mac != nullptr && memcmp(mac, GATEWAY_MAC, sizeof(GATEWAY_MAC)) == 0;
}

void OnEspNowSent(const uint8_t* mac, esp_now_send_status_t result) {
    if (!IsGatewayMac(mac)) return;

    portENTER_CRITICAL(&callback_mux);
    if (pending_active && send_status == STATUS_SENDING) {
        send_callback_result = result == ESP_NOW_SEND_SUCCESS
            ? CALLBACK_SUCCESS
            : CALLBACK_FAILED;
    }
    portEXIT_CRITICAL(&callback_mux);
}

void OnEspNowReceived(const uint8_t* mac, const uint8_t* data, int length) {
    if (!IsGatewayMac(mac) || data == nullptr ||
        length != static_cast<int>(SECURE_PACKET_SIZE)) {
        return;
    }

    portENTER_CRITICAL(&callback_mux);
    memcpy(&response_packet, data, sizeof(response_packet));
    response_ready = true;
    portEXIT_CRITICAL(&callback_mux);
}

void ClearPending(Event_Send_Status_t final_status) {
    memset(&pending, 0, sizeof(pending));
    pending_active = false;
    send_status = final_status;
}

void ScheduleRetry(const char* reason) {
    if (!pending_active) return;

    if (pending.retry_count >= MAX_RETRY_COUNT) {
        Serial.printf(
            "[ESP-NOW] Vượt quá %u lần retry. Lý do: %s\n",
            static_cast<unsigned int>(MAX_RETRY_COUNT),
            reason
        );
        ClearPending(STATUS_RETRY_EXCEEDED);
        return;
    }

    pending.last_sent_ms = millis();
    send_status = STATUS_RETRY_WAIT;
    Serial.printf(
        "[ESP-NOW] Chờ retry %u/%u. Lý do: %s\n",
        static_cast<unsigned int>(pending.retry_count + 1U),
        static_cast<unsigned int>(MAX_RETRY_COUNT),
        reason
    );
}

void SendPending(void) {
    if (!espnow_ready || !pending_active) return;

    // Retry luôn gửi lại chính packet cũ, không sinh sequence/nonce mới.
    send_status = STATUS_SENDING;
    pending.last_sent_ms = millis();

    portENTER_CRITICAL(&callback_mux);
    send_callback_result = CALLBACK_NONE;
    portEXIT_CRITICAL(&callback_mux);

    const esp_err_t result = esp_now_send(
        GATEWAY_MAC,
        reinterpret_cast<const uint8_t*>(&pending.packet),
        sizeof(pending.packet)
    );

    if (result != ESP_OK) {
        send_status = STATUS_SEND_ERROR;
        ScheduleRetry("ESP_NOW_SEND_CALL_FAILED");
    }
}

} // namespace

bool EspNow_Setup(void) {
    if (espnow_ready) return true;

    const uint32_t node_id = PacketMetadata_GetDeviceId();
    if (node_id == 0U ||
        !SecureSender_Init(node_id, KEY_NODE_TO_GATEWAY) ||
        !SecureResponse_Init(node_id, GATEWAY_DEVICE_ID, KEY_GATEWAY_TO_NODE)) {
        Serial.println("[ESP-NOW] Không khởi tạo được lớp bảo mật.");
        return false;
    }

    WiFi.mode(WIFI_STA);
    if (esp_now_init() != ESP_OK) return false;

    if (esp_now_register_send_cb(OnEspNowSent) != ESP_OK ||
        esp_now_register_recv_cb(OnEspNowReceived) != ESP_OK) {
        esp_now_deinit();
        return false;
    }

    esp_now_peer_info_t peer{};
    memcpy(peer.peer_addr, GATEWAY_MAC, sizeof(GATEWAY_MAC));
    peer.channel = ESP_NOW_CHANNEL;
    peer.ifidx = WIFI_IF_STA;
    peer.encrypt = false; // Payload đã được bảo vệ bằng AES-128-GCM.

    if (!esp_now_is_peer_exist(GATEWAY_MAC) && esp_now_add_peer(&peer) != ESP_OK) {
        esp_now_deinit();
        return false;
    }

    memset(&pending, 0, sizeof(pending));
    portENTER_CRITICAL(&callback_mux);
    send_callback_result = CALLBACK_NONE;
    response_ready = false;
    memset(&response_packet, 0, sizeof(response_packet));
    portEXIT_CRITICAL(&callback_mux);

    pending_active = false;
    send_status = STATUS_IDLE;
    espnow_ready = true;

    Serial.printf(
        "[ESP-NOW] Sẵn sàng | NodeID=0x%08lX | GatewayID=0x%08lX\n",
        static_cast<unsigned long>(node_id),
        static_cast<unsigned long>(GATEWAY_DEVICE_ID)
    );
    return true;
}

bool EspNow_IsReady(void) {
    return espnow_ready;
}

bool EspNow_QueuePatientEvent(const Node_Payload_t* payload) {
    if (!espnow_ready || payload == nullptr || pending_active) return false;

    Pending_Event_t next{};
    next.session_id = payload->session_id;

    const uint32_t sequence = PacketMetadata_NextSequence();
    const Secure_Sender_Result_t result = SecureSender_BuildPatientEvent(
        payload,
        sequence,
        &next.packet
    );

    if (result != SECURE_SENDER_OK) {
        Serial.printf(
            "[ESP-NOW] Không mã hóa được sự kiện. SecureSenderResult=%u\n",
            static_cast<unsigned int>(result)
        );
        return false;
    }

    pending = next;
    pending_active = true;
    send_status = STATUS_QUEUED;

    portENTER_CRITICAL(&callback_mux);
    send_callback_result = CALLBACK_NONE;
    response_ready = false;
    portEXIT_CRITICAL(&callback_mux);

    Serial.printf(
        "[ESP-NOW] Đã lưu pending | Sequence=%lu | SessionID=0x%08lX\n",
        static_cast<unsigned long>(sequence),
        static_cast<unsigned long>(pending.session_id)
    );

    SendPending();
    return true; // Packet vẫn nằm trong pending nếu lần gửi đầu thất bại.
}

void EspNow_Process(void) {
    if (!espnow_ready) return;

    // Lấy một ảnh chụp mailbox rồi xử lý bên ngoài callback Wi-Fi.
    int8_t radio_send_result = CALLBACK_NONE;
    bool has_response = false;
    Secure_Packet_t packet{};

    portENTER_CRITICAL(&callback_mux);
    radio_send_result = send_callback_result;
    send_callback_result = CALLBACK_NONE;
    if (response_ready) {
        memcpy(&packet, &response_packet, sizeof(packet));
        response_ready = false;
        has_response = true;
    }
    portEXIT_CRITICAL(&callback_mux);

    if (!pending_active) return;

    // 1. Kết quả gửi ở tầng sóng; thành công vẫn phải chờ ACK của Gateway.
    if (radio_send_result == CALLBACK_SUCCESS) {
        send_status = STATUS_ACK_PENDING;
        Serial.println("[ESP-NOW] RF send thành công; đang chờ ACK/NACK từ Gateway.");
    } else if (radio_send_result == CALLBACK_FAILED) {
        send_status = STATUS_SEND_ERROR;
        ScheduleRetry("ESP_NOW_SEND_CALLBACK_FAILED");
    }

    // 2. Xác thực, giải mã và xử lý phản hồi nghiệp vụ từ Gateway.
    if (has_response && pending_active) {
        Response_Payload_t response{};
        const Secure_Response_Decrypt_Result_t decrypt_result =
            SecureResponseDecryptor_Decrypt(
                &packet,
                pending.packet.sequence,
                pending.session_id,
                &response
            );

        if (decrypt_result != SECURE_RESPONSE_DECRYPT_OK) {
            Serial.printf(
                "[ESP-NOW] Bỏ phản hồi không hợp lệ. DecryptResult=%u\n",
                static_cast<unsigned int>(decrypt_result)
            );
        } else {
            switch (static_cast<Gateway_Response_Code_t>(response.response_code)) {
                case RESPONSE_ACK_ACCEPTED:
                    Serial.println("[ESP-NOW] Gateway đã nhận và chấp nhận sự kiện.");
                    ClearPending(STATUS_ACK_CONFIRMED);
                    break;

                case RESPONSE_ACK_DUPLICATE:
                    Serial.println("[ESP-NOW] Gateway đã nhận sự kiện này trước đó.");
                    ClearPending(STATUS_ACK_CONFIRMED);
                    break;

                case RESPONSE_NACK_BUSY:
                    ScheduleRetry("GATEWAY_BUSY");
                    break;

                case RESPONSE_NACK_INTERNAL:
                    ScheduleRetry("GATEWAY_INTERNAL_ERROR");
                    break;

                case RESPONSE_NACK_UNSUPPORTED:
                    Serial.println("[ESP-NOW] Gateway không hỗ trợ packet; dừng gửi.");
                    ClearPending(STATUS_NACK_RECEIVED);
                    break;

                default:
                    break;
            }
        }
    }

    if (!pending_active) return;

    // 3. Timeout và retry theo trạng thái hiện tại.
    const uint32_t elapsed = millis() - pending.last_sent_ms;

    if (send_status == STATUS_SENDING && elapsed >= SEND_CALLBACK_TIMEOUT_MS) {
        ScheduleRetry("SEND_CALLBACK_TIMEOUT");
    } else if (send_status == STATUS_ACK_PENDING && elapsed >= ACK_TIMEOUT_MS) {
        ScheduleRetry("GATEWAY_RESPONSE_TIMEOUT");
    } else if (send_status == STATUS_RETRY_WAIT && elapsed >= RETRY_DELAY_MS) {
        ++pending.retry_count;
        Serial.printf(
            "[ESP-NOW] Retry %u/%u | Sequence=%lu\n",
            static_cast<unsigned int>(pending.retry_count),
            static_cast<unsigned int>(MAX_RETRY_COUNT),
            static_cast<unsigned long>(pending.packet.sequence)
        );
        SendPending();
    }
}

bool EspNow_HasPendingEvent(void) {
    return pending_active;
}

Event_Send_Status_t EspNow_GetStatus(void) {
    return send_status;
}
