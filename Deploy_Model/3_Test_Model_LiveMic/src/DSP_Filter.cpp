#include "DSP_Preprocessing/DSP_Filter.h"

// ==== BỘ LỌC BUTTERWORTH BANDPASS BẬC 5 - DẠNG SOS (CASCADE BIQUAD) ====
// Hệ số lấy từ 9_Coef_Butter.py:
// scipy.signal.butter(5, [100,2000]/nyq, btype='band', output='sos')
// # y[n] = b0.x[n] + b1.x[n-1] + b2.x[n-2] - a1.y[n-1] - a2.y[n-2]

struct BiquadCoeffs {
    float b0, b1, b2;
    float a1, a2;
};

#define NUM_SECTIONS 5

static const BiquadCoeffs sos_coeffs[NUM_SECTIONS] = {
    // {  b0,          b1,          b2,          a1,           a2        }
    {  0.0026486f,  0.0052972f,  0.0026486f, -0.96499274f,  0.31053903f },
    {  1.0f,         2.0f,        1.0f,      -1.1858251f,   0.66801213f },
    {  1.0f,         0.0f,       -1.0f,      -1.41421356f,  0.43740897f },
    {  1.0f,        -2.0f,        1.0f,      -1.93546095f,  0.93714828f },
    {  1.0f,        -2.0f,        1.0f,      -1.97630681f,  0.97785523f }
};

// Trạng thái trễ (delay line) — đổi tên tránh trùng với hàm math.h (y1, y2 là hàm Bessel)
static float sos_x1[NUM_SECTIONS] = {0.0f}; // x[n-1]
static float sos_x2[NUM_SECTIONS] = {0.0f}; // x[n-2]
static float sos_y1[NUM_SECTIONS] = {0.0f}; // y[n-1]
static float sos_y2[NUM_SECTIONS] = {0.0f}; // y[n-2]

// ==== PRE-EMPHASIS ====
// y[n] = x[n] - coef . x[n-1]
void Apply_Pre_Emphasis(float* signal, int length){
    if(length <= 1) return;

    for(int i = length - 1 ; i >= 1 ; i--){
        signal[i] = signal[i] - Pre_Coef * signal[i - 1];
    }
}

// ==== RESET TRẠNG THÁI BUTTERWORTH ====
void Butterworth_Reset(void) {
    for (int i = 0; i < NUM_SECTIONS; i++) {
        sos_x1[i] = sos_x2[i] = sos_y1[i] = sos_y2[i] = 0.0f;
    }
}

// ==== LỌC 1 SAMPLE QUA 5 SECTION NỐI TIẾP (CASCADE) ====
// Mô phỏng phương trình bộ lọc
// Dòng chảy dữ liệu: Tín hiệu đi vào section 0, tính toán ra out. 
// Giá trị out này lập tức trở thành in cho section 1, 
// cứ thế cuốn cuốn qua đủ 5 lớp
// y[n] = b0.x[n] + b1.x[n-1] + b2.x[n-2] - a1.y[n-1] - a2.y[n-2]
float Butterworth_Process_Sample(float x_new) {
    float in = x_new;

    for (int s = 0; s < NUM_SECTIONS; s++) {
        const BiquadCoeffs& coef = sos_coeffs[s];

        float out = coef.b0 * in + coef.b1 * sos_x1[s] + coef.b2 * sos_x2[s]
                     - coef.a1 * sos_y1[s] - coef.a2 * sos_y2[s];

        sos_x2[s] = sos_x1[s];
        sos_x1[s] = in;
        sos_y2[s] = sos_y1[s];
        sos_y1[s] = out;

        in = out;
    }

    return in;
}

// ==== LỌC CẢ BUFFER ====
void Butterworth_Process_Buffer(float* buffer, int length) {
    for (int i = 0; i < length; i++) {
        buffer[i] = Butterworth_Process_Sample(buffer[i]);
    }
}

// ==== CHUẨN HÓA int16 -> float [-1, 1] ====
// int32 tránh tràn số khi đạt max dải
void Normalize_To_Float(int16_t* input, float* output, int length){
    int32_t max_val = 0;
    
    // Tìm giá trị max làm tham chiếu
    for(int i = 0 ; i < length ; i++){
        int32_t abs_val = abs(input[i]);

        if(abs_val > max_val) max_val = abs_val;
    }
    
    // Chống chia cho 0
    if(max_val == 0) max_val = 1;

    for(int i = 0 ; i < length ; i++){
        output[i] = input[i] / (float)max_val;
    }
}