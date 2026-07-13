#include "Interface_Asthma.h"
#include <TensorFlowLite_ESP32.h>

#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/system_setup.h"
#include "tensorflow/lite/schema/schema_generated.h"

#include "Asthma_Model.h"

// ==== BIẾN TOÀN CỤC ====
const tflite::Model* model = nullptr;
tflite::MicroInterpreter* interpreter = nullptr;
tflite::ErrorReporter* error_reporter = nullptr;
TfLiteTensor* input_tensor = nullptr;
TfLiteTensor* output_tensor = nullptr;

const int kTensorArenaSize = 270 * 1024;
static uint8_t* tensor_arena = nullptr;

static tflite::MicroErrorReporter micro_error_reporter;
static tflite::AllOpsResolver resolver;


bool Init_Asthma_Model(void){
    tflite::InitializeTarget();
    error_reporter = &micro_error_reporter;

    if(tensor_arena == nullptr){
        tensor_arena = (uint8_t*)heap_caps_aligned_alloc(
            16, kTensorArenaSize,
            MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT
        );

        if(tensor_arena == nullptr){
            TF_LITE_REPORT_ERROR(error_reporter, 
                "[LOI] Khong the cap phat %d bytes PSRAM cho Tensor Arena!", kTensorArenaSize
            );
            return false;
        }
        
        Serial.println("[AI] Da cap phat thanh cong tren PSRAM !");
    }

    model = tflite::GetModel(model_data);
    if(model->version() != TFLITE_SCHEMA_VERSION){
        TF_LITE_REPORT_ERROR(error_reporter,
        "[LOI] Phien ban schema mo hinh (%d) khong khop voi TFLITE (%d)!",
        model->version(), TFLITE_SCHEMA_VERSION
        );

        return false;
    }

    static tflite::MicroInterpreter static_interpreter(
        model, resolver, tensor_arena,
        kTensorArenaSize, error_reporter
    );
    interpreter = &static_interpreter;

    TfLiteStatus allocate_status = interpreter->AllocateTensors();
    if (allocate_status != kTfLiteOk) {
        TF_LITE_REPORT_ERROR(error_reporter, "[LỖI] Cap phat Tensor Arena that bai. Hay kiem tra lai PSRAM!");
        return false;
    }

    input_tensor = interpreter->input(0);
    output_tensor = interpreter->output(0);

    Serial.println("[AI] Khoi tao mo hinh Asthma TFLite THANH CONG!");
    Serial.printf("[AI] Input shape: [%d, %d, %d, %d]\n", 
        input_tensor->dims->data[0], input_tensor->dims->data[1], 
        input_tensor->dims->data[2], input_tensor->dims->data[3]);

    return true;
}

Asthma_Result Run_Asthma_Interface(float input_mel_db[][N_MELS]){
    Asthma_Result result = {0.0f, 0.0f, -1};

    float* input_data_ptr = input_tensor->data.f;
    int idx = 0;
    
    for (int f = 0; f < MAX_FRAMES; f++) {       
        for (int m = 0; m < N_MELS; m++) {       
            input_data_ptr[idx] = input_mel_db[f][m];
            idx++;
        }
    }

    TfLiteStatus invoke_status = interpreter->Invoke();
    if (invoke_status != kTfLiteOk) {
        TF_LITE_REPORT_ERROR(error_reporter, "[LỖI] Chay Invoke() that bai!");
        return result;
    }

    // 3. INDEX: 0 = Asthma, 1 = Normal
    result.Asthma_Prob = output_tensor->data.f[0] * 100.0f;
    result.Normal_Prob = output_tensor->data.f[1] * 100.0f;

    // 4. KẾT LUẬN THEO NHÃN MỚI
    if (result.Asthma_Prob > result.Normal_Prob) {
        result.Predicted_Class = 0; // Asthma = 0
        Serial.printf(">> CANH BAO: Phat hien tieng rit Hen Suyen! (%.2f%%)\n", result.Asthma_Prob);
    } else {
        result.Predicted_Class = 1; // Normal = 1
        Serial.printf(">> Binh thuong. (%.2f%%)\n", result.Normal_Prob);
    }

    return result;
}
