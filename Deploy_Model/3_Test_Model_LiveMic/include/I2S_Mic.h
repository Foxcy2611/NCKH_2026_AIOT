#ifndef I2S_MIC_H
#define I2S_MIC_H

#include <Arduino.h>
#include <driver/i2s.h>

#define I2S_WS 15
#define I2S_SD 32
#define I2S_SCK 14

const uint16_t Buffer_Samples = 256;

const uint32_t Sample_Rate = 16000;
const i2s_port_t I2S_Port = I2S_NUM_0;

const uint8_t Amplify_Factor = 4;

void I2S_Mic_Init(
    int SCK_Pin,
    int WS_Pin,
    int SD_Pin
);

void I2S_Mic_Read_and_Send(void);

#endif