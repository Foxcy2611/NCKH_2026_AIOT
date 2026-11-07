"""
===============================================================================
Tên script: Generate_Static_Test_Tensors.py

Mục đích:
- Bốc cố định theo seed 6 WAV Asthma + 6 WAV Non-Asthma từ tập Test.
- Sinh tensor riêng cho ba model được chốt tại D13.2.
- Đọc cấu hình frontend, normalization và I/O quantization từ artifact D.
- Chạy đúng frontend Python đã dùng khi train từng model.
- Sinh C++ header và manifest cho project profiling tĩnh trên ESP32-S3.

Script không train, không sửa WAV và không thay đổi các file .npy.
===============================================================================
"""

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
# Tránh Numba bị kẹt khi cố tạo cache bên trong thư mục site-packages trên
# Windows. Cache tạm này chỉ hỗ trợ tốc độ import/librosa, không phải artifact.
os.environ.setdefault(
    "NUMBA_CACHE_DIR",
    str(Path(tempfile.gettempdir()) / "nckh_numba_cache"),
)

import tensorflow as tf


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# =============================================================================
# CẤU HÌNH
# =============================================================================

RANDOM_SEED = 42
SAMPLES_PER_CLASS = 6

LABEL_ASTHMA = 0
LABEL_NON_ASTHMA = 1
CLASS_NAMES = {
    LABEL_ASTHMA: "Asthma",
    LABEL_NON_ASTHMA: "Non_Asthma",
}


SCRIPT_DIR = Path(__file__).resolve().parent
AI_DIR = SCRIPT_DIR.parent
WORKSPACE_DIR = AI_DIR.parent

FRONTEND_DIR = (
    WORKSPACE_DIR
    / "Experiments_Benchmarking"
    / "Patient_Node"
    / "Frontend_Benchmarking"
)
FRONTEND_CORE_PATH = FRONTEND_DIR / "frontend_core.py"
D_QUANTIZATION_DIR = FRONTEND_DIR / "artifacts" / "D_Quantization"
D_DEPLOYMENT_DIR = FRONTEND_DIR / "artifacts" / "D_Deployment"

# Shortlist phần D13.2. Khóa chỉ dùng để gọi CLI; trial/method là nguồn thật.
TARGETS = {
    "C4_QAT_INT8": {
        "trial_id": "combo_pre0_mel40_fft2048__V1__s44",
        "method_id": "QAT_INT8",
    },
    "F0_PTQ_INT8": {
        "trial_id": "F0__V1__s43",
        "method_id": "PTQ_INT8",
    },
    "C3_QAT_INT8": {
        "trial_id": "combo_mel40_fft2048__V1__s44",
        "method_id": "QAT_INT8",
    },
}

DATASET_DIR = AI_DIR / "Dataset_Chia_V2"
ASTHMA_TEST_DIR = DATASET_DIR / "Asthma" / "test"
NON_ASTHMA_TEST_DIR = DATASET_DIR / "Non_Asthma_Disease" / "test"

DEPLOY_INCLUDE_DIR = ( # Ném luôn header tạo đc vào 1_Test_Static
    WORKSPACE_DIR
    / "Deploy_Model"
    / "1_Test_Model_Static_Profiling"
    / "include"
)
OUTPUT_DIR = SCRIPT_DIR / "Output_Static_Test_Tensors"

# Hai file phẳng cũ vẫn được cập nhật bằng F0 để không phá luồng cũ.
LEGACY_HEADER_PATH = DEPLOY_INCLUDE_DIR / "Static_Test_Tensors.h"
LEGACY_MANIFEST_PATH = OUTPUT_DIR / "Static_Test_Tensors_Manifest.csv"


MANIFEST_COLUMNS = [
    "test_index",
    "class_label",
    "class_name",
    "source_file",
    "source_relative_path",
    "tensor_name",
    "tensor_elements",
    "input_scale",
    "input_zero_point",
    "expected_output_int8",
    "probability_non_asthma",
    "predicted_label",
    "predicted_class",
    "prediction_correct",
    "model_version",
    "model_variant",
    "model_path",
    "model_sha256",
]


