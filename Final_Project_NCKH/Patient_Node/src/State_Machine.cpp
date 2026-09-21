#include "Core_Logic/State_Machine.h"

#include <string.h>
#include "Audio_IO/I2S_Mic.h"
#include "Core_Logic/Quality_Check.h"

#include "Vitals_UI/PPG_Sensor.h"
#include "Vitals_UI/UI_Oled.h"

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
    //  * Packet 56 byte, sequence, nonce và tag thuộc mô-đun truyền thông.
    //  */
    Node_Payload_t ready_payload{};
    bool payload_built = false;
    bool monitor_enabled = false;
    bool monitor_buffer_ready_displayed = false;
    bool vitals_sensor_available = false;
    bool vitals_wait_logged = false;
    bool has_check_press = false;
    bool has_monitor_press = false;
    uint32_t last_check_press_ms = 0;
    uint32_t last_monitor_press_ms = 0;

    // Gom toàn bộ dữ liệu vote Monitor vào một chỗ thay vì dùng 7 biến rời.
    struct Monitor_Votes_t {
        uint8_t round = 0;
        uint8_t count[3] = {0, 0, 0};
        float score_sum[3] = {0.0f, 0.0f, 0.0f};
    } monitor_votes;

    void IRAM_ATTR ISR_BTN_Sleep(void) {
        abort_requested = true;
    }

    void IRAM_ATTR ISR_BTN_Check(void) {
        pending_button_bits |= kCheckEventBit;
    }

    void IRAM_ATTR ISR_BTN_Monitor(void) {
        pending_button_bits |= kMonitorEventBit;
    }

    const char* const kStateNames[] = {
        "STANDBY", "MANUAL_CAPTURE", "AUDIO_QUALITY", "AI_PROCESSING",
        "AUDIO_RESULT", "VITAL_CHECK", "SESSION_READY", "MONITOR_LISTENING",
        "MONITOR_CAPTURE", "ERROR"
    };
    const char* const kEventNames[] = {"MANUAL_CHECK", "MONITOR_EVENT", "STATUS"};
    const char* const kQualityNames[] = {
        "AUDIO_OK", "AUDIO_TOO_WEAK", "AUDIO_TOO_LOUD", "AUDIO_INACTIVE"
    };
    const char* const kClassificationNames[] = {"ASTHMA", "NON_ASTHMA", "UNSURE"};

    template <size_t N>
    const char* EnumName(int value, const char* const (&names)[N], const char* fallback) {
        return value >= 0 && value < static_cast<int>(N) ? names[value] : fallback;
    }

    const char* StateName(Patient_State_t value) {
        return EnumName(value, kStateNames, "UNKNOWN");
    }

    const char* EventTypeName(Event_Type_t value) {
        return EnumName(value, kEventNames, "EVENT_UNKNOWN");
    }

    const char* AudioQualityName(Audio_Quality_t value) {
        return EnumName(value, kQualityNames, "AUDIO_UNKNOWN");
    }

    const char* ClassificationName(Interface_TinyML_t value) {
        return EnumName(value, kClassificationNames, "CLASS_UNKNOWN");
    }

    int UiClassificationCode(Interface_TinyML_t value) {
        return value >= INTERFACE_ASTHMA_LIKE && value <= INTERFACE_UNSURE
            ? static_cast<int>(value)
            : static_cast<int>(INTERFACE_UNSURE);
    }

    void RenderStateOnOled(Patient_State_t state) {
        switch (state) {
            case STATE_STANDBY:
                OLED_Show_Standby();
                break;
            case STATE_MANUAL_CAPTURE:
                OLED_Show_Recording();
                break;
            case STATE_AI_PROCESSING:
                OLED_Show_Processing();
                break;
            case STATE_AUDIO_RESULT:
                OLED_Show_AI_Result(UiClassificationCode(current_session.classification));
                break;
            case STATE_VITAL_CHECK:
                OLED_Show_PlaceFinger();
                break;
            case STATE_MONITOR_LISTENING:
                // Màn này được điều khiển theo trạng thái thật của bộ đệm I2S.
                break;
            case STATE_MONITOR_CAPTURE:
                OLED_Show_SoundDetected();
                break;
            default:
                break;
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
        RenderStateOnOled(current_state);
    }

    void Reset_MonitorVotes(void) {
        monitor_votes = {};
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

    void PrepareNextMonitorCapture(void) {
        I2S_MonitorPrepareNextCapture();
        monitor_buffer_ready_displayed = false;
        OLED_Show_MonitorPreparing();
    }

    void Begin_NewSession(Event_Type_t event_type) {
        Reset_CurrentSession();
        current_session.session_id = PacketMetadata_NewSessionId();
        current_session.event_type = event_type;

        Serial.printf(
            "[SESSION] Bắt đầu %s | SessionID=0x%08lX\n",
            EventTypeName(event_type),
            static_cast<unsigned long>(current_session.session_id)
        );
    }

    uint8_t MonitorVoteIndex(Interface_TinyML_t classification) {
        return classification >= INTERFACE_ASTHMA_LIKE
            && classification <= INTERFACE_UNSURE
            ? static_cast<uint8_t>(classification)
            : static_cast<uint8_t>(INTERFACE_UNSURE);
    }

    void AddMonitorVote(Interface_TinyML_t classification, float score) {
        const uint8_t index = MonitorVoteIndex(classification);
        ++monitor_votes.round;
        ++monitor_votes.count[index];
        monitor_votes.score_sum[index] += score;
    }

    void FinishMonitorVoting(void) {
        uint8_t winner = 0;
        bool tied = false;

        for (uint8_t index = 1; index < 3; ++index) {
            if (monitor_votes.count[index] > monitor_votes.count[winner]) {
                winner = index;
                tied = false;
            } else if (monitor_votes.count[index] == monitor_votes.count[winner]) {
                tied = true;
            }
        }

        if (tied) {
            current_session.classification = INTERFACE_UNSURE;
            current_session.model_score = 0.0f;
            Serial.println("[RESULT] Ba vote không tạo được đa số, cần kiểm tra lại.");
            return;
        }

        current_session.classification = static_cast<Interface_TinyML_t>(winner);
        current_session.model_score =
            monitor_votes.score_sum[winner] / monitor_votes.count[winner];

        switch (current_session.classification) {
            case INTERFACE_ASTHMA_LIKE:
                Serial.println("[RESULT] Cảnh báo phát hiện âm thanh giống mẫu hen.");
                break;
            case INTERFACE_NON_ASTHMA:
                Serial.println("[RESULT] Không phát hiện âm thanh giống mẫu hen.");
                break;
            case INTERFACE_UNSURE:
            default:
                Serial.println("[RESULT] Không chắc chắn, cần kiểm tra lại.");
                break;
        }
    }

    void HandleMonitorAudioResult(
        Interface_TinyML_t classification,
        float safe_score
    ) {
        AddMonitorVote(classification, safe_score);

        Serial.printf(
            "[VOTE] %u/%u | Lần này=%s (%.2f%%) | ASTHMA=%u | NON_ASTHMA=%u | UNSURE=%u\n",
            monitor_votes.round,
            kMonitorVoteRounds,
            ClassificationName(classification),
            safe_score * 100.0f,
            monitor_votes.count[INTERFACE_ASTHMA_LIKE],
            monitor_votes.count[INTERFACE_NON_ASTHMA],
            monitor_votes.count[INTERFACE_UNSURE]
        );

        OLED_Show_AI_Result(UiClassificationCode(classification));
        delay(1000);

        if (monitor_votes.round < kMonitorVoteRounds) {
            PrepareNextMonitorCapture();
            StateMachine_StateTransition(STATE_MONITOR_LISTENING, "MONITOR_NEXT_VOTE");
            return;
        }

        FinishMonitorVoting();
        current_session.vitals_valid = false;
        OLED_Show_AI_Result(UiClassificationCode(current_session.classification));
        delay(1200);
        StateMachine_StateTransition(STATE_SESSION_READY, "MONITOR_VOTE_DONE");
    }

    Button_Event_t Consume_ButtonEvent(void) {
        noInterrupts();
        const uint8_t bits = pending_button_bits;
        pending_button_bits = 0;
        interrupts();

        const uint32_t now = millis();

        // Nếu hai nút đến cùng lúc, CHECK được ưu tiên và sự kiện MONITOR bị bỏ.
        if ((bits & kCheckEventBit) != 0U) {
            if (!has_check_press
                || static_cast<uint32_t>(now - last_check_press_ms) >= kButtonDebounceMs) {
                has_check_press = true;
                last_check_press_ms = now;
                return BTN_CHECK_PRESSED;
            }
        }

        if ((bits & kMonitorEventBit) != 0U) {
            if (!has_monitor_press
                || static_cast<uint32_t>(now - last_monitor_press_ms) >= kButtonDebounceMs) {
                has_monitor_press = true;
                last_monitor_press_ms = now;
                return BTN_MONITOR_PRESSED;
            }
        }

        return BTN_NONE;
    }

    // /** Chuyển Session cục bộ thành plaintext 16 byte.
    //  * Hàm này không sinh sequence/nonce và không thực hiện AES-GCM.
    //  */
    bool Build_EventPayload(
        const Patient_Session_t& session,
        Node_Payload_t* payload
    ){
        if(payload == nullptr){
            Serial.println("[PATIENT EVENT] Payload pointer không hợp lệ.");
            return false;
        }

        memset(payload, 0, sizeof(*payload));

        payload->session_id  = session.session_id;

        payload->event_type  = static_cast<uint8_t>(session.event_type);

        payload->classification  = static_cast<uint8_t>(session.classification);
        payload->model_score     = session.model_score;

        payload->audio_quality   = static_cast<uint8_t>(session.audio_quality);

        payload->vitals_valid    = session.vitals_valid ? 1U : 0U;
        payload->heart_rate      = session.vitals_valid ? session.heart_rate : 0U;
        payload->spo2            = session.vitals_valid ? session.spo2 : 0U;

        payload->battery_node    = 0U; // Sau này lấy từ mô-đun quản lý pin.

        return true;
    }

    void Handle_Standby(Button_Event_t event) {
        if (event == BTN_CHECK_PRESSED) {
            monitor_enabled = false;
            Begin_NewSession(EVENT_MANUAL_CHECK);
            OLED_Show_PlaceNearMouth();
            StateMachine_StateTransition(STATE_MANUAL_CAPTURE, "CHECK");
        } else if (event == BTN_MONITOR_PRESSED) {
            monitor_enabled = true;
            Reset_CurrentSession();
            I2S_MonitorReset();
            monitor_buffer_ready_displayed = false;
            OLED_Show_MonitorPreparing();
            Serial.println("[MONITOR] Đã bật; đang ổn định micro và tạo bộ đệm 1 giây.");
            StateMachine_StateTransition(STATE_MONITOR_LISTENING, "MONITOR_ON");
        }
    }

    void Handle_ManualCapture(void) {
        if(I2S_RecordSamples()){
            StateMachine_NotifyCaptureDone();
            return;
        }

        if(!abort_requested){
            StateMachine_ReportError("MANUAL_CAPTURE_FAILED");
        }
    }

    void Handle_AudioQuality(void) {
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

    void Handle_AIProcessing(void) {
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

    void Handle_VitalCheck(void) {
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

    void Handle_SessionReady(void) {
        if (payload_built) return;

        payload_built = Build_EventPayload(current_session, &ready_payload);
        if (!payload_built) return;

        Serial.printf(
            "[PAYLOAD] Size=%u | SessionID=0x%08lX\n",
            static_cast<unsigned int>(sizeof(ready_payload)),
            static_cast<unsigned long>(ready_payload.session_id)
        );
        Serial.printf(
            "[PAYLOAD] Event=%s | Result=%s | Score=%.2f%% | Quality=%s | Vitals=%s | Battery=%u%%\n",
            EventTypeName(current_session.event_type),
            ClassificationName(current_session.classification),
            current_session.model_score * 100.0f,
            AudioQualityName(current_session.audio_quality),
            current_session.vitals_valid ? "VALID" : "NOT_AVAILABLE",
            static_cast<unsigned int>(ready_payload.battery_node)
        );
        Serial.println("[PAYLOAD READY] Đã tạo plaintext; đang chờ AES-GCM đóng gói và lưu pending.");
    }

    void Handle_MonitorListening(Button_Event_t event) {
        if (event == BTN_MONITOR_PRESSED) {
            monitor_enabled = false;
            I2S_MonitorReset();
            monitor_buffer_ready_displayed = false;
            Reset_CurrentSession();
            Serial.println("[MONITOR] Đã tắt; đã xóa session, vote và buffer tạm.");
            StateMachine_StateTransition(STATE_STANDBY, "MONITOR_OFF");

            return;
        }

        const bool triggered = I2S_MonitorListenStep();

        if(!monitor_buffer_ready_displayed && I2S_MonitorIsBufferReady()){
            monitor_buffer_ready_displayed = true;
            OLED_Show_Monitoring();
            Serial.println("[MONITOR] Bộ đệm 1 giây đã sẵn sàng; đang chờ âm vượt ngưỡng.");
        }

        if(triggered){
            StateMachine_NotifyMonitorTriggered();
        }
    }

    void Handle_MonitorCapture(void) {
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
    monitor_buffer_ready_displayed = false;
    vitals_sensor_available = false;
    vitals_wait_logged = false;
    abort_requested = false;
    pending_button_bits = 0;
    payload_built = false;
    has_check_press = false;
    has_monitor_press = false;
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
            Handle_ManualCapture();
            break;
        case STATE_AUDIO_QUALITY:
            Handle_AudioQuality();
            break;
        case STATE_AI_PROCESSING:
            Handle_AIProcessing();
            break;
        case STATE_AUDIO_RESULT:
            Handle_AudioResult(event);
            break;
        case STATE_VITAL_CHECK:
            Handle_VitalCheck();
            break;
        case STATE_SESSION_READY:
            Handle_SessionReady();
            break;
        case STATE_MONITOR_LISTENING:
            Handle_MonitorListening(event);
            break;
        case STATE_MONITOR_CAPTURE:
            Handle_MonitorCapture();
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

    // Vote đầu tiên mở session. Các vote sau giữ nguyên session_id.
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
            monitor_votes.round,
            kMonitorVoteRounds
        );
        OLED_Show_QualityError(AudioQualityName(quality));
        delay(700);
        PrepareNextMonitorCapture();
        StateMachine_StateTransition(
            STATE_MONITOR_LISTENING,
            "MONITOR_AUDIO_REJECTED"
        );
        return;
    }

    if(quality == AUDIO_INACTIVE){
        Serial.println("[QUALITY FAIL] Âm thanh gần như không có hoạt động. Yêu cầu thu lại.");
        OLED_Show_QualityError("AUDIO INACTIVE");
        StateMachine_StateTransition(STATE_ERROR, "AUDIO_INACTIVE");

    } else if(quality == AUDIO_TOO_LOUD){
        Serial.println("[QUALITY FAIL] Âm thanh quá lớn hoặc bị clipping. Vui lòng thu lại.");
        OLED_Show_QualityError("AUDIO TOO LOUD");
        StateMachine_StateTransition(STATE_ERROR, "AUDIO_TOO_LOUD");

    } else if(quality == AUDIO_TOO_WEAK){
        Serial.println("[QUALITY FAIL] Âm thanh quá yếu. Vui lòng thu lại.");
        OLED_Show_QualityError("AUDIO TOO WEAK");
        StateMachine_StateTransition(STATE_ERROR, "AUDIO_TOO_WEAK");

    } else {
        Serial.println("[QUALITY OK] Âm thanh đạt yêu cầu. Tiến hành xử lý.");
        OLED_Show_AudioOK();
        delay(700);
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
        HandleMonitorAudioResult(classification, safe_score);
        return;
    }

    current_session.classification = classification;
    current_session.model_score = safe_score;
    StateMachine_StateTransition(STATE_AUDIO_RESULT, "AI_RESULT_SUBMITTED");
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
    OLED_Show_FinalResult(
        UiClassificationCode(current_session.classification),
        current_session.heart_rate,
        current_session.spo2
    );
    delay(1200);
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
    OLED_Show_QualityError(safe_reason);
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

    OLED_Show_DataSent();
    delay(700);
    Reset_CurrentSession();
    if(return_to_monitor) PrepareNextMonitorCapture();
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

const Node_Payload_t* StateMachine_GetReadyEventPayload(void){
    return StateMachine_IsEventPayloadReady() ? &ready_payload : nullptr;
}
