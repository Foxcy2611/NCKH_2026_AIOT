#ifndef NCKH_MEL_SCALE_H
#define NCKH_MEL_SCALE_H

#include <Arduino.h>
#include <arduinoFFT.h>
#include <math.h>

// ==== CẤU HÌNH ====
#define SAMPLE_RATE     16000
#define N_FFT           2048
#define HOP_LENGTH      625
#define N_MELS          40 // C4: 40 dải Mel
#define F_MIN           100.0f // Lowcut
#define F_MAX           2000.0f // Highcut
#define N_FREQ_BINS     1025 // (N_FFT / 2) + 1
#define MAX_FRAMES      129

float Hz_to_Mel(float hz);
float Mel_to_Hz(float mel);

void Get_Centered_Frame(
    const float* input, 
    int Input_length, 
    int frame_idx, 
    float* Out_frame
);

// Cấp phát bảng lọc trong PSRAM và khởi tạo trọng số.
// Trả về false nếu không cấp phát được bộ nhớ.
bool Init_Mel_Filterbank(void);

int Compute_Mel_Power_Spectrogram(
    const float* input,
    int input_length,
    float mel_power_out[][MAX_FRAMES],
    int max_frames
);

void Power_To_dB_RefMax(
    float mel_power[][MAX_FRAMES],
    float mel_db_out[][MAX_FRAMES],
    int num_frames
);

#endif /* NCKH_DSP_FILTER_H */