def load_module(module_name, module_path):
    """Import module từ đường dẫn có ký tự '&' mà không sửa sys.path toàn cục."""
    if not module_path.is_file():
        raise FileNotFoundError(f"Không tìm thấy module: {module_path}")

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Không thể tạo import spec: {module_path}")

    module = importlib.util.module_from_spec(spec)
    # dataclasses và một số decorator tra cứu module qua sys.modules trong
    # lúc exec; cần đăng ký trước khi chạy module được import động.
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def read_selected_model_metadata(path):
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy metadata model: {path}")

    metadata = json.loads(path.read_text(encoding="utf-8"))
    normalization = metadata.get("normalization", {})
    train_min = float(normalization.get("train_min"))
    train_max = float(normalization.get("train_max"))
    if train_max <= train_min:
        raise ValueError("train_min/train_max trong metadata không hợp lệ")
    return metadata, train_min, train_max


def resolve_target(target_key):
    """Phân giải toàn bộ nguồn/đích của một model trong shortlist D13.2."""
    spec = TARGETS[target_key]
    trial_id = spec["trial_id"]
    method_id = spec["method_id"]
    method_dir = D_QUANTIZATION_DIR / trial_id / "methods" / method_id
    deployment_dir = D_DEPLOYMENT_DIR / trial_id / method_id
    output_dir = OUTPUT_DIR / trial_id / method_id
    deploy_include_dir = DEPLOY_INCLUDE_DIR / trial_id / method_id

    target = {
        "key": target_key,
        "trial_id": trial_id,
        "method_id": method_id,
        "model_path": method_dir / f"{method_id}.tflite",
        "metadata_path": method_dir / "conversion_metadata.json",
        "deployment_manifest_path": deployment_dir / "deployment_manifest.json",
        "deployment_model_header_path": deployment_dir / "Asthma_Model.h",
        "output_header_path": output_dir / "Static_Test_Tensors.h",
        "output_manifest_path": output_dir / "Static_Test_Tensors_Manifest.csv",
        "deploy_tensor_header_path": deploy_include_dir / "Static_Test_Tensors.h",
        "deploy_model_header_path": deploy_include_dir / "Asthma_Model.h",
    }

    required = (
        "model_path",
        "metadata_path",
        "deployment_manifest_path",
        "deployment_model_header_path",
        "deploy_model_header_path",
    )
    missing = [str(target[name]) for name in required if not target[name].is_file()]
    if missing:
        raise FileNotFoundError(
            f"Thiếu artifact cho {target_key}:\n- " + "\n- ".join(missing)
        )
    return target


def choose_files(folder, amount, rng):
    files = sorted(folder.glob("*.wav"), key=lambda path: path.name.casefold())
    if len(files) < amount:
        raise ValueError(
            f"{folder} chỉ có {len(files)} WAV, không đủ bốc {amount} mẫu"
        )

    indices = rng.choice(len(files), size=amount, replace=False)
    return sorted((files[int(index)] for index in indices), key=lambda p: p.name)


def normalize_mel(mel_db, train_min, train_max):
    return (
        (mel_db.astype(np.float32) - train_min)
        / (train_max - train_min)
    ).astype(np.float32)


def quantize_tensor(float_tensor, dtype, scale, zero_point):
    if scale <= 0:
        raise ValueError(f"Input quantization scale không hợp lệ: {scale}")

    quantized = np.round(float_tensor / scale + zero_point)
    limits = np.iinfo(dtype)
    return np.clip(quantized, limits.min, limits.max).astype(dtype)


def dequantize_scalar(value, scale, zero_point):
    return float((float(value) - zero_point) * scale)


def safe_identifier(text):
    identifier = re.sub(r"[^A-Za-z0-9_]", "_", text)
    if not identifier or identifier[0].isdigit():
        identifier = f"tensor_{identifier}"
    return identifier.lower()


def portable_path(path):
    """Ưu tiên lưu đường dẫn tương đối workspace để artifact dùng được máy khác."""
    path = Path(path).resolve()
    try:
        return path.relative_to(WORKSPACE_DIR).as_posix()
    except ValueError:
        return path.as_posix()


def format_int8_array(values, values_per_line=16):
    flat = np.asarray(values, dtype=np.int8).reshape(-1)
    lines = []
    for start in range(0, flat.size, values_per_line):
        chunk = flat[start : start + values_per_line]
        lines.append("    " + ", ".join(f"{int(value):4d}" for value in chunk))
    return ",\n".join(lines)


