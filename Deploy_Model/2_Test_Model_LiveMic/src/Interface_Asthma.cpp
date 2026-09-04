#include "Model_AI/Interface_Asthma.h"
#include <TensorFlowLite_ESP32.h>
#include <math.h>

#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/system_setup.h"
#include "tensorflow/lite/schema/schema_generated.h"

// Model INT8 tạo bởi AI_Training_Model/P3_Quantize_Model/Quantize_Model.py
#include "Model_AI/Asthma_Model_3.h"

// ==== BIẾN TOÀN CỤC ====
const tflite::Model* model = nullptr;
tflite::MicroInterpreter* interpreter = nullptr;
tflite::ErrorReporter* error_reporter = nullptr;
TfLiteTensor* input_tensor = nullptr;
TfLiteTensor* output_tensor = nullptr;

const int kTensorArenaSize = 270 * 1024;
static uint8_t* tensor_arena = nullptr;

static tflite::MicroErrorReporter micro_error_reporter;
static tflite::AllOpsResolver resolver; // full toán tử

// Dùng đúng ngưỡng đã đánh giá trong Python.
// Vùng "không chắc chắn" và bỏ phiếu là bước hậu xử lý, chỉ thêm sau khi
// Python và ESP32 đã cho cùng kết quả với ngưỡng 0.5.
static constexpr float DECISION_THRESHOLD = 0.5f;

bool Init_Asthma_Model(void){
    // 1. Khai báo ... và hệ thống phát hiện lỗi (Tự động in lên monitor khi lỗi)
    tflite::InitializeTarget();
    error_reporter = &micro_error_reporter;
    
    Serial.printf("[DEBUG] model_data_len = %d bytes\n", model_data_len);
    
    // 2. Cấp phát ra ngoài PSRAM, vì RAM nội bộ quá ít
    if(tensor_arena == nullptr){
        tensor_arena = (uint8_t*)heap_caps_aligned_alloc(
            16, kTensorArenaSize, // Căn lề 16-byte
            // Hai FLAG quan trọng:
            // Không đc động vào RAM nội, ra PSRAM tìm | 
            // Báo hệ thống đc truy xuất vs 8bit (Cùng dạng uint8_t* vs tensor arena)
            MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT
        );

        if(tensor_arena == nullptr){
            TF_LITE_REPORT_ERROR(error_reporter, 
                "[LỖI] Không thể cấp phát %d bytes PSRAM cho Tensor Arena!", kTensorArenaSize 
            );
            return false;
        }
        
        Serial.println("[AI] Đã cấp phát thành công trên PSRAM !");

    }

    // 3. Load model và kiểm tra phiên bản
    model = tflite::GetModel(model_data);
    if(model->version() != TFLITE_SCHEMA_VERSION){
        TF_LITE_REPORT_ERROR(error_reporter,
            "[LỖI] Phiên bản schema mô hình (%d) không khớp với TFLITE (%d)!",
            model->version(), TFLITE_SCHEMA_VERSION
        );

        return false;
    }

    // 4. Tạo Interpreter (Phiên dịch viên)
    static tflite::MicroInterpreter static_interpreter(
        model, resolver, tensor_arena,
        kTensorArenaSize, error_reporter
    );
    interpreter = &static_interpreter;

    // 5. Cấp phát tensor arena
    TfLiteStatus allocate_status = interpreter->AllocateTensors();
    if (allocate_status != kTfLiteOk) {
        TF_LITE_REPORT_ERROR(error_reporter, "[LỖI] Cấp phát Tensor Arena thất bại. Hãy kiểm tra lại PSRAM!");
        return false;
    }

    // 6. Lấy input/output tensor
    input_tensor = interpreter->input(0);
    output_tensor = interpreter->output(0);

    if(input_tensor->type != kTfLiteInt8 || output_tensor->type != kTfLiteInt8){
        TF_LITE_REPORT_ERROR(error_reporter,
            "[LỖI] Model phải có cả input và output kiểu INT8!");
        return false;
    }

    if(input_tensor->dims->size != 4 ||
       input_tensor->dims->data[0] != 1 ||
       input_tensor->dims->data[1] != N_MELS ||
       input_tensor->dims->data[2] != MAX_FRAMES ||
       input_tensor->dims->data[3] != 1){
        TF_LITE_REPORT_ERROR(error_reporter,
            "[LỖI] Kích thước input model không phải [1, 64, 129, 1]!");
        return false;
    }

    // 7. Debug thông tin input
    // scale: Hệ số chuyển đổi giá trị int8 sang float
    // zero_point: Offset để quy đổi dữ liệu
    Serial.printf("[DEBUG] Input scale=%.6f, zero_point=%d\n", 
    input_tensor->params.scale, input_tensor->params.zero_point);
    Serial.printf("[DEBUG] Output scale=%.6f, zero_point=%d\n",
    output_tensor->params.scale, output_tensor->params.zero_point);

    Serial.println("[AI] Khởi tạo mô hình Asthma TFLite THÀNH CÔNG!");
    Serial.printf("[AI] Input shape: [%d, %d, %d, %d]\n",  // Phải là [1, 64, 129, 1]
        input_tensor->dims->data[0], input_tensor->dims->data[1], 
        input_tensor->dims->data[2], input_tensor->dims->data[3]);

    return true;
}

