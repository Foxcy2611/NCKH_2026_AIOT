#include "ESP32_DHT11_Lib.h"

static portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;

// Hàm đo thời gian xung => Ngang delay
static uint32_t DHT11_ExpectPulse(bool state){
    uint32_t cnt = 0;
    uint32_t max_cycles = 1000;

    while(digitalRead(DHT11_PIN) == state){
        if(cnt++ >= max_cycles){
            return 0;
        }

        delayMicroseconds(1);
    }
    return cnt;
}

// Gọi trong setup
void DHT11_Init(void){
    pinMode(DHT11_PIN, INPUT_PULLUP);
}

uint8_t DHT11_ReadData(float* temp, float* humi){
    uint8_t data[5] = {0};
    uint8_t i, j;

    pinMode(DHT11_PIN, OUTPUT_OPEN_DRAIN);
    digitalWrite(DHT11_PIN, LOW);
    delay(20); // Kéo LOW > 18ms
    digitalWrite(DHT11_PIN, HIGH);
    delayMicroseconds(30); // Kéo HIGH khoảng 20-40us

    pinMode(DHT11_PIN, INPUT);

    // Response: DHT11 đáp lại bằng cách
    // Kéo LOW 80us sau đó HIGH 80us
    if(DHT11_ExpectPulse(LOW) == 0) return 1;
    if(DHT11_ExpectPulse(HIGH) == 0) return 1;

    // [QUAN TRỌNG]: Tắt ngắt để hệ điều hành FreeRTOS không can thiệp 
    // làm sai lệch thời gian đo micro-giây
    // portENTER_CRITICAL: Chặn mọi ngắt
    portENTER_CRITICAL(&mux);
    
    for(int j = 0 ; j < 5 ; j++){
        uint8_t byte = 0;
        for(int i = 0 ; i < 8 ; i++){
            if(DHT11_ExpectPulse(LOW) == 0){
                // portEXIT_CRITICAL: Mở lại ngắt nếu lỗi
                portEXIT_CRITICAL(&mux);
                return 1;
            }

            uint32_t highCycles = DHT11_ExpectPulse(HIGH);
            if(highCycles == 0){
                portEXIT_CRITICAL(&mux);
                return 1;
            }

            if(highCycles > 40){
                byte |= (1 << (7 - i));
            }
        }

        data[j] = byte;
    }

    // Bật lại ngắt cho hệ thống bình thường
    portEXIT_CRITICAL(&mux);
    
    // Kiểm tra Checksum
    uint8_t sum = (data[0] + data[1] + data[2] + data[3]) & 0xFF;
    if (data[4] != sum) {
        return 2; // Lỗi dữ liệu nhiễu
    }

    // Xuất dữ liệu
    *humi = (float)data[0] + ((float)data[1] / 10.0);
    *temp = (float)data[2] + ((float)data[3] / 10.0);

    return 0;
}

void DHT11_TestMain(void){
    float temp, humi;
    
    uint8_t err = DHT11_ReadData(&temp, &humi);

    if (err == 0) {
        Serial.printf("[OK] Nhiet do: %.1f *C  |  Do am: %.1f %%\n", temp, humi);
    } 
    else if (err == 1) {
        Serial.println("[ERR] Loi Timeout - Kiem tra day DHT11 hoac tro keo pull-up!");
    } 
    else if (err == 2) {
        Serial.println("[ERR] Loi Checksum - Nhieu tin hieu tren day DATA!");
    }
}