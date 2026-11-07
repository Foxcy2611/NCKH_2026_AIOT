#include "Test_Model_Static_Profiling.h"

#include <Arduino.h>
#include <TensorFlowLite_ESP32.h>
#include <cmath>
#include <cstring>
#include <limits.h>

#include "esp_heap_caps.h"
#include "esp_timer.h"
#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"

// ============================================================================
// CHỌN MODEL PROFILING
// Chỉ bỏ comment cho ĐÚNG MỘT dòng #define bên dưới.
// Mỗi nhánh include cả Asthma_Model.h và Static_Test_Tensors.h tương ứng;
// không được trộn model của nhánh này với tensor của nhánh khác.
// ============================================================================
#define PROFILE_MODEL_C4_QAT_INT8
// #define PROFILE_MODEL_F0_PTQ_INT8
// #define PROFILE_MODEL_C3_QAT_INT8
// #define PROFILE_MODEL_V3_PTQ_INT8

#if (defined(PROFILE_MODEL_C4_QAT_INT8) + \
     defined(PROFILE_MODEL_F0_PTQ_INT8) + \
     defined(PROFILE_MODEL_C3_QAT_INT8) + \
     defined(PROFILE_MODEL_V3_PTQ_INT8)) != 1
#error "Chi duoc chon dung mot model profiling."
#endif

#if defined(PROFILE_MODEL_C4_QAT_INT8)
#include "combo_pre0_mel40_fft2048__V1__s44/QAT_INT8/Asthma_Model.h"
#include "combo_pre0_mel40_fft2048__V1__s44/QAT_INT8/Static_Test_Tensors.h"
static constexpr const char* model_name =
    "combo_pre0_mel40_fft2048__V1__s44 / QAT_INT8";
static constexpr bool kHasPythonInt8Reference = true;

#elif defined(PROFILE_MODEL_F0_PTQ_INT8)
#include "F0__V1__s43/PTQ_INT8/Asthma_Model.h"
#include "F0__V1__s43/PTQ_INT8/Static_Test_Tensors.h"
static constexpr const char* model_name = "F0__V1__s43 / PTQ_INT8";
static constexpr bool kHasPythonInt8Reference = true;

#elif defined(PROFILE_MODEL_C3_QAT_INT8)
#include "combo_mel40_fft2048__V1__s44/QAT_INT8/Asthma_Model.h"
#include "combo_mel40_fft2048__V1__s44/QAT_INT8/Static_Test_Tensors.h"
static constexpr const char* model_name =
    "combo_mel40_fft2048__V1__s44 / QAT_INT8";
static constexpr bool kHasPythonInt8Reference = true;

#elif defined(PROFILE_MODEL_V3_PTQ_INT8)
#include "V3_HelloEdge/PTQ_INT8/Asthma_Model.h"
#include "V3_HelloEdge/PTQ_INT8/Static_Test_Tensors.h"
static constexpr const char* model_name = "V3_HelloEdge / PTQ_INT8";
static constexpr bool kHasPythonInt8Reference = true;
#endif


