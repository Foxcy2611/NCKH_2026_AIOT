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
// #define L_R_Pin 3.3V

enum System_State {
    STATE_LISTENING, // Đang nghe ngóng để quyết định
    STATE_RECORDING, // Ghi đủ 5s, chạy đủ 312 lần (312.5 x 256 = 80k)
    STATE_PROCESSING, // TXL
    STATE_INTERFACE, // Chạy AI, gọi hàm Invoke()
};

// Thu đc 256 mẫu thì ném vào mảng
// Ứng với 256/16k = 0.016s
const uint16_t Buffer_Samples = 256;

// Tốc độ lấy mẫu 16k => 1s đẻ ra 16k mẫu
const uint32_t Sample_Rate = 16000;

const i2s_port_t I2S_Port = I2S_NUM_0;

const uint8_t Amplify_Factor = 4;

void I2S_Mic_Init(
    int SCK_Pin,
    int WS_Pin,
    int SD_Pin
);

void Process_Audio_Stream(void);

#endif