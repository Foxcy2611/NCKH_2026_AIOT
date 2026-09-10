#include <Arduino.h>


#include "Audio_IO/I2S_Mic.h"
#include "Core_Logic/State_Machine.h"
#include "DSP_Preprocessing/Mel_Scale.h"
#include "Model_AI/Interface_Asthma.h"
#include "board_pinout.h"

static void Stop_OnInitError(const char* message) {
    Serial.println(message);
    while (true) delay(1000);
}

void setup(void) {
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

    Serial.println("\n=== HỆ THỐNG TINYML ASTHMA SẴN SÀNG ===");
}

void loop(void) {
    StateMachine_Run();
}
