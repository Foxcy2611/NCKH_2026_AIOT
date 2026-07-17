#include "ESP32_BMP280_Lib.h"

static BMP280_CalibData calib;
static double t_fine;

static void BMP280_Write(uint8_t reg, uint8_t value){
    Wire.beginTransmission(BMP280_ADDR_REG);
    Wire.write(reg);
    Wire.write(value);
    Wire.endTransmission();
}

static uint8_t BMP280_Read_8Bit(uint8_t reg){
    Wire.beginTransmission(BMP280_ADDR_REG);
    Wire.write(reg);
    Wire.endTransmission(false);
    Wire.requestFrom(BMP280_ADDR_REG, (uint8_t)1);

    return Wire.read();
}

static uint16_t BMP280_Read_16Bit(uint8_t reg){
    Wire.beginTransmission(BMP280_ADDR_REG);
    Wire.write(reg);
    Wire.endTransmission(false);
    Wire.requestFrom(BMP280_ADDR_REG, (uint8_t)2);

    uint8_t lsb = Wire.read();
    uint8_t msb = Wire.read();

    return (msb << 8) | lsb;
}

// --- ĐỌC 24 BYTE HỆ SỐ BÙ TỪ ROM CHIP ---
static void BMP280_ReadCoefficients(){
    calib.dig_T1 = BMP280_Read_16Bit(BMP280_COEF_T1);
    calib.dig_T2 = BMP280_Read_16Bit(BMP280_COEF_T2);
    calib.dig_T3 = BMP280_Read_16Bit(BMP280_COEF_T3);

    calib.dig_P1 = BMP280_Read_16Bit(BMP280_COEF_P1);
    calib.dig_P2 = BMP280_Read_16Bit(BMP280_COEF_P2);
    calib.dig_P3 = BMP280_Read_16Bit(BMP280_COEF_P3);
    calib.dig_P4 = BMP280_Read_16Bit(BMP280_COEF_P4);
    calib.dig_P5 = BMP280_Read_16Bit(BMP280_COEF_P5);
    calib.dig_P6 = BMP280_Read_16Bit(BMP280_COEF_P6);
    calib.dig_P7 = BMP280_Read_16Bit(BMP280_COEF_P7);
    calib.dig_P8 = BMP280_Read_16Bit(BMP280_COEF_P8);
    calib.dig_P9 = BMP280_Read_16Bit(BMP280_COEF_P9);
}

// ==== THUẬT TOÁN BÙ TRỪ ====
// Tính theo BOSCH Trang 45 Datasheet
static double BMP280_Compensate_T_Double(int32_t adc_T){
    double var1, var2, T;
    var1 = (((double)adc_T) / 16384.0 - ((double)calib.dig_T1) / 1024.0) * ((double)calib.dig_T2);
    var2 = ((((double)adc_T) / 131072.0 - ((double)calib.dig_T1) / 8192.0) *
            (((double)adc_T) / 131072.0 - ((double)calib.dig_T1) / 8192.0)) * ((double)calib.dig_T3);
    t_fine = (int32_t)(var1 + var2);
    T = (var1 + var2) / 5120.0;

    return T;
}

static double BMP280_Compensate_P_Double(int32_t adc_P){
    double var1, var2, p;
    var1 = ((double)t_fine/2.0) - 64000.0;
    var2 = var1 * var1 * ((double)calib.dig_P6) / 32768.0;
    var2 = var2 + var1 * ((double)calib.dig_P5) * 2.0;
    var2 = (var2/4.0)+(((double)calib.dig_P4) * 65536.0);
    var1 = (((double)calib.dig_P3) * var1 * var1 / 524288.0 + ((double)calib.dig_P2) * var1) / 524288.0;
    var1 = (1.0 + var1 / 32768.0)*((double)calib.dig_P1);
 
    if (var1 == 0.0){
        return 0; // Tránh lỗi chia cho 0
    }

    p = 1048576.0 - (double)adc_P;
    p = (p - (var2 / 4096.0)) * 6250.0 / var1;
    var1 = ((double)calib.dig_P9) * p * p / 2147483648.0;
    var2 = p * ((double)calib.dig_P8) / 32768.0;
    p = p + (var1 + var2 + ((double)calib.dig_P7)) / 16.0;
    
    return p;
}

