#ifndef DSP_FILTER_H
#define DSP_FILTER_H

#include <Arduino.h>

const float Pre_Coef = 0.97f;

void Apply_Pre_Emphasis(float* signal, int length);

void Butterworth_Reset(void);
float Butterworth_Process_Sample(float x_new);
void Butterworth_Process_Buffer(float* buffer, int length);

void Normalize_To_Float(int16_t* input, float* output, int length);

#endif