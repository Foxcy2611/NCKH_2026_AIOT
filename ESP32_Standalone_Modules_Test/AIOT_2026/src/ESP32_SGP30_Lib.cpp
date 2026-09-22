#include <ESP32_SGP30_Lib.h>

// Thuật toán kiểm tra checksum CRC-8
// x8 + x5 + x4 + 1 = 0x31 
// I2C nên khởi tạo = 0xFF
static uint8_t SGP30_Caculate_CRC(uint8_t data[2]){
    uint8_t crc = 0xFF;
    for(int i = 0 ; i < 2 ; i++){
        crc ^= data[i];

        for(int j = 0 ; j < 8 ; j++){
            if(crc & 0x80){
                crc = (crc << 1) ^ 0x31;
            } else {
                crc = crc << 1;
            }
        }
    }

    return crc;
}

static bool SGP30_Write_CMD(uint16_t cmd){
    Wire.beginTransmission(SGP30_I2C_ADDR);
    Wire.write(cmd >> 8);
    Wire.write(cmd & 0xFF);
    return Wire.endTransmission() == 0;
}

bool SGP30_Init(){
    // 1. Kiểm tra kết nối bằng cách đọc Feature Set
    if(!SGP30_Write_CMD(SGP30_CMD_GET_FEATURE_SET)){
        return false;
    }
    delay(2);

    if(Wire.requestFrom(SGP30_I2C_ADDR, 3) != 3){
        return false;
    }

    uint8_t featureSet[2] = {
        (uint8_t)Wire.read(),
        (uint8_t)Wire.read()
    };
    uint8_t featureCrc = (uint8_t)Wire.read();
    if(SGP30_Caculate_CRC(featureSet) != featureCrc){
        return false;
    }

    // 2. Khởi tạo thuật toán đo đạc Air Quality
    if(!SGP30_Write_CMD(SGP30_CMD_INIT_AIR_QUALITY)){
        return false;
    }
    delay(10);

    return true;
}

bool SGP30_Measure(SGP30_Data_t* data){
    if(data == nullptr || !SGP30_Write_CMD(SGP30_CMD_MEASURE_AIR_QUALITY)){
        return false;
    }
    delay(12);

    if(Wire.requestFrom(SGP30_I2C_ADDR, 6) != 6){
        return false;
    }

    uint8_t CO2_eq_bytes[2], TVOC_bytes[2];
    uint8_t crc_C02, crc_TVOC;

    CO2_eq_bytes[0] = Wire.read();
    CO2_eq_bytes[1] = Wire.read();
    crc_C02 = Wire.read();

    TVOC_bytes[0] = Wire.read();
    TVOC_bytes[1] = Wire.read();
    crc_TVOC = Wire.read();

    if(SGP30_Caculate_CRC(CO2_eq_bytes) != crc_C02 || 
        SGP30_Caculate_CRC(TVOC_bytes) != crc_TVOC){
        
        return false;
    }

    data->CO2_eq = (CO2_eq_bytes[0] << 8) | CO2_eq_bytes[1];
    data->TVOC   = (TVOC_bytes[0] << 8) | TVOC_bytes[1];

    return true;
}

// ==== TEST MAIN ====
SGP30_Data_t mySGP30;
unsigned long last_sgp30_read = 0;

void SGP30_TestSetup(void){
    Serial.begin(115200);
    Wire.begin();
    delay(500);

    Serial.println("\n--- SGP30 TVOC/eCO2 Test ---");

    if (SGP30_Init()) {
        Serial.println("[OK] SGP30 San sang. Cho 15s de thuat toan Base-line on dinh...");
    } else {
        Serial.println("[ERR] Khong tim thay SGP30. Kiem tra lai day I2C hoac Nguon!");
        while(1);
    }
}

void SGP30_TestLoop(void) {
    // Ép buộc đọc đúng 1 giây/lần theo Datasheet SGP30 để bù đường nền
    if (millis() - last_sgp30_read >= 1000) {
        last_sgp30_read = millis();

        if (SGP30_Measure(&mySGP30)) {
            Serial.printf("[SGP30] TVOC: %u ppb | eCO2: %u ppm\n", mySGP30.TVOC, mySGP30.CO2_eq);
            
            if(mySGP30.CO2_eq == 400 && mySGP30.TVOC == 0) {
                 Serial.println("  -> (Chip dang trong 15s Warm-up...)");
            }
        } else {
            Serial.println("[ERR] Loi doc SGP30 (Loi CRC hoac mat ket noi)!");
        }
    }
}