def write_header(
    records,
    input_detail,
    output_detail,
    model_version,
    model_variant,
    model_path,
    model_sha256,
    header_path,
):
    input_scale, input_zero = input_detail["quantization"]
    output_scale, output_zero = output_detail["quantization"]
    tensor_elements = int(np.prod(input_detail["shape"][1:]))

    lines = [
        "#ifndef STATIC_TEST_TENSORS_H",
        "#define STATIC_TEST_TENSORS_H",
        "",
        "#include <stddef.h>",
        "#include <stdint.h>",
        "",
        "// Tự động sinh bởi Generate_Static_Test_Tensors.py.",
        f"// Model: {model_version} / {model_variant}",
        f"// Source: {portable_path(model_path)}",
        f"// SHA-256: {model_sha256}",
        "// Label: 0=Asthma, 1=Non-Asthma.",
        "",
        f"constexpr size_t kStaticTensorElements = {tensor_elements};",
        f"constexpr size_t kStaticTestTensorCount = {len(records)};",
        f"constexpr float kStaticInputScale = {float(input_scale):.12g}f;",
        f"constexpr int kStaticInputZeroPoint = {int(input_zero)};",
        f"constexpr float kStaticOutputScale = {float(output_scale):.12g}f;",
        f"constexpr int kStaticOutputZeroPoint = {int(output_zero)};",
        "",
    ]

    for record in records:
        lines.extend(
            [
                f'// [{record["test_index"]}] {record["class_name"]}: '
                f'{record["source_relative_path"]}',
                f'static const int8_t {record["tensor_name"]}'
                f'[kStaticTensorElements] = {{',
                format_int8_array(record["tensor"]),
                "};",
                "",
            ]
        )

    lines.extend(
        [
            "struct StaticTestTensor {",
            "    const char* source_name;",
            "    uint8_t expected_label;",
            "    int8_t expected_output_int8;",
            "    float expected_probability_non_asthma;",
            "    const int8_t* data;",
            "};",
            "",
            "static const StaticTestTensor kStaticTestTensors[] = {",
        ]
    )

    for record in records:
        source_name = record["source_file"].replace("\\", "\\\\").replace('"', '\\"')
        lines.append(
            "    {"
            f'"{source_name}", '
            f'{record["class_label"]}, '
            f'{record["expected_output_int8"]}, '
            f'{record["probability_non_asthma"]:.9f}f, '
            f'{record["tensor_name"]}'
            "},"
        )

    lines.extend(
        [
            "};",
            "",
            "#endif  // STATIC_TEST_TENSORS_H",
            "",
        ]
    )

    header_path.parent.mkdir(parents=True, exist_ok=True)
    header_path.write_text("\n".join(lines), encoding="utf-8")


def write_manifest(
    records,
    model_version,
    model_variant,
    model_path,
    model_sha256,
    input_detail,
    manifest_path,
):
    input_scale, input_zero = input_detail["quantization"]
    rows = []
    for record in records:
        rows.append(
            {
                "test_index": record["test_index"],
                "class_label": record["class_label"],
                "class_name": record["class_name"],
                "source_file": record["source_file"],
                "source_relative_path": record["source_relative_path"],
                "tensor_name": record["tensor_name"],
                "tensor_elements": record["tensor"].size,
                "input_scale": float(input_scale),
                "input_zero_point": int(input_zero),
                "expected_output_int8": record["expected_output_int8"],
                "probability_non_asthma": record["probability_non_asthma"],
                "predicted_label": record["predicted_label"],
                "predicted_class": record["predicted_class"],
                "prediction_correct": int(record["prediction_correct"]),
                "model_version": model_version,
                "model_variant": model_variant,
                "model_path": portable_path(model_path),
                "model_sha256": model_sha256,
            }
        )

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def verify_deploy_model_header(model_bytes, deploy_model_header_path):
    """Đối chiếu binary nhúng trong Asthma_Model.h với TFLite đang chọn."""
    if not deploy_model_header_path.is_file():
        return False, "Chưa có Asthma_Model.h trong project static"

    text = deploy_model_header_path.read_text(encoding="utf-8", errors="ignore")
    byte_tokens = re.findall(r"0x([0-9A-Fa-f]{2})", text)
    if not byte_tokens:
        return False, "Asthma_Model.h không chứa mảng byte dạng 0xNN"

    embedded_bytes = bytes(int(token, 16) for token in byte_tokens)
    if embedded_bytes == model_bytes:
        return True, "Asthma_Model.h trùng tuyệt đối với TFLite đã chọn"

    embedded_hash = hashlib.sha256(embedded_bytes).hexdigest()
    selected_hash = hashlib.sha256(model_bytes).hexdigest()
    return (
        False,
        "Asthma_Model.h KHÔNG khớp TFLite đã chọn\n"
        f"  Deploy header: {len(embedded_bytes)} bytes | {embedded_hash}\n"
        f"  TFLite chọn : {len(model_bytes)} bytes | {selected_hash}",
    )


