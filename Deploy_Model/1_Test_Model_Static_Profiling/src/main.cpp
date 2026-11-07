#include <Arduino.h>

#include "Test_Model_Static_Profiling.h"

void setup() {
    Serial.begin(115200);
    delay(3000);  // Cho Windows nhan lai cong USB Serial sau khi reset.

    Serial.println("\n==================================================");
    Serial.println(" ESP32-S3 STATIC MODEL PROFILING");
    Serial.println("==================================================");
    Serial.printf("CPU frequency : %u MHz\n", getCpuFrequencyMhz());

    if (!Setup_TinyML()) {
        Serial.println("[FATAL] Khoi tao TinyML that bai. Dung benchmark.");
        return;
    }

    Run_Static_Benchmark();
}

void loop() {
    // Benchmark chi chay mot lan trong setup de log khong bi lap vo han.
    delay(1000);
}
