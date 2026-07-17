#include "ESP32_MAX30102_Lib.h"

static void MAX30102_WriteReg(uint8_t reg, uint8_t value){
    Wire.beginTransmission(MAX30102_ADDR_REG);
    Wire.write(reg);
    Wire.write(value);
    Wire.endTransmission();
}

static uint8_t MAX30102_ReadReg(uint8_t reg){
    Wire.beginTransmission(MAX30102_ADDR_REG);
    Wire.write(reg);
    Wire.endTransmission(false);
    Wire.requestFrom(MAX30102_ADDR_REG, (uint8_t)1);

    return Wire.read();
}

bool MAX30102_Init(void){
    uint8_t configValue;
    pinMode(INT_PIN, INPUT_PULLUP);

    // 1. Kiếm tra ID
    if(MAX30102_ReadReg(REG_PART_ID) != VALUE_PART_ID){
        return false;
    }

    // 2. Reset thiết bị
    MAX30102_WriteReg(REG_MODE_CONFIG, MODE_RESET);
    delay(100); // vTaskDelay

    // 3. Cấu hình FIFO 0x08
    configValue = FIFO_SMP_AVE_4 | FIFO_ROLLOVER_ENABLE | FIFO_A_FULL_15;
    MAX30102_WriteReg(REG_FIFO_CONFIG, configValue);

    // 4. Cấu hình Mode CONFIG 0x09
    configValue = MODE_SP02;
    MAX30102_WriteReg(REG_MODE_CONFIG, configValue);

    // 5. Cấu hình Sp02
    configValue = SP02_ADC_RGE_4096 | SP02_SR_100 | SP02_LED_PW_411;
    MAX30102_WriteReg(REG_SP02_CONFIG, configValue);

    // 6. Cấu hình dòng điện LED 
    MAX30102_WriteReg(REG_PULSE_AMP_1, LED_CURRENT);
    MAX30102_WriteReg(REG_PULSE_AMP_2, LED_CURRENT);

    // 7. Đọc để xóa cờ ngắt cũ và Reset con trỏ
    MAX30102_ClearInterrupt();
    MAX30102_WriteReg(REG_WR_PTR_CONF, ERASER_POINTER);
    MAX30102_WriteReg(REG_OVF_COUNTER, ERASER_POINTER);
    MAX30102_WriteReg(REG_RD_PTR_CONF, ERASER_POINTER);

    // 8. Cho phép ngắt
    configValue = A_FULL_EN | PPG_RDY_EN;
    MAX30102_WriteReg(REG_INTER_ENABL, configValue);

    return true;
}

void MAX30102_ClearInterrupt(){
    MAX30102_ReadReg(REG_INTER_STTUS);
}

bool MAX30102_HasInterrupt(){
    return (digitalRead(INT_PIN) == LOW);
}

bool MAX30102_ReadFIFO(uint32_t* redLED, uint32_t* irLED){
    uint8_t wrPtr = MAX30102_ReadReg(REG_WR_PTR_CONF);
    uint8_t rdPtr = MAX30102_ReadReg(REG_RD_PTR_CONF);

    // Nếu vị trí đầu == cuối => Tức chưa có dữ liệu mới
    if(wrPtr == rdPtr){
        return false;
    }

    Wire.beginTransmission(MAX30102_ADDR_REG);
    Wire.write(REG_FIFO_DATA);
    Wire.endTransmission(false);

    // Đọc 6 bytes
    if(Wire.requestFrom(MAX30102_ADDR_REG, (uint8_t)6) != 6){
        return false;
    }

    uint8_t data[6];
    for(int i = 0 ; i < 6 ; i++){
        data[i] = Wire.read();
    }

    *redLED = (((uint32_t)data[0] << 16) | ((uint32_t)data[1] << 8) | data[2]) & 0x03FFFF;
    *irLED  = (((uint32_t)data[3] << 16) | ((uint32_t)data[4] << 8) | data[5]) & 0x03FFFF;

    return true;
}

// ======= TEST MAIN =========
// Lưu ý: Phải vác hoàn toàn vào main.cpp
// Không được gọi hàm tại main.cpp
volatile bool MAX30102_is_ready = false;

void IRAM_ATTR MAX30102_ISR(void){
    MAX30102_is_ready = true;    
}

void MAX30102_TestSetup(void){
    Serial.begin(115200);
    Serial.println("\n--- MAX30102 Ngat Phan Cung (Hardware Interrupt) ---");

    Wire.begin(SDA_PIN, SCL_PIN);
    Wire.setClock(400000); // Ép xung I2C lên 400kHz đọc cho nhanh

    // Khởi tạo MAX30102
    if (MAX30102_Init()) {
        Serial.println("[OK] Khoi tao MAX30102 thanh cong!");
    } else {
        Serial.println("[ERR] Khong the ket noi toi MAX30102!");
        while(1);
    }

    // Gắn ngắt phần cứng vào chân INT_PIN
    // Bắt tín hiệu khi chân bị ghì từ HIGH xuống LOW (FALLING)
    attachInterrupt(digitalPinToInterrupt(INT_PIN), MAX30102_ISR, FALLING);

}
void MAX30102_TestLoop(void){
    uint32_t red, ir;

    // Thay vì đứng chờ, ESP32 chỉ làm việc khi cờ ngắt được dựng lên
    if (MAX30102_is_ready) {
        // 1. Hạ cờ ngắt xuống ngay lập tức
        MAX30102_is_ready = false;

        // 2. Đọc dữ liệu từ FIFO
        if (MAX30102_ReadFIFO(&red, &ir)) {
            // In ra Serial Plotter (Mở biểu đồ của Arduino IDE lên xem sóng tim nhảy)
            Serial.printf("%lu,%lu\n", red, ir);
        }

        // 3. Xóa cờ ngắt trên cảm biến để chân INT nhả lại mức HIGH, chuẩn bị cho nhịp ngắt tiếp theo
        MAX30102_ClearInterrupt();
    }
}