#ifndef TEST_ASTHMA_1_H
#define TEST_ASTHMA_1_H

#include <Arduino.h>

bool Setup_TinyML();
void Predict_Static_Dummy_0();
void Predict_Static_Dummy(
    const signed char* input_data, 
    const char* ten_mau
);

#endif