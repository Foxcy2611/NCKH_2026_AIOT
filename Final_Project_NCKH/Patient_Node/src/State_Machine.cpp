#include "Core_Logic/State_Machine.h"

#include <string.h>

#include "Packet_Metadata.h"
#include "Checksum_CRC32.h"
#include "board_pinout.h"

// Toàn bộ biến và hàm trong anonymous namespace chỉ tồn tại trong file này,
// tương đương static nội bộ nhưng phù hợp hơn với C++.
namespace {
    constexpr uint8_t kCheckEventBit = 1U << 0;
    constexpr uint8_t kMonitorEventBit = 1U << 1;
    constexpr uint32_t kButtonDebounceMs = 180;

    Patient_State_t current_state = STATE_STANDBY;
    Patient_Session_t current_session;

    // ISR chỉ đặt cờ. Mọi chuyển trạng thái đều diễn ra trong StateMachine_Run().
    volatile uint8_t pending_button_bits = 0;
    volatile bool abort_requested = false;

    Patient_Event_Packet_t ready_packet{};
    bool packet_built = false;
    bool packet_queued = false;
    bool monitor_enabled = false;
    bool has_check_timestamp = false;
    bool has_monitor_timestamp = false;
    uint32_t last_check_timestamp = 0;
    uint32_t last_monitor_timestamp = 0;

    void IRAM_ATTR ISR_BTN_Sleep(void) {
        abort_requested = true;
    }

    void IRAM_ATTR ISR_BTN_Check(void) {
        pending_button_bits |= kCheckEventBit;
    }

    void IRAM_ATTR ISR_BTN_Monitor(void) {
        pending_button_bits |= kMonitorEventBit;
    }

    const char* StateName(Patient_State_t state) {
        switch (state) {
            case STATE_STANDBY:           return "STANDBY";
            case STATE_MANUAL_CAPTURE:    return "MANUAL_CAPTURE";
            case STATE_AUDIO_QUALITY:     return "AUDIO_QUALITY";
            case STATE_AI_PROCESSING:     return "AI_PROCESSING";
            case STATE_AUDIO_RESULT:      return "AUDIO_RESULT";
            case STATE_VITAL_CHECK:       return "VITAL_CHECK";
            case STATE_SESSION_READY:     return "SESSION_READY";
            case STATE_MONITOR_LISTENING: return "MONITOR_LISTENING";
            case STATE_MONITOR_CAPTURE:   return "MONITOR_CAPTURE";
            case STATE_ERROR:             return "ERROR";
            default:                      return "UNKNOWN";
        }
    }

    void StateMachine_StateTransition(Patient_State_t next_state, const char* reason) {
        if (next_state == current_state) return;

        Serial.printf(
            "[STATE] %s --%s--> %s\n",
            StateName(current_state),
            reason,
            StateName(next_state)
        );
        current_state = next_state;
    }

    void Reset_CurrentSession(void) {
        memset(&current_session, 0, sizeof(current_session));
        current_session.audio_quality = AUDIO_INACTIVE;
        current_session.classification = INTERFACE_UNSURE;
        current_session.vitals_valid = false;

        memset(&ready_packet, 0, sizeof(ready_packet));
        packet_built = false;
        packet_queued = false;
    }

    void Begin_NewSession(Event_Type_t event_type) {
        Reset_CurrentSession();
        current_session.session_id = PacketMetadata_NewSessionId();
        current_session.event_type = event_type;
        current_session.event_timestamp = static_cast<uint64_t>(millis());
    }

    Button_Event_t Consume_ButtonEvent(void) {
        noInterrupts();
        const uint8_t bits = pending_button_bits;
        pending_button_bits = 0;
        interrupts();

        const uint32_t now = millis();

        // Nếu hai nút đến cùng lúc, CHECK được ưu tiên và sự kiện MONITOR bị bỏ.
        if ((bits & kCheckEventBit) != 0U) {
            if (!has_check_timestamp
                || static_cast<uint32_t>(now - last_check_timestamp) >= kButtonDebounceMs) {
                has_check_timestamp = true;
                last_check_timestamp = now;
                return BTN_CHECK_PRESSED;
            }
        }

        if ((bits & kMonitorEventBit) != 0U) {
            if (!has_monitor_timestamp
                || static_cast<uint32_t>(now - last_monitor_timestamp) >= kButtonDebounceMs) {
                has_monitor_timestamp = true;
                last_monitor_timestamp = now;
                return BTN_MONITOR_PRESSED;
            }
        }

        return BTN_NONE;
    }

