#include <Arduino.h>

#include "Test_Asthma_2.h"
#include "sample_asthma_1.h"
#include "sample_non_asthma_1.h"

/*
- Nhiệm vụ 1: Vào Test_Asthma_2.cpp để thay đổi kích thước
tensor_arena sao cho nó tối ưu nhất

- Nhiệm vụ 2: Vào platform.ini tiến hành ép tần số hoạt động
lên 240 MHz (Theo max thông số của NXS) và 1 số cờ
+ Tại file platformio.ini, dù đã ép tần số lên 240MHz mà tốc độ
suy luận vẫn ở 1867ms
+ Nên coi như đó là tốc độ interface max có thể có
*/

void setup() {
    Serial.begin(115200);
    delay(3000); // Chờ 3 giây để Windows nhận diện lại cổng USB COM6

    Serial.printf("CPU Freq: %d MHz\n", getCpuFrequencyMhz());

    if (!Setup_TinyML()) {
        Serial.println("He thong AI khoi dong that bai. Treo may!");
        while(1) { delay(100); } 
    }
}

void loop() {
  Predict_Static_Dummy(sample_asthma_data, "MAU BENH NHAN HEN SUYEN");
  delay(3000); 

  Predict_Static_Dummy(sample_non_asthma_data, "MAU NGUOI BINH THUONG");
  delay(10000); 
  // Không khác so vs Prj 1 
}