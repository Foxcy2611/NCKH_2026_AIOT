#include <Arduino.h>
#include "Audio_IO/I2S_Mic.h"
#include "DSP_Preprocessing/Mel_Scale.h"
#include "Model_AI/Interface_Asthma.h"

// Note: Tại PRJ này
// Model có sự thay đổi nhẹ (Vì cần phải train lại) - Asthma_Model.h
// Nhưng không đáng kể

void setup() {
    Serial.begin(115200);
    delay(3000); // Chờ USB CDC ổn định

    Serial.println("\n========================================");
    Serial.println("   HỆ THỐNG AI CHẨN ĐOÁN HEN SUYỄN");
    Serial.println("========================================\n");

    // 1. Khởi tạo Mel filterbank (chỉ cần tính 1 lần duy nhất)
    Serial.println("[CÀI ĐẶT] Đang khởi tạo Mel Filterbank...");
    Init_Mel_Filterbank();
    Serial.println("[CÀI ĐẶT] Mel Filterbank sẵn sàng.");

    // 2. Khởi tạo model TFLite (cấp phát tensor_arena, load model)
    Serial.println("[CÀI ĐẶT] Đang khởi tạo mô hình TFLite...");
    if (!Init_Asthma_Model()) {
        Serial.println("[CÀI ĐẶT] LỖI: Khởi tạo mô hình thất bại! Treo máy.");
        while (1) { delay(100); }
    }

    // 3. Khởi tạo I2S cho mic INMP441
    Serial.println("[CÀI ĐẶT] Đang khởi tạo Microphone I2S...");
    I2S_Mic_Init(I2S_SCK, I2S_WS, I2S_SD);
    Serial.println("[CÀI ĐẶT] I2S sẵn sàng.");

    Serial.println("\n[CÀI ĐẶT] HỆ THỐNG SẴN SÀNG! Đang lắng nghe...\n");
}

void loop() {
  Process_Audio_Stream();
}