Asthma_Result Run_Asthma_Interface(
    float input_mel_db[][MAX_FRAMES],
    const int8_t* expected_tensor,
    int expected_length,
    Input_Tensor_Comparison* comparison_out
){
    Asthma_Result result = {0.0f, 0.0f, -1, 0};

    // ==== HẰNG SỐ CỐ ĐỊNH từ lúc train ====
    const float TRAIN_MIN_VAL = -80.0f;
    const float TRAIN_MAX_VAL = 0.0f;
    const float TRAIN_RANGE = TRAIN_MAX_VAL - TRAIN_MIN_VAL;   // = 80.0f

    // 1. Quét theo chuẩn ảnh: Khi nạp vào Conv2D, nó sẽ quét từng điểm ảnh của 1 bức ảnh (pixel)
    for(int mel_idx = 0 ; mel_idx < N_MELS ; mel_idx++){
        for(int frame_idx = 0 ; frame_idx < MAX_FRAMES ; frame_idx++){
            float val = input_mel_db[mel_idx][frame_idx]; // Giá trị dB 1 điểm ảnh
            int idx = mel_idx * MAX_FRAMES + frame_idx; // Đập dẹp thành 1 mảng 1D gồm 8256 phần tử
            // Lượng tử hóa mẫu đầu vào từ float->int8
            // Vẫn như mọi mẫu, khi đi qua Preprocess C++ nó là Float
            // Việc lượng tử về int8 phù hợp vs model TFLite

            // Chuẩn hóa về [0, 1], giống Training_Model.py.
            float normalized = (val - TRAIN_MIN_VAL) / TRAIN_RANGE;
            if(normalized < 0.0f) normalized = 0.0f;
            if(normalized > 1.0f) normalized = 1.0f;

            // np.round() của Python và lrintf() đều làm tròn tới số nguyên gần nhất
            // trong chế độ làm tròn mặc định. Không ép kiểu trực tiếp vì cách đó
            // chỉ cắt phần thập phân và làm lệch tensor INT8.
            long quantized = lrintf(normalized / input_tensor->params.scale
                                  + input_tensor->params.zero_point);
            if(quantized > 127) quantized = 127;
            if(quantized < -128) quantized = -128;
            input_tensor->data.int8[idx] = static_cast<int8_t>(quantized);
        }
    }

    // Phải so sánh tại đây, trước Invoke(). TensorFlow Lite Micro có thể dùng
    // lại vùng nhớ input làm vùng nhớ trung gian trong quá trình suy luận.
    if(comparison_out != nullptr){
        *comparison_out = Compare_Asthma_Input_Tensor(
            expected_tensor,
            expected_length
        );
    }

    Serial.println("[DEBUG] 10 gia tri int8 dau cua input_tensor:");
    for (int i = 0; i < 10; i++) {
        Serial.printf("%d ", input_tensor->data.int8[i]);
    }
    Serial.println();

    // Đếm xem có bao nhiêu giá trị bị clamp chạm biên 127 hoặc -128
    int count_127 = 0, count_neg128 = 0;
    int total = N_MELS * MAX_FRAMES;
    for (int i = 0; i < total; i++) {
        if (input_tensor->data.int8[i] == 127) count_127++;
        if (input_tensor->data.int8[i] == -128) count_neg128++;
    }
    Serial.printf("[DEBUG] So gia tri = 127: %d / %d | = -128: %d / %d\n", 
        count_127, total, count_neg128, total);

    // 2. Run Invoke()
    TfLiteStatus invoke_sts = interpreter->Invoke();
    if(invoke_sts != kTfLiteOk){
        TF_LITE_REPORT_ERROR(error_reporter,
        "[LỖI] Chạy Invoke() thất bại");
        return result;
    }

    // 3. Đọc kết quả từ Output Tensor (SIGMOID, chỉ 1 giá trị)
    float scale = output_tensor->params.scale;
    int zero_point = output_tensor->params.zero_point;
    int8_t raw = output_tensor->data.int8[0];
    result.Output_Raw_Int8 = raw;
    float probability = (raw - zero_point) * scale;
    if(probability < 0.0f) probability = 0.0f;
    if(probability > 1.0f) probability = 1.0f;

    // 4. KẾT LUẬN — gần 0 = Asthma, gần 1 = Non-Asthma.
    // Non-Asthma không đồng nghĩa với một người chắc chắn khỏe mạnh.
    result.Asthma_Prob = (1.0f - probability) * 100.0f;
    result.Non_Asthma_Prob = probability * 100.0f;

    // Trong phần đọc output, thêm ngay trước khi tính probability
    Serial.printf("[DEBUG] Output raw int8: %d, scale=%.6f, zero_point=%d\n",
    output_tensor->data.int8[0], output_tensor->params.scale, output_tensor->params.zero_point);
//
    if(probability < DECISION_THRESHOLD){
        result.Predicted_Class = 0;
        Serial.printf(">> Kết quả sàng lọc: ASTHMA (%.2f%%)\n",
            result.Asthma_Prob);
    }else{
        result.Predicted_Class = 1;
        Serial.printf(">> Kết quả sàng lọc: NON-ASTHMA (%.2f%%)\n",
            result.Non_Asthma_Prob);
    }

    return result;
}

