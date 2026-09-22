#include <ESP32_MLX90614_Driver.h>

// CRC-8
// PEC - Khởi tạo 0x00
// x8 + x2 + x1 + 1 = 0x07 (1000 00111)
static uint8_t MLX90614_Caculate_PEC(uint8_t pec, uint8_t data){
    uint8_t v = pec ^ data;

    for(int i = 0 ; i < 8 ; i++){
        if(v & 0x80){
            v = (v << 1) ^ 0x07;
        } else {
            v = v << 1;
        }
    }

    return v;
}

static uint8_t MLX90614_Get_CRC8(uint8_t *data, uint8_t len){
    uint8_t crc = 0;
    for(uint8_t i = 0 ; i < len ; i++){
        crc = MLX90614_Caculate_PEC(crc, data[i]);
    }

    return crc;
}

// Hàm đọc giao tiếp (8.4.3.1.1)
bool MLX90614_ReadWord(uint8_t regAddr, uint16_t *data){
    // 1. Start -> Slave Addr -> CMD -> Repeated Start 
    Wire.beginTransmission(MLX90614_ADDR_I2C);
    Wire.write(regAddr);
    if(Wire.endTransmission(false) != 0){
        return false;
    }

    // 2. Yêu cầu trả về 3 byte (low - high - pec)
    uint8_t bytes_Received = Wire.requestFrom(MLX90614_ADDR_I2C, (uint8_t)3);
    if(bytes_Received != 3){
        return false;
    }

    uint8_t lsb = Wire.read();
    uint8_t msb = Wire.read();
    uint8_t pec = Wire.read();

    /* Theo datasheet: The PEC calculation includes all bits except the 
    START, REPEATED START, STOP, ACK, and NACK bits.

    Sơ đồ khung hình 5:
    S -> Slave Addres | Wr -> A -> Cmd -> A -> Sr -> Slave Address | Rd -> A
    -> Data low -> A -> Data high -> A -> PEC -> A -> P
    
    Việc loại bỏ các bit/byte để tính toán PEC giờ còn các thứ sau
    + Slave Address | Wr và | Rd
    + Cmd
    + Data low và high
    */

    static uint8_t pecBuff[5];
    pecBuff[0] = (MLX90614_ADDR_I2C << 1); // Slave Address | Wr
    pecBuff[1] = regAddr; // CMD
    pecBuff[2] = (MLX90614_ADDR_I2C << 1) | 0x01; // Slave Address | Rd
    pecBuff[3] = lsb;
    pecBuff[4] = msb;

    if(MLX90614_Get_CRC8(pecBuff, 5) != pec){
        return false;
    }

    *data = (msb << 8) | lsb;
    return true;
}

// Hàm chuyển đổi nhiệt độ
// Giá trị Raw là 16-bit, độ phân giải 0.02 độ K
// T = Toreg * 0.02
bool MLX90614_Read_Object_Temp(float *tempC){
    uint16_t rawValue = 0;
    if(! MLX90614_ReadWord(MLX90614_REG_TOBJ1, &rawValue)){
        return false;
    }

    float tempKevin = (float)rawValue * 0.02;
    *tempC = tempKevin - 273.15;

    return true;
}

bool MLX90614_Read_Ambient_Temp(float *tempC){
    
    uint16_t rawValue = 0;
    if(! MLX90614_ReadWord(MLX90614_REG_TA, &rawValue)){
        return false;
    }

    float tempKevin = (float)rawValue * 0.02;
    *tempC = tempKevin - 273.15;

    return true;
}

// ==== Hàm test main ====
void MLX90614_TestSetup(){
    // Serial.begin(115200);
    // Wire.begin(); // Khởi tạo I2C cho phần cứng (SDA, SCL)
    Serial.println("Khoi tao Driver MLX90614 thanh cong!");
}

void MLX90614_TestLoop(){
    float bodyTemp = 0.0;
    float ambTemp = 0.0;

    // Đọc thân nhiệt
    if (MLX90614_Read_Object_Temp(&bodyTemp)) {
        Serial.printf("Nhiet do doi tuong (To) : %.2f °C\n", bodyTemp);
    } else {
        Serial.println("Loi: Khong the doc To (Kiem tra day dien hoac nhieu Bus)!");
    }

    // Đọc nhiệt độ môi trường
    if (MLX90614_Read_Ambient_Temp(&ambTemp)) {
        Serial.printf("Nhiet do moi truong (Ta): %.2f °C\n", ambTemp);
    }

    Serial.println("-----------------------------------");
    delay(1000); 
}