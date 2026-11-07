#include "Model_AI/Inference_Asthma.h"

#include <TensorFlowLite_ESP32.h>
#include <math.h>

#include "esp_heap_caps.h"
#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/system_setup.h"
#include "tensorflow/lite/schema/schema_generated.h"

#include "Model_AI/Asthma_Model.h"

static const unsigned char* const kModelData = model_data;
static const unsigned int kModelDataLength =
    static_cast<unsigned int>(model_data_len);
static const char kModelName[] =
    "combo_pre0_mel40_fft2048__V1__s44 / QAT_INT8";

namespace {

const tflite::Model* model = nullptr;
tflite::MicroInterpreter* interpreter = nullptr;
tflite::ErrorReporter* error_reporter = nullptr;
TfLiteTensor* input_tensor = nullptr;
TfLiteTensor* output_tensor = nullptr;

// Cap rong de do lai model F0. Sau khi chay on dinh, doc arena_used_bytes tren
// Serial Monitor de thu nho co kiem soat.
constexpr size_t kTensorArenaSize = 1024 * 1024;
uint8_t* tensor_arena = nullptr;

tflite::MicroErrorReporter micro_error_reporter;
tflite::AllOpsResolver resolver;

constexpr float kDecisionThreshold = 0.5f;
constexpr float kTrainMin = -80.0f;
constexpr float kTrainMax = 0.0f;

}  // namespace

const char* Get_Asthma_Model_Name(void) {
    return kModelName;
}

bool Asthma_Model_Has_Python_Reference(void) {
    return true;
}

bool Init_Asthma_Model(void) {
    tflite::InitializeTarget();
    error_reporter = &micro_error_reporter;

    Serial.printf("[AI] Model=%s | model_bytes=%u\n", kModelName, kModelDataLength);

    if (tensor_arena == nullptr) {
        tensor_arena = static_cast<uint8_t*>(heap_caps_aligned_alloc(
            16,
            kTensorArenaSize,
            MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT
        ));
        if (tensor_arena == nullptr) {
            TF_LITE_REPORT_ERROR(
                error_reporter,
                "[AI][ERROR] Khong cap phat duoc %u bytes PSRAM cho Tensor Arena",
                static_cast<unsigned int>(kTensorArenaSize)
            );
            return false;
        }
    }

    model = tflite::GetModel(kModelData);
    if (model->version() != TFLITE_SCHEMA_VERSION) {
        TF_LITE_REPORT_ERROR(
            error_reporter,
            "[AI][ERROR] Schema model=%d, TFLM=%d",
            model->version(),
            TFLITE_SCHEMA_VERSION
        );
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
        TF_LITE_REPORT_ERROR(error_reporter, "[AI][ERROR] AllocateTensors that bai");
        return false;
    }

    input_tensor = interpreter->input(0);
    output_tensor = interpreter->output(0);
    if (input_tensor == nullptr || output_tensor == nullptr ||
        input_tensor->type != kTfLiteInt8 || output_tensor->type != kTfLiteInt8) {
        TF_LITE_REPORT_ERROR(error_reporter, "[AI][ERROR] Model phai co input/output INT8");
        return false;
    }

    if (input_tensor->dims->size != 4 ||
        input_tensor->dims->data[0] != 1 ||
        input_tensor->dims->data[1] != N_MELS ||
        input_tensor->dims->data[2] != MAX_FRAMES ||
        input_tensor->dims->data[3] != 1) {
        TF_LITE_REPORT_ERROR(error_reporter, "[AI][ERROR] Input model khong phai [1,40,129,1]");
        return false;
    }

    Serial.printf(
        "[AI] arena_capacity=%u | arena_used=%u bytes\n",
        static_cast<unsigned int>(kTensorArenaSize),
        static_cast<unsigned int>(interpreter->arena_used_bytes())
    );
    Serial.printf(
        "[AI] input(scale=%.9f,zp=%d) | output(scale=%.9f,zp=%d)\n",
        input_tensor->params.scale,
        input_tensor->params.zero_point,
        output_tensor->params.scale,
        output_tensor->params.zero_point
    );
    Serial.println("[AI] Khoi tao model thanh cong.");
    return true;
}

Asthma_Result Run_Asthma_Inference(float input_mel_db[][MAX_FRAMES]) {
    Asthma_Result result = {0.0f, 0.0f, -1, 0};
    if (interpreter == nullptr || input_tensor == nullptr || output_tensor == nullptr) {
        Serial.println("[AI][ERROR] Model chua duoc khoi tao.");
        return result;
    }

    constexpr float kTrainRange = kTrainMax - kTrainMin;
    for (int mel = 0; mel < N_MELS; ++mel) {
        for (int frame = 0; frame < MAX_FRAMES; ++frame) {
            float normalized = (input_mel_db[mel][frame] - kTrainMin) / kTrainRange;
            if (normalized < 0.0f) normalized = 0.0f;
            if (normalized > 1.0f) normalized = 1.0f;

            long quantized = lrintf(
                normalized / input_tensor->params.scale + input_tensor->params.zero_point
            );
            if (quantized > 127) quantized = 127;
            if (quantized < -128) quantized = -128;
            input_tensor->data.int8[mel * MAX_FRAMES + frame] =
                static_cast<int8_t>(quantized);
        }
    }

    if (interpreter->Invoke() != kTfLiteOk) {
        TF_LITE_REPORT_ERROR(error_reporter, "[AI][ERROR] Invoke that bai");
        return result;
    }

    const int8_t raw = output_tensor->data.int8[0];
    float p_non =
        (static_cast<int>(raw) - output_tensor->params.zero_point) *
        output_tensor->params.scale;
    if (p_non < 0.0f) p_non = 0.0f;
    if (p_non > 1.0f) p_non = 1.0f;

    result.Output_Raw_Int8 = raw;
    result.Non_Asthma_Prob = p_non * 100.0f;
    result.Asthma_Prob = (1.0f - p_non) * 100.0f;
    result.Predicted_Class = p_non < kDecisionThreshold ? 0 : 1;

    Serial.printf(
        "[AI] model=%s | raw=%d | p_non=%.9f | class=%d (%s)\n",
        kModelName,
        static_cast<int>(raw),
        p_non,
        result.Predicted_Class,
        result.Predicted_Class == 0 ? "ASTHMA" : "NON-ASTHMA"
    );
    return result;
}
