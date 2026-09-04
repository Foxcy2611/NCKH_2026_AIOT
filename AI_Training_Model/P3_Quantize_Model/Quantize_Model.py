"""
===============================================================================
Tên script: Quantize_Model.py

Tác dụng:
- Chuyển model Keras đã chọn sang TFLite INT8 toàn phần, gồm cả input/output.
- Xuất file .tflite, header C++ và báo cáo so sánh Keras với INT8.
- Ghi shape, scale, zero point, dự đoán từng file và ma trận nhầm lẫn.

Điểm tinh chỉnh so với model ban đầu:
- Dữ liệu đại diện để lượng tử chỉ lấy cân bằng từ train.
- Dùng đúng min/max đã lưu lúc train; không đọc min/max từ test.
- Test chỉ đánh giá ảnh hưởng của lượng tử, không tham gia tạo model INT8.
===============================================================================
"""

import csv
import os
import sys

os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import numpy as np
import tensorflow as tf
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


SEED = 42
REPRESENTATIVE_PER_CLASS = 50
THRESHOLD = 0.5

P2_DIR = os.path.join(
    "AI_Training_Model",
    "P2_Preprocess_&_Traning_Model"
)
FEATURE_DIR = os.path.join(P2_DIR, "Output_Preprocess")
TRAIN_OUTPUT_DIR = os.path.join(P2_DIR, "Output_Train")

MODEL_PATH = os.path.join(TRAIN_OUTPUT_DIR, "Bin_Asthma.keras")
NORMALIZATION_PATH = os.path.join(
    TRAIN_OUTPUT_DIR,
    "Normalization_Params.txt"
)

OUTPUT_DIR = os.path.join(
    "AI_Training_Model",
    "P3_Quantize_Model",
    "Output_Quantize"
)
TFLITE_PATH = os.path.join(OUTPUT_DIR, "Asthma_Model_Int8.tflite")
HEADER_PATH = os.path.join(OUTPUT_DIR, "Asthma_Model.h")
REPORT_PATH = os.path.join(OUTPUT_DIR, "Quantization_Report.txt")
PREDICTION_PATH = os.path.join(OUTPUT_DIR, "Test_Predictions_Int8.csv")


def load_normalization_params():
    if not os.path.exists(NORMALIZATION_PATH):
        raise FileNotFoundError(
            f"Không tìm thấy tham số chuẩn hóa: {NORMALIZATION_PATH}"
        )

    params = {}
    with open(NORMALIZATION_PATH, "r", encoding="utf-8") as file:
        for line in file:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                params[key] = float(value)

    if "TRAIN_MIN" not in params or "TRAIN_MAX" not in params:
        raise ValueError("Normalization_Params.txt thiếu TRAIN_MIN/TRAIN_MAX")

    train_min = params["TRAIN_MIN"]
    train_max = params["TRAIN_MAX"]

    if train_max <= train_min:
        raise ValueError("TRAIN_MIN/TRAIN_MAX không hợp lệ")

    return train_min, train_max


def normalize_mel(x_data, train_min, train_max):
    x_data = x_data.astype(np.float32)
    x_data -= train_min
    x_data /= train_max - train_min
    return x_data


def choose_representative_indices(y_train):
    rng = np.random.default_rng(SEED)
    selected = []

    for label in [0, 1]:
        indices = np.where(y_train == label)[0]
        amount = min(REPRESENTATIVE_PER_CLASS, len(indices))
        selected.extend(rng.choice(indices, amount, replace=False))

    selected = np.asarray(selected, dtype=np.int64)
    rng.shuffle(selected)
    return selected


def convert_to_int8(model, x_train, y_train):
    representative_indices = choose_representative_indices(y_train)

    def representative_dataset():
        for index in representative_indices:
            yield [x_train[index:index + 1]]

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_dataset
    converter.target_spec.supported_ops = [
        tf.lite.OpsSet.TFLITE_BUILTINS_INT8
    ]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8

    return converter.convert(), len(representative_indices)


def convert_to_c_header(tflite_data):
    lines = []
    for start in range(0, len(tflite_data), 12):
        chunk = tflite_data[start:start + 12]
        lines.append("    " + ", ".join(f"0x{byte:02x}" for byte in chunk))

    array_text = ",\n".join(lines)
    header = f"""#ifndef ASTHMA_MODEL_H
#define ASTHMA_MODEL_H

// Model TFLite int8: {len(tflite_data)} bytes
const int model_data_len = {len(tflite_data)};

const unsigned char model_data[] __attribute__((aligned(4))) = {{
{array_text}
}};

#endif // ASTHMA_MODEL_H
"""

    with open(HEADER_PATH, "w", encoding="utf-8") as file:
        file.write(header)


