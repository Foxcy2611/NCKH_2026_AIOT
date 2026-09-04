#ifndef INTERFACE_ASTHMA_H
#define INTERFACE_ASTHMA_H

#include <Arduino.h>

#include "DSP_Preprocessing/Mel_Scale.h"

struct Asthma_Result{
    float Asthma_Prob;     // Xác suất thuộc lớp Asthma
    float Non_Asthma_Prob; // Xác suất thuộc lớp Non-Asthma
    int Predicted_Class;   // 0: Asthma | 1: Non-Asthma
    int8_t Output_Raw_Int8; // Giá trị output thô để đối chiếu Python
};

struct Input_Tensor_Comparison{
    int Different_Count;
    int Max_Abs_Difference;
    float Mean_Abs_Difference;
};

// 1. Khởi tạo mô hình
// Return true nếu load model thành công
bool Init_Asthma_Model(void);

// 2. Nạp input và chạy suy luận.
// Khi kiểm tra đối chiếu, tensor được so ngay trước Invoke() để tránh vùng nhớ
// input bị TensorFlow Lite Micro tái sử dụng trong lúc suy luận.
Asthma_Result Run_Asthma_Interface(
    float input_mel_db[][MAX_FRAMES],
    const int8_t* expected_tensor = nullptr,
    int expected_length = 0,
    Input_Tensor_Comparison* comparison_out = nullptr
);

// So tensor INT8 vừa nạp vào model với tensor tham chiếu do Python tạo.
Input_Tensor_Comparison Compare_Asthma_Input_Tensor(
    const int8_t* expected,
    int expected_length
);

/**/ // THAY ĐỔI P4: Hàm nạp thẳng tensor INT8, bỏ qua toàn bộ preprocess C++.
Asthma_Result Run_Asthma_From_Int8_Tensor(
    const int8_t* tensor_int8,
    int tensor_length,
    float decision_threshold = 0.5f
);

#endif
