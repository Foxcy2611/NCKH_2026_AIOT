"""
===============================================================================
Tên script: 3_Tao_113_Tensor_Test.py

Tác dụng:
- Đọc 113 Mel-Spectrogram test đã được Python tiền xử lý.
- Chuẩn hóa, lượng tử INT8 và chạy đúng model TFLite trên laptop.
- Đọc ngưỡng đã chọn từ validation, không tối ưu lại ngưỡng bằng test.
- Xuất CSV/NPZ, báo cáo cuối và header để ESP32 nạp thẳng tensor INT8.

Lưu ý:
- Phải chạy 2_Tao_108_Tensor_Validation.py trước.
- Test chỉ dùng chấm kết quả cuối sau khi ngưỡng đã được khóa.
===============================================================================
"""

import csv
import os
import sys
from pathlib import Path

os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import numpy as np
import tensorflow as tf


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[2]
P2_DIR = ROOT / "AI_Training_Model" / "P2_Preprocess_&_Traning_Model"
FEATURE_DIR = P2_DIR / "Output_Preprocess"
TRAIN_DIR = P2_DIR / "Output_Train"
TFLITE_PATH = (
    ROOT
    / "AI_Training_Model"
    / "P3_Quantize_Model"
    / "Output_Quantize"
    / "Asthma_Model_Int8.tflite"
)
VALIDATION_DIR = (
    ROOT
    / "AI_Training_Model"
    / "P4_Kiem_Tra_CPP"
    / "Output_Validation_108"
)
THRESHOLD_PATH = VALIDATION_DIR / "Selected_Threshold.txt"
OUTPUT_DIR = (
    ROOT
    / "AI_Training_Model"
    / "P4_Kiem_Tra_CPP"
    / "Output_Test_113"
)
HEADER_PATH = (
    ROOT
    / "Deploy_Model"
    / "2_Test_Model_LiveMic"
    / "include"
    / "Tensor_Include_Test113"
    / "Test_Tensors_113.h"
)


def load_key_value(path):
    values = {}
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                values[key] = value
    return values


def load_normalization_params():
    values = load_key_value(TRAIN_DIR / "Normalization_Params.txt")
    train_min = float(values["TRAIN_MIN"])
    train_max = float(values["TRAIN_MAX"])
    if train_max <= train_min:
        raise ValueError("TRAIN_MIN/TRAIN_MAX không hợp lệ")
    return train_min, train_max


def prepare_interpreter():
    interpreter = tf.lite.Interpreter(model_path=str(TFLITE_PATH))
    interpreter.allocate_tensors()
    input_detail = interpreter.get_input_details()[0]
    output_detail = interpreter.get_output_details()[0]

    if input_detail["dtype"] != np.int8 or output_detail["dtype"] != np.int8:
        raise TypeError("Model phải có input/output INT8")
    if tuple(input_detail["shape"]) != (1, 64, 129, 1):
        raise ValueError(f"Sai input shape: {input_detail['shape']}")

    return interpreter, input_detail, output_detail


def quantize_input(mel, train_min, train_max, input_detail):
    normalized = (mel.astype(np.float32) - train_min) / (train_max - train_min)
    scale, zero_point = input_detail["quantization"]
    quantized = np.round(normalized / scale + zero_point)
    return np.clip(quantized, -128, 127).astype(np.int8)


def run_tflite(interpreter, input_detail, output_detail, tensor_int8):
    interpreter.set_tensor(input_detail["index"], tensor_int8[np.newaxis, ...])
    interpreter.invoke()

    raw = int(interpreter.get_tensor(output_detail["index"]).reshape(-1)[0])
    scale, zero_point = output_detail["quantization"]
    probability = float((raw - zero_point) * scale)
    return raw, min(1.0, max(0.0, probability))


