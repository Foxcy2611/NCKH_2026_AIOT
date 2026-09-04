#include <Arduino.h>
#include "Audio_IO/I2S_Mic.h"
#include "DSP_Preprocessing/Mel_Scale.h"
#include "Model_AI/Interface_Asthma.h"

/**/ // THAY ĐỔI P4: Header chỉ chứa 108 tensor INT8 validation, không có audio raw.
#if RUN_VALIDATION_108_TEST
#include "Tensor_Include_Validation108/Validation_Tensors_108.h"
void Run_Validation_108_Test(void);
#endif

/**/ // THAY ĐỔI P4: Header test 113 dùng ngưỡng 0.5 đã khóa từ validation.
#if RUN_TEST_113_TEST
#include "Tensor_Include_Test113/Test_Tensors_113.h"
void Run_Test_113_Test(void);
#endif

void setup() {
    Serial.begin(115200);
    delay(3000); // Chờ USB CDC ổn định

    Serial.println("\n========================================");
    Serial.println("   HỆ THỐNG AI CHẨN ĐOÁN HEN SUYỄN");
    Serial.println("========================================\n");

/**/ // THAY ĐỔI P5: Chế độ đo VAD không cần Mel Filterbank.
#if !RUN_DIRECT_TENSOR_TEST && !RUN_VAD_CALIBRATION_TEST
    // 1. Khởi tạo Mel filterbank (chỉ cần tính 1 lần duy nhất)
    Serial.println("[CÀI ĐẶT] Đang khởi tạo Mel Filterbank...");
    if(!Init_Mel_Filterbank()){
        Serial.println("[CÀI ĐẶT] LỖI: Khởi tạo Mel Filterbank thất bại! Treo máy.");
        while(1){ delay(100); }
    }
    Serial.println("[CÀI ĐẶT] Mel Filterbank sẵn sàng.");
#elif RUN_DIRECT_TENSOR_TEST
    Serial.println("[DIRECT_TENSOR] Bỏ qua Mel Filterbank và preprocess C++.");
/**/ // THAY ĐỔI P5: Chỉ đo raw từ INMP441, bỏ toàn bộ tiền xử lý.
#else
    Serial.println("[VAD_CAL] Bỏ qua Mel Filterbank và preprocess C++.");
#endif

/**/ // THAY ĐỔI P5: Chế độ đo VAD không cần cấp phát hoặc invoke mô hình.
#if !RUN_VAD_CALIBRATION_TEST
    // 2. Khởi tạo model TFLite (cấp phát tensor_arena, load model)
    Serial.println("[CÀI ĐẶT] Đang khởi tạo mô hình TFLite...");
    if (!Init_Asthma_Model()) {
        Serial.println("[CÀI ĐẶT] LỖI: Khởi tạo mô hình thất bại! Treo máy.");
        while (1) { delay(100); }
    }
#else
    Serial.println("[VAD_CAL] Bỏ qua mô hình TFLite.");
#endif

/**/ // THAY ĐỔI P4: Validation tensor không khởi tạo hoặc đọc INMP441.
#if !RUN_DIRECT_TENSOR_TEST
    // 3. Khởi tạo I2S cho mic INMP441
    Serial.println("[CÀI ĐẶT] Đang khởi tạo Microphone I2S...");
    I2S_Mic_Init(I2S_SCK, I2S_WS, I2S_SD);
    Serial.println("[CÀI ĐẶT] I2S sẵn sàng.");

    /**/ // THAY ĐỔI P5: In đúng trạng thái của phép đo năng lượng.
#if RUN_VAD_CALIBRATION_TEST
    Serial.println("\n[VAD_CAL] Micro sẵn sàng, bắt đầu phép đo tự động.\n");
#else
    Serial.println("\n[CÀI ĐẶT] HỆ THỐNG SẴN SÀNG! Đang lắng nghe...\n");
#endif
#else
    Serial.println("[DIRECT_TENSOR] Sẵn sàng chạy tensor trực tiếp.\n");
#endif
}

void loop() {
/**/ // THAY ĐỔI P5: Đo năng lượng INMP441, không chạy pipeline AI.
#if RUN_VAD_CALIBRATION_TEST
    Run_VAD_Calibration();
/**/ // THAY ĐỔI P4: Gọi bộ validation thay cho pipeline audio khi bật chế độ test.
#elif RUN_VALIDATION_108_TEST
    Run_Validation_108_Test();
/**/ // THAY ĐỔI P4: Test 113 được chạy sau khi validation đã khóa ngưỡng.
#elif RUN_TEST_113_TEST
    Run_Test_113_Test();
#else
    Process_Audio_Stream();
#endif
}