def generate_target(target_key, selected, frontend):
    target = resolve_target(target_key)
    model_path = target["model_path"].resolve()
    model_bytes = model_path.read_bytes()
    model_sha256 = hashlib.sha256(model_bytes).hexdigest()
    metadata, train_min, train_max = read_selected_model_metadata(
        target["metadata_path"]
    )
    if metadata.get("tflite_sha256") != model_sha256:
        raise RuntimeError("SHA-256 model không khớp conversion_metadata.json")

    deployment_manifest = json.loads(
        target["deployment_manifest_path"].read_text(encoding="utf-8")
    )
    if deployment_manifest.get("source_tflite_sha256") != model_sha256:
        raise RuntimeError("SHA-256 model không khớp deployment_manifest.json")
    if deployment_manifest.get("trial_id") != target["trial_id"]:
        raise RuntimeError("trial_id trong deployment manifest không khớp target")
    if deployment_manifest.get("method_id") != target["method_id"]:
        raise RuntimeError("method_id trong deployment manifest không khớp target")

    frontend_values = deployment_manifest.get("frontend_config", {})
    missing_frontend = [key for key in frontend.CONFIG_KEYS if key not in frontend_values]
    if missing_frontend:
        raise ValueError(
            "Deployment manifest thiếu frontend_config: "
            + ", ".join(missing_frontend)
        )
    frontend_config = frontend.Frontend(
        **{key: frontend_values[key] for key in frontend.CONFIG_KEYS}
    )
    frontend.validate(frontend_config)

    interpreter = tf.lite.Interpreter(model_path=str(model_path))
    interpreter.allocate_tensors()
    input_detail = interpreter.get_input_details()[0]
    output_detail = interpreter.get_output_details()[0]

    if input_detail["dtype"] != np.int8:
        raise TypeError(
            f"Model phải có input INT8, hiện tại là {input_detail['dtype']}"
        )
    if output_detail["dtype"] != np.int8:
        raise TypeError(
            f"Model phải có output INT8, hiện tại là {output_detail['dtype']}"
        )

    expected_shape = (
        1,
        frontend_config.n_mels,
        1 + frontend.SAMPLES // frontend_config.hop_length,
        1,
    )
    actual_shape = tuple(int(value) for value in input_detail["shape"])
    if actual_shape != expected_shape:
        raise ValueError(
            f"Input shape TFLite {actual_shape} không khớp frontend {expected_shape}"
        )

    input_scale, input_zero = input_detail["quantization"]
    output_scale, output_zero = output_detail["quantization"]
    records = []

    print("=" * 64)
    print(f"Target      : {target_key}")
    print(f"Trial/method: {target['trial_id']} / {target['method_id']}")
    print(f"Model       : {model_path}")
    print(f"Frontend    : {frontend_config}")
    print(f"Normalization: [{train_min}, {train_max}]")
    print(f"Input INT8  : scale={input_scale}, zero={input_zero}")
    print(f"Output INT8 : scale={output_scale}, zero={output_zero}")
    print("=" * 64)

    for index, (wav_path, label) in enumerate(selected, start=1):
        audio = frontend.load_raw_window(wav_path)
        filtered = frontend.process_wave(audio, frontend_config)
        mel_db = frontend.mel_from_wave(filtered, frontend_config)
        normalized = normalize_mel(mel_db, train_min, train_max)
        float_input = normalized[np.newaxis, ..., np.newaxis]
        quantized_input = quantize_tensor(
            float_input,
            input_detail["dtype"],
            float(input_scale),
            int(input_zero),
        )

        interpreter.set_tensor(input_detail["index"], quantized_input)
        interpreter.invoke()
        raw_output = interpreter.get_tensor(output_detail["index"]).reshape(-1)
        output_int8 = int(raw_output[0])
        probability = dequantize_scalar(
            output_int8,
            float(output_scale),
            int(output_zero),
        )
        probability = float(np.clip(probability, 0.0, 1.0))
        predicted_label = int(probability >= 0.5)

        class_token = "asthma" if label == LABEL_ASTHMA else "non_asthma"
        tensor_name = safe_identifier(f"static_{class_token}_{index:02d}")
        relative_path = wav_path.relative_to(DATASET_DIR).as_posix()

        records.append(
            {
                "test_index": index,
                "class_label": label,
                "class_name": CLASS_NAMES[label],
                "source_file": wav_path.name,
                "source_relative_path": relative_path,
                "tensor_name": tensor_name,
                "tensor": quantized_input.reshape(-1),
                "expected_output_int8": output_int8,
                "probability_non_asthma": probability,
                "predicted_label": predicted_label,
                "predicted_class": CLASS_NAMES[predicted_label],
                "prediction_correct": predicted_label == label,
            }
        )

        result = "ĐÚNG" if predicted_label == label else "SAI"
        print(
            f"[{index:02d}/12] {CLASS_NAMES[label]:<11} | "
            f"p_non={probability:.6f} | {result} | {wav_path.name}"
        )

    write_header(
        records,
        input_detail,
        output_detail,
        target["trial_id"],
        target["method_id"],
        model_path,
        model_sha256,
        target["output_header_path"],
    )
    write_manifest(
        records,
        target["trial_id"],
        target["method_id"],
        model_path,
        model_sha256,
        input_detail,
        target["output_manifest_path"],
    )

    target["deploy_tensor_header_path"].parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        target["output_header_path"],
        target["deploy_tensor_header_path"],
    )

    # Duy trì đường dẫn cũ cho benchmark F0 hiện có.
    if target_key == "F0_PTQ_INT8":
        LEGACY_HEADER_PATH.parent.mkdir(parents=True, exist_ok=True)
        LEGACY_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target["output_header_path"], LEGACY_HEADER_PATH)
        shutil.copy2(target["output_manifest_path"], LEGACY_MANIFEST_PATH)

    deploy_model_matches, deploy_model_message = verify_deploy_model_header(
        model_bytes,
        target["deploy_model_header_path"],
    )

    correct = sum(int(record["prediction_correct"]) for record in records)
    print("\n" + "=" * 64)
    print(f"Đã tạo {len(records)} tensor, model đúng nhãn: {correct}/{len(records)}")
    print(f"Header  : {target['output_header_path']}")
    print(f"Manifest: {target['output_manifest_path']}")
    print(f"Deploy  : {target['deploy_tensor_header_path']}")
    if deploy_model_matches:
        print(f"Model   : OK - {deploy_model_message}")
    else:
        print(f"Model   : CẢNH BÁO - {deploy_model_message}")
    print("=" * 64)


def main():
    parser = argparse.ArgumentParser(
        description="Sinh static INT8 tensors cho shortlist D13.2."
    )
    parser.add_argument(
        "--target",
        action="append",
        choices=tuple(TARGETS),
        help=(
            "Target cần sinh; có thể truyền nhiều lần. "
            "Mặc định sinh cả C4, F0 và C3."
        ),
    )
    args = parser.parse_args()

    frontend = load_module("frontend_core_phase4", FRONTEND_CORE_PATH)
    rng = np.random.default_rng(RANDOM_SEED)
    selected = [
        *((path, LABEL_ASTHMA) for path in choose_files(
            ASTHMA_TEST_DIR, SAMPLES_PER_CLASS, rng
        )),
        *((path, LABEL_NON_ASTHMA) for path in choose_files(
            NON_ASTHMA_TEST_DIR, SAMPLES_PER_CLASS, rng
        )),
    ]

    targets = args.target or list(TARGETS)
    for target_key in targets:
        generate_target(target_key, selected, frontend)


if __name__ == "__main__":
    main()
