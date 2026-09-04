#include "Test_Model_Static_Profiling.h"
#include <TensorFlowLite_ESP32.h>

#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"

#include "Asthma_Model.h"
#include "Sample_Asthma_1.h"
#include "Sample_Non_Asthma_1.h"

// NV2: Thêm lib qly Heap
#include "esp_heap_caps.h"

static const tflite::Model* model = nullptr;
static tflite::MicroInterpreter* interpreter = nullptr;
static tflite::ErrorReporter* error_reporter = nullptr;
static TfLiteTensor* input = nullptr;
static TfLiteTensor* output = nullptr;

// Mục tiêu: Giảm giá trị này đến khi nào tối ưu nhất
/* Từ 300 -> 200: Lỗi : 
- Failed to resize buffer. 
+ Requested: 264192 => Cần thiết: 
+ available 200416 : Dung lượng trống
+ missing: 63776 : Thiếu: 263776 byte

- Thực tế cấp: 200 Kb = 204.800 bytes
=> Lúc cập nhật mạng, chỉ còn available = 200416
=> 1 lượng bytes hụt - 200Kb - 200416 = 4.384

=> Thực sự nên cần = 264192 + 4384 = 268.576 bytes
- 268.576 bytes ~= 262.3 KB
=> Quyết định cấp 270 KB

*/

constexpr int kTensorArenaSize_loss = 200 * 1024; // Sẽ gây thiếu
constexpr int kTensorArenaSize = 270 * 1024;  
static uint8_t* tensor_arena = nullptr; 

static tflite::MicroErrorReporter micro_error_reporter;
static tflite::AllOpsResolver resolver;

bool Setup_TinyML() {
    Serial.println("\n=== BAT DAU HE THONG TINYML ESP32-S3 ===");
    Serial.println("[AI] Dang doc mo hinh tu bo nho...");
    error_reporter = &micro_error_reporter;

    model = tflite::GetModel(model_data);
    if (model->version() != TFLITE_SCHEMA_VERSION) {
        Serial.println("[AI] LOI: Phien ban mo hinh khong khop!");
        return false;
    }

    if (tensor_arena == nullptr) {

        // tensor_arena = (uint8_t*)ps_malloc(kTensorArenaSize);
        // NVU2
        tensor_arena = (uint8_t*)heap_caps_aligned_alloc(
            16, 
            kTensorArenaSize, 
            MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT
        );

        if (tensor_arena == nullptr) {
            Serial.println("[AI] LOI: PSRAM da het hoac chua bat!");
            return false;
        }
        Serial.println("[AI] Xin bo nho PSRAM thanh cong!");
    }

    static tflite::MicroInterpreter static_interpreter(
        model, resolver, tensor_arena, kTensorArenaSize, error_reporter);
    interpreter = &static_interpreter;

    TfLiteStatus allocate_status = interpreter->AllocateTensors();
    if (allocate_status != kTfLiteOk) {
        Serial.println("[AI] LOI: AllocateTensors() that bai! (Arena too small?)");
        return false;
    }

    input = interpreter->input(0);
    output = interpreter->output(0);
    
    Serial.println("[AI] KHOI TAO THANH CONG! (Dang dung AllOps)");
    Serial.printf("[AI] Input Shape: %d x %d x %d\n", 
                  input->dims->data[1], input->dims->data[2], input->dims->data[3]);
    return true;
}

void Predict_Static_Dummy(const signed char* input_data, const char* ten_mau) {
    Serial.printf("\n>>> DANG PHAN TICH: %s <<<\n", ten_mau);

    for (int i = 0; i < input->bytes; i++) {
        input->data.int8[i] = input_data[i]; 
    }

    uint32_t start_time = esp_timer_get_time();
    TfLiteStatus invoke_status = interpreter->Invoke();
    uint32_t end_time = esp_timer_get_time();

    if (invoke_status != kTfLiteOk) {
        Serial.println("[AI] LOI: Ham Invoke() that bai!");
        return;
    }

    int8_t y_pred = output->data.int8[0];
    uint32_t inference_time_ms = (end_time - start_time) / 1000;
    float probability = (y_pred + 128.0) / 255.0;

    Serial.println("====================================");
    Serial.printf("Thoi gian suy luan : %d ms\n", inference_time_ms);
    Serial.printf("Gia tri Int8 goc   : %d\n", y_pred);
    Serial.printf("Xac suat Output    : %.2f %%\n", probability * 100.0);
    Serial.println("------------------------------------");
    
    if (probability < 0.5) {
        float confidence = (1.0 - probability) * 100.0;
        Serial.printf("=> DU DOAN         : HEN SUYEN (Nhan 0)\n");
        Serial.printf("=> DO TU TIN       : %.1f %%\n", confidence);
    } else {
        float confidence = probability * 100.0;
        Serial.printf("=> DU DOAN         : NON-ASTHMA (Nhan 1)\n");
        Serial.printf("=> DO TU TIN       : %.1f %%\n", confidence);
    }
    Serial.println("====================================\n");
}
