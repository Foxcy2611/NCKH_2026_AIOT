#include "Network/EspNow_Client.h"

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>

#include <string.h>

#include "Network/Secure_Response_Decryptor.h"
#include "Network/Secure_Sender.h"
#include "Packet_Metadata.h"

#define ESP_NOW_CHANNEL 0

namespace {

    /**
     * CẤU HÌNH TẠM TRONG GIAI ĐOẠN HOÀN THIỆN NODE.
     * Hai chiều truyền dùng hai khóa riêng biệt.
     */
    const uint8_t Gateway_MAC[6] = {
        0x02, 0x00, 0x00,
        0x00, 0x00, 0x01
    };

    constexpr uint32_t GATEWAY_DEVICE_ID = 0x47575431UL;

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

    bool is_espnow_ready = false;
    volatile Event_Send_Status_t send_status = STATUS_IDLE;
    Pending_ACK_Entry_t pending_entry{};
    volatile bool pending_active = false;

    portMUX_TYPE callback_mux = portMUX_INITIALIZER_UNLOCKED;
    volatile bool send_callback_ready = false;
    volatile bool send_callback_success = false;
    volatile bool received_packet_ready = false;
    Secure_EspNow_Packet_t received_packet{};

    void EspNow_SetStatus(Event_Send_Status_t status){
        send_status = status;
        if(pending_active) pending_entry.status = status;
    }

    void EspNow_ClearCallbackFlags(void){
        portENTER_CRITICAL(&callback_mux);
        send_callback_ready = false;
        send_callback_success = false;
        received_packet_ready = false;
        memset(&received_packet, 0, sizeof(received_packet));
        portEXIT_CRITICAL(&callback_mux);
    }

    void EspNow_ClearPending(Event_Send_Status_t final_status){
        memset(&pending_entry, 0, sizeof(pending_entry));
        pending_active = false;
        send_status = final_status;
    }

    void EspNow_FinishRetryExceeded(const char* reason){
        Serial.printf(
            "[ESP-NOW] Đã vượt quá %u lần retry. Lý do cuối: %s\n",
            static_cast<unsigned int>(MAX_RETRY_COUNT),
            reason
        );
        EspNow_ClearPending(STATUS_RETRY_EXCEEDED);
    }

    void EspNow_ScheduleRetry(const char* reason){
        if(!pending_active) return;

        if(pending_entry.retry_count >= MAX_RETRY_COUNT){
            EspNow_FinishRetryExceeded(reason);
            return;
        }

        pending_entry.last_sent_timestamp = millis();
        EspNow_SetStatus(STATUS_RETRY_WAIT);
        Serial.printf(
            "[ESP-NOW] Chờ retry %u/%u. Lý do: %s\n",
            static_cast<unsigned int>(pending_entry.retry_count + 1U),
            static_cast<unsigned int>(MAX_RETRY_COUNT),
            reason
        );
    }

    void EspNow_OnSent(
        const uint8_t* mac_addr,
        esp_now_send_status_t status
    ){
        if(mac_addr == nullptr || memcmp(mac_addr, Gateway_MAC, 6) != 0) return;

        portENTER_CRITICAL(&callback_mux);
        if(pending_active && send_status == STATUS_SENDING){
            send_callback_success = status == ESP_NOW_SEND_SUCCESS;
            send_callback_ready = true;
        }
        portEXIT_CRITICAL(&callback_mux);
    }

    /**
     * Callback chỉ kiểm tra nguồn/kích thước, chép đúng 64 byte và đặt cờ.
     * AES-GCM được xử lý trong EspNow_Process(), không chạy trong Wi-Fi task.
     */
    void EspNow_OnReceive(
        const uint8_t* mac_addr,
        const uint8_t* data,
        int data_len
    ){
        if(mac_addr == nullptr || data == nullptr ||
            memcmp(mac_addr, Gateway_MAC, 6) != 0 ||
            data_len != static_cast<int>(SECURE_PACKET_SIZE)){
            return;
        }

        portENTER_CRITICAL(&callback_mux);
        memcpy(&received_packet, data, SECURE_PACKET_SIZE);
        received_packet_ready = true;
        portEXIT_CRITICAL(&callback_mux);
    }

    bool EspNow_TakeSendResult(bool* success){
        if(success == nullptr) return false;

        bool ready = false;
        portENTER_CRITICAL(&callback_mux);
        if(send_callback_ready){
            *success = send_callback_success;
            send_callback_ready = false;
            ready = true;
        }
        portEXIT_CRITICAL(&callback_mux);
        return ready;
    }

