#include "Core_Logic/State_Machine.h"

#include <string.h>
#include "Audio_IO/I2S_Mic.h"
#include "Core_Logic/Quality_Check.h"

#include "Vitals_UI/PPG_Sensor.h"

#include "Packet_Metadata.h"
#include "board_pinout.h"

// Toàn bộ biến và hàm trong anonymous namespace chỉ tồn tại trong file này,
// tương đương static nội bộ nhưng phù hợp hơn với C++.
namespace {
    constexpr uint8_t kCheckEventBit = 1U << 0;
    constexpr uint8_t kMonitorEventBit = 1U << 1;
    constexpr uint32_t kButtonDebounceMs = 180;
    constexpr uint8_t kMonitorVoteRounds = 3;

    Patient_State_t current_state = STATE_STANDBY;
    Patient_Session_t current_session;

    // ISR chỉ đặt cờ. Mọi chuyển trạng thái đều diễn ra trong StateMachine_Run().
    volatile uint8_t pending_button_bits = 0;
    volatile bool abort_requested = false;

    // /** AES-GCM MIGRATION:
    //  * State Machine chỉ giữ dữ liệu nghiệp vụ trước mã hóa.
    //  * Packet 64 byte, sequence, nonce và tag thuộc mô-đun truyền thông.
    //  */
    Patient_Event_Payload_t ready_payload{};
    bool payload_built = false;
    bool monitor_enabled = false;
    bool vitals_sensor_available = false;
    bool vitals_wait_logged = false;
    bool has_check_timestamp = false;
    bool has_monitor_timestamp = false;
    uint32_t last_check_timestamp = 0;
    uint32_t last_monitor_timestamp = 0;

    uint8_t monitor_vote_round = 0;
    uint8_t asthma_votes = 0;
    uint8_t non_asthma_votes = 0;
    uint8_t unsure_votes = 0;
    float asthma_score_sum = 0.0f;
    float non_asthma_score_sum = 0.0f;
    float unsure_score_sum = 0.0f;

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

    /** Bổ sung tên dễ đọc để log không chỉ hiện giá trị enum dạng số. */
    const char* EventTypeName(Event_Type_t event_type) {
        switch (event_type) {
            case EVENT_MANUAL_CHECK:  return "MANUAL_CHECK";
            case EVENT_MONITOR_EVENT: return "MONITOR_EVENT";
            case EVENT_STATUS:        return "STATUS";
            default:                  return "EVENT_UNKNOWN";
        }
    }

    const char* AudioQualityName(Audio_Quality_t quality) {
        switch (quality) {
            case AUDIO_OK:       return "AUDIO_OK";
            case AUDIO_TOO_WEAK: return "AUDIO_TOO_WEAK";
            case AUDIO_TOO_LOUD: return "AUDIO_TOO_LOUD";
            case AUDIO_INACTIVE: return "AUDIO_INACTIVE";
            default:             return "AUDIO_UNKNOWN";
        }
    }

