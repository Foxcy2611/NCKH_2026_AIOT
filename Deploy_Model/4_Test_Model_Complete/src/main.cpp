#include <Arduino.h>
#include "Audio_IO/I2S_Mic.h"
#include "DSP_Preprocessing/Mel_Scale.h"
#include "Model_AI/Interface_Asthma.h"

void setup() {
  Serial.begin(115200);
  delay(3000);

  Serial.println("\n========================================");
  Serial.println("   HỆ THỐNG AI CHẨN ĐOÁN HEN SUYỄN");
  Serial.println("========================================\n");

  Serial.println("[CÀI ĐẶT] Đang khởi tạo Mel Filterbank...");
  Init_Mel_Filterbank();
  Serial.println("[CÀI ĐẶT] Mel Filterbank sẵn sàng.");

  Serial.println("[CÀI ĐẶT] Đang khởi tạo mô hình TFLite...");
  if (!Init_Asthma_Model()) {
      Serial.println("[CÀI ĐẶT] LỖI: Khởi tạo mô hình thất bại! Treo máy.");
      while (1) { 
        delay(100); 
      }
  }

  Serial.println("[CÀI ĐẶT] Đang khởi tạo Microphone I2S...");
  I2S_Mic_Init(I2S_SCK, I2S_WS, I2S_SD);
  Serial.println("[CÀI ĐẶT] I2S sẵn sàng.");

  Serial.println("\n[CÀI ĐẶT] HỆ THỐNG SẴN SÀNG! Đang lắng nghe...\n");
}

void loop() {
  Process_Audio_Stream();
}