    bool EspNow_TakeReceivedPacket(Secure_EspNow_Packet_t* packet){
        if(packet == nullptr) return false;

        bool ready = false;
        portENTER_CRITICAL(&callback_mux);
        if(received_packet_ready){
            memcpy(packet, &received_packet, SECURE_PACKET_SIZE);
            received_packet_ready = false;
            ready = true;
        }
        portEXIT_CRITICAL(&callback_mux);
        return ready;
    }

    void EspNow_UpdateTime(const Gateway_Response_Payload_t& response){
        if(response.time_valid == 0U || response.gateway_timestamp == 0U) return;

        const int64_t offset_ms = static_cast<int64_t>(response.gateway_timestamp)
            - static_cast<int64_t>(millis());
        PacketMetadata_SetTimeOffset(offset_ms);
        Serial.println("[ESP-NOW] Đã đồng bộ offset thời gian từ Gateway.");
    }

    void EspNow_HandleResponse(const Secure_EspNow_Packet_t& packet){
        if(!pending_active) return;

        Gateway_Response_Payload_t response{};
        const Secure_Response_Decrypt_Result_t result =
            SecureResponseDecryptor_Decrypt(
                &packet,
                pending_entry.packet.sequence,
                pending_entry.session_id,
                &response
            );

        if(result != SECURE_RESPONSE_DECRYPT_OK){
            Serial.printf(
                "[ESP-NOW] Bỏ phản hồi không hợp lệ. DecryptResult=%u\n",
                static_cast<unsigned int>(result)
            );
            return;
        }

        EspNow_UpdateTime(response);

        switch (static_cast<Gateway_Response_Code_t>(response.response_code)){
            case RESPONSE_ACK_ACCEPTED:
                Serial.printf(
                    "[ESP-NOW] Gateway ACK thành công. Sequence=%lu | SessionID=0x%08lX\n",
                    static_cast<unsigned long>(pending_entry.packet.sequence),
                    static_cast<unsigned long>(pending_entry.session_id)
                );
                EspNow_ClearPending(STATUS_ACK_CONFIRMED);
                break;

            case RESPONSE_ACK_DUPLICATE:
                Serial.println("[ESP-NOW] Gateway báo packet trùng; sự kiện đã được nhận trước đó.");
                EspNow_ClearPending(STATUS_ACK_CONFIRMED);
                break;

            case RESPONSE_NACK_BUSY:
                EspNow_SetStatus(STATUS_NACK_RECEIVED);
                EspNow_ScheduleRetry("GATEWAY_BUSY");
                break;

            case RESPONSE_NACK_INTERNAL:
                EspNow_SetStatus(STATUS_NACK_RECEIVED);
                EspNow_ScheduleRetry("GATEWAY_INTERNAL_ERROR");
                break;

            case RESPONSE_NACK_UNSUPPORTED:
                Serial.println("[ESP-NOW] Gateway không hỗ trợ packet; dừng gửi sự kiện này.");
                EspNow_ClearPending(STATUS_NACK_RECEIVED);
                break;

            default:
                // SecureResponseDecryptor đã chặn response_code ngoài miền cho phép.
                break;
        }
    }

} // namespace

bool EspNow_Setup(void){
    if(is_espnow_ready) return true;

    const uint32_t node_device_id = PacketMetadata_GetDeviceId();
    if(node_device_id == 0U ||
        !SecureSender_Init(node_device_id, KEY_NODE_TO_GATEWAY) ||
        !SecureResponse_Init(
            node_device_id,
            GATEWAY_DEVICE_ID,
            KEY_GATEWAY_TO_NODE
        )){
        Serial.println("[ESP-NOW] Không khởi tạo được lớp bảo mật.");
        return false;
    }

    WiFi.mode(WIFI_STA);

    if(esp_now_init() != ESP_OK) return false;

    if(esp_now_register_send_cb(EspNow_OnSent) != ESP_OK){
        esp_now_deinit();
        return false;
    }

    if(esp_now_register_recv_cb(EspNow_OnReceive) != ESP_OK){
        esp_now_unregister_send_cb();
        esp_now_deinit();
        return false;
    }

    esp_now_peer_info_t peer_info{};
    memcpy(peer_info.peer_addr, Gateway_MAC, 6);
    peer_info.channel = ESP_NOW_CHANNEL;
    peer_info.ifidx = WIFI_IF_STA;
    peer_info.encrypt = false;

    if(!esp_now_is_peer_exist(Gateway_MAC) &&
        esp_now_add_peer(&peer_info) != ESP_OK){
        esp_now_unregister_recv_cb();
        esp_now_unregister_send_cb();
        esp_now_deinit();
        return false;
    }

    memset(&pending_entry, 0, sizeof(pending_entry));
    pending_active = false;
    EspNow_ClearCallbackFlags();
    is_espnow_ready = true;
    send_status = STATUS_IDLE;

    Serial.printf(
        "[ESP-NOW] Sẵn sàng | NodeID=0x%08lX | GatewayID=0x%08lX\n",
        static_cast<unsigned long>(node_device_id),
        static_cast<unsigned long>(GATEWAY_DEVICE_ID)
    );
    return true;
}

