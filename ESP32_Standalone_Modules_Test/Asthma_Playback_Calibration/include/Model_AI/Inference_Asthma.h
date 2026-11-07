#ifndef INFERENCE_ASTHMA_H
#define INFERENCE_ASTHMA_H

#include <Arduino.h>

#include "DSP_Preprocessing/Mel_Scale.h"

struct Asthma_Result {
    float Asthma_Prob;       // Don vi %, chi de hien thi.
    float Non_Asthma_Prob;   // Don vi %, chi de hien thi.
    int Predicted_Class;     // 0: Asthma | 1: Non-Asthma | 2: Unsure | -1: loi.
    int8_t Output_Raw_Int8;  // Output INT8 goc de doi chieu Python/C++.
};

bool Init_Asthma_Model(void);
Asthma_Result Run_Asthma_Inference(float input_mel_db[][MAX_FRAMES]);

#endif