        bool Build_EventPacket(
        const Patient_Session_t& session,
        Patient_Event_Packet_t* packet
    ){
        if(packet == nullptr){
            Serial.println("[PATIENT EVENT] Packet pointer không hợp lệ.");
            return false;
        }

        memset(packet, 0, sizeof(*packet));

        packet->device_id   = PacketMetadata_GetDeviceId();
        packet->sequence    = PacketMetadata_NextSequence();
        packet->session_id  = session.session_id;
        packet->timestamp   = PacketMetadata_GetTimestamp(session.event_timestamp);

        packet->event_type  = static_cast<uint8_t>(session.event_type);

        packet->classification  = static_cast<uint8_t>(session.classification);
        packet->model_score     = session.model_score;

        packet->audio_quality   = static_cast<uint8_t>(session.audio_quality);

        packet->vitals_valid    = session.vitals_valid;
        packet->heart_rate      = session.vitals_valid ? session.heart_rate : 0U;
        packet->spo2            = session.vitals_valid ? session.spo2 : 0U;

        packet->battery         = 0U; // Sau này thay

        packet->crc32           = Crc32_Compute(packet, offsetof(Patient_Event_Packet_t, crc32));

        return true;
    }

    void Handle_Standby(Button_Event_t event) {
        if (event == BTN_CHECK_PRESSED) {
            monitor_enabled = false;
            Begin_NewSession(EVENT_MANUAL_CHECK);
            StateMachine_StateTransition(STATE_MANUAL_CAPTURE, "CHECK");
        } else if (event == BTN_MONITOR_PRESSED) {
            monitor_enabled = true;
            Reset_CurrentSession();
            StateMachine_StateTransition(STATE_MONITOR_LISTENING, "MONITOR_ON");
        }
    }

    void Handle_ManualCapture(Button_Event_t event) {
        (void)event;
        // Chờ Audio_IO gọi StateMachine_NotifyCaptureDone().
    }

    void Handle_AudioQuality(Button_Event_t event) {
        (void)event;
        // Chờ Quality Gate gọi StateMachine_SubmitAudioQuality().
    }

    void Handle_AIProcessing(Button_Event_t event) {
        (void)event;
        // Chờ TinyML gọi StateMachine_SubmitAudioResult().
    }

    void Handle_AudioResult(Button_Event_t event) {
        if (event == BTN_CHECK_PRESSED) {
            StateMachine_StateTransition(STATE_VITAL_CHECK, "CHECK_VITALS");
        }
    }

    void Handle_VitalCheck(Button_Event_t event) {
        (void)event;
        // Chờ mô-đun MAX30102 gọi StateMachine_SubmitVitals().
    }

    void Handle_SessionReady(Button_Event_t event) {
        (void)event;
        
        if(!packet_built){

            packet_built = Build_EventPacket(current_session, &ready_packet);
        }

        if(packet_built && !packet_queued){
            // Đưa vào now
            // packet_queued = EspNow_Enqueue(ready_packet);
        }
    }

    void Handle_MonitorListening(Button_Event_t event) {
        if (event == BTN_MONITOR_PRESSED) {
            monitor_enabled = false;
            Reset_CurrentSession();
            StateMachine_StateTransition(STATE_STANDBY, "MONITOR_OFF");
        }
        // VAD gọi StateMachine_NotifyMonitorTriggered() khi phát hiện âm thanh.
    }

    void Handle_MonitorCapture(Button_Event_t event) {
        (void)event;
        // Chờ Audio_IO gọi StateMachine_NotifyCaptureDone().
    }