/**/ // THAY ĐỔI P4: Hàm mới đặt cuối file, chạy và tổng kết 108 tensor validation.
#if RUN_VALIDATION_108_TEST
void Run_Validation_108_Test(void){
    static int validation_index = 0;
    static int same_prediction_count = 0;
    static int correct_label_count = 0;
    static int exact_output_count = 0;
    static int maximum_raw_difference = 0;
    static float maximum_probability_difference = 0.0f;
    static bool completed = false;

    if(completed){
        delay(1000);
        return;
    }

    const int index = validation_index;
    const int true_label = VALIDATION_TRUE_LABELS[index];
    const int python_prediction = VALIDATION_PYTHON_PREDICTIONS[index];
    const int python_output_raw = VALIDATION_PYTHON_OUTPUT_RAW[index];
    const float python_probability =
        VALIDATION_PYTHON_PROBABILITIES[index];

    Serial.printf(
        "\n[VALIDATION_108] Mẫu %d/%d: %s\n",
        index + 1,
        VALIDATION_SAMPLE_COUNT,
        VALIDATION_FILE_NAMES[index]
    );

    Asthma_Result result = Run_Asthma_From_Int8_Tensor(
        VALIDATION_TENSORS[index],
        VALIDATION_TENSOR_LENGTH,
        VALIDATION_SELECTED_THRESHOLD
    );

    const float esp_probability = result.Non_Asthma_Prob / 100.0f;
    int raw_difference =
        static_cast<int>(result.Output_Raw_Int8) - python_output_raw;
    if(raw_difference < 0) raw_difference = -raw_difference;

    float probability_difference = esp_probability - python_probability;
    if(probability_difference < 0.0f){
        probability_difference = -probability_difference;
    }

    const bool same_prediction =
        result.Predicted_Class == python_prediction;
    const bool correct_label = result.Predicted_Class == true_label;

    if(same_prediction) same_prediction_count++;
    if(correct_label) correct_label_count++;
    if(raw_difference == 0) exact_output_count++;
    if(raw_difference > maximum_raw_difference){
        maximum_raw_difference = raw_difference;
    }
    if(probability_difference > maximum_probability_difference){
        maximum_probability_difference = probability_difference;
    }

    Serial.printf(
        "[VALIDATION_RESULT] index=%d,file=%s,true=%d,py_pred=%d,esp_pred=%d,"
        "py_raw=%d,esp_raw=%d,raw_diff=%d,py_prob=%.9f,esp_prob=%.9f,"
        "prob_diff=%.9f\n",
        index,
        VALIDATION_FILE_NAMES[index],
        true_label,
        python_prediction,
        result.Predicted_Class,
        python_output_raw,
        static_cast<int>(result.Output_Raw_Int8),
        raw_difference,
        python_probability,
        esp_probability,
        probability_difference
    );

    validation_index++;
    if(validation_index >= VALIDATION_SAMPLE_COUNT){
        Serial.println("\n========== TỔNG KẾT VALIDATION 108 ==========");
        Serial.printf(
            "Cùng lớp Python - ESP32: %d/%d\n",
            same_prediction_count,
            VALIDATION_SAMPLE_COUNT
        );
        Serial.printf(
            "ESP32 đúng nhãn thật: %d/%d\n",
            correct_label_count,
            VALIDATION_SAMPLE_COUNT
        );
        Serial.printf(
            "Output INT8 trùng tuyệt đối: %d/%d\n",
            exact_output_count,
            VALIDATION_SAMPLE_COUNT
        );
        Serial.printf(
            "Raw lệch lớn nhất: %d\n",
            maximum_raw_difference
        );
        Serial.printf(
            "Điểm lệch lớn nhất: %.9f\n",
            maximum_probability_difference
        );
        Serial.printf(
            "Ngưỡng validation đang dùng: %.9f\n",
            VALIDATION_SELECTED_THRESHOLD
        );
        Serial.println("=============================================\n");
        completed = true;
    }

    delay(20);
}
#endif

