#include "State_Machine/state_machine.h"

#include "board_pinout.h"

static Patient_State_t current_state = STATE_STANDBY;

// ISR sẽ ghi vào đây
static volatile Button_Event_t pending_event = BTN_NONE;
static volatile bool abort_requested = false;

static Patient_Session_t curren_session;

static void IRAM_ATTR ISR_BTN_Sleep(void){
    abort_requested = true;
}

static void IRAM_ATTR ISR_BTN_Check(void){
    StateMachine_PushButtonEvent(BTN_CHECK_PRESSED);
}

static void IRAM_ATTR ISR_BTN_Monitor(void){
    StateMachine_PushButtonEvent(BTN_MONITOR_PRESSED);
}

static void StateMachine_StateTransition(Patient_State_t next_evt, const char* reason){
    Serial.printf("[STATE] %d --%s--> %d\n", current_state, reason, next_evt);
    current_state = next_evt;
}

static void Handle_Standby(Button_Event_t event){
    if(event == BTN_CHECK_PRESSED){
        /*
        Gọi Audio bắt đầu record
        Đi qua quality audio
        */
       StateMachine_StateTransition(STATE_MANUAL_CHECK, "CHECK");
    } else if(event == BTN_MONITOR_PRESSED){
        // Gọi audio bật I2S + VAD stream liên tục
        StateMachine_StateTransition(STATE_AUTO_MONITOR, "MONITOR");
    } 
}

static void Handle_ManualCheck(Button_Event_t event){
    // Khi audio ghi đủ 5s báo chuyển trạng thái
    StateMachine_StateTransition(STATE_PROCESSING, "CAPTURE_DONE");
}

static void Handle_AutoMonitor(Button_Event_t event){
    // Bấm lại MONITOR 1 lần nữa về STANDBY
    if(event == BTN_MONITOR_PRESSED){
        // Gọi hàm tắt I2S/VAD
        StateMachine_StateTransition(STATE_STANDBY, "MONITOR_TOGGLE_OFF");
    }
}

static void Handle_Processing(Button_Event_t event){
    // Mọi nút đều bị ignore trừ SLEEP (abort) khi đang DSP/AI.
    // KHÔNG tự chuyển đổi ở đây 
    // StateMachine_SubmitAudioResult() (do Model_AI gọi khi có kết quả thật) 
    // là nơi DUY NHẤT được chuyển sang STATE_AUDIO_RESULT.
    (void)event;
}

static void Handle_AudioResult(Button_Event_t event){
    if(event == BTN_CHECK_PRESSED){
        // Gọi hàm đo 
        StateMachine_StateTransition(STATE_VITAL_CHECK, "CHECK_VITALS");
    } else if(event == BTN_SLEEP_PRESSED){
        // Bỏ qua đo vitals, = false nhưng session hợp lệ
        StateMachine_SubmitVitals(false, 0, 0);
    }
}

static void Handle_VitalCheck(Button_Event_t event) {
    // Ignore CHECK/MONITOR khi đang đo; chờ MAX30102 gọi SubmitVitals()
    // hoặc SLEEP abort (xử lý riêng trong StateMachine_Run)
}

static void Handle_SessionReady(Button_Event_t event) {
    // Đóng gói Patient_Event_Packet_t từ current_session, gửi ESP-NOW
    // Sau khi gửi (thành công hoặc lưu pending) -> quay lại Standby
    (void)event;
}

static void Handle_Error(Button_Event_t event){
    // Xử lý cụ thể cho retry/reset
    // tạm thời SLEEP sẽ đưa về STANDBY
}

// Xử lý ABORT - Ưu tiên cao nhất
static void Handle_AbortAction(void){
    if(!abort_requested) return;

    switch(current_state){
        case STATE_VITAL_CHECK: {
            // Stop I2S -> STOP MAX30102 -> reset buffer -> OLED OFF -> ESP-NOW OFF
            StateMachine_StateTransition(STATE_STANDBY, "SLEEP_ABORT");
            break;
        }

        default: {
            // STANDBY/AUDIO_RESULT/SESSION_READY/ERROR: về Standby bình thường,
            StateMachine_StateTransition(STATE_STANDBY, "SLEEP");
            break;
        }  
    }

    abort_requested = false;
}