    void Handle_Error(Button_Event_t event) {
        if (event == BTN_CHECK_PRESSED) {
            monitor_enabled = false;
            Begin_NewSession(EVENT_MANUAL_CHECK);
            StateMachine_StateTransition(STATE_MANUAL_CAPTURE, "ERROR_RETRY");
        }
    }

    // SLEEP/STOP có mức ưu tiên cao nhất và được xử lý trước nút thường.
    bool Handle_AbortAction(void) {
        if (!abort_requested) return false;

        noInterrupts();
        abort_requested = false;
        pending_button_bits = 0;
        interrupts();

        switch (current_state) {
            case STATE_AUDIO_RESULT:
            case STATE_VITAL_CHECK:
                // Giữ kết quả âm thanh, chỉ bỏ qua phần đo sinh hiệu.
                current_session.vitals_valid = false;
                current_session.heart_rate = 0;
                current_session.spo2 = 0;
                StateMachine_StateTransition(STATE_SESSION_READY, "SKIP_VITALS");
                break;

            case STATE_SESSION_READY:
                // Không xóa phiên đã hoàn thành đang chờ gửi.
                break;

            case STATE_STANDBY:
                // Chế độ tiết kiệm điện sẽ được bổ sung ở bước nguồn.
                break;

            default:
                // Hủy phiên đang thu/xử lý hoặc tắt chế độ Monitor.
                monitor_enabled = false;
                Reset_CurrentSession();
                StateMachine_StateTransition(STATE_STANDBY, "SLEEP_ABORT");
                break;
        }

        return true;
    }
}  // namespace

void StateMachine_Init(void) {
    PacketMetadata_Init();
    current_state = STATE_STANDBY;
    monitor_enabled = false;
    abort_requested = false;
    pending_button_bits = 0;
    packet_built = false;
    has_check_timestamp = false;
    has_monitor_timestamp = false;
    Reset_CurrentSession();

    pinMode(PIN_BTN_SLEEP, INPUT_PULLUP);
    pinMode(PIN_BTN_CHECK, INPUT_PULLUP);
    pinMode(PIN_BTN_MONITOR, INPUT_PULLUP);

    attachInterrupt(digitalPinToInterrupt(PIN_BTN_SLEEP), ISR_BTN_Sleep, FALLING);
    attachInterrupt(digitalPinToInterrupt(PIN_BTN_CHECK), ISR_BTN_Check, FALLING);
    attachInterrupt(digitalPinToInterrupt(PIN_BTN_MONITOR), ISR_BTN_Monitor, FALLING);
}

void StateMachine_Run(void) {
    if (Handle_AbortAction()) return;

    const Button_Event_t event = Consume_ButtonEvent();

    switch (current_state) {
        case STATE_STANDBY:
            Handle_Standby(event);
            break;
        case STATE_MANUAL_CAPTURE:
            Handle_ManualCapture(event);
            break;
        case STATE_AUDIO_QUALITY:
            Handle_AudioQuality(event);
            break;
        case STATE_AI_PROCESSING:
            Handle_AIProcessing(event);
            break;
        case STATE_AUDIO_RESULT:
            Handle_AudioResult(event);
            break;
        case STATE_VITAL_CHECK:
            Handle_VitalCheck(event);
            break;
        case STATE_SESSION_READY:
            Handle_SessionReady(event);
            break;
        case STATE_MONITOR_LISTENING:
            Handle_MonitorListening(event);
            break;
        case STATE_MONITOR_CAPTURE:
            Handle_MonitorCapture(event);
            break;
        case STATE_ERROR:
            Handle_Error(event);
            break;
        default:
            Reset_CurrentSession();
            StateMachine_StateTransition(STATE_ERROR, "INVALID_STATE");
            break;
    }
}

Patient_State_t StateMachine_GetCurrentState(void) {
    return current_state;
}

bool StateMachine_IsAbortRequested(void) {
    return abort_requested;
}

void StateMachine_PushButtonEvent(Button_Event_t event) {
    switch (event) {
        case BTN_CHECK_PRESSED:
            pending_button_bits |= kCheckEventBit;
            break;
        case BTN_MONITOR_PRESSED:
            pending_button_bits |= kMonitorEventBit;
            break;
        case BTN_SLEEP_PRESSED:
            abort_requested = true;
            break;
        case BTN_NONE:
        default:
            break;
    }
}

