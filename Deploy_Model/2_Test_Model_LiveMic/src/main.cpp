#include <Arduino.h>

#include "Audio_IO/I2S_Mic.h"
#include "DSP_Preprocessing/Mel_Scale.h"
#include "Model_AI/Inference_Asthma.h"

void setup() {
    Serial.begin(115200);
    delay(3000);

    Serial.println("\n========================================");
    Serial.println("  TEST PIPELINE C++ VA INFERENCE ASTHMA");
    Serial.println("========================================");

#if !RUN_VAD_CALIBRATION_TEST
    Serial.println("[SETUP] Khoi tao Mel Filterbank...");
    if (!Init_Mel_Filterbank()) {
        Serial.println("[SETUP][ERROR] Khoi tao Mel Filterbank that bai.");
        while (true) delay(1000);
    }

    Serial.println("[SETUP] Khoi tao model TFLite...");
    if (!Init_Asthma_Model()) {
        Serial.println("[SETUP][ERROR] Khoi tao model that bai.");
        while (true) delay(1000);
    }
    Serial.printf("[SETUP] Model dang chay: %s\n", Get_Asthma_Model_Name());
#else
    Serial.println("[VAD_CAL] Bo qua Mel va model.");
#endif

    I2S_Mic_Init(I2S_SCK, I2S_WS, I2S_SD);

#if RUN_RAW_PCM16_TEST
    Serial.println("[SETUP] San sang chay 12 mau RAW PCM16 qua pipeline C++.");
#elif RUN_VAD_CALIBRATION_TEST
    Serial.println("[SETUP] San sang do nang luong VAD tu INMP441.");
#else
    Serial.println("[SETUP] INMP441 san sang; bat dau lang nghe VAD.");
#endif
}

void loop() {
#if RUN_VAD_CALIBRATION_TEST
    Run_VAD_Calibration();
#else
    Process_Audio_Stream();
#endif
}