def run_int8_model(x_test):
    interpreter = tf.lite.Interpreter(model_path=TFLITE_PATH)
    interpreter.allocate_tensors()

    input_detail = interpreter.get_input_details()[0]
    output_detail = interpreter.get_output_details()[0]

    if input_detail["dtype"] != np.int8 or output_detail["dtype"] != np.int8:
        raise TypeError("Model TFLite chưa có đầu vào/đầu ra int8")

    input_scale, input_zero = input_detail["quantization"]
    output_scale, output_zero = output_detail["quantization"]

    if input_scale <= 0 or output_scale <= 0:
        raise ValueError("Thông số lượng tử input/output không hợp lệ")

    probabilities = []

    for sample in x_test:
        sample_int8 = np.round(sample / input_scale + input_zero)
        sample_int8 = np.clip(sample_int8, -128, 127).astype(np.int8)
        sample_int8 = sample_int8[np.newaxis, ...]

        interpreter.set_tensor(input_detail["index"], sample_int8)
        interpreter.invoke()

        output_int8 = interpreter.get_tensor(output_detail["index"])
        output_float = (
            output_int8.astype(np.float32) - output_zero
        ) * output_scale
        probabilities.append(float(output_float.reshape(-1)[0]))

    quantization_info = {
        "input_shape": input_detail["shape"].tolist(),
        "input_scale": float(input_scale),
        "input_zero_point": int(input_zero),
        "output_shape": output_detail["shape"].tolist(),
        "output_scale": float(output_scale),
        "output_zero_point": int(output_zero),
    }

    return np.asarray(probabilities), quantization_info


def save_predictions(
    file_names,
    y_test,
    float_probabilities,
    int8_probabilities,
    float_predictions,
    int8_predictions
):
    with open(PREDICTION_PATH, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow([
            "file_name",
            "true_label",
            "float_probability_non_asthma",
            "int8_probability_non_asthma",
            "float_prediction",
            "int8_prediction"
        ])

        for row in zip(
            file_names,
            y_test,
            float_probabilities,
            int8_probabilities,
            float_predictions,
            int8_predictions
        ):
            writer.writerow(row)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("1. ĐỌC MODEL VÀ DỮ LIỆU")
    model = tf.keras.models.load_model(MODEL_PATH)
    train_min, train_max = load_normalization_params()

    x_train = np.load(os.path.join(FEATURE_DIR, "X_train_mel.npy"))
    y_train = np.load(os.path.join(FEATURE_DIR, "Y_train_mel.npy"))
    x_test = np.load(os.path.join(FEATURE_DIR, "X_test_mel.npy"))
    y_test = np.load(os.path.join(FEATURE_DIR, "Y_test_mel.npy")).astype(int)
    file_names = np.load(os.path.join(FEATURE_DIR, "Files_test.npy"))

    x_train = normalize_mel(x_train, train_min, train_max)
    x_test = normalize_mel(x_test, train_min, train_max)

    print(f"Train: {x_train.shape}, Test: {x_test.shape}")
    print(f"TRAIN_MIN={train_min}, TRAIN_MAX={train_max}")

    print("\n2. LƯỢNG TỬ TOÀN PHẦN SANG INT8")
    tflite_data, representative_count = convert_to_int8(
        model,
        x_train,
        y_train
    )

    with open(TFLITE_PATH, "wb") as file:
        file.write(tflite_data)

    convert_to_c_header(tflite_data)

    print("\n3. SO SÁNH MODEL KERAS VÀ MODEL INT8 TRÊN TẬP TEST")
    float_probabilities = model.predict(x_test, verbose=0).reshape(-1)
    int8_probabilities, quantization_info = run_int8_model(x_test)

    float_predictions = (float_probabilities >= THRESHOLD).astype(int)
    int8_predictions = (int8_probabilities >= THRESHOLD).astype(int)

    float_accuracy = accuracy_score(y_test, float_predictions)
    int8_accuracy = accuracy_score(y_test, int8_predictions)
    changed_count = int(np.sum(float_predictions != int8_predictions))

    float_matrix = confusion_matrix(y_test, float_predictions, labels=[0, 1])
    int8_matrix = confusion_matrix(y_test, int8_predictions, labels=[0, 1])
    int8_report = classification_report(
        y_test,
        int8_predictions,
        labels=[0, 1],
        target_names=["Asthma", "Non_Asthma"],
        digits=4,
        zero_division=0
    )

    save_predictions(
        file_names,
        y_test,
        float_probabilities,
        int8_probabilities,
        float_predictions,
        int8_predictions
    )

    keras_size = os.path.getsize(MODEL_PATH)
    tflite_size = os.path.getsize(TFLITE_PATH)
    reduction = 100.0 * (1.0 - tflite_size / keras_size)

    report = f"""KẾT QUẢ LƯỢNG TỬ INT8

Dữ liệu đại diện: {representative_count} mẫu từ tập train
TRAIN_MIN: {train_min}
TRAIN_MAX: {train_max}
Ngưỡng quyết định: {THRESHOLD}

Keras size: {keras_size} bytes
TFLite int8 size: {tflite_size} bytes
Giảm dung lượng: {reduction:.2f}%

Input shape: {quantization_info['input_shape']}
Input scale: {quantization_info['input_scale']}
Input zero point: {quantization_info['input_zero_point']}
Output shape: {quantization_info['output_shape']}
Output scale: {quantization_info['output_scale']}
Output zero point: {quantization_info['output_zero_point']}

Keras test accuracy: {float_accuracy:.6f}
INT8 test accuracy: {int8_accuracy:.6f}
Số mẫu đổi kết quả sau lượng tử: {changed_count}/{len(y_test)}

Keras confusion matrix [Asthma, Non_Asthma]:
{np.array2string(float_matrix)}

INT8 confusion matrix [Asthma, Non_Asthma]:
{np.array2string(int8_matrix)}

INT8 classification report:
{int8_report}
"""

    with open(REPORT_PATH, "w", encoding="utf-8") as file:
        file.write(report)

    print(report)
    print(f"Model TFLite: {TFLITE_PATH}")
    print(f"Header C++: {HEADER_PATH}")


if __name__ == "__main__":
    main()
