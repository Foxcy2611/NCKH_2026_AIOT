#ifndef INTERFACE_ASTHMA_H
#define INTERFACE_ASTHMA_H

#include <Arduino.h>
#include "DSP_Preprocessing/Mel_Scale.h"

struct Asthma_Result{
    float Asthma_Prob;
    float Normal_Prob;
    int Predicted_Class;
};

bool Init_Asthma_Model(void);
Asthma_Result Run_Asthma_Interface(float input_mel_db[][MAX_FRAMES]);

#endif