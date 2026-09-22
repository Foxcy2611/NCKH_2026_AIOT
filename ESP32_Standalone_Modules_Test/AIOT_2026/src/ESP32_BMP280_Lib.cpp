#include "ESP32_BMP280_Lib.h"

static BMP280_CalibData calib;
static double t_fine;
static uint8_t bmp280_i2c_addr = BMP280_ADDR_REG;

static bool BMP280_Write(uint8_t reg, uint8_t value){
    Wire.beginTransmission(bmp280_i2c_addr);
    Wire.write(reg);
    Wire.write(value);
    return Wire.endTransmission() == 0;
}

static bool BMP280_Read_8Bit(uint8_t reg, uint8_t* value){
    if(value == nullptr){
        return false;
    }

    Wire.beginTransmission(bmp280_i2c_addr);
    Wire.write(reg);
    if(Wire.endTransmission(false) != 0){
        return false;
    }

    if(Wire.requestFrom(bmp280_i2c_addr, (uint8_t)1) != 1 || !Wire.available()){
        return false;
    }

    *value = Wire.read();
    return true;
}

// Đọc toàn bộ 24 byte hệ số trong một giao dịch I2C.
static bool BMP280_ReadCoefficients(){
    uint16_t coefficient[12];

    Wire.beginTransmission(bmp280_i2c_addr);
    Wire.write(BMP280_COEF_T1);
    if(Wire.endTransmission(false) != 0){
        return false;
    }

    if(Wire.requestFrom(bmp280_i2c_addr, (uint8_t)24) != 24){
        return false;
    }

    for(uint8_t i = 0; i < 12; ++i){
        if(Wire.available() < 2){
            return false;
        }

        uint8_t lsb = Wire.read();
        uint8_t msb = Wire.read();
        coefficient[i] = ((uint16_t)msb << 8) | lsb;
    }

    calib.dig_T1 = coefficient[0];
    calib.dig_T2 = (int16_t)coefficient[1];
    calib.dig_T3 = (int16_t)coefficient[2];
    calib.dig_P1 = coefficient[3];
    calib.dig_P2 = (int16_t)coefficient[4];
    calib.dig_P3 = (int16_t)coefficient[5];
    calib.dig_P4 = (int16_t)coefficient[6];
    calib.dig_P5 = (int16_t)coefficient[7];
    calib.dig_P6 = (int16_t)coefficient[8];
    calib.dig_P7 = (int16_t)coefficient[9];
    calib.dig_P8 = (int16_t)coefficient[10];
    calib.dig_P9 = (int16_t)coefficient[11];

    return calib.dig_T1 != 0 && calib.dig_T1 != 0xFFFF &&
           calib.dig_P1 != 0 && calib.dig_P1 != 0xFFFF;
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
    uint8_t addrs[2] = {0x77, 0x76};

    if (i2cAddr == 0x76 || i2cAddr == 0x77) {
        addrs[0] = i2cAddr;
        addrs[1] = (i2cAddr == 0x77) ? 0x76 : 0x77;
    }

    for (uint8_t i = 0; i < 2; ++i) {
        bmp280_i2c_addr = addrs[i];

        Wire.beginTransmission(bmp280_i2c_addr);
        uint8_t err = Wire.endTransmission();
        if (err != 0) {
            continue;
        }

        uint8_t chipID = 0;
        if (!BMP280_Read_8Bit(BMP280_ID_REG, &chipID) ||
            chipID != BMP280_ID_RES) {
            continue;
        }

        if (!BMP280_Write(BMP280_RST_REG, BMP280_RST_VAL)) {
            continue;
        }
        delay(10);

        if (!BMP280_ReadCoefficients() ||
            !BMP280_Write(BMP280_CONFIG_REG, 0xA8) ||
            !BMP280_Write(BMP280_CTRL_MEAS_REG, 0x2F)) {
            continue;
        }

        return true;
    }

    return false;
}

bool BMP280_ReadData(float* temperature, float* pressure){
    if(temperature == nullptr || pressure == nullptr){
        return false;
    }

    Wire.beginTransmission(bmp280_i2c_addr);
    Wire.write(BMP280_PRESSURE_MSB_REG);
    
    // Không gửi STOP mà Repeated tín hiệu, thành công thì = 0
    if (Wire.endTransmission(false) != 0){
        return false;
    }
    
    // Gửi 6 bytes dữ liệu gồm: 3 bytes Áp suất + 3 bytes Nhiệt độ
    if(Wire.requestFrom(bmp280_i2c_addr, (uint8_t)6) != 6){
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

    if(adc_P == 0x80000 || adc_T == 0x80000){
        return false;
    }

    *temperature = (float)BMP280_Compensate_T_Double(adc_T);
    double pressurePa = BMP280_Compensate_P_Double(adc_P);
    if(pressurePa <= 0.0){
        return false;
    }

    *pressure = (float)pressurePa / 100.0; // Ra hPa
        
    return true;
}

// --- HÀM TÍNH ĐỘ CAO ---
float BMP280_CalculateAltitude(float currentPressure_hPa, float seaLevelPressure_hPa){
    if(currentPressure_hPa <= 0.0f || seaLevelPressure_hPa <= 0.0f){
        return NAN;
    }

    // Công thức Barometric
    return 44330.0f * (1.0f - pow(currentPressure_hPa / seaLevelPressure_hPa, 0.1903));
}

// Test trong main.cpp
void BMP280_TestSetup(void){
    Serial.begin(115200);
    Serial.println("\n--- BMP280 Test ---");

    Wire.begin(I2C_SDA, I2C_SCL);

    if (BMP280_Init(0x77)) {
        Serial.println("[OK] BMP280 Khoi tao thanh cong!");
    } else {
        Serial.println("[ERR] Khong tim thay BMP280. Kiem tra dia chi 0x77 hoac day I2C!");
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
