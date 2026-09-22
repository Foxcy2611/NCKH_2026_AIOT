#ifndef ESP32_MLX90614_DRIVER_H
#define ESP32_MLX90614_DRIVER_H

#include <Arduino.h>
#include <Wire.h>

#define MLX90614_ADDR_I2C 0x5A
#define MLX90614_REG_TA    0x06 // Thanh ghi RAM nhiệt độ môi trường
#define MLX90614_REG_TOBJ1 0x07 // Thanh ghi nhiệt độ đối tượng/thân nhiệt

bool MLX90614_ReadWord(uint8_t regAddr, uint16_t *data);
bool MLX90614_Read_Object_Temp(float *tempC);
bool MLX90614_Read_Ambient_Temp(float *tempC);

// ==== Hàm test main ====
void MLX90614_TestSetup();
void MLX90614_TestLoop();

#endif