Input_Tensor_Comparison Compare_Asthma_Input_Tensor(
    const int8_t* expected,
    int expected_length
){
    Input_Tensor_Comparison comparison = {-1, -1, -1.0f};
    const int tensor_length = N_MELS * MAX_FRAMES;

    if(expected == nullptr || input_tensor == nullptr ||
       input_tensor->type != kTfLiteInt8 || expected_length != tensor_length){
        return comparison;
    }

    comparison.Different_Count = 0;
    comparison.Max_Abs_Difference = 0;
    long total_abs_difference = 0;

    for(int i = 0; i < tensor_length; i++){
        int difference = static_cast<int>(input_tensor->data.int8[i])
                       - static_cast<int>(expected[i]);
        if(difference < 0) difference = -difference;

        if(difference != 0) comparison.Different_Count++;
        if(difference > comparison.Max_Abs_Difference){
            comparison.Max_Abs_Difference = difference;
        }
        total_abs_difference += difference;
    }

    comparison.Mean_Abs_Difference =
        static_cast<float>(total_abs_difference) / tensor_length;
    return comparison;
}

/**/ // THAY ĐỔI P4: Hàm mới đặt cuối file, chạy model trực tiếp từ tensor INT8 Python.
Asthma_Result Run_Asthma_From_Int8_Tensor(
    const int8_t* tensor_int8,
    int tensor_length,
    float decision_threshold
){
    Asthma_Result result = {0.0f, 0.0f, -1, 0};
    const int required_length = N_MELS * MAX_FRAMES;

    if(interpreter == nullptr || input_tensor == nullptr ||
       output_tensor == nullptr){
        Serial.println("[LỖI] Model chưa được khởi tạo!");
        return result;
    }

    if(tensor_int8 == nullptr || tensor_length != required_length){
        Serial.printf(
            "[LỖI] Tensor INT8 phải có đúng %d phần tử, nhận %d!\n",
            required_length,
            tensor_length
        );
        return result;
    }

    if(input_tensor->type != kTfLiteInt8 || output_tensor->type != kTfLiteInt8){
        Serial.println("[LỖI] Model không có input/output INT8!");
        return result;
    }

    if(decision_threshold < 0.0f || decision_threshold > 1.0f){
        Serial.printf(
            "[LỖI] Ngưỡng %.6f nằm ngoài khoảng [0, 1]!\n",
            decision_threshold
        );
        return result;
    }

    // Chép nguyên tensor Python vào input model, không chuẩn hóa hoặc lượng tử lại.
    for(int i = 0; i < required_length; i++){
        input_tensor->data.int8[i] = tensor_int8[i];
    }

    Serial.println("[DIRECT_TENSOR] 10 giá trị INT8 đầu:");
    for(int i = 0; i < 10; i++){
        Serial.printf("%d ", input_tensor->data.int8[i]);
    }
    Serial.println();

    TfLiteStatus invoke_status = interpreter->Invoke();
    if(invoke_status != kTfLiteOk){
        TF_LITE_REPORT_ERROR(
            error_reporter,
            "[LỖI] Chạy Invoke() từ tensor INT8 thất bại"
        );
        return result;
    }

    const int8_t raw = output_tensor->data.int8[0];
    const float output_scale = output_tensor->params.scale;
    const int output_zero_point = output_tensor->params.zero_point;

    float probability =
        (static_cast<int>(raw) - output_zero_point) * output_scale;
    if(probability < 0.0f) probability = 0.0f;
    if(probability > 1.0f) probability = 1.0f;

    result.Output_Raw_Int8 = raw;
    result.Asthma_Prob = (1.0f - probability) * 100.0f;
    result.Non_Asthma_Prob = probability * 100.0f;
    result.Predicted_Class = probability < decision_threshold ? 0 : 1;

    Serial.printf(
        "[DIRECT_TENSOR] raw=%d | p_non=%.9f | threshold=%.9f | class=%d\n",
        static_cast<int>(raw),
        probability,
        decision_threshold,
        result.Predicted_Class
    );

    return result;
}
