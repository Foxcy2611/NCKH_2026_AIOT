#ifndef NCKH_I2S_MIC_H
#define NCKH_I2S_MIC_H

#include <Arduino.h>
#include <driver/i2s.h>
#include "board_pinout.h"

#include "DSP_Preprocessing/DSP_Filter.h"
#include "DSP_Preprocessing/Mel_Scale.h"
#include "Model_AI/Interface_Asthma.h"

enum System_State {
    MICRO_STATE_LISTENING,
    MICRO_STATE_RECORDING,
    MICRO_STATE_PROCESSING,
    MICRO_STATE_INTERFACE,
};

const uint16_t Buffer_Samples = 256;
const uint32_t Sample_Rate = 16000;
const i2s_port_t I2S_Port = I2S_NUM_0;
const uint8_t Amplify_Factor = 1;

void I2S_Mic_Init(int SCK_Pin, int WS_Pin, int SD_Pin);
void Process_Audio_Stream(void);

/* API thêm */
// Thu đủ 80000 samples ở 16KHz, ko dùng VAD/pre-triger
// Block cho tới khi ghi đủ, hủy vẫn đc nếu là SLEEP
bool I2S_RecordSamples(void);

// Con trỏ buffer chứa kết quả manual check gần nhất
// Hợp lệ nếu record sample return true
const int16_t* I2S_GetRecordedBuffer(void);

// Số sample cố định 1 lần Manual Check (80000)
uint32_t I2S_GetRecordedSampleCount(void);

float* I2S_GetFloatBuffer(void);
float (*I2S_GetMelBuffer(void))[MAX_FRAMES];

#endif /* NCKH_I2S_MIC_H */
