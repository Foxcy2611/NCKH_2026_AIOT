#include "ESP32_MQ135_Driver.h"

static uint8_t _mq_pin;

void MQ135_Init(uint8_t pin) {
    _mq_pin = pin;
    analogSetPinAttenuation(_mq_pin, ADC_11db);
    pinMode(_mq_pin, INPUT);
}

float MQ135_ReadRs() {
    uint32_t adc_sum = 0;
    for (int i = 0; i < 20; i++) {
        adc_sum += analogRead(_mq_pin);
        delay(2); 
    }
    float adc_value = (float)adc_sum / 20.0f;
    float v_esp = (adc_value / ESP32_ADC_MAX) * ESP32_ADC_REF_VOLTS;
    float v_a0 = v_esp * VOLTAGE_DIVIDER_RATIO;

    if (v_a0 <= 0.0f) return 0.0f; 
        // deo hieu :))
    return MQ135_RL_kOhm * (MQ135_VC_Volts - v_a0) / v_a0;
}

float MQ135_CalibrateR0() {
    float rs_clean_air = MQ135_ReadRs();
    // deo hieu :))
    return rs_clean_air / 3.6f;
}

// HÀM HỖ TRỢ ĐA KHÍ
float MQ135_GetPPM(float r0, MQ135_GasType_t gasType) {
    if (r0 <= 0.0f) return 0.0f; 

    float rs = MQ135_ReadRs();
    float ratio = rs / r0; 
    float para_A = 0, para_B = 0;

    // Chọn hệ số dựa vào loại khí được yêu cầu
    switch(gasType) {
        case MQ135_GAS_CO2:
            para_A = 110.47f;  para_B = -2.862f; break;
        case MQ135_GAS_CO:
            para_A = 605.18f;  para_B = -3.937f; break;
        case MQ135_GAS_ALCOHOL:
            para_A = 77.255f;  para_B = -3.18f;  break;
        case MQ135_GAS_NH3:
            para_A = 102.2f;   para_B = -2.473f; break; // Hệ số chuẩn cộng đồng (chính xác hơn tính tay)
        case MQ135_GAS_TOLUENE:
            para_A = 44.947f;  para_B = -3.445f; break;
        case MQ135_GAS_ACETONE:
            para_A = 34.668f;  para_B = -3.369f; break;
        default:
            return 0.0f;
    }

    return para_A * pow(ratio, para_B);
}

// ==== TEST MAIN ==== 

float global_R0 = 0.0f;
unsigned long last_mq135_read = 0; 

void MQ135_TestSetup(void){
    // Lưu ý: Nếu ở hàm setup() chính đã gọi Serial.begin(115200) thì bỏ dòng dưới đi
    Serial.begin(115200);

    MQ135_Init(MQ135_PIN);
    
    Serial.println("\n--- MQ135 Gas Sensor Test ---");
    Serial.println("[INFO] Dang lam nong va hieu chuan MQ135 (Air)...");
    
    // Đo R0 trong không khí sạch
    global_R0 = MQ135_CalibrateR0();
    Serial.printf("[OK] R0 cua MQ135 = %.2f kOhm\n", global_R0);
}

void MQ135_TestLoop(void){
    // Thay vì dùng delay(2000) làm treo hệ thống, ta dùng thuật toán millis()
    if (millis() - last_mq135_read >= 2000) {
        last_mq135_read = millis(); // Chốt mốc thời gian mới

        // Tính nồng độ khí dựa trên hệ số
        float ppm_nh3 = MQ135_GetPPM(global_R0, MQ135_GAS_NH3);
        float ppm_co2 = MQ135_GetPPM(global_R0, MQ135_GAS_CO2);

        Serial.printf("[MQ135] CO2: %.2f ppm | NH3: %.2f ppm\n", ppm_co2, ppm_nh3);
    }
}