namespace {

// Cấp rộng để đo lần đầu cho cả ba model. Dùng "Arena used" trong log để giảm
// dần giá trị này và truy tìm kích thước arena tối thiểu sau đó.
constexpr size_t kTensorArenaCapacity = 1024U * 1024U;
constexpr size_t kArenaSafetyMargin = 16U * 1024U;
constexpr uint8_t kBenchmarkRounds = 3;
constexpr float kDecisionThreshold = 0.5F;

const tflite::Model* g_model = nullptr;
tflite::MicroInterpreter* g_interpreter = nullptr;
TfLiteTensor* g_input = nullptr;
TfLiteTensor* g_output = nullptr;
uint8_t* g_tensor_arena = nullptr;

tflite::MicroErrorReporter g_micro_error_reporter;
tflite::ErrorReporter* g_error_reporter = &g_micro_error_reporter;
tflite::AllOpsResolver g_resolver;

size_t g_internal_free_before_setup = 0;
size_t g_psram_free_before_setup = 0;
size_t g_internal_free_after_setup = 0;
size_t g_psram_free_after_setup = 0;
size_t g_arena_used_bytes = 0;

struct BenchmarkStats {
    uint32_t invoke_ok = 0;
    uint32_t invoke_failed = 0;
    uint32_t correct_first_round = 0;
    uint32_t python_int8_matches = 0;
    uint32_t python_label_matches = 0;
    uint32_t python_int8_absolute_error_sum = 0;
    uint32_t python_int8_absolute_error_max = 0;
    uint32_t latency_min_us = UINT32_MAX;
    uint32_t latency_max_us = 0;
    uint64_t latency_total_us = 0;
    size_t lowest_internal_free = SIZE_MAX;
    size_t lowest_psram_free = SIZE_MAX;
    bool stable = true;
};

size_t FreeInternalRam() {
    return heap_caps_get_free_size(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
}

size_t FreePsram() {
    return heap_caps_get_free_size(MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
}

size_t RoundUpToKiB(size_t bytes) {
    return ((bytes + 1023U) / 1024U) * 1024U;
}

const char* LabelName(uint8_t label) {
    return label == 0 ? "ASTHMA" : "NON-ASTHMA";
}

float DequantizeOutput(int8_t raw_value) {
    float probability =
        (static_cast<int32_t>(raw_value) - g_output->params.zero_point) *
        g_output->params.scale;
    if (probability < 0.0F) probability = 0.0F;
    if (probability > 1.0F) probability = 1.0F;
    return probability;
}

bool QuantizationMatchesStaticTensor() {
    const float input_scale_error = fabsf(g_input->params.scale - kStaticInputScale);
    const float output_scale_error = fabsf(g_output->params.scale - kStaticOutputScale);
    return input_scale_error <= 1.0e-7F &&
           g_input->params.zero_point == kStaticInputZeroPoint &&
           output_scale_error <= 1.0e-7F &&
           g_output->params.zero_point == kStaticOutputZeroPoint;
}

void PrintMemorySnapshot(const char* stage) {
    Serial.printf(
        "[RAM] %-18s | Internal free=%u B, largest=%u B | PSRAM free=%u B, largest=%u B\n",
        stage,
        static_cast<unsigned>(FreeInternalRam()),
        static_cast<unsigned>(heap_caps_get_largest_free_block(
            MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT)),
        static_cast<unsigned>(FreePsram()),
        static_cast<unsigned>(heap_caps_get_largest_free_block(
            MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT)));
}

bool RunOneInference(const StaticTestTensor& sample,
                     size_t sample_index,
                     uint8_t round,
                     int8_t* first_round_outputs,
                     BenchmarkStats& stats,
                     bool print_detail) {
    memcpy(g_input->data.int8, sample.data, kStaticTensorElements);

    const size_t internal_before = FreeInternalRam();
    const size_t psram_before = FreePsram();
    const int64_t start_us = esp_timer_get_time();
    const TfLiteStatus status = g_interpreter->Invoke();
    const int64_t end_us = esp_timer_get_time();
    const size_t internal_after = FreeInternalRam();
    const size_t psram_after = FreePsram();

    stats.lowest_internal_free = min(stats.lowest_internal_free,
                                     min(internal_before, internal_after));
    stats.lowest_psram_free = min(stats.lowest_psram_free,
                                  min(psram_before, psram_after));

    if (status != kTfLiteOk) {
        ++stats.invoke_failed;
        stats.stable = false;
        Serial.printf("[FAIL] Round=%u, sample=%u, Invoke failed: %s\n",
                      round,
                      static_cast<unsigned>(sample_index + 1U),
                      sample.source_name);
        return false;
    }

    const uint32_t latency_us = static_cast<uint32_t>(end_us - start_us);
    const int8_t raw_output = g_output->data.int8[0];
    const float probability_non_asthma = DequantizeOutput(raw_output);
    const uint8_t predicted_label =
        probability_non_asthma < kDecisionThreshold ? 0U : 1U;

    ++stats.invoke_ok;
    stats.latency_total_us += latency_us;
    stats.latency_min_us = min(stats.latency_min_us, latency_us);
    stats.latency_max_us = max(stats.latency_max_us, latency_us);

    if (round == 1U) {
        first_round_outputs[sample_index] = raw_output;
        if (predicted_label == sample.expected_label) {
            ++stats.correct_first_round;
        }
        if (kHasPythonInt8Reference) {
            // So sanh ca raw INT8 va nhan Python. Raw lech 1 LSB van co the
            // cho cung mot nhan; hai phep do khong duoc gop lam mot.
            const int int8_delta = static_cast<int>(raw_output) -
                                   static_cast<int>(sample.expected_output_int8);
            const uint32_t absolute_error = static_cast<uint32_t>(
                int8_delta < 0 ? -int8_delta : int8_delta);
            stats.python_int8_absolute_error_sum += absolute_error;
            stats.python_int8_absolute_error_max = max(
                stats.python_int8_absolute_error_max, absolute_error);
            if (int8_delta == 0) ++stats.python_int8_matches;
            const uint8_t python_label =
                DequantizeOutput(sample.expected_output_int8) <
                        kDecisionThreshold ? 0U : 1U;
            if (python_label == predicted_label) ++stats.python_label_matches;
        }
    } else if (raw_output != first_round_outputs[sample_index]) {
        stats.stable = false;
        Serial.printf("[WARN] Output changed sample %u: round1=%d, round%u=%d\n",
                      static_cast<unsigned>(sample_index + 1U),
                      first_round_outputs[sample_index],
                      round,
                      raw_output);
    }

    if (print_detail) {
        const bool correct = predicted_label == sample.expected_label;
        Serial.printf(
            "[%02u] %-42s | true=%-10s pred=%-10s | raw=%4d | P(non)=%.6f | %8u us | %s\n",
            static_cast<unsigned>(sample_index + 1U),
            sample.source_name,
            LabelName(sample.expected_label),
            LabelName(predicted_label),
            raw_output,
            probability_non_asthma,
            latency_us,
            correct ? "OK" : "WRONG");
        if (kHasPythonInt8Reference) {
            const int int8_delta = static_cast<int>(raw_output) -
                                   static_cast<int>(sample.expected_output_int8);
            const uint8_t python_label =
                DequantizeOutput(sample.expected_output_int8) <
                        kDecisionThreshold ? 0U : 1U;
            Serial.printf(
                "     [PARITY] py_raw=%d esp_raw=%d delta=%+d LSB "
                "| py_label=%s esp_label=%s | label_match=%s\n",
                static_cast<int>(sample.expected_output_int8),
                static_cast<int>(raw_output),
                int8_delta,
                LabelName(python_label),
                LabelName(predicted_label),
                python_label == predicted_label ? "YES" : "NO");
        }
    }

    return true;
}

}  // namespace

bool Setup_TinyML() {
    Serial.println("\n========== MODEL SETUP ==========");
    Serial.printf("[MODEL] Active model       : %s\n", model_name);
    Serial.printf("[MODEL] Flash model size   : %u B\n",
                  static_cast<unsigned>(model_data_len));
    Serial.println("[MODEL] Resolver           : AllOpsResolver");
    Serial.printf("[MODEL] Arena capacity     : %u B (%.1f KiB, PSRAM)\n",
                  static_cast<unsigned>(kTensorArenaCapacity),
                  kTensorArenaCapacity / 1024.0F);

    g_internal_free_before_setup = FreeInternalRam();
    g_psram_free_before_setup = FreePsram();
    PrintMemorySnapshot("before setup");

    if (!psramFound()) {
        Serial.println("[AI] ERROR: PSRAM not found.");
        return false;
    }

    g_model = tflite::GetModel(model_data);
    if (g_model == nullptr || g_model->version() != TFLITE_SCHEMA_VERSION) {
        Serial.printf("[AI] ERROR: schema model=%d, runtime=%d.\n",
                      g_model == nullptr ? -1 : g_model->version(),
                      TFLITE_SCHEMA_VERSION);
        return false;
    }

    g_tensor_arena = static_cast<uint8_t*>(heap_caps_aligned_alloc(
        16, kTensorArenaCapacity, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
    if (g_tensor_arena == nullptr) {
        Serial.println("[AI] ERROR: cannot allocate tensor arena in PSRAM.");
        return false;
    }

    static tflite::MicroInterpreter static_interpreter(
        g_model,
        g_resolver,
        g_tensor_arena,
        kTensorArenaCapacity,
        g_error_reporter);
    g_interpreter = &static_interpreter;

    if (g_interpreter->AllocateTensors() != kTfLiteOk) {
        Serial.println("[AI] ERROR: AllocateTensors failed. Check operators/arena.");
        return false;
    }

    g_input = g_interpreter->input(0);
    g_output = g_interpreter->output(0);
    if (g_input == nullptr || g_output == nullptr) {
        Serial.println("[AI] ERROR: model input/output tensor is null.");
        return false;
    }
    if (g_input->type != kTfLiteInt8 || g_output->type != kTfLiteInt8) {
        Serial.printf("[AI] ERROR: expected INT8, got input=%d output=%d.\n",
                      g_input->type,
                      g_output->type);
        return false;
    }
    if (g_input->bytes != kStaticTensorElements || g_output->bytes < 1U) {
        Serial.printf("[AI] ERROR: size mismatch, input=%u expected=%u output=%u.\n",
                      static_cast<unsigned>(g_input->bytes),
                      static_cast<unsigned>(kStaticTensorElements),
                      static_cast<unsigned>(g_output->bytes));
        return false;
    }
    if (!QuantizationMatchesStaticTensor()) {
        Serial.printf(
            "[AI] ERROR: quantization mismatch. Header=(%.10f,%d), model=(%.10f,%d).\n",
            kStaticInputScale,
            kStaticInputZeroPoint,
            g_input->params.scale,
            g_input->params.zero_point);
        Serial.printf(
            "[AI] Output: Header=(%.10f,%d), model=(%.10f,%d).\n",
            kStaticOutputScale,
            kStaticOutputZeroPoint,
            g_output->params.scale,
            g_output->params.zero_point);
        Serial.println("[AI] Regenerate Static_Test_Tensors.h for selected model.");
        return false;
    }

    g_arena_used_bytes = g_interpreter->arena_used_bytes();
    g_internal_free_after_setup = FreeInternalRam();
    g_psram_free_after_setup = FreePsram();

    Serial.printf("[AI] Input bytes         : %u\n",
                  static_cast<unsigned>(g_input->bytes));
    Serial.printf("[AI] Input quantization  : scale=%.10f, zero_point=%d\n",
                  g_input->params.scale,
                  g_input->params.zero_point);
    Serial.printf("[AI] Output quantization : scale=%.10f, zero_point=%d\n",
                  g_output->params.scale,
                  g_output->params.zero_point);
    Serial.printf("[AI] Arena used          : %u B (%.1f KiB)\n",
                  static_cast<unsigned>(g_arena_used_bytes),
                  g_arena_used_bytes / 1024.0F);
    Serial.printf("[AI] Suggested next test : %u B (used + 16 KiB, rounded)\n",
                  static_cast<unsigned>(
                      RoundUpToKiB(g_arena_used_bytes + kArenaSafetyMargin)));
    PrintMemorySnapshot("after setup");
    Serial.println("[AI] AllocateTensors OK -> operator compatibility: INITIAL PASS");
    return true;
}

void Run_Static_Benchmark() {
    if (g_interpreter == nullptr || g_input == nullptr || g_output == nullptr) {
        Serial.println("[BENCH] ERROR: Setup_TinyML has not succeeded.");
        return;
    }

    Serial.println("\n========== WARM-UP (NOT COUNTED) ==========");
    memcpy(g_input->data.int8, kStaticTestTensors[0].data, kStaticTensorElements);
    if (g_interpreter->Invoke() != kTfLiteOk) {
        Serial.println("[BENCH] ERROR: warm-up Invoke failed.");
        return;
    }
    Serial.println("[BENCH] Warm-up OK.");

    BenchmarkStats stats;
    int8_t first_round_outputs[kStaticTestTensorCount] = {};
    stats.lowest_internal_free = FreeInternalRam();
    stats.lowest_psram_free = FreePsram();

    Serial.println("\n========== ROUND 1: DETAILED RESULTS ==========");
    for (uint8_t round = 1; round <= kBenchmarkRounds; ++round) {
        if (round > 1U) {
            Serial.printf("[BENCH] Stability round %u/%u...\n", round, kBenchmarkRounds);
        }
        for (size_t i = 0; i < kStaticTestTensorCount; ++i) {
            RunOneInference(kStaticTestTensors[i],
                            i,
                            round,
                            first_round_outputs,
                            stats,
                            round == 1U);
        }
    }

    const float average_latency_us =
        stats.invoke_ok == 0U
            ? 0.0F
            : static_cast<float>(stats.latency_total_us) / stats.invoke_ok;
    const float static_accuracy =
        100.0F * stats.correct_first_round / kStaticTestTensorCount;
    const size_t min_internal_since_boot = heap_caps_get_minimum_free_size(
        MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    const size_t min_psram_since_boot = heap_caps_get_minimum_free_size(
        MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    const size_t internal_setup_delta =
        g_internal_free_before_setup > g_internal_free_after_setup
            ? g_internal_free_before_setup - g_internal_free_after_setup
            : 0U;
    const size_t psram_reserved_delta =
        g_psram_free_before_setup > g_psram_free_after_setup
            ? g_psram_free_before_setup - g_psram_free_after_setup
            : 0U;
    // Dung muc thap nhat quan sat trong chinh benchmark, khong lay low-water
    // mark tu giai doan boot de tranh phong dai Peak RAM cua model.
    const size_t lowest_internal_benchmark =
        min(g_internal_free_after_setup, stats.lowest_internal_free);
    const size_t peak_internal_delta =
        g_internal_free_before_setup > lowest_internal_benchmark
            ? g_internal_free_before_setup - lowest_internal_benchmark
            : 0U;
    const size_t estimated_active_model_ram = g_arena_used_bytes + peak_internal_delta;
    const bool operator_compatible = stats.invoke_failed == 0U;
    const bool stable = stats.stable && stats.invoke_failed == 0U;

    Serial.println("\n============================================================");
    Serial.println(" TARGET BENCHMARK SUMMARY - REPORT SECTION 10.2");
    Serial.println("============================================================");
    Serial.printf("Model                    : %s\n", model_name);
    Serial.printf("Model Flash size         : %u B\n",
                  static_cast<unsigned>(model_data_len));
    Serial.printf("Tensor Arena capacity    : %u B\n",
                  static_cast<unsigned>(kTensorArenaCapacity));
    Serial.printf("Tensor Arena used        : %u B\n",
                  static_cast<unsigned>(g_arena_used_bytes));
    Serial.printf("Arena next test (+16KiB) : %u B\n",
                  static_cast<unsigned>(
                      RoundUpToKiB(g_arena_used_bytes + kArenaSafetyMargin)));
    Serial.printf("Internal setup delta     : %u B\n",
                  static_cast<unsigned>(internal_setup_delta));
    Serial.printf("PSRAM reserved delta     : %u B\n",
                  static_cast<unsigned>(psram_reserved_delta));
    Serial.printf("Min internal since boot  : %u B\n",
                  static_cast<unsigned>(min_internal_since_boot));
    Serial.printf("Min PSRAM since boot     : %u B\n",
                  static_cast<unsigned>(min_psram_since_boot));
    Serial.printf("Peak RAM estimate        : %u B (arena used + peak internal delta)\n",
                  static_cast<unsigned>(estimated_active_model_ram));
    Serial.printf("Lowest internal observed : %u B\n",
                  static_cast<unsigned>(stats.lowest_internal_free));
    Serial.printf("Lowest PSRAM observed    : %u B\n",
                  static_cast<unsigned>(stats.lowest_psram_free));
    Serial.printf("Inference count          : %u OK / %u failed\n",
                  stats.invoke_ok,
                  stats.invoke_failed);
    const uint32_t latency_min =
        stats.latency_min_us == UINT32_MAX ? 0U : stats.latency_min_us;
    Serial.printf("Inference latency min    : %u us (%.3f ms)\n",
                  latency_min,
                  latency_min / 1000.0F);
    Serial.printf("Inference latency avg    : %.1f us (%.3f ms)\n",
                  average_latency_us,
                  average_latency_us / 1000.0F);
    Serial.printf("Inference latency max    : %u us (%.3f ms)\n",
                  stats.latency_max_us,
                  stats.latency_max_us / 1000.0F);
    Serial.printf("Static sample accuracy   : %u/%u (%.2f%%)\n",
                  stats.correct_first_round,
                  static_cast<unsigned>(kStaticTestTensorCount),
                  static_accuracy);
    if (kHasPythonInt8Reference) {
        Serial.printf("Python/ESP32 INT8 exact  : %u/%u\n",
                      stats.python_int8_matches,
                      static_cast<unsigned>(kStaticTestTensorCount));
        Serial.printf("Python/ESP32 label match : %u/%u\n",
                      stats.python_label_matches,
                      static_cast<unsigned>(kStaticTestTensorCount));
        Serial.printf("Python/ESP32 INT8 MAE    : %.3f LSB\n",
                      static_cast<float>(stats.python_int8_absolute_error_sum) /
                          static_cast<float>(kStaticTestTensorCount));
        Serial.printf("Python/ESP32 INT8 maxerr : %u LSB\n",
                      static_cast<unsigned>(stats.python_int8_absolute_error_max));
    } else {
        Serial.println("Python/ESP32 INT8 parity : N/A (chua co moc Python)");
    }
    Serial.printf("Operator compatibility   : %s (AllOpsResolver)\n",
                  operator_compatible ? "PASS" : "FAIL");
    Serial.printf("Stability (%u rounds)     : %s\n",
                  kBenchmarkRounds,
                  stable ? "PASS" : "FAIL");
    Serial.println("============================================================");
    Serial.println("[BENCH] Hoan tat. Reset board de chay lai benchmark.");
}
