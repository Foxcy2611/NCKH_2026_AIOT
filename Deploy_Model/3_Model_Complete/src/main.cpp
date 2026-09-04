#include <Arduino.h>

#include "Audio_IO/I2S_Mic.h"
#include "DSP_Preprocessing/Mel_Scale.h"
#include "Model_AI/Interface_Asthma.h"

void setup() {
    Serial.begin(115200);
    delay(3000);

    Serial.println("\n=== HE THONG TINYML HO TRO SANG LOC ASTHMA ===");

    if (!Init_Mel_Filterbank()) {
        Serial.println("[LOI] Khong khoi tao duoc Mel Filterbank.");
        while (true) delay(100);
    }

    if (!Init_Asthma_Model()) {
        Serial.println("[LOI] Khong khoi tao duoc mo hinh.");
        while (true) delay(100);
    }

    I2S_Mic_Init(I2S_SCK, I2S_WS, I2S_SD);
    Serial.println("[SAN SANG] Dang tao bo dem am thanh 1 giay...");
}

void loop() {
    Process_Audio_Stream();
}
