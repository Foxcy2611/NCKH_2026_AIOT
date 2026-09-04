#ifndef I2S_MIC_H
#define I2S_MIC_H

#include <Arduino.h>
#include <driver/i2s.h>

#include "DSP_Preprocessing/DSP_Filter.h"
#include "DSP_Preprocessing/Mel_Scale.h"
#include "Model_AI/Interface_Asthma.h"

#define I2S_WS 15
#define I2S_SD 16
#define I2S_SCK 14

enum System_State {
    STATE_LISTENING,
    STATE_RECORDING,
    STATE_PROCESSING,
    STATE_INTERFACE,
};

const uint16_t Buffer_Samples = 256;
const uint32_t Sample_Rate = 16000;
const i2s_port_t I2S_Port = I2S_NUM_0;
const uint8_t Amplify_Factor = 1;

void I2S_Mic_Init(int SCK_Pin, int WS_Pin, int SD_Pin);
void Process_Audio_Stream(void);

#endif
