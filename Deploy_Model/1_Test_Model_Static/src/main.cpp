#include <Arduino.h>

#include "Test_Asthma_1.h"
#include "Sample_Asthma_1.h"
#include "Sample_Non_Asthma_1.h"


void setup(){
    Serial.begin(115200);
    delay(2000);
    
    Serial.println("\n\n=== BAT DAU HE THONG TINYML ESP32-S3 ===");
    if (!Setup_TinyML()) {
        Serial.println("He thong AI khoi dong that bai. Treo may!");
        while(1){ 
            delay(100); 
        } // Dừng chương trình vô hạn nếu lỗi
    }
}

void loop() {
    // 1.a
    // Test bộ não khởi tạo thành công
    // Predict_Static_Dummy_0();
    // delay(2000); 
    /*
    OUTPUT:

    [   242][I][esp32-hal-psram.c:96] psramInit(): PSRAM enabled


    === BAT DAU HE THONG TINYML ESP32-S3 ===

    [AI] Dang doc mo hinh tu bo nho...
    [AI] Xin bo nho PSRAM thanh cong!
    [AI] KHOI TAO THANH CONG! (Dang dung AllOps)
    [AI] Input Shape: 64 x 129 x 1
    ====================================
    Thoi gian suy luan : 1869 ms
    Ket qua (Int8)    : -128
    ====================================
    */

    // 1.b
    // Test mẫu Hen suyễn trước
    Predict_Static_Dummy(sample_asthma_data, "MAU BENH NHAN HEN SUYEN");
    delay(3000); 
    // Test mẫu Bình thường sau
    Predict_Static_Dummy(sample_non_asthma_data, "MAU NGUOI BENH COPD");
    // Chờ 10 giây rồi lặp lại
    delay(10000);
    /*
    OUPUT:
    >>> DANG PHAN TICH: MAU BENH NHAN HEN SUYEN <<<
    ====================================
    Thoi gian suy luan : 1867 ms
    Gia tri Int8 goc   : -69
    Xac suat Output    : 23.14 %
    ------------------------------------
    => DU DOAN         : HEN SUYEN (Nhan 0)
    => DO TU TIN       : 76.9 %
    ====================================


    >>> DANG PHAN TICH: MAU NGUOI BENH COPD <<<
    ====================================
    Thoi gian suy luan : 1867 ms
    Gia tri Int8 goc   : 107
    Xac suat Output    : 92.16 %
    ------------------------------------
    => DU DOAN         : BINH THUONG / BENH KHAC (Nhan 1)
    => DO TU TIN       : 92.2 %
    ====================================
    */
}
