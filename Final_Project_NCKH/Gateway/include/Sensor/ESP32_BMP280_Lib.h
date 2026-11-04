#ifndef ESP_BMP280_LIB_H
#define ESP_BMP280_LIB_H

#include <Arduino.h>
#include <Wire.h>
#include <math.h>

// PIN-OUT I2C
#define I2C_SDA 21
#define I2C_SCL 22

// Áp suất chuẩn tại mực nước biển
#define SEA_LEVEL_PRESSURE_HPA 1013.25f

// ==== TẬP THANH GHI ====
// Địa chỉ
#define BMP280_ADDR_REG 0x76

// ID CHIP
#define BMP280_ID_REG 0xD0
#define BMP280_ID_RES 0x58

// Khởi động lại chip
#define BMP280_RST_REG 0xE0
#define BMP280_RST_VAL 0xB6

// Trạng thái chứa 2 bit cờ báo trạng thái
// Bit 3 = 1 khi chip bận đo lường
// Bit 0 = 1 khi đang copy data từ ROM ra bộ nhớ
#define BMP280_STATUS_REG 0xF3

// Điều khiển đo lường
// 7:5 - Cài đặt Over-Sampling cho nhiệt độ
// 4:2 - Cài đặt Over-Sampling cho áp suất
// 1:0 - 00: Ngủ ; 01: Đo 1 lần ; 11: Đo liên tục
#define BMP280_CTRL_MEAS_REG 0xF4

// Cấu hình hệ thống
// 7:5: Cài đặt thời gian ngủ giữa các các lần đo (Normal mode)
// 4:2: Bật bộ lọc IIR chống nhiễu
#define BMP280_CONFIG_REG 0xF5

// Dữ liệu áp suất (20 bit)
// 8 + 8 + 4 (7 : 4) = 1 + 1 + 1 bytes
#define BMP280_PRESSURE_MSB_REG 0xF7
#define BMP280_PRESSURE_LSB_REG 0xF8
#define BMP280_PRESSURE_XLSB_REG 0xF9

// Dữ liệu nhiệt độ (20 bit)
#define BMP280_TEMP_MSB_REG 0xFA
#define BMP280_TEMP_LSB_REG 0xFB
#define BMP280_TEMP_XLSB_REG 0xFC

// Lưu hệ số bù trừ
// Các giá trị đo và đọc từ Reg đều là raw
// Áp dụng các công thức để vs các raw data và hệ số bù trừ
// Ta thu được con số thực tế
#define BMP280_COEF_T1 0x88
#define BMP280_COEF_T2 0x8A
#define BMP280_COEF_T3 0x8C
#define BMP280_COEF_P1 0x8E
#define BMP280_COEF_P2 0x90
#define BMP280_COEF_P3 0x92
#define BMP280_COEF_P4 0x94
#define BMP280_COEF_P5 0x96
#define BMP280_COEF_P6 0x98
#define BMP280_COEF_P7 0x9A
#define BMP280_COEF_P8 0x9C
#define BMP280_COEF_P9 0x9E

struct BMP280_CalibData {
    uint16_t dig_T1;
    int16_t  dig_T2;
    int16_t  dig_T3;

    uint16_t dig_P1;
    int16_t  dig_P2;
    int16_t  dig_P3;

    int16_t  dig_P4;
    int16_t  dig_P5;
    int16_t  dig_P6;

    int16_t  dig_P7;
    int16_t  dig_P8;
    int16_t  dig_P9;
};

bool BMP280_Init(uint8_t i2cAddr);
bool BMP280_ReadData(float* temperature, float* pressure);
float BMP280_CalculateAltitude(float currentPressure_hPa, float seaLevelPressure_hPa = 1013.25);

// Test trong main.cpp
void BMP280_TestSetup(void);
void BMP280_TestLoop(void);

#endif