void StateMachine_Init(void){
    current_state = STATE_STANDBY;
    pending_event = BTN_NONE;
    abort_requested = false;
    memset(&curren_session, 0, sizeof(curren_session));

    pinMode(PIN_BTN_SLEEP, INPUT_PULLUP);
    pinMode(PIN_BTN_CHECK, INPUT_PULLUP);
    pinMode(PIN_BTN_MONITOR, INPUT_PULLUP);

    attachInterrupt(digitalPinToInterrupt(PIN_BTN_SLEEP), ISR_BTN_Sleep, FALLING);
    attachInterrupt(digitalPinToInterrupt(PIN_BTN_CHECK), ISR_BTN_Check, FALLING);
    attachInterrupt(digitalPinToInterrupt(PIN_BTN_MONITOR), ISR_BTN_Monitor, FALLING);
}


void StateMachine_Run(void){
    // SLEEP luôn được xử lý trước
    Handle_AbortAction();

    Button_Event_t event = pending_event;;
    pending_event = BTN_NONE;

    if(event == BTN_NONE && 
        current_state != STATE_PROCESSING &&
        current_state != STATE_SESSION_READY
    ){
        // Không có việc thì return
        return;
    }

    switch(current_state){
        case STATE_STANDBY:       Handle_Standby(event);      break;
        case STATE_MANUAL_CHECK:  Handle_ManualCheck(event);  break;
        case STATE_AUTO_MONITOR:  Handle_AutoMonitor(event);  break;
        case STATE_PROCESSING:    Handle_Processing(event);   break;
        case STATE_AUDIO_RESULT:  Handle_AudioResult(event);  break;
        case STATE_VITAL_CHECK:   Handle_VitalCheck(event);   break;
        case STATE_SESSION_READY: Handle_SessionReady(event); break;
        case STATE_ERROR_STATE:   Handle_Error(event);        break;
    }
}


Patient_State_t StateMachine_GetCurrentState(void){
    return current_state;
}


bool StateMachine_IsAbortRequested(void){
    return abort_requested;
}


void StateMachine_PushButtonEvent(Button_Event_t event){
    pending_event = event;
}


void StateMachine_SubmitAudioResult(
    Audio_Quality_t quality,
    Interface_TinyML_t classification,
    float model_score
){
    curren_session.audio_quality = quality;
    curren_session.classification = classification;
    curren_session.model_score = model_score;

    StateMachine_StateTransition(STATE_AUDIO_RESULT, "AI_RESULT_SUBMITTED");
}


void StateMachine_SubmitVitals(
    bool vitals_valid,
    uint16_t heart_rate,
    uint16_t spo2
){
    curren_session.vitals_valid = vitals_valid;
    curren_session.heart_rate = heart_rate;
    curren_session.spo2 = spo2;

    StateMachine_StateTransition(STATE_SESSION_READY, "VITALS_SUBMITTED");
}


const Patient_Session_t* StateMachine_GetCurrentSession(void){
    return &curren_session;
}

void StateMachine_NotifyCaptureDone(void){
    if(current_state != STATE_MANUAL_CHECK && 
        current_state != STATE_AUTO_MONITOR
    ){
        Serial.println("[STATE] Bo qua NotifyCaptureDone: sai state hien tai.");
        return;
    }
    
    StateMachine_StateTransition(STATE_PROCESSING, "CAPTURE_DONE");
}

void StateMachine_NotifyEventSent(void){
    if(current_state != STATE_SESSION_READY){
        Serial.println("[STATE] Bo qua NotifyEventSent: sai state hien tai.");
        return;
    }

    StateMachine_StateTransition(STATE_STANDBY, "SESSION_SENT");
}