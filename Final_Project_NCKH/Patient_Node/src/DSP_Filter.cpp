#include "DSP_Preprocessing/DSP_Filter.h"

// ==== BUTTERWORTH BANDPASS BẬC 5, DẠNG BA GIỐNG SCIPY.LFILTER ====
// Python dùng:
// butter(5, [100/8000, 2000/8000], btype="band") rồi lfilter(b, a, audio).
// Bộ lọc bandpass thu được có bậc thực tế là 10. Dùng số double cho hệ số
// và trạng thái để giảm sai lệch tích lũy so với scipy (float64).
static constexpr int FILTER_ORDER = 10;

static const double FILTER_B[FILTER_ORDER + 1] = {
     0.00264859843270488, 0.0,
    -0.01324299216352442, 0.0,
     0.02648598432704884, 0.0,
    -0.02648598432704884, 0.0,
     0.01324299216352442, 0.0,
    -0.00264859843270488
};

static const double FILTER_A[FILTER_ORDER + 1] = {
     1.0,
    -7.476799167318891,
    25.287631600296383,
   -51.077736076658205,
    68.3766618665573,
   -63.475048625087915,
    41.40605063526075,
   -18.741440784236254,
     5.632155953182581,
    -1.014627085470675,
     0.08315169357239377
};

// Trạng thái của Direct Form II Transposed, cùng cấu trúc scipy.signal.lfilter.
static double filter_state[FILTER_ORDER] = {0.0};

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
    for(int i = 0; i < FILTER_ORDER; i++){
        filter_state[i] = 0.0;
    }
}

float Butterworth_Process_Sample(float x_new){
    const double x = static_cast<double>(x_new);
    const double y = FILTER_B[0] * x + filter_state[0];

    for(int i = 0; i < FILTER_ORDER - 1; i++){
        filter_state[i] = filter_state[i + 1]
                        + FILTER_B[i + 1] * x
                        - FILTER_A[i + 1] * y;
    }
    filter_state[FILTER_ORDER - 1] = FILTER_B[FILTER_ORDER] * x
                                   - FILTER_A[FILTER_ORDER] * y;

    return static_cast<float>(y);
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
        const int32_t sample = static_cast<int32_t>(input[i]);
        const int32_t abs_val = (sample < 0) ? -sample : sample;

        if(abs_val > max_val) max_val = abs_val;
    }
    
    // Chống chia cho 0
    if(max_val == 0) max_val = 1;

    for(int i = 0 ; i < length ; i++){
        output[i] = input[i] / (float)max_val;
    }
}
