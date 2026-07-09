#include "Test_Asthma_1.h"
#include <TensorFlowLite_ESP32.h>

// Bỏ thư viện micro_mutable_op_resolver.h đi, gọi all_ops_resolver.h
#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"

#include "Asthma_Model.h"

#include "Sample_Asthma_1.h"
#include "Sample_Non_Asthma_1.h"

// --- CÁC BIẾN TOÀN CỤC ---
static const tflite::Model* model = nullptr;
static tflite::MicroInterpreter* interpreter = nullptr;
static tflite::ErrorReporter* error_reporter = nullptr;
static TfLiteTensor* input = nullptr;
static TfLiteTensor* output = nullptr;

// Cấp phát 300KB RAM cho AI
constexpr int kTensorArenaSize = 300 * 1024;
// Khai báo con trỏ rỗng thay vì mảng tĩnh
// Để chuyển 300KB RAM này sang 8MB PSRAM ngoài
static uint8_t* tensor_arena = nullptr;

static tflite::MicroErrorReporter micro_error_reporter;

// Nạp toàn bộ phép toán
static tflite::AllOpsResolver resolver;

// --- HÀM KHỞI TẠO AI ---
bool Setup_TinyML() {
    Serial.println("\n[AI] Dang doc mo hinh tu bo nho...");
    error_reporter = &micro_error_reporter;
    
    // Đọc model_data
    model = tflite::GetModel(model_data);
    
    if (model->version() != TFLITE_SCHEMA_VERSION) {
        TF_LITE_REPORT_ERROR(error_reporter,
                             "[AI] Loi phien ban Schema! Model: %d, Ho tro: %d",
                             model->version(), TFLITE_SCHEMA_VERSION);
        return false;
    }

    // --- BẮT ĐẦU ÉP DÙNG PSRAM ---
    if (tensor_arena == nullptr) {
        // Gọi hàm ps_malloc để lấy 300KB trực tiếp từ cục 8MB ngoài
        tensor_arena = (uint8_t*)ps_malloc(kTensorArenaSize);
        if (tensor_arena == nullptr) {
            Serial.println("[AI] LOI: PSRAM da het hoac chua bat, khong the cap phat!");
            return false;
        }
        Serial.println("[AI] Xin bo nho PSRAM thanh cong!");
    }
    // --- KẾT THÚC CẤP PHÁT ---

    static tflite::MicroInterpreter static_interpreter(
        model, resolver, tensor_arena, kTensorArenaSize, error_reporter);
    interpreter = &static_interpreter;

    TfLiteStatus allocate_status = interpreter->AllocateTensors();
    if (allocate_status != kTfLiteOk) {
        TF_LITE_REPORT_ERROR(error_reporter, "[AI] LOI: Khong cap phat duoc Tensor Arena!");
        return false;
    }

    input = interpreter->input(0);
    output = interpreter->output(0);

    Serial.println("[AI] KHOI TAO THANH CONG! (Dang dung AllOps)");
    Serial.printf("[AI] Input Shape: %d x %d x %d\n", input->dims->data[1], input->dims->data[2], input->dims->data[3]);
    return true;
}

// --- HÀM CHẠY SUY LUẬN TEST TĨNH ---
void Predict_Static_Dummy_0() {
    // 1. Nhồi dữ liệu vào Input
    // Kịch bản test 1.a
    // Nhét dữ liệu toàn 0 để tính thời gian phản hồi
    // Đảm bảo khởi tạo thành công
    for (int i = 0; i < input->bytes; i++) {
        input->data.int8[i] = 0; 
    }
    // 2. Bắt đầu bấm giờ
    uint32_t start_time = esp_timer_get_time();
    
    // 3. KÍCH HOẠT SUY LUẬN
    TfLiteStatus invoke_status = interpreter->Invoke();
    
    // 4. Chốt giờ
    uint32_t end_time = esp_timer_get_time();

    if (invoke_status != kTfLiteOk) {
        Serial.println("[AI] LOI: Ham Invoke() that bai!");
        return;
    }

    // 5. Lấy kết quả và in ra
    int8_t y_pred = output->data.int8[0];
    uint32_t inference_time_ms = (end_time - start_time) / 1000;

    float probability = (y_pred + 128.0) / 255.0;

    // 6. In Bảng kết quả chuyên nghiệp
    Serial.println("====================================");
    Serial.printf("Thoi gian suy luan : %d ms\n", inference_time_ms);
    Serial.printf("Gia tri Int8 goc   : %d\n", y_pred);
    Serial.printf("Xac suat Output    : %.2f %%\n", probability * 100.0);
    Serial.println("------------------------------------");
    
    // 7. Phán quyết cuối cùng
    if (probability < 0.5) {
        float confidence = (1.0 - probability) * 100.0;
        Serial.printf("=> DU DOAN         : HEN SUYEN (Nhan 0)\n");
        Serial.printf("=> DO TU TIN       : %.1f %%\n", confidence);
    } else {
        float confidence = probability * 100.0;
        Serial.printf("=> DU DOAN         : BINH THUONG (Nhan 1)\n");
        Serial.printf("=> DO TU TIN       : %.1f %%\n", confidence);
    }
    Serial.println("====================================\n");    
}

void Predict_Static_Dummy(const signed char* input_data, const char* ten_mau) {
    Serial.printf("\n>>> DANG PHAN TICH: %s <<<\n", ten_mau);
    // Kịch bản test 1.b
    // Chắc chắn model đoán đúng hoặc sai
    for (int i = 0; i < input->bytes; i++) {
        input->data.int8[i] = input_data[i]; 
    }

    // 2. Kích hoạt suy luận & Bấm giờ
    uint32_t start_time = esp_timer_get_time();
    TfLiteStatus invoke_status = interpreter->Invoke();
    uint32_t end_time = esp_timer_get_time();

    if (invoke_status != kTfLiteOk) {
        Serial.println("[AI] LOI: Ham Invoke() that bai!");
        return;
    }

    // 3. Lấy kết quả
    int8_t y_pred = output->data.int8[0];
    uint32_t inference_time_ms = (end_time - start_time) / 1000;

    // 4. Dịch Int8 sang Xác suất (0.0 đến 1.0)
    // Mô hình Sigmoid: -128 = 0% | 0 = 50% | 127 = 100%
    float probability = (y_pred + 128.0) / 255.0;

    // 5. In Bảng kết quả chuyên nghiệp
    Serial.println("====================================");
    Serial.printf("Thoi gian suy luan : %d ms\n", inference_time_ms);
    Serial.printf("Gia tri Int8 goc   : %d\n", y_pred);
    Serial.printf("Xac suat Output    : %.2f %%\n", probability * 100.0);
    Serial.println("------------------------------------");
    
    // 6. Phán quyết cuối cùng
    if (probability < 0.5) {
        float confidence = (1.0 - probability) * 100.0;
        Serial.printf("=> DU DOAN         : HEN SUYEN (Nhan 0)\n");
        Serial.printf("=> DO TU TIN       : %.1f %%\n", confidence);
    } else {
        float confidence = probability * 100.0;
        Serial.printf("=> DU DOAN         : BINH THUONG / BENH KHAC (Nhan 1)\n");
        Serial.printf("=> DO TU TIN       : %.1f %%\n", confidence);
    }
    Serial.println("====================================\n");
}