bool EspNow_IsReady(void){
    return is_espnow_ready;
}

bool EspNow_SendSecurePacket(const Secure_EspNow_Packet_t* packet){
    if(!is_espnow_ready || packet == nullptr) return false;

    EspNow_SetStatus(STATUS_SENDING);
    if(pending_active) pending_entry.last_sent_timestamp = millis();

    const esp_err_t result = esp_now_send(
        Gateway_MAC,
        reinterpret_cast<const uint8_t*>(packet),
        SECURE_PACKET_SIZE
    );

    if(result != ESP_OK){
        EspNow_SetStatus(STATUS_SEND_ERROR);
        return false;
    }

    return true;
}

bool EspNow_QueuePatientEvent(const Patient_Event_Payload_t* payload){
    if(!is_espnow_ready || payload == nullptr || pending_active) return false;

    Pending_ACK_Entry_t new_entry{};
    new_entry.session_id = payload->session_id;
    new_entry.retry_count = 0U;
    new_entry.status = STATUS_QUEUED;

    const uint32_t sequence = PacketMetadata_NextSequence();
    const Secure_Sender_Result_t build_result =
        SecureSender_BuildPatientEvent(payload, sequence, &new_entry.packet);

    if(build_result != SECURE_SENDER_OK){
        Serial.printf(
            "[ESP-NOW] Không đóng gói được Patient Event. SecureSenderResult=%u\n",
            static_cast<unsigned int>(build_result)
        );
        return false;
    }

    pending_entry = new_entry;
    pending_active = true;
    EspNow_ClearCallbackFlags();
    EspNow_SetStatus(STATUS_QUEUED);

    Serial.printf(
        "[ESP-NOW] Đã lưu pending | Sequence=%lu | SessionID=0x%08lX\n",
        static_cast<unsigned long>(sequence),
        static_cast<unsigned long>(pending_entry.session_id)
    );

    // Queue vẫn thành công nếu lần send đầu lỗi vì packet đã được giữ để retry.
    if(!EspNow_SendSecurePacket(&pending_entry.packet)){
        EspNow_ScheduleRetry("ESP_NOW_SEND_CALL_FAILED");
    }

    return true;
}

void EspNow_Process(void){
    if(!is_espnow_ready) return;

    Secure_EspNow_Packet_t packet{};
    if(EspNow_TakeReceivedPacket(&packet)){
        EspNow_HandleResponse(packet);
    }

    if(!pending_active) return;

    bool link_send_success = false;
    if(EspNow_TakeSendResult(&link_send_success)){
        if(link_send_success){
            EspNow_SetStatus(STATUS_ACK_PENDING);
            Serial.println("[ESP-NOW] RF send thành công; đang chờ ACK/NACK bảo mật từ Gateway.");
        } else {
            EspNow_SetStatus(STATUS_SEND_ERROR);
            EspNow_ScheduleRetry("ESP_NOW_SEND_CALLBACK_FAILED");
        }
    }

    if(!pending_active) return;

    const uint32_t elapsed = millis() - pending_entry.last_sent_timestamp;

    if(send_status == STATUS_SENDING && elapsed >= SEND_CALLBACK_TIMEOUT_MS){
        EspNow_ScheduleRetry("SEND_CALLBACK_TIMEOUT");
        return;
    }

    if(send_status == STATUS_ACK_PENDING && elapsed >= ACK_TIMEOUT_MS){
        EspNow_ScheduleRetry("GATEWAY_RESPONSE_TIMEOUT");
        return;
    }

    if(send_status == STATUS_RETRY_WAIT && elapsed >= RETRY_DELAY_MS){
        ++pending_entry.retry_count;
        Serial.printf(
            "[ESP-NOW] Gửi lại nguyên packet | Retry=%u/%u | Sequence=%lu\n",
            static_cast<unsigned int>(pending_entry.retry_count),
            static_cast<unsigned int>(MAX_RETRY_COUNT),
            static_cast<unsigned long>(pending_entry.packet.sequence)
        );

        if(!EspNow_SendSecurePacket(&pending_entry.packet)){
            EspNow_ScheduleRetry("ESP_NOW_RETRY_CALL_FAILED");
        }
    }
}

bool EspNow_HasPendingEvent(void){
    return pending_active;
}

Event_Send_Status_t EspNow_GetStatus(void){
    return send_status;
}