def calculate_metrics(labels, probabilities, threshold):
    predictions = (probabilities >= threshold).astype(np.int8)
    asthma_total = int(np.sum(labels == 0))
    non_asthma_total = int(np.sum(labels == 1))
    asthma_correct = int(np.sum((labels == 0) & (predictions == 0)))
    non_asthma_correct = int(np.sum((labels == 1) & (predictions == 1)))
    asthma_recall = asthma_correct / asthma_total
    non_asthma_recall = non_asthma_correct / non_asthma_total

    return {
        "predictions": predictions,
        "asthma_correct": asthma_correct,
        "asthma_total": asthma_total,
        "asthma_recall": asthma_recall,
        "non_asthma_correct": non_asthma_correct,
        "non_asthma_total": non_asthma_total,
        "non_asthma_recall": non_asthma_recall,
        "balanced_accuracy": (asthma_recall + non_asthma_recall) / 2.0,
        "accuracy": float(np.mean(predictions == labels)),
    }


def write_numeric_array(file, c_type, name, values, row_size=24):
    flat = np.asarray(values).reshape(-1)
    file.write(f"static const {c_type} {name}[{len(flat)}] = {{\n")
    for start in range(0, len(flat), row_size):
        row = flat[start:start + row_size]
        file.write("    " + ", ".join(str(int(value)) for value in row))
        if start + row_size < len(flat):
            file.write(",")
        file.write("\n")
    file.write("};\n\n")


def c_string(value):
    value = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{value}"'


def write_header(tensors, labels, names, raw_outputs, probabilities, threshold, metrics):
    HEADER_PATH.parent.mkdir(parents=True, exist_ok=True)
    predictions = metrics["predictions"]

    with HEADER_PATH.open("w", encoding="utf-8", newline="\n") as file:
        file.write("#ifndef TEST_TENSORS_113_H\n")
        file.write("#define TEST_TENSORS_113_H\n\n")
        file.write("#include <stdint.h>\n\n")
        file.write(f"static const int TEST_SAMPLE_COUNT = {len(labels)};\n")
        file.write("static const int TEST_TENSOR_LENGTH = 64 * 129;\n")
        file.write(
            "static constexpr float TEST_LOCKED_THRESHOLD = "
            f"{threshold:.9f}f;\n\n"
        )

        for index, tensor in enumerate(tensors):
            write_numeric_array(
                file,
                "int8_t",
                f"test_tensor_{index:03d}",
                tensor,
            )

        file.write(
            "static const int8_t* const TEST_TENSORS[TEST_SAMPLE_COUNT] = {\n"
        )
        for index in range(len(labels)):
            suffix = "," if index + 1 < len(labels) else ""
            file.write(f"    test_tensor_{index:03d}{suffix}\n")
        file.write("};\n\n")

        file.write(
            "static const char* const TEST_FILE_NAMES[TEST_SAMPLE_COUNT] = {\n"
        )
        for index, name in enumerate(names):
            suffix = "," if index + 1 < len(names) else ""
            file.write(f"    {c_string(Path(str(name)).name)}{suffix}\n")
        file.write("};\n\n")

        write_numeric_array(file, "int8_t", "TEST_TRUE_LABELS", labels)
        write_numeric_array(file, "int8_t", "TEST_PYTHON_OUTPUT_RAW", raw_outputs)
        write_numeric_array(
            file, "int8_t", "TEST_PYTHON_PREDICTIONS", predictions
        )

        values = ", ".join(f"{value:.9f}f" for value in probabilities)
        file.write(
            "static const float "
            f"TEST_PYTHON_PROBABILITIES[{len(probabilities)}] = {{\n"
            f"    {values}\n"
            "};\n\n"
        )
        file.write("#endif // TEST_TENSORS_113_H\n")


def save_outputs(
    tensors,
    labels,
    names,
    raw_outputs,
    probabilities,
    threshold,
    metrics,
    input_detail,
    output_detail,
):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    predictions = metrics["predictions"]

    with (OUTPUT_DIR / "Python_Reference_Test_113.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.writer(file)
        writer.writerow([
            "index", "file_name", "true_label", "python_output_raw_int8",
            "python_probability_non_asthma", "python_prediction", "correct"
        ])
        for index in range(len(labels)):
            writer.writerow([
                index,
                str(names[index]),
                int(labels[index]),
                int(raw_outputs[index]),
                f"{probabilities[index]:.9f}",
                int(predictions[index]),
                int(predictions[index] == labels[index]),
            ])

    report = f"""KẾT QUẢ TFLITE PYTHON TRÊN TẬP TEST 113

Ngưỡng đã khóa từ validation: {threshold:.9f}
Tổng mẫu: {len(labels)}

Asthma đúng: {metrics['asthma_correct']}/{metrics['asthma_total']}
Độ nhận Asthma: {metrics['asthma_recall']:.6f}

Non-Asthma đúng: {metrics['non_asthma_correct']}/{metrics['non_asthma_total']}
Độ nhận Non-Asthma: {metrics['non_asthma_recall']:.6f}

Độ chính xác cân bằng: {metrics['balanced_accuracy']:.6f}
Accuracy toàn bộ: {metrics['accuracy']:.6f}

Test không tham gia chọn lại ngưỡng.
"""
    (OUTPUT_DIR / "Test_113_Report.txt").write_text(report, encoding="utf-8")

    np.savez_compressed(
        OUTPUT_DIR / "Python_Reference_Test_113.npz",
        tensor_int8=tensors,
        true_labels=labels,
        file_names=names,
        output_raw_int8=raw_outputs,
        probabilities=probabilities,
        predictions=predictions,
        locked_threshold=np.asarray(threshold),
        input_scale=np.asarray(input_detail["quantization"][0]),
        input_zero_point=np.asarray(input_detail["quantization"][1]),
        output_scale=np.asarray(output_detail["quantization"][0]),
        output_zero_point=np.asarray(output_detail["quantization"][1]),
    )

    print(report)


def main():
    required = [
        FEATURE_DIR / "X_test_mel.npy",
        FEATURE_DIR / "Y_test_mel.npy",
        FEATURE_DIR / "Files_test.npy",
        TRAIN_DIR / "Normalization_Params.txt",
        TFLITE_PATH,
        THRESHOLD_PATH,
    ]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(
                f"Thiếu file: {path}\n"
                "Hãy chạy 2_Tao_108_Tensor_Validation.py trước."
            )

    threshold_values = load_key_value(THRESHOLD_PATH)
    threshold = float(threshold_values["THRESHOLD"])
    if not 0.0 < threshold < 1.0:
        raise ValueError(f"Ngưỡng validation không hợp lệ: {threshold}")

    x_test = np.load(FEATURE_DIR / "X_test_mel.npy", mmap_mode="r")
    labels = np.load(FEATURE_DIR / "Y_test_mel.npy").astype(np.int8)
    names = np.load(FEATURE_DIR / "Files_test.npy")

    if x_test.shape != (113, 64, 129, 1):
        raise ValueError(f"Test phải có shape (113, 64, 129, 1), nhận {x_test.shape}")
    if len(labels) != 113 or len(names) != 113:
        raise ValueError("X/Y/Files test không cùng 113 mẫu")

    train_min, train_max = load_normalization_params()
    interpreter, input_detail, output_detail = prepare_interpreter()

    tensors = []
    raw_outputs = []
    probabilities = []

    print("1. Lượng tử và chạy TFLite Python trên 113 mẫu test")
    for mel in x_test:
        tensor = quantize_input(mel, train_min, train_max, input_detail)
        raw, probability = run_tflite(
            interpreter, input_detail, output_detail, tensor
        )
        tensors.append(tensor)
        raw_outputs.append(raw)
        probabilities.append(probability)

    tensors = np.stack(tensors)
    raw_outputs = np.asarray(raw_outputs, dtype=np.int8)
    probabilities = np.asarray(probabilities, dtype=np.float32)
    metrics = calculate_metrics(labels, probabilities, threshold)

    print("2. Xuất báo cáo test và header ESP32")
    save_outputs(
        tensors, labels, names, raw_outputs, probabilities, threshold, metrics,
        input_detail, output_detail
    )
    write_header(
        tensors, labels, names, raw_outputs, probabilities, threshold, metrics
    )

    print(f"Header ESP32: {HEADER_PATH}")
    print(f"Báo cáo: {OUTPUT_DIR / 'Test_113_Report.txt'}")
    print("Không tối ưu lại ngưỡng bằng tập test.")


if __name__ == "__main__":
    main()
