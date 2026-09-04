#ifndef INTERFACE_ASTHMA_H
#define INTERFACE_ASTHMA_H

#include <Arduino.h>

#include "DSP_Preprocessing/Mel_Scale.h"

struct Asthma_Result {
    float Asthma_Prob;
    float Non_Asthma_Prob;
    int Predicted_Class;
    int8_t Output_Raw_Int8;
};

bool Init_Asthma_Model(void);
Asthma_Result Run_Asthma_Interface(float input_mel_db[][MAX_FRAMES]);

#endif
