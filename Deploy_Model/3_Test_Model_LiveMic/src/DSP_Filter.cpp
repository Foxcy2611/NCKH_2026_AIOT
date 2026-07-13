#include "DSP_Filter.h"

#define FILTER_ORDER 10   // Bậc 10 do bandpass bậc 5 -> 2*order
#define NUM_COEFFS (FILTER_ORDER + 1) // 11 hệ số

// Dùng static để giữ trạng thái qua các gói I2S liên tiếp
static float x_hist[NUM_COEFFS] = {0.0f}; 
static float y_hist[NUM_COEFFS] = {0.0f}; 

// Cặp hệ số trích xuất từ Python (Bandpass Order 5 -> 11 hệ số)
const float b_coeffs[11] = { 
    0.00264860f, 0.00000000f, -0.01324299f, 0.00000000f, 0.02648598f, 
    0.00000000f, -0.02648598f, 0.00000000f, 0.01324299f, 0.00000000f, -0.00264860f 
};

const float a_coeffs[11] = { 
    1.00000000f, -7.47679917f, 25.28763160f, -51.07773608f, 68.37666187f, 
    -63.47504863f, 41.40605064f, -18.74144078f, 5.63215595f, -1.01462709f, 0.08315169f 
};

// Filter Pre-Amphasis
// y[n] = x[n] - a.x[n-1]
void Apply_Pre_Emphasis(int16_t* signal, int length){
    if(length <= 1) return;

    for(int i = length - 1 ; i >= 1 ; i--){
        signal[i] = signal[i] - (int16_t)(Pre_Coef * signal[i - 1]);
    }
}

// Reset trạng thái (Gọi khi bắt đầu state STATE_RECORDING)
void Butterworth_Reset(void) {
    for (int i = 0; i < NUM_COEFFS; i++) {
        x_hist[i] = 0.0f;
        y_hist[i] = 0.0f;
    }
}

// Lọc từng sample (Logic đã được làm đồng bộ, mượt mà hơn)
// Công thức: y[n] = sigma(k=0 -> 10)(bk.x[n-k]) - sigma(k=1 -> 10)(ak.y[n-k])
float Butterworth_Process_Sample(float x_new) {
    // 1. Dịch toàn bộ lịch sử input và output lùi lại 1 bước
    for (int i = NUM_COEFFS - 1; i > 0; i--) {
        x_hist[i] = x_hist[i - 1];
        y_hist[i] = y_hist[i - 1];
    }
    
    // 2. Nạp giá trị hiện tại vào đầu mảng input
    x_hist[0] = x_new;

    // 3. Tính toán phương trình sai phân
    float acc = 0.0f;
    for (int k = 0; k < NUM_COEFFS; k++) {
        acc += b_coeffs[k] * x_hist[k];
    }
    for (int k = 1; k < NUM_COEFFS; k++) {
        acc -= a_coeffs[k] * y_hist[k]; // <-- Giờ chỉ cần gọi y_hist[k], không cần [k-1] nữa
    }

    // 4. Lưu lại kết quả output hiện tại và trả về
    y_hist[0] = acc;
    return acc;
}

// Lọc cả buffer (Đã đổi sang int16_t để khớp với kho audio_buffer của I2S)
void Butterworth_Process_Buffer(int16_t* buffer, int length) {
    for (int i = 0; i < length; i++) {
        // Ép kiểu int16_t sang float để xử lý, sau đó ép ngược lại in-place
        float x_float = (float)buffer[i];
        float y_float = Butterworth_Process_Sample(x_float);
        buffer[i] = (int16_t)y_float;
    }
}

void Normalize_To_Float(int16_t* input, float* output, int length){
    int16_t max_val = 0;
    
    for(int i = 0 ; i < length ; i++){
        int16_t abs_val = abs(input[i]);

        if(abs_val > max_val) max_val = abs_val;
    }

    if(max_val == 0) max_val = 1;

    for(int i = 0 ; i < length ; i++){
        output[i] = input[i] / (float)max_val;
    }
}