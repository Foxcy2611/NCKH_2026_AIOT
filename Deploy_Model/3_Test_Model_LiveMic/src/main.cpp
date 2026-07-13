#include <Arduino.h>
#include "I2S_Mic.h"
#include "Mel_Scale.h"
#include "Interface_Asthma.h"

void setup() {
    Serial.begin(115200);
    delay(3000); // Chờ USB CDC ổn định

    Serial.println("\n========================================");
    Serial.println("   HE THONG AI CHUAN DOAN HEN SUYEN");
    Serial.println("========================================\n");

    // 1. Khởi tạo Mel filterbank (chỉ cần tính 1 lần duy nhất)
    Serial.println("[SETUP] Dang khoi tao Mel Filterbank...");
    Init_Mel_Filterbank();
    Serial.println("[SETUP] Mel Filterbank san sang.");

    // 2. Khởi tạo model TFLite (cấp phát tensor_arena, load model)
    Serial.println("[SETUP] Dang khoi tao model TFLite...");
    if (!Init_Asthma_Model()) {
        Serial.println("[SETUP] LOI: Khoi tao model that bai! Treo may.");
        while (1) { delay(100); }
    }

    // 3. Khởi tạo I2S cho mic INMP441
    Serial.println("[SETUP] Dang khoi tao I2S Microphone...");
    I2S_Mic_Init(I2S_SCK, I2S_WS, I2S_SD);
    Serial.println("[SETUP] I2S san sang.");

    Serial.println("\n[SETUP] HE THONG SAN SANG! Dang lang nghe...\n");
}

void loop() {
  Process_Audio_Stream();
}