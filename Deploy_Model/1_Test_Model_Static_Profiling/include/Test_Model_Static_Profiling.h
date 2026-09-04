#ifndef TEST_MODEL_STATIC_PROFILING_H
#define TEST_MODEL_STATIC_PROFILING_H

#include <Arduino.h>

bool Setup_TinyML();
void Predict_Static_Dummy(
    const signed char* input_data, 
    const char* ten_mau
);

#endif
