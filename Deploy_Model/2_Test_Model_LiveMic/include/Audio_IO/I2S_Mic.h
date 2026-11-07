#ifndef I2S_MIC_H
#define I2S_MIC_H

#include <Arduino.h>
#include <driver/i2s.h>

#include "DSP_Preprocessing/DSP_Filter.h"
#include "DSP_Preprocessing/Mel_Scale.h"
#include "Model_AI/Inference_Asthma.h"

#define I2S_WS 15
#define I2S_SD 16
#define I2S_SCK 14

// 1: chay 12 WAV PCM16 nhung san qua toan bo preprocess C++ + model.
// 0: doc INMP441 that, dung VAD va vote 3 lan.
#define RUN_RAW_PCM16_TEST 1

// Che do do nang luong VAD; khong chay model. Khong bat cung RAW test.
#define RUN_VAD_CALIBRATION_TEST 0

#if (RUN_RAW_PCM16_TEST + RUN_VAD_CALIBRATION_TEST) > 1
#error "Chi duoc bat mot che do kiem tra tai mot thoi diem"
#endif

enum System_State {
    STATE_LISTENING,
    STATE_RECORDING,
    STATE_PROCESSING,
    STATE_INFERENCE,
    STATE_DONE,
};

constexpr uint16_t Buffer_Samples = 256;
constexpr uint32_t Sample_Rate = 16000;
constexpr i2s_port_t I2S_Port = I2S_NUM_0;
constexpr uint8_t Amplify_Factor = 1;

// Cap phat buffer. Chi khoi tao I2S hardware khi RUN_RAW_PCM16_TEST=0.
void I2S_Mic_Init(int SCK_Pin, int WS_Pin, int SD_Pin);

// Chay state machine audio: RAW header hoac INMP441 tuy cau hinh tren.
void Process_Audio_Stream(void);

// Do phan bo nang luong nen/tin hieu de chon nguong VAD.
void Run_VAD_Calibration(void);

#endif