/**/ // THAY ĐỔI P4: Hàm mới đặt cuối file, chạy và tổng kết 113 tensor test.
#if RUN_TEST_113_TEST
void Run_Test_113_Test(void){
    static int test_index = 0;
    static int same_prediction_count = 0;
    static int correct_label_count = 0;
    static int exact_output_count = 0;
    static int asthma_correct_count = 0;
    static int asthma_total_count = 0;
    static int non_asthma_correct_count = 0;
    static int non_asthma_total_count = 0;
    static int maximum_raw_difference = 0;
    static float maximum_probability_difference = 0.0f;
    static bool completed = false;

    if(completed){
        delay(1000);
        return;
    }

    const int index = test_index;
    const int true_label = TEST_TRUE_LABELS[index];
    const int python_prediction = TEST_PYTHON_PREDICTIONS[index];
    const int python_output_raw = TEST_PYTHON_OUTPUT_RAW[index];
    const float python_probability = TEST_PYTHON_PROBABILITIES[index];

    Serial.printf(
        "\n[TEST_113] Mẫu %d/%d: %s\n",
        index + 1,
        TEST_SAMPLE_COUNT,
        TEST_FILE_NAMES[index]
    );

    Asthma_Result result = Run_Asthma_From_Int8_Tensor(
        TEST_TENSORS[index],
        TEST_TENSOR_LENGTH,
        TEST_LOCKED_THRESHOLD
    );

    const float esp_probability = result.Non_Asthma_Prob / 100.0f;
    int raw_difference =
        static_cast<int>(result.Output_Raw_Int8) - python_output_raw;
    if(raw_difference < 0) raw_difference = -raw_difference;

    float probability_difference = esp_probability - python_probability;
    if(probability_difference < 0.0f){
        probability_difference = -probability_difference;
    }

    const bool same_prediction =
        result.Predicted_Class == python_prediction;
    const bool correct_label = result.Predicted_Class == true_label;

    if(same_prediction) same_prediction_count++;
    if(correct_label) correct_label_count++;
    if(raw_difference == 0) exact_output_count++;

    if(true_label == 0){
        asthma_total_count++;
        if(correct_label) asthma_correct_count++;
    }else{
        non_asthma_total_count++;
        if(correct_label) non_asthma_correct_count++;
    }

    if(raw_difference > maximum_raw_difference){
        maximum_raw_difference = raw_difference;
    }
    if(probability_difference > maximum_probability_difference){
        maximum_probability_difference = probability_difference;
    }

    Serial.printf(
        "[TEST_RESULT] index=%d,file=%s,true=%d,py_pred=%d,esp_pred=%d,"
        "py_raw=%d,esp_raw=%d,raw_diff=%d,py_prob=%.9f,esp_prob=%.9f,"
        "prob_diff=%.9f\n",
        index,
        TEST_FILE_NAMES[index],
        true_label,
        python_prediction,
        result.Predicted_Class,
        python_output_raw,
        static_cast<int>(result.Output_Raw_Int8),
        raw_difference,
        python_probability,
        esp_probability,
        probability_difference
    );

    test_index++;
    if(test_index >= TEST_SAMPLE_COUNT){
        const float balanced_accuracy = 0.5f * (
            static_cast<float>(asthma_correct_count) / asthma_total_count
            + static_cast<float>(non_asthma_correct_count)
              / non_asthma_total_count
        );

        Serial.println("\n============= TỔNG KẾT TEST 113 =============");
        Serial.printf(
            "Cùng lớp Python - ESP32: %d/%d\n",
            same_prediction_count,
            TEST_SAMPLE_COUNT
        );
        Serial.printf(
            "ESP32 đúng nhãn thật: %d/%d\n",
            correct_label_count,
            TEST_SAMPLE_COUNT
        );
        Serial.printf(
            "Asthma đúng: %d/%d\n",
            asthma_correct_count,
            asthma_total_count
        );
        Serial.printf(
            "Non-Asthma đúng: %d/%d\n",
            non_asthma_correct_count,
            non_asthma_total_count
        );
        Serial.printf(
            "Độ chính xác cân bằng ESP32: %.6f\n",
            balanced_accuracy
        );
        Serial.printf(
            "Output INT8 trùng tuyệt đối: %d/%d\n",
            exact_output_count,
            TEST_SAMPLE_COUNT
        );
        Serial.printf("Raw lệch lớn nhất: %d\n", maximum_raw_difference);
        Serial.printf(
            "Điểm lệch lớn nhất: %.9f\n",
            maximum_probability_difference
        );
        Serial.printf(
            "Ngưỡng test đã khóa: %.9f\n",
            TEST_LOCKED_THRESHOLD
        );
        Serial.println("=============================================\n");
        completed = true;
    }

    delay(20);
}
#endif