    const char* ClassificationName(Interface_TinyML_t classification) {
        switch (classification) {
            case INTERFACE_ASTHMA_LIKE: return "ASTHMA";
            case INTERFACE_NON_ASTHMA:  return "NON_ASTHMA";
            case INTERFACE_UNSURE:      return "UNSURE";
            default:                    return "CLASS_UNKNOWN";
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

    void Reset_MonitorVotes(void) {
        monitor_vote_round = 0;
        asthma_votes = 0;
        non_asthma_votes = 0;
        unsure_votes = 0;
        asthma_score_sum = 0.0f;
        non_asthma_score_sum = 0.0f;
        unsure_score_sum = 0.0f;
    }

    void Reset_CurrentSession(void) {
        memset(&current_session, 0, sizeof(current_session));
        current_session.audio_quality = AUDIO_INACTIVE;
        current_session.classification = INTERFACE_UNSURE;
        current_session.vitals_valid = false;

        memset(&ready_payload, 0, sizeof(ready_payload));
        payload_built = false;
        Reset_MonitorVotes();
    }

    void Begin_NewSession(Event_Type_t event_type) {
        Reset_CurrentSession();
        current_session.session_id = PacketMetadata_NewSessionId();
        current_session.event_type = event_type;
        current_session.event_timestamp = static_cast<uint64_t>(millis());

        Serial.printf(
            "[SESSION] Bắt đầu %s | SessionID=0x%08lX | LocalMillis=%llu\n",
            EventTypeName(event_type),
            static_cast<unsigned long>(current_session.session_id),
            static_cast<unsigned long long>(current_session.event_timestamp)
        );
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

    // /** Chuyển Session cục bộ thành plaintext 24 byte.
    //  * Hàm này không sinh sequence/nonce và không thực hiện AES-GCM.
    //  */
    bool Build_EventPayload(
        const Patient_Session_t& session,
        Patient_Event_Payload_t* payload
    ){
        if(payload == nullptr){
            Serial.println("[PATIENT EVENT] Payload pointer không hợp lệ.");
            return false;
        }

        memset(payload, 0, sizeof(*payload));

        payload->session_id  = session.session_id;
        payload->timestamp   = PacketMetadata_GetTimestamp(session.event_timestamp);

        payload->event_type  = static_cast<uint8_t>(session.event_type);

        payload->classification  = static_cast<uint8_t>(session.classification);
        payload->model_score     = session.model_score;

        payload->audio_quality   = static_cast<uint8_t>(session.audio_quality);

        payload->vitals_valid    = session.vitals_valid ? 1U : 0U;
        payload->heart_rate      = session.vitals_valid ? session.heart_rate : 0U;
        payload->spo2            = session.vitals_valid ? session.spo2 : 0U;

        payload->battery         = 0U; // Sau này lấy từ mô-đun quản lý pin.

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
            I2S_MonitorReset();
            Serial.println("[MONITOR] Đã bật; đang ổn định micro và tạo bộ đệm 1 giây.");
            StateMachine_StateTransition(STATE_MONITOR_LISTENING, "MONITOR_ON");
        }
    }

    void Handle_ManualCapture(Button_Event_t event) {
        (void)event;
        
        if(I2S_RecordSamples()){
            StateMachine_NotifyCaptureDone();
            return;
        }

        if(!abort_requested){
            StateMachine_ReportError("MANUAL_CAPTURE_FAILED");
        }
    }

    void Handle_AudioQuality(Button_Event_t event) {
        (void)event;
        Audio_Quality_Metrics_t metrics = {};

        Serial.printf(
            "[AUDIO] Kiểm tra chất lượng | Nguồn=%s | Samples=%lu\n",
            EventTypeName(current_session.event_type),
            static_cast<unsigned long>(I2S_GetRecordedSampleCount())
        );

        const Audio_Quality_t quality = AudioQuality_Check(
            I2S_GetRecordedBuffer(),
            I2S_GetRecordedSampleCount(),
            &metrics
        );

        StateMachine_SubmitAudioQuality(quality);
    }

    void Handle_AIProcessing(Button_Event_t event) {
        (void)event;

        Interface_TinyML_t classification = INTERFACE_UNSURE;
        float model_score = 0.0f;

        Serial.printf(
            "[AUDIO] Bắt đầu DSP/TinyML | Nguồn=%s\n",
            EventTypeName(current_session.event_type)
        );

        if(!Process_Record_Audio(&classification, &model_score)){
            StateMachine_ReportError("AI_PROCESS_FAILED");
            return;
        }

        StateMachine_SubmitAudioResult(
            current_session.audio_quality, 
            classification,
            model_score
        );
        // Chờ TinyML gọi StateMachine_SubmitAudioResult().
    }

    void Handle_AudioResult(Button_Event_t event) {
        if (event == BTN_CHECK_PRESSED) {
            vitals_wait_logged = false;
            StateMachine_StateTransition(STATE_VITAL_CHECK, "CHECK_VITALS");
        }
    }

    void Handle_VitalCheck(Button_Event_t event) {
        (void)event;

        if(!vitals_sensor_available){
            if(!vitals_wait_logged){
                Serial.println("[VITALS] MAX30102 chưa sẵn sàng; nhấn SLEEP để bỏ qua.");
                vitals_wait_logged = true;
            }
            return;
        }

        const MAX30102_State state = MAX30102_Poll();
        
        if(state == MAX30102_STATE_RESULT_READY){
            int32_t heart_rate = 0;
            int32_t spo2 = 0;

            int8_t valid_hr = 0;
            int8_t valid_spo2 = 0;

            MAX30102_GetLastResult(
                &heart_rate, &valid_hr,
                &spo2, &valid_spo2
            );

            StateMachine_SubmitVitals(
                valid_hr && valid_spo2,
                static_cast<uint16_t>(heart_rate),
                static_cast<uint16_t>(spo2)
            );

        } else if (state == MAX30102_STATE_TIMEOUT){
            StateMachine_SubmitVitals(false, 0, 0); 
        }
        // Chờ mô-đun MAX30102 gọi StateMachine_SubmitVitals().
    }

    void Handle_SessionReady(Button_Event_t event) {
        (void)event;
        
        if(!payload_built){
            payload_built = Build_EventPayload(current_session, &ready_payload);

            if(payload_built){
                Serial.printf(
                    "[PAYLOAD] Size=%u | SessionID=0x%08lX | Timestamp=%llu%s\n",
                    static_cast<unsigned int>(sizeof(ready_payload)),
                    static_cast<unsigned long>(ready_payload.session_id),
                    static_cast<unsigned long long>(ready_payload.timestamp),
                    PacketMetadata_HasTimeSync() ? "" : " (NOT_SYNCED)"
                );
                Serial.printf(
                    "[PAYLOAD] Event=%s | Result=%s | Score=%.2f%% | Quality=%s | Vitals=%s | Battery=%u%%\n",
                    EventTypeName(current_session.event_type),
                    ClassificationName(current_session.classification),
                    current_session.model_score * 100.0f,
                    AudioQualityName(current_session.audio_quality),
                    current_session.vitals_valid ? "VALID" : "NOT_AVAILABLE",
                    static_cast<unsigned int>(ready_payload.battery)
                );
                Serial.println("[PAYLOAD READY] Đã tạo plaintext; đang chờ AES-GCM đóng gói và lưu pending.");
            }
        }
    }

    void Handle_MonitorListening(Button_Event_t event) {
        if (event == BTN_MONITOR_PRESSED) {
            monitor_enabled = false;
            I2S_MonitorReset();
            Reset_CurrentSession();
            Serial.println("[MONITOR] Đã tắt; đã xóa session, vote và buffer tạm.");
            StateMachine_StateTransition(STATE_STANDBY, "MONITOR_OFF");

            return;
        }

        if(I2S_MonitorListenStep()){
            StateMachine_NotifyMonitorTriggered();
        }
    }

    void Handle_MonitorCapture(Button_Event_t event) {
        (void)event;

        if(I2S_MonitorCaptureStep()){
            StateMachine_NotifyCaptureDone();
        }
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
                if(monitor_enabled) {
                    I2S_MonitorReset();
                    Serial.println("[MONITOR] Đã hủy; đã xóa session, vote và buffer tạm.");
                }
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
    vitals_sensor_available = false;
    vitals_wait_logged = false;
    abort_requested = false;
    pending_button_bits = 0;
    payload_built = false;
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

// ------------------- API MAIN ------------------- //

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

// --------------------------------------------------------- //

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

    // Vote đầu tiên mở session. Các vote sau giữ nguyên session_id/timestamp.
    if(current_session.session_id == 0U){
        Begin_NewSession(EVENT_MONITOR_EVENT);
    }
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

    if(quality != AUDIO_OK
        && current_session.event_type == EVENT_MONITOR_EVENT){
        Serial.printf(
            "[MONITOR] Bỏ đoạn thu do %s; vote vẫn là %u/%u và tiếp tục lắng nghe.\n",
            AudioQualityName(quality),
            monitor_vote_round,
            kMonitorVoteRounds
        );
        I2S_MonitorPrepareNextCapture();
        StateMachine_StateTransition(
            STATE_MONITOR_LISTENING,
            "MONITOR_AUDIO_REJECTED"
        );
        return;
    }

    if(quality == AUDIO_INACTIVE){
        Serial.println("[QUALITY FAIL] Âm thanh gần như không có hoạt động. Yêu cầu thu lại.");
        StateMachine_StateTransition(STATE_ERROR, "AUDIO_INACTIVE");

    } else if(quality == AUDIO_TOO_LOUD){
        Serial.println("[QUALITY FAIL] Âm thanh quá lớn hoặc bị clipping. Vui lòng thu lại.");
        StateMachine_StateTransition(STATE_ERROR, "AUDIO_TOO_LOUD");

    } else if(quality == AUDIO_TOO_WEAK){
        Serial.println("[QUALITY FAIL] Âm thanh quá yếu. Vui lòng thu lại.");
        StateMachine_StateTransition(STATE_ERROR, "AUDIO_TOO_WEAK");

    } else {
        Serial.println("[QUALITY OK] Âm thanh đạt yêu cầu. Tiến hành xử lý.");
        StateMachine_StateTransition(STATE_AI_PROCESSING, "AUDIO_OK");

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

    const float safe_score = constrain(model_score, 0.0f, 1.0f);
    current_session.audio_quality = quality;

    if (current_session.event_type == EVENT_MONITOR_EVENT) {
        ++monitor_vote_round;

        switch(classification){
            case INTERFACE_ASTHMA_LIKE:
                ++asthma_votes;
                asthma_score_sum += safe_score;
                break;
            case INTERFACE_NON_ASTHMA:
                ++non_asthma_votes;
                non_asthma_score_sum += safe_score;
                break;
            case INTERFACE_UNSURE:
            default:
                ++unsure_votes;
                unsure_score_sum += safe_score;
                break;
        }

        Serial.printf(
            "[VOTE] %u/%u | Lần này=%s (%.2f%%) | ASTHMA=%u | NON_ASTHMA=%u | UNSURE=%u\n",
            monitor_vote_round,
            kMonitorVoteRounds,
            ClassificationName(classification),
            safe_score * 100.0f,
            asthma_votes,
            non_asthma_votes,
            unsure_votes
        );

        if(monitor_vote_round < kMonitorVoteRounds){
            I2S_MonitorPrepareNextCapture();
            StateMachine_StateTransition(
                STATE_MONITOR_LISTENING,
                "MONITOR_NEXT_VOTE"
            );
            return;
        }

        if(asthma_votes > non_asthma_votes && asthma_votes > unsure_votes){
            current_session.classification = INTERFACE_ASTHMA_LIKE;
            current_session.model_score = asthma_score_sum / asthma_votes;
            Serial.println("[RESULT] Cảnh báo phát hiện âm thanh giống mẫu hen.");
        } else if(non_asthma_votes > asthma_votes
            && non_asthma_votes > unsure_votes){
            current_session.classification = INTERFACE_NON_ASTHMA;
            current_session.model_score = non_asthma_score_sum / non_asthma_votes;
            Serial.println("[RESULT] Không phát hiện âm thanh giống mẫu hen.");
        } else if(unsure_votes > asthma_votes && unsure_votes > non_asthma_votes){
            current_session.classification = INTERFACE_UNSURE;
            current_session.model_score = unsure_score_sum / unsure_votes;
            Serial.println("[RESULT] Không chắc chắn, cần kiểm tra lại.");
        } else {
            // Trường hợp 1-1-1: không có kết quả chiếm đa số.
            current_session.classification = INTERFACE_UNSURE;
            current_session.model_score = 0.0f;
            Serial.println("[RESULT] Ba vote không tạo được đa số, cần kiểm tra lại.");
        }

        current_session.vitals_valid = false;
        StateMachine_StateTransition(STATE_SESSION_READY, "MONITOR_VOTE_DONE");
    } else {
        current_session.classification = classification;
        current_session.model_score = safe_score;
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

    const char* safe_reason = reason != nullptr ? reason : "MODULE_ERROR";
    Serial.printf(
        "[ERROR] State=%s | Lỗi=%s\n",
        StateName(current_state),
        safe_reason
    );
    StateMachine_StateTransition(STATE_ERROR, safe_reason);
}

const Patient_Session_t* StateMachine_GetCurrentSession(void) {
    return &current_session;
}

void StateMachine_NotifyEventQueued(void) {
    if (current_state != STATE_SESSION_READY) {
        Serial.println("[STATE] Bỏ qua EventQueued: sai state hiện tại.");
        return;
    }

    if (!payload_built) {
        Serial.println("[STATE] Bỏ qua EventQueued: payload chưa sẵn sàng.");
        return;
    }

    const bool return_to_monitor =
        monitor_enabled && current_session.event_type == EVENT_MONITOR_EVENT;

    Reset_CurrentSession();
    if(return_to_monitor) I2S_MonitorPrepareNextCapture();
    StateMachine_StateTransition(
        return_to_monitor ? STATE_MONITOR_LISTENING : STATE_STANDBY,
        return_to_monitor ? "EVENT_QUEUED_MONITOR" : "EVENT_QUEUED"
    );
}

void StateMachine_SetVitalsAvailable(bool available){
    vitals_sensor_available = available;
    vitals_wait_logged = false;
}

bool StateMachine_IsEventPayloadReady(void){
    return current_state == STATE_SESSION_READY && payload_built;
}

const Patient_Event_Payload_t* StateMachine_GetReadyEventPayload(void){
    return StateMachine_IsEventPayloadReady() ? &ready_payload : nullptr;
}
