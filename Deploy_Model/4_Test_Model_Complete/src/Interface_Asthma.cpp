#include "Model_AI/Interface_Asthma.h"
#include <TensorFlowLite_ESP32.h>

#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/system_setup.h"
#include "tensorflow/lite/schema/schema_generated.h"

#include "Model_AI/Asthma_Model.h"

const tflite::Model* model = nullptr;
tflite::MicroInterpreter* interpreter = nullptr;
tflite::ErrorReporter* error_reporter = nullptr;
TfLiteTensor* input_tensor = nullptr;
TfLiteTensor* output_tensor = nullptr;

const int kTensorArenaSize = 270 * 1024;
static uint8_t* tensor_arena = nullptr;

static tflite::MicroErrorReporter micro_error_reporter;
static tflite::AllOpsResolver resolver;

const float LOW_THRESHOLD = 0.35f;    
const float HIGH_THRESHOLD = 0.65f;  

const float TRAIN_MIN_VAL = -80.0f;
const float TRAIN_MAX_VAL = 0.0f;
const float TRAIN_RANGE = TRAIN_MAX_VAL - TRAIN_MIN_VAL;

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
                "[LỖI] Không thể cấp phát %d bytes PSRAM cho Tensor Arena!", kTensorArenaSize 
            );
            return false;
        }
    }

    model = tflite::GetModel(model_data);
    if(model->version() != TFLITE_SCHEMA_VERSION){
        TF_LITE_REPORT_ERROR(error_reporter,
            "[LỖI] Phiên bản schema mô hình (%d) không khớp với TFLITE (%d)!",
            model->version(), TFLITE_SCHEMA_VERSION
        );

        return false;
    }

    static tflite::MicroInterpreter static_interpreter(
        model, resolver, tensor_arena, 
        kTensorArenaSize, error_reporter
    );
    interpreter = &static_interpreter;

    if (interpreter->AllocateTensors() != kTfLiteOk) {
        TF_LITE_REPORT_ERROR(
            error_reporter, 
            "[LỖI] Cấp phát Tensor Arena thất bại. Hãy kiểm tra lại PSRAM!"
        );

        return false;
    }

    input_tensor = interpreter->input(0);
    output_tensor = interpreter->output(0);

    Serial.println("[AI] Khởi tạo mô hình Asthma TFLite THÀNH CÔNG!");
    Serial.printf("[AI] Input shape: [%d, %d, %d, %d]\n",
        input_tensor->dims->data[0], input_tensor->dims->data[1],
        input_tensor->dims->data[2], input_tensor->dims->data[3]);

    return true;
}

Asthma_Result Run_Asthma_Interface(float input_mel_db[][MAX_FRAMES]){
    Asthma_Result result = {0.0f, 0.0f, -1};

    bool is_quan = (input_tensor->type == kTfLiteInt8);

    for(int mel_idx = 0 ; mel_idx < N_MELS ; mel_idx++){
        for(int frame_idx = 0 ; frame_idx < MAX_FRAMES ; frame_idx++){
            float val = input_mel_db[mel_idx][frame_idx]; 
            int idx = mel_idx * MAX_FRAMES + frame_idx; 

            if(is_quan){
                float normalized = (val - TRAIN_MIN_VAL) / TRAIN_RANGE; 

                float quantized = normalized / input_tensor->params.scale 
                                + input_tensor->params.zero_point;

                if (quantized > 127.0f) quantized = 127.0f;
                if (quantized < -128.0f) quantized = -128.0f;
                
                input_tensor->data.int8[idx] = (int8_t)quantized;
            } else {
                input_tensor->data.f[idx] = val;
            }
        }
    }

    if(interpreter->Invoke() != kTfLiteOk){
        TF_LITE_REPORT_ERROR(
            error_reporter,
            "[LỖI] Chạy Invoke() thất bại"
        );

        return result;
    }

    float probability;
    if (is_quan) {
        float scale = output_tensor->params.scale;
        int zero_point = output_tensor->params.zero_point;

        int8_t raw = output_tensor->data.int8[0];
        probability = (raw - zero_point) * scale;

    } else {
        probability = output_tensor->data.f[0];

    }

    result.Asthma_Prob = (1.0f - probability) * 100.0f;
    result.Normal_Prob = probability * 100.0f;

    if (probability < LOW_THRESHOLD) {
        result.Predicted_Class = 0;
        Serial.printf(">> CẢNH BÁO: Phát hiện tiếng rít Hen Suyễn - ASTHMA! (%.2f%%)\n", result.Asthma_Prob);
    } else if (probability > HIGH_THRESHOLD) {
        result.Predicted_Class = 1;
        Serial.printf(">> Bình thường. (%.2f%%)\n", result.Normal_Prob);
    } else {
        result.Predicted_Class = -1;
        Serial.printf(">> KHÔNG CHẮC CHẮN - Cần đo lại (Asthma: %.2f%% / Normal: %.2f%%)\n", 
            result.Asthma_Prob, result.Normal_Prob);
    }

    return result;
}