bool BMP280_Init(uint8_t i2cAddr){
    // 1. Đọc ID chip
    uint8_t chipID = BMP280_Read_8Bit(BMP280_ID_REG);
    if(chipID != BMP280_ID_RES){
        return false;
    }

    // 2. Reset chip
    BMP280_Write(BMP280_RST_REG, BMP280_RST_VAL);
    delay(10); // xTaskDelay

    // 3. Đọc dữ liệu Calib
    BMP280_ReadCoefficients();

    // 4. Cấu hình thanh ghi Config
    // Standby - 1000ms - 101
    // Filter - 4 - 010 
    // => 101 010 00 = 1010 1000 = 0xA8
    BMP280_Write(BMP280_CONFIG_REG, 0xA8);

    // 5. Cấu hình thanh ghi Ctrl_Meas
    // Over sampling NĐ - x1 - 001
    // Over sampling AS - x4 - 011
    // Mode - Normal mode (Đo liên tục) - 11
    // 001 011 11 = 0010 1111 = 0x2F
    BMP280_Write(BMP280_CTRL_MEAS_REG, 0x2F);

    return true;
}

bool BMP280_ReadData(float* temperature, float* pressure){
    Wire.beginTransmission(BMP280_ADDR_REG);
    Wire.write(BMP280_PRESSURE_MSB_REG);
    
    // Không gửi STOP mà Repeated tín hiệu, thành công thì = 0
    if (Wire.endTransmission(false) != 0){
        return false;
    }
    
    // Gửi 6 bytes dữ liệu gồm: 3 bytes Áp suất + 3 bytes Nhiệt độ
    if(Wire.requestFrom(BMP280_ADDR_REG, (uint8_t)6) != 6){
        return false;
    }
    
    uint8_t p_msb = Wire.read();
    uint8_t p_lsb = Wire.read();
    uint8_t p_xlsb = Wire.read();

    uint8_t t_msb = Wire.read();
    uint8_t t_lsb = Wire.read();
    uint8_t t_xlsb = Wire.read();

    int32_t adc_P = (p_msb << 12) | (p_lsb << 4) | (p_xlsb >> 4);
    int32_t adc_T = (t_msb << 12) | (t_lsb << 4) | (t_xlsb >> 4);

    *pressure    = (float)BMP280_Compensate_P_Double(adc_P) / 100.0; // Ra hPa
    *temperature = (float)BMP280_Compensate_T_Double(adc_T);
        
    return true;
}

// --- HÀM TÍNH ĐỘ CAO ---
float BMP280_CalculateAltitude(float currentPressure_hPa, float seaLevelPressure_hPa){
    // Công thức Barometric
    return 44330.0f * (1.0f - pow(currentPressure_hPa / seaLevelPressure_hPa, 0.1903));
}

// Test trong main.cpp
void BMP280_TestSetup(void){
    Serial.begin(115200);
    Serial.println("\n--- BMP280 Test ---");

    Wire.begin(I2C_SDA, I2C_SCL);

    // Khởi tạo BMP280 ở địa chỉ 0x76
    if (BMP280_Init(0x76)) {
        Serial.println("[OK] BMP280 Khoi tao thanh cong!");
    } else {
        Serial.println("[ERR] Khong tim thay BMP280. Kiem tra dia chi hoac day I2C!");
        while(1);
    }
}
void BMP280_TestLoop(void){
    float temp, press, altitude;
    
    if (BMP280_ReadData(&temp, &press)) {
        altitude = BMP280_CalculateAltitude(press, SEA_LEVEL_PRESSURE_HPA);
        Serial.printf("Nhiet do: %.2f *C  |  Ap suat: %.2f hPa  |  Do cao: %.2f m\n", temp, press, altitude);
    } else {
        Serial.println("[ERR] Loi doc I2C tu BMP280!");
    }
}