#include "Model_AI/Interface_Asthma.h"

#include <TensorFlowLite_ESP32.h>
#include <esp_heap_caps.h>
#include <math.h>

#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/system_setup.h"
#include "tensorflow/lite/schema/schema_generated.h"

#include "Model_AI/Asthma_Model.h"

namespace {
constexpr size_t kTensorArenaSize = 270 * 1024;
constexpr float kTrainMinValue = -80.0f;
constexpr float kTrainRange = 80.0f;
constexpr float kDecisionThreshold = 0.5f;

const tflite::Model* model = nullptr;
tflite::MicroInterpreter* interpreter = nullptr;
tflite::ErrorReporter* error_reporter = nullptr;
TfLiteTensor* input_tensor = nullptr;
TfLiteTensor* output_tensor = nullptr;
uint8_t* tensor_arena = nullptr;

tflite::MicroErrorReporter micro_error_reporter;
tflite::AllOpsResolver resolver;
}

bool Init_Asthma_Model(void) {
    tflite::InitializeTarget();
    error_reporter = &micro_error_reporter;

    tensor_arena = static_cast<uint8_t*>(heap_caps_aligned_alloc(
        16,
        kTensorArenaSize,
        MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT
    ));
    if (tensor_arena == nullptr) {
        TF_LITE_REPORT_ERROR(error_reporter, "Khong du PSRAM cho Tensor Arena.");
        return false;
    }

    model = tflite::GetModel(model_data);
    if (model->version() != TFLITE_SCHEMA_VERSION) {
        TF_LITE_REPORT_ERROR(error_reporter, "Sai phien ban TFLite schema.");
        return false;
    }

    static tflite::MicroInterpreter static_interpreter(
        model,
        resolver,
        tensor_arena,
        kTensorArenaSize,
        error_reporter
    );
    interpreter = &static_interpreter;

    if (interpreter->AllocateTensors() != kTfLiteOk) {
        TF_LITE_REPORT_ERROR(error_reporter, "Cap phat tensor that bai.");
        return false;
    }

    input_tensor = interpreter->input(0);
    output_tensor = interpreter->output(0);

    if (input_tensor->type != kTfLiteInt8 || output_tensor->type != kTfLiteInt8) {
        TF_LITE_REPORT_ERROR(error_reporter, "Model phai co input/output INT8.");
        return false;
    }

    if (input_tensor->dims->size != 4
        || input_tensor->dims->data[0] != 1
        || input_tensor->dims->data[1] != N_MELS
        || input_tensor->dims->data[2] != MAX_FRAMES
        || input_tensor->dims->data[3] != 1) {
        TF_LITE_REPORT_ERROR(error_reporter, "Input model khong phai [1,64,129,1].");
        return false;
    }

    Serial.printf("[AI] Model INT8: %u byte, Tensor Arena: %u byte.\n",
        static_cast<unsigned int>(model_data_len),
        static_cast<unsigned int>(kTensorArenaSize));
    return true;
}

Asthma_Result Run_Asthma_Interface(float input_mel_db[][MAX_FRAMES]) {
    Asthma_Result result = {0.0f, 0.0f, -1, 0};

    for (int mel_idx = 0; mel_idx < N_MELS; mel_idx++) {
        for (int frame_idx = 0; frame_idx < MAX_FRAMES; frame_idx++) {
            float normalized =
                (input_mel_db[mel_idx][frame_idx] - kTrainMinValue) / kTrainRange;
            if (normalized < 0.0f) normalized = 0.0f;
            if (normalized > 1.0f) normalized = 1.0f;

            long quantized = lrintf(
                normalized / input_tensor->params.scale
                + input_tensor->params.zero_point
            );
            if (quantized > 127) quantized = 127;
            if (quantized < -128) quantized = -128;

            const int index = mel_idx * MAX_FRAMES + frame_idx;
            input_tensor->data.int8[index] = static_cast<int8_t>(quantized);
        }
    }

    if (interpreter->Invoke() != kTfLiteOk) {
        TF_LITE_REPORT_ERROR(error_reporter, "Invoke that bai.");
        return result;
    }

    const int8_t raw = output_tensor->data.int8[0];
    float probability =
        (static_cast<int>(raw) - output_tensor->params.zero_point)
        * output_tensor->params.scale;
    if (probability < 0.0f) probability = 0.0f;
    if (probability > 1.0f) probability = 1.0f;

    result.Output_Raw_Int8 = raw;
    result.Asthma_Prob = (1.0f - probability) * 100.0f;
    result.Non_Asthma_Prob = probability * 100.0f;
    result.Predicted_Class = probability < kDecisionThreshold ? 0 : 1;

    Serial.printf(
        "[AI] Asthma=%.2f%% | Non-Asthma=%.2f%% | Lop=%d\n",
        result.Asthma_Prob,
        result.Non_Asthma_Prob,
        result.Predicted_Class
    );
    return result;
}
