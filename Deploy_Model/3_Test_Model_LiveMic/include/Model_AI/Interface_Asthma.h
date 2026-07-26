#ifndef INTERFACE_ASTHMA_H
#define INTERFACE_ASTHMA_H

#include <Arduino.h>

#include "DSP_Preprocessing/Mel_Scale.h"

struct Asthma_Result{
    float Asthma_Prob; // Xác xuất người bị Hen suyễn
    float Normal_Prob; // Xác suất người bình thường
    int Predicted_Class; // // 0: Asthma | 1: Normal | -1: Khong chac chan
};

// 1. Khởi tạo mô hình
// Return true nếu load model thành công
bool Init_Asthma_Model(void);

// 2. Chạy suy luận
Asthma_Result Run_Asthma_Interface(float input_mel_db[][MAX_FRAMES]);


#endif