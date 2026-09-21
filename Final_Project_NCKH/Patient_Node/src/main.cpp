#include <Arduino.h>
#include <Wire.h>

#include "Audio_IO/I2S_Mic.h"
#include "Core_Logic/State_Machine.h"
#include "DSP_Preprocessing/Mel_Scale.h"
#include "Model_AI/Interface_Asthma.h"
#include "Network/EspNow_Client.h"
#include "Vitals_UI/PPG_Sensor.h"
#include "Vitals_UI/UI_Oled.h"
#include "board_pinout.h"

static void Stop_OnInitError(const char* message) {
    Serial.println(message);
    while (true) delay(1000);
}

void setup(void) {
    Serial.begin(115200);
    delay(3000);

    Serial.println("\n=== HỆ THỐNG TINYML HỖ TRỢ SÀNG LỌC ASTHMA ===");

    Wire.begin(PIN_SDA_I2C, PIN_SCL_I2C);
    OLED_Init();
    OLED_Show_Welcome();
    Serial.println("--> [INIT] 0. Khởi tạo I2C và OLED thành công.");

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

    const bool vitals_ready = MAX30102_Init();
    StateMachine_SetVitalsAvailable(vitals_ready);
    Serial.println(
        vitals_ready
            ? "--> [INIT] MAX30102 sẵn sàng."
            : "[WARNING] MAX30102 chưa sẵn sàng; có thể bỏ qua đo sinh hiệu."
    );

    if (!EspNow_Setup()) {
        Serial.println("[WARNING] ESP-NOW chưa sẵn sàng; payload sẽ giữ tại SESSION_READY.");
    } else {
        Serial.println("--> [INIT] 5. Khởi tạo ESP-NOW và AES-GCM thành công.");
    }

    OLED_Show_Standby();
    Serial.println("\n=== HỆ THỐNG TINYML ASTHMA SẴN SÀNG ===");
}

void loop(void) {
    StateMachine_Run();

    /**
     * Chỉ kết thúc SESSION_READY sau khi plaintext đã được mã hóa và packet
     * 56 byte được sao chép an toàn vào pending của EspNow_Client.
     */
    if (StateMachine_IsEventPayloadReady()) {
        const Node_Payload_t* payload =
            StateMachine_GetReadyEventPayload();

        if (EspNow_QueuePatientEvent(payload)) {
            StateMachine_NotifyEventQueued();
        }
    }

    EspNow_Process();
}
