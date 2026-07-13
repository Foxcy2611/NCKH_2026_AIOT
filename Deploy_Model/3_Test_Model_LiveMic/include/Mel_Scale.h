#ifndef MEL_SCALE_H
#define MEL_SCALE_H

#include <Arduino.h>
#include <arduinoFFT.h>
#include <math.h>

// ==== CẤU HÌNH ====
#define SAMPLE_RATE     16000
#define N_FFT           1024
#define HOP_LENGTH      625
#define N_MELS          64
#define F_MIN           100.0f // Lowcut
#define F_MAX           2000.0f // Highcut
#define N_FREQ_BINS     513
#define MAX_FRAMES      129

float Hz_to_Mel(float hz);
float Mel_to_Hz(float mel);

void Get_Centered_Frame(
    const float* input, 
    int Input_length, 
    int frame_idx, 
    float* Out_frame
);

void Init_Mel_Filterbank(void);

int Compute_Mel_Power_Spectrogram(
    const float* input,
    int input_length,
    float mel_power_out[][N_MELS],
    int max_frames
);

void Power_To_dB_RefMax(
    float mel_power[][N_MELS],
    float mel_db_out[][N_MELS],
    int num_frames
);

#endif