void StateMachine_NotifyMonitorTriggered(void) {
    if (current_state != STATE_MONITOR_LISTENING || !monitor_enabled) {
        Serial.println("[STATE] Bỏ qua MonitorTriggered: sai state hiện tại.");
        return;
    }

    Begin_NewSession(EVENT_MONITOR_EVENT);
    StateMachine_StateTransition(STATE_MONITOR_CAPTURE, "VAD_TRIGGER");
}

void StateMachine_NotifyCaptureDone(void) {
    if (current_state != STATE_MANUAL_CAPTURE
        && current_state != STATE_MONITOR_CAPTURE) {
        Serial.println("[STATE] Bỏ qua CaptureDone: sai state hiện tại.");
        return;
    }

    StateMachine_StateTransition(STATE_AUDIO_QUALITY, "CAPTURE_DONE");
}

void StateMachine_SubmitAudioQuality(Audio_Quality_t quality) {
    if (current_state != STATE_AUDIO_QUALITY) {
        Serial.println("[STATE] Bỏ qua AudioQuality: sai state hiện tại.");
        return;
    }

    current_session.audio_quality = quality;
    if (quality == AUDIO_OK) {
        StateMachine_StateTransition(STATE_AI_PROCESSING, "AUDIO_QUALITY_OK");
    } else {
        StateMachine_StateTransition(STATE_ERROR, "AUDIO_QUALITY_FAILED");
    }
}

void StateMachine_SubmitAudioResult(
    Audio_Quality_t quality,
    Interface_TinyML_t classification,
    float model_score
) {
    if (current_state != STATE_AI_PROCESSING) {
        Serial.println("[STATE] Bỏ qua AudioResult: sai state hiện tại.");
        return;
    }

    current_session.audio_quality = quality;
    current_session.classification = classification;
    current_session.model_score = constrain(model_score, 0.0f, 1.0f);

    if (current_session.event_type == EVENT_MONITOR_EVENT) {
        current_session.vitals_valid = false;
        StateMachine_StateTransition(STATE_SESSION_READY, "MONITOR_AI_RESULT");
    } else {
        StateMachine_StateTransition(STATE_AUDIO_RESULT, "AI_RESULT_SUBMITTED");
    }
}

void StateMachine_SubmitVitals(
    bool vitals_valid,
    uint16_t heart_rate,
    uint16_t spo2
) {
    if (current_state != STATE_VITAL_CHECK) {
        Serial.println("[STATE] Bỏ qua Vitals: sai state hiện tại.");
        return;
    }

    current_session.vitals_valid = vitals_valid;
    current_session.heart_rate = vitals_valid ? heart_rate : 0;
    current_session.spo2 = vitals_valid
        ? static_cast<uint8_t>(constrain(spo2, static_cast<uint16_t>(0), static_cast<uint16_t>(100)))
        : 0;
    StateMachine_StateTransition(STATE_SESSION_READY, "VITALS_SUBMITTED");
}

void StateMachine_ReportError(const char* reason) {
    if (current_state == STATE_STANDBY || current_state == STATE_SESSION_READY) {
        Serial.println("[STATE] Bỏ qua ReportError: sai state hiện tại.");
        return;
    }

    StateMachine_StateTransition(STATE_ERROR, reason != nullptr ? reason : "MODULE_ERROR");
}

const Patient_Session_t* StateMachine_GetCurrentSession(void) {
    return &current_session;
}

void StateMachine_NotifyEventSent(void) {
    if (current_state != STATE_SESSION_READY) {
        Serial.println("[STATE] Bỏ qua EventSent: sai state hiện tại.");
        return;
    }

    const bool return_to_monitor =
        monitor_enabled && current_session.event_type == EVENT_MONITOR_EVENT;

    Reset_CurrentSession();
    StateMachine_StateTransition(
        return_to_monitor ? STATE_MONITOR_LISTENING : STATE_STANDBY,
        return_to_monitor ? "SESSION_SENT_MONITOR" : "SESSION_SENT"
    );
}
