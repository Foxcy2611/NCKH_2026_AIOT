#include "Core_Logic/Patient_Node_App.h"

#include <Arduino.h>

#include "Audio_IO/I2S_Mic.h"
#include "Core_Logic/State_Machine.h"
#include "DSP_Preprocessing/Mel_Scale.h"
#include "Model_AI/Interface_Asthma.h"
#include "board_pinout.h"

namespace {
Patient_State_t last_state = STATE_STANDBY;

void Stop_OnInitError(const char* message) {
    Serial.println(message);
    while (true) delay(1000);
}

void OnEnter_ManualCapture(void) {
    Process_ManualCheck_Pipeline();
}

void OnEnter_SessionReady(void) {
    // Tạm thời chưa đóng gói packet. Giữ luồng thử nghiệm có thể quay về STANDBY.
    Serial.println("[SESSION] Dữ liệu phiên đã sẵn sàng; tầng packet sẽ được ghép sau.");
    StateMachine_NotifyEventSent();
}

void Handle_StateEntry(Patient_State_t state) {
    switch (state) {
        case STATE_MANUAL_CAPTURE:
            OnEnter_ManualCapture();
            break;
        case STATE_AUDIO_RESULT:
            Serial.println("[FLOW] Nhấn CHECK để đo HR/SpO2; nhấn SLEEP để bỏ qua.");
            break;
        case STATE_VITAL_CHECK:
            Serial.println("[FLOW] Đang chờ MAX30102; hiện tại nhấn SLEEP để bỏ qua.");
            break;
        case STATE_SESSION_READY:
            OnEnter_SessionReady();
            break;
        default:
            break;
    }
}
}  // namespace

void PatientNodeApp_Init(void) {
    Serial.begin(115200);
    delay(3000);

    Serial.println("\n=== HỆ THỐNG TINYML HỖ TRỢ SÀNG LỌC ASTHMA ===");

    if (!Init_Mel_Filterbank()) {
        Stop_OnInitError("[ERROR] Không khởi tạo được Mel Filterbank.");
    }
    Serial.println("--> [INIT] 1. Khởi tạo Mel Filterbank thành công.");

    if (!Init_Asthma_Model()) {
        Stop_OnInitError("[ERROR] Không khởi tạo được model.");
    }
    Serial.println("--> [INIT] 2. Khởi tạo model TFLite thành công.");

    I2S_Mic_Init(PIN_I2S_SCK, PIN_I2S_WS, PIN_I2S_SD);
    Serial.println("--> [INIT] 3. Khởi tạo Micro thành công.");

    StateMachine_Init();
    Serial.println("--> [INIT] 4. Khởi tạo State Machine thành công.");

    last_state = StateMachine_GetCurrentState();

    Serial.println("\n=== HỆ THỐNG TINYML ASTHMA SẴN SÀNG ===");
}

void PatientNodeApp_Run(void) {
    StateMachine_Run();

    const Patient_State_t current_state = StateMachine_GetCurrentState();
    if (current_state == last_state) return;

    // Lưu state trước khi entry-action chạy vì action có thể chuyển state ngay.
    last_state = current_state;
    Handle_StateEntry(current_state);
}
