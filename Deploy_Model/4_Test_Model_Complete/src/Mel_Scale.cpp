#include "DSP_Preprocessing/Mel_Scale.h"

static float vReal[N_FFT];
static float vImag[N_FFT];
static float mel_filterbank[N_MELS][N_FREQ_BINS];
ArduinoFFT<float> FFT(vReal, vImag, N_FFT, (float)SAMPLE_RATE);

float Hz_to_Mel(float hz){
    const float f_sp = 200.0f / 3.0f;
    const float min_log_hz = 1000.0f;
    const float min_log_mel = min_log_hz / f_sp;
    const float logstep = logf(6.4f) / 27.0f;

    if (hz < min_log_hz) return hz / f_sp;
    return min_log_mel + logf(hz / min_log_hz) / logstep;
}

float Mel_to_Hz(float mel){
    const float f_sp = 200.0f / 3.0f;
    const float min_log_hz = 1000.0f;
    const float min_log_mel = min_log_hz / f_sp;
    const float logstep = logf(6.4f) / 27.0f;

    if (mel < min_log_mel) return mel * f_sp;
    return min_log_hz * expf(logstep * (mel - min_log_mel));
}

void Get_Centered_Frame(
    const float* input, 
    int Input_length, 
    int frame_idx, 
    float* Out_frame
){
    int pad = N_FFT / 2;
    int start_idx = (frame_idx * HOP_LENGTH) - pad;

    for(int i = 0; i < N_FFT; i++){
        int real_idx = start_idx + i;

        if(real_idx < 0 || real_idx >= Input_length){
            Out_frame[i] = 0.0f;
        } else {
            Out_frame[i] = input[real_idx];
        }
    }
}

void Init_Mel_Filterbank(void){
    float mel_max = Hz_to_Mel(F_MAX);
    float mel_min = Hz_to_Mel(F_MIN);

    float mel_points[N_MELS + 2];
    for(int i = 0; i < N_MELS + 2; i++){
        mel_points[i] = mel_min + (mel_max - mel_min) * i / (N_MELS + 1);
    }

    int bin_points[N_MELS + 2];
    float hz_points[N_MELS + 2];
    for(int i = 0; i < N_MELS + 2; i++){
        float hz = Mel_to_Hz(mel_points[i]);
        hz_points[i] = hz;
        bin_points[i] = (int)floorf((N_FFT + 1) * hz / SAMPLE_RATE);
    }

    for(int m = 0; m < N_MELS; m++){
        for(int f = 0; f < N_FREQ_BINS; f++){
            mel_filterbank[m][f] = 0.0f;
        }
    }

    for(int m = 1; m <= N_MELS; m++){
        int f_left = bin_points[m - 1];
        int f_center = bin_points[m];
        int f_right = bin_points[m + 1];

        for(int f = f_left; f < f_center; f++){
            if(f >= 0 && f < N_FREQ_BINS && f_center != f_left){
                mel_filterbank[m - 1][f] = 
                (float)(f - f_left) / (f_center - f_left);
            }
        }

        for(int f = f_center; f < f_right; f++){
            if(f >= 0 && f < N_FREQ_BINS && f_center != f_right){
                mel_filterbank[m - 1][f] = 
                (float)(f_right - f) / (f_right - f_center);
            }
        }

        float enorm = 2.0f / (hz_points[m + 1] - hz_points[m - 1]);
        for(int f = 0; f < N_FREQ_BINS; f++){
            mel_filterbank[m - 1][f] *= enorm;
        }
    }
}

int Compute_Mel_Power_Spectrogram(
    const float* input, 
    int input_length,
    float mel_power_out[][MAX_FRAMES], 
    int max_frames
){
    static float frame_buf[N_FFT];
    static float power_spectrum[N_FREQ_BINS];

    int num_frames = (input_length / HOP_LENGTH) + 1;
    if(num_frames > max_frames) num_frames = max_frames;

    for(int frame_idx = 0; frame_idx < num_frames; frame_idx++){
        Get_Centered_Frame(input, input_length, frame_idx, frame_buf);

        for(int i = 0; i < N_FFT; i++){
            vReal[i] = frame_buf[i];
            vImag[i] = 0.0f;
        }

        FFT.windowing(FFTWindow::Hann, FFTDirection::Forward);
        FFT.compute(FFTDirection::Forward);

        for(int k = 0; k < N_FREQ_BINS; k++){
            power_spectrum[k] = vReal[k] * vReal[k] + vImag[k] * vImag[k];
        }

        for(int m = 0; m < N_MELS; m++){
            float mel_energy = 0.0f;
            for(int k = 0; k < N_FREQ_BINS; k++){
                mel_energy += power_spectrum[k] * mel_filterbank[m][k];
            }
            mel_power_out[m][frame_idx] = mel_energy;
        }
    }

    return num_frames;
}

void Power_To_dB_RefMax(
    float mel_power[][MAX_FRAMES], 
    float mel_db_out[][MAX_FRAMES], 
    int num_frames
){
    const float epsilon = 1e-10f;
    const float top_db = 80.0f;

    float max_power = epsilon;
    for(int m = 0 ; m < N_MELS ; m++){
        for(int f = 0 ; f < num_frames ; f++){
            if(mel_power[m][f] > max_power){
                max_power = mel_power[m][f];
            }
        }
    }

    float max_db = -INFINITY;
    for(int m = 0 ; m < N_MELS ; m++){
        for(int f = 0 ; f < num_frames ; f++){
            float p = mel_power[m][f];
            
            if(p < epsilon) p = epsilon; 
            
            float db = 10.0f * log10f(p / max_power);
            mel_db_out[m][f] = db;

            if(db > max_db) max_db = db;
        }
    }

    float floor_db = max_db - top_db;
    for(int m = 0 ; m < N_MELS ; m++){
        for(int f = 0 ; f < num_frames ; f++){
            if(mel_db_out[m][f] < floor_db){
                mel_db_out[m][f] = floor_db;
            }
        }
    }
}