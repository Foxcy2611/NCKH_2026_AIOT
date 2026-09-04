"""
===============================================================================
Tên script: 1_Tao_20_Mau_Kiem_Tra.py

Tác dụng:
- Chọn cố định bằng SEED 10 Asthma + 10 Non-Asthma từ train, mỗi file là PCM16
  mono 16 kHz và đúng 80.000 mẫu.
- Lấy Mel Python, lượng tử tensor, chạy model TFLite Python và xuất header để
  ESP32 tự chạy lại cùng 20 PCM16.
- Lưu CSV/NPZ tham chiếu gồm nhãn, tensor INT8, output INT8 và xác suất Python.

Điểm tinh chỉnh so với model ban đầu:
- Python và C++ bắt đầu từ đúng cùng một PCM16, nhờ đó phép test chỉ đo độ khớp
  tiền xử lý/suy luận, không bị lẫn sai số do hai cách đọc WAV khác nhau.
- Mục tiêu là ESP32 khớp Python 20/20; không ép model phải đúng nhãn 20/20.
===============================================================================
"""

import csv
import os
import sys
import wave
from pathlib import Path

os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import numpy as np
import tensorflow as tf


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


SEED = 42
SAMPLES_PER_CLASS = 10
SAMPLE_RATE = 16000
TOTAL_SAMPLES = 80000
DECISION_THRESHOLD = 0.5

ROOT = Path.cwd()
DATASET_DIR = ROOT / "AI_Training_Model" / "Dataset_Chia"
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
OUTPUT_DIR = ROOT / "AI_Training_Model" / "P4_Kiem_Tra_CPP" / "Output_Test_20"
HEADER_DIR = (
    ROOT
    / "Deploy_Model"
    / "2_Test_Model_LiveMic"
    / "include"
    / "Raw_Include_Parity20"
)
HEADER_PATH = HEADER_DIR / "Raw_Test_20.h"


def load_normalization_params():
    params = {}
    path = TRAIN_DIR / "Normalization_Params.txt"
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                params[key] = float(value)

    train_min = params["TRAIN_MIN"]
    train_max = params["TRAIN_MAX"]
    if train_max <= train_min:
        raise ValueError("TRAIN_MIN/TRAIN_MAX không hợp lệ")
    return train_min, train_max


def read_pcm16_if_compatible(path):
    """Trả về PCM16 nếu WAV là mono, 16 kHz, 16-bit và đúng 5 giây."""
    try:
        with wave.open(str(path), "rb") as wav:
            valid = (
                wav.getnchannels() == 1
                and wav.getsampwidth() == 2
                and wav.getframerate() == SAMPLE_RATE
                and wav.getnframes() == TOTAL_SAMPLES
                and wav.getcomptype() == "NONE"
            )
            if not valid:
                return None
            raw = wav.readframes(TOTAL_SAMPLES)
    except (wave.Error, OSError):
        return None

    pcm = np.frombuffer(raw, dtype="<i2").copy()
    if pcm.shape != (TOTAL_SAMPLES,):
        return None
    return pcm


def choose_samples(file_names, labels):
    candidates = {0: [], 1: []}

    for index, (relative_name, label) in enumerate(zip(file_names, labels)):
        label = int(label)
        path = DATASET_DIR / str(relative_name)
        if read_pcm16_if_compatible(path) is not None:
            candidates[label].append(index)

    rng = np.random.default_rng(SEED)
    selected = []
    for label in [0, 1]:
        indices = np.asarray(candidates[label], dtype=np.int64)
        if len(indices) < SAMPLES_PER_CLASS:
            raise RuntimeError(
                f"Lớp {label} chỉ có {len(indices)} WAV PCM16/16k/5s, "
                f"không đủ {SAMPLES_PER_CLASS} mẫu"
            )
        chosen = rng.choice(indices, SAMPLES_PER_CLASS, replace=False)
        selected.extend(sorted(chosen.tolist()))

    return np.asarray(selected, dtype=np.int64)


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

    output_raw = int(interpreter.get_tensor(output_detail["index"]).reshape(-1)[0])
    output_scale, output_zero = output_detail["quantization"]
    probability = float((output_raw - output_zero) * output_scale)
    probability = min(1.0, max(0.0, probability))
    prediction = int(probability >= DECISION_THRESHOLD)
    return output_raw, probability, prediction


def write_numeric_array(file, c_type, name, values, row_size):
    flat = np.asarray(values).reshape(-1)
    file.write(f"static const {c_type} {name}[{len(flat)}] = {{\n")
    for start in range(0, len(flat), row_size):
        row = flat[start:start + row_size]
        file.write("    " + ", ".join(str(int(value)) for value in row))
        if start + row_size < len(flat):
            file.write(",")
        file.write("\n")
    file.write("};\n\n")


def write_header(records):
    HEADER_DIR.mkdir(parents=True, exist_ok=True)

    with HEADER_PATH.open("w", encoding="utf-8", newline="\n") as file:
        file.write("#ifndef RAW_TEST_20_H\n#define RAW_TEST_20_H\n\n")
        file.write("#include <stdint.h>\n\n")
        file.write(f"static const int PARITY_SAMPLE_COUNT = {len(records)};\n")
        file.write(f"static const int PARITY_AUDIO_LENGTH = {TOTAL_SAMPLES};\n")
        file.write("static const int PARITY_TENSOR_LENGTH = 64 * 129;\n\n")

        for index, record in enumerate(records):
            write_numeric_array(
                file,
                "int16_t",
                f"parity_audio_{index:02d}",
                record["pcm"],
                15
            )
            write_numeric_array(
                file,
                "int8_t",
                f"parity_tensor_{index:02d}",
                record["tensor"],
                24
            )

        file.write("static const int16_t* const PARITY_AUDIO[PARITY_SAMPLE_COUNT] = {\n")
        for index in range(len(records)):
            file.write(f"    parity_audio_{index:02d}")
            file.write(",\n" if index + 1 < len(records) else "\n")
        file.write("};\n\n")

        file.write("static const int8_t* const PARITY_TENSOR[PARITY_SAMPLE_COUNT] = {\n")
        for index in range(len(records)):
            file.write(f"    parity_tensor_{index:02d}")
            file.write(",\n" if index + 1 < len(records) else "\n")
        file.write("};\n\n")

        names = ",\n".join(f'    "{record["name"]}"' for record in records)
        labels = ", ".join(str(record["label"]) for record in records)
        outputs = ", ".join(str(record["output_raw"]) for record in records)
        predictions = ", ".join(str(record["prediction"]) for record in records)
        probabilities = ", ".join(
            f'{record["probability"]:.9f}f' for record in records
        )

        file.write(
            "static const char* const PARITY_FILE_NAMES[PARITY_SAMPLE_COUNT] = {\n"
            f"{names}\n}};\n\n"
        )
        file.write(
            "static const int8_t PARITY_TRUE_LABELS[PARITY_SAMPLE_COUNT] = {"
            f"{labels}}};\n"
        )
        file.write(
            "static const int8_t PARITY_EXPECTED_OUTPUT_RAW[PARITY_SAMPLE_COUNT] = {"
            f"{outputs}}};\n"
        )
        file.write(
            "static const int8_t PARITY_EXPECTED_PREDICTIONS[PARITY_SAMPLE_COUNT] = {"
            f"{predictions}}};\n"
        )
        file.write(
            "static const float PARITY_EXPECTED_PROBABILITIES[PARITY_SAMPLE_COUNT] = {"
            f"{probabilities}}};\n\n"
        )
        file.write("#endif // RAW_TEST_20_H\n")


def save_reports(records, selected_indices, input_detail, output_detail):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = OUTPUT_DIR / "Python_Reference_20.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow([
            "test_index",
            "train_index",
            "file_name",
            "true_label",
            "python_output_raw_int8",
            "python_probability_non_asthma",
            "python_prediction",
            "python_correct"
        ])
        for test_index, record in enumerate(records):
            writer.writerow([
                test_index,
                record["train_index"],
                record["name"],
                record["label"],
                record["output_raw"],
                f'{record["probability"]:.9f}',
                record["prediction"],
                int(record["prediction"] == record["label"])
            ])

    np.savez_compressed(
        OUTPUT_DIR / "Python_Reference_20.npz",
        selected_train_indices=selected_indices,
        pcm=np.stack([record["pcm"] for record in records]),
        mel=np.stack([record["mel"] for record in records]),
        tensor_int8=np.stack([record["tensor"] for record in records]),
        true_labels=np.asarray([record["label"] for record in records]),
        output_raw_int8=np.asarray([record["output_raw"] for record in records]),
        probabilities=np.asarray([record["probability"] for record in records]),
        predictions=np.asarray([record["prediction"] for record in records]),
        input_scale=np.asarray(input_detail["quantization"][0]),
        input_zero_point=np.asarray(input_detail["quantization"][1]),
        output_scale=np.asarray(output_detail["quantization"][0]),
        output_zero_point=np.asarray(output_detail["quantization"][1])
    )


def main():
    required = [
        FEATURE_DIR / "X_train_mel.npy",
        FEATURE_DIR / "Y_train_mel.npy",
        FEATURE_DIR / "Files_train.npy",
        TRAIN_DIR / "Normalization_Params.txt",
        TFLITE_PATH
    ]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(f"Thiếu file: {path}")

    print("1. Đọc tập train đã tiền xử lý")
    x_train = np.load(FEATURE_DIR / "X_train_mel.npy", mmap_mode="r")
    y_train = np.load(FEATURE_DIR / "Y_train_mel.npy").astype(int)
    file_names = np.load(FEATURE_DIR / "Files_train.npy")
    train_min, train_max = load_normalization_params()

    selected_indices = choose_samples(file_names, y_train)
    interpreter, input_detail, output_detail = prepare_interpreter()

    print("2. Chạy model TFLite Python trên 20 mẫu")
    records = []
    for test_index, train_index in enumerate(selected_indices):
        relative_name = str(file_names[train_index])
        pcm = read_pcm16_if_compatible(DATASET_DIR / relative_name)
        if pcm is None:
            raise RuntimeError(f"WAV đã chọn không còn hợp lệ: {relative_name}")

        mel = np.asarray(x_train[train_index], dtype=np.float32)
        tensor = quantize_input(mel, train_min, train_max, input_detail)
        output_raw, probability, prediction = run_tflite(
            interpreter,
            input_detail,
            output_detail,
            tensor
        )
        label = int(y_train[train_index])

        record = {
            "train_index": int(train_index),
            "name": Path(relative_name).name,
            "label": label,
            "pcm": pcm,
            "mel": mel,
            "tensor": tensor,
            "output_raw": output_raw,
            "probability": probability,
            "prediction": prediction
        }
        records.append(record)

        status = "ĐÚNG" if prediction == label else "SAI NHÃN"
        print(
            f"  [{test_index:02d}] {record['name']} | nhãn={label} | "
            f"dự đoán={prediction} | p_non={probability:.6f} | {status}"
        )

    print("3. Xuất header và kết quả tham chiếu")
    write_header(records)
    save_reports(records, selected_indices, input_detail, output_detail)

    correct = sum(record["prediction"] == record["label"] for record in records)
    print(f"\nPython đúng nhãn: {correct}/{len(records)}")
    print(f"Header ESP32: {HEADER_PATH}")
    print(f"Báo cáo: {OUTPUT_DIR / 'Python_Reference_20.csv'}")
    print("Lưu ý: mục tiêu chính là ESP32 khớp Python, không ép sửa pipeline nếu Python sai nhãn.")


if __name__ == "__main__":
    main()
