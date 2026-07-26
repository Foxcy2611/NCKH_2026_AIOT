#include "Model_AI/Interface_Asthma.h"
#include <TensorFlowLite_ESP32.h>

#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/system_setup.h"
#include "tensorflow/lite/schema/schema_generated.h"

// #include "Model_AI/Asthma_Model.h"
// Đã chuyển đổi sang model mới nhất
#include "Model_AI/Asthma_Model_2.h"

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

// ==== Ngưỡng quyết định ==== //
const float LOW_THRESHOLD = 0.35f;   // dưới ngưỡng này -> chắc chắn Asthma
const float HIGH_THRESHOLD = 0.65f;  // trên ngưỡng này -> chắc chắn Normal

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

    // 7. Debug thông tin input
    // scale: Hệ số chuyển đổi giá trị int8 sang float
    // zero_point: Offset để quy đổi dữ liệu
    Serial.printf("[DEBUG] Input scale=%.6f, zero_point=%d\n", 
    input_tensor->params.scale, input_tensor->params.zero_point);

    Serial.println("[AI] Khởi tạo mô hình Asthma TFLite THÀNH CÔNG!");
    Serial.printf("[AI] Input shape: [%d, %d, %d, %d]\n",  // Phải là [1, 64, 129, 1]
        input_tensor->dims->data[0], input_tensor->dims->data[1], 
        input_tensor->dims->data[2], input_tensor->dims->data[3]);

    return true;
}

Asthma_Result Run_Asthma_Interface(float input_mel_db[][MAX_FRAMES]){
    Asthma_Result result = {0.0f, 0.0f, -1};

    // Kiểm tra mô hình thuộc loại INT8 ?
    bool is_quan = (input_tensor->type == kTfLiteInt8);

    // ==== HẰNG SỐ CỐ ĐỊNH từ lúc train (6_Train_Model.py) ====
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

            if(is_quan){
                // Chuẩn hóa về 0 1
                float normalized = (val - TRAIN_MIN_VAL) / TRAIN_RANGE;  // dùng hằng số cố định

                // scale và zero_point do model quyết định
                float quantized = normalized / input_tensor->params.scale 
                                + input_tensor->params.zero_point;

                // Chốt chặn
                if (quantized > 127.0f) quantized = 127.0f;
                if (quantized < -128.0f) quantized = -128.0f;
                
                // Nạp
                input_tensor->data.int8[idx] = (int8_t)quantized;
            } else {
                input_tensor->data.f[idx] = val;
            }
        }
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
    float probability;
    if (is_quan) {
        float scale = output_tensor->params.scale;
        int zero_point = output_tensor->params.zero_point;
        int8_t raw = output_tensor->data.int8[0];

        // Giải lượng tử về khoảng [0,1] (sigmoid output)
        // Ngược vs dòng 127
        probability = (raw - zero_point) * scale;   
    } else {
        probability = output_tensor->data.f[0];
    }

    // 4. KẾT LUẬN — probability gần 0 = Asthma (nhãn 0), gần 1 = Normal (nhãn 1)
    result.Asthma_Prob = (1.0f - probability) * 100.0f;
    result.Normal_Prob = probability * 100.0f;

    // Trong phần đọc output, thêm ngay trước khi tính probability
    Serial.printf("[DEBUG] Output raw int8: %d, scale=%.6f, zero_point=%d\n",
    output_tensor->data.int8[0], output_tensor->params.scale, output_tensor->params.zero_point);

    // ======================= //
    // Thêm ngưỡng quyết định Phase 4 từ chỉ có phân biệt có và không
    // Thành: Có + Chưa chắc + Không
    // Dựa theo tỉ lệ đoán

    if (probability < LOW_THRESHOLD) {
        result.Predicted_Class = 0;
        Serial.printf(">> CẢNH BÁO: Phát hiện tiếng rít Hen Suyễn - ASTHMA! (%.2f%%)\n", result.Asthma_Prob);
    } else if (probability > HIGH_THRESHOLD) {
        result.Predicted_Class = 1;
        Serial.printf(">> Bình thường. (%.2f%%)\n", result.Normal_Prob);
    } else {
        result.Predicted_Class = -1;   // -1 = không chắc chắn
        Serial.printf(">> KHÔNG CHẮC CHẮN - Cần đo lại (Asthma: %.2f%% / Normal: %.2f%%)\n", 
            result.Asthma_Prob, result.Normal_Prob);
    }

    return result;
    /*
    if (probability < 0.5f) {
        result.Predicted_Class = 0;
        Serial.printf(">> CẢNH BÁO: Phát hiện tiếng rít Hen Suyễn - ASTHMA! (%.2f%%)\n", result.Asthma_Prob);
    } else {
        result.Predicted_Class = 1;
        Serial.printf(">> Bình thường. (%.2f%%)\n", result.Normal_Prob);
    }
    return result;
    */
}
