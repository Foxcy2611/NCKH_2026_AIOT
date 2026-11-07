#ifndef INFERENCE_ASTHMA_H
#define INFERENCE_ASTHMA_H

#include <Arduino.h>

#include "DSP_Preprocessing/Mel_Scale.h"

struct Asthma_Result {
    float Asthma_Prob;       // Xac suat Asthma, don vi %.
    float Non_Asthma_Prob;   // Xac suat Non-Asthma, don vi %.
    int Predicted_Class;     // 0: Asthma | 1: Non-Asthma | -1: loi.
    int8_t Output_Raw_Int8;  // Output INT8 de doi chieu khi can.
};

// Khởi tạo model cuối C4 V1 s44 / QAT INT8.
bool Init_Asthma_Model(void);

// Ten model dang duoc compile vao firmware.
const char* Get_Asthma_Model_Name(void);

// Mốc Python trong Raw_PCM16_Test_Samples.h được sinh từ cùng model F0.
bool Asthma_Model_Has_Python_Reference(void);

// Chay suy luan tu Mel-spectrogram do pipeline C++ tao ra.
Asthma_Result Run_Asthma_Inference(float input_mel_db[][MAX_FRAMES]);

#endif
