"""Chuẩn bị V3 HelloEdge PTQ INT8 cho Deploy_Model/1.

Script tái sử dụng 12 tensor input C4 đã có vì V3 PTQ INT8 dùng cùng:
- input shape: (1, 40, 129, 1);
- input quantization: scale=1/255, zero-point=-128.

Output Python tham chiếu được suy luận lại bằng chính V3_PTQ_INT8.tflite.
Nhờ đó dữ liệu đầu vào không đổi nhưng phép đối chiếu Python/ESP32 vẫn đúng
với model V3 mới.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

import numpy as np

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

import tensorflow as tf


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


SCRIPT_DIR = Path(__file__).resolve().parent
AI_DIR = SCRIPT_DIR.parent
WORKSPACE_DIR = AI_DIR.parent

MODEL_PATH = (
    AI_DIR
    / "Phase3_Quantization_Model"
    / "Output_Quantize_V3"
    / "models"
    / "V3_PTQ_INT8.tflite"
)
SOURCE_TENSOR_HEADER = (
    WORKSPACE_DIR
    / "Deploy_Model"
    / "1_Test_Model_Static_Profiling"
    / "include"
    / "combo_pre0_mel40_fft2048__V1__s44"
    / "QAT_INT8"
    / "Static_Test_Tensors.h"
)

OUTPUT_DIR = SCRIPT_DIR / "Output_Static_Test_Tensors" / "V3_HelloEdge" / "PTQ_INT8"
DEPLOY_DIR = (
    WORKSPACE_DIR
    / "Deploy_Model"
    / "1_Test_Model_Static_Profiling"
    / "include"
    / "V3_HelloEdge"
    / "PTQ_INT8"
)

EXPECTED_ELEMENTS = 40 * 129
EXPECTED_INPUT_QUANT = (0.003921568859368563, -128)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_source_tensors(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="strict")

    element_match = re.search(r"kStaticTensorElements\s*=\s*(\d+)", text)
    input_scale_match = re.search(r"kStaticInputScale\s*=\s*([0-9.eE+-]+)f", text)
    input_zero_match = re.search(r"kStaticInputZeroPoint\s*=\s*(-?\d+)", text)
    if not (element_match and input_scale_match and input_zero_match):
        raise ValueError("Header tensor nguồn thiếu metadata input")

    elements = int(element_match.group(1))
    input_scale = float(input_scale_match.group(1))
    input_zero = int(input_zero_match.group(1))
    if elements != EXPECTED_ELEMENTS:
        raise ValueError(f"Tensor nguồn có {elements} phần tử, cần {EXPECTED_ELEMENTS}")
    if not np.isclose(input_scale, EXPECTED_INPUT_QUANT[0], atol=1e-12):
        raise ValueError(f"Input scale tensor nguồn không khớp: {input_scale}")
    if input_zero != EXPECTED_INPUT_QUANT[1]:
        raise ValueError(f"Input zero-point tensor nguồn không khớp: {input_zero}")

    arrays: dict[str, np.ndarray] = {}
    array_pattern = re.compile(
        r"static const int8_t\s+(\w+)\[kStaticTensorElements\]\s*=\s*\{(.*?)\};",
        re.DOTALL,
    )
    for name, body in array_pattern.findall(text):
        values = np.fromstring(body.replace("\n", " "), sep=",", dtype=np.int16)
        if values.size != EXPECTED_ELEMENTS:
            raise ValueError(f"{name}: có {values.size} phần tử, cần {EXPECTED_ELEMENTS}")
        if np.any(values < -128) or np.any(values > 127):
            raise ValueError(f"{name}: dữ liệu nằm ngoài miền INT8")
        arrays[name] = values.astype(np.int8)

    row_pattern = re.compile(
        r'\{"([^"]+)",\s*(\d+),\s*-?\d+,\s*[-+0-9.eE]+f,\s*(\w+)\},'
    )
    rows = []
    for index, (source_name, label_text, tensor_name) in enumerate(
        row_pattern.findall(text), start=1
    ):
        if tensor_name not in arrays:
            raise ValueError(f"Không tìm thấy mảng {tensor_name}")
        rows.append(
            {
                "test_index": index,
                "source_file": source_name,
                "class_label": int(label_text),
                "tensor_name": tensor_name,
                "tensor": arrays[tensor_name],
            }
        )

    if len(rows) != 12 or len(arrays) != 12:
        raise ValueError(f"Cần đúng 12 tensor, đọc được rows={len(rows)}, arrays={len(arrays)}")
    return rows


def format_int8_array(values: np.ndarray, per_line: int = 16) -> str:
    flat = np.asarray(values, dtype=np.int8).reshape(-1)
    lines = []
    for start in range(0, flat.size, per_line):
        chunk = flat[start : start + per_line]
        lines.append("    " + ", ".join(f"{int(value):4d}" for value in chunk))
    return ",\n".join(lines)


def write_model_header(model_bytes: bytes, model_sha: str, path: Path) -> None:
    lines = [
        "#ifndef ASTHMA_MODEL_H",
        "#define ASTHMA_MODEL_H",
        "",
        "#include <stddef.h>",
        "#include <stdint.h>",
        "",
        "// V3 HelloEdge - PTQ full INT8.",
        f"// Source: {MODEL_PATH.relative_to(WORKSPACE_DIR).as_posix()}",
        f"// SHA-256: {model_sha}",
        "",
        "alignas(16) const unsigned char model_data[] = {",
    ]
    for start in range(0, len(model_bytes), 12):
        chunk = model_bytes[start : start + 12]
        lines.append("    " + ", ".join(f"0x{value:02x}" for value in chunk) + ",")
    lines.extend(
        [
            "};",
            f"const unsigned int model_data_len = {len(model_bytes)};",
            "",
            "#endif  // ASTHMA_MODEL_H",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_tensor_header(
    records: list[dict],
    input_detail: dict,
    output_detail: dict,
    model_sha: str,
    path: Path,
) -> None:
    input_scale, input_zero = input_detail["quantization"]
    output_scale, output_zero = output_detail["quantization"]
    lines = [
        "#ifndef STATIC_TEST_TENSORS_H",
        "#define STATIC_TEST_TENSORS_H",
        "",
        "#include <stddef.h>",
        "#include <stdint.h>",
        "",
        "// Tái sử dụng input C4; output Python được tính lại bằng V3 PTQ INT8.",
        "// Model: V3_HelloEdge / PTQ_INT8",
        f"// SHA-256: {model_sha}",
        "// Label: 0=Asthma, 1=Non-Asthma.",
        "",
        f"constexpr size_t kStaticTensorElements = {EXPECTED_ELEMENTS};",
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
                f'// [{record["test_index"]}] {record["class_name"]}: {record["source_file"]}',
                f'static const int8_t {record["tensor_name"]}[kStaticTensorElements] = {{',
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
        lines.append(
            f'    {{"{record["source_file"]}", {record["class_label"]}, '
            f'{record["expected_output_int8"]}, '
            f'{record["probability_non_asthma"]:.9f}f, '
            f'{record["tensor_name"]}}},'
        )
    lines.extend(["};", "", "#endif  // STATIC_TEST_TENSORS_H", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(MODEL_PATH)
    if not SOURCE_TENSOR_HEADER.is_file():
        raise FileNotFoundError(SOURCE_TENSOR_HEADER)

    model_bytes = MODEL_PATH.read_bytes()
    model_sha = sha256_bytes(model_bytes)
    records = parse_source_tensors(SOURCE_TENSOR_HEADER)

    interpreter = tf.lite.Interpreter(model_path=str(MODEL_PATH))
    interpreter.allocate_tensors()
    input_detail = interpreter.get_input_details()[0]
    output_detail = interpreter.get_output_details()[0]

    actual_shape = tuple(int(value) for value in input_detail["shape"])
    if actual_shape != (1, 40, 129, 1):
        raise ValueError(f"V3 input shape không khớp: {actual_shape}")
    if input_detail["dtype"] != np.int8 or output_detail["dtype"] != np.int8:
        raise TypeError("V3 PTQ phải có input/output INT8")
    input_scale, input_zero = input_detail["quantization"]
    if not np.isclose(input_scale, EXPECTED_INPUT_QUANT[0], atol=1e-12):
        raise ValueError(f"V3 input scale không khớp tensor nguồn: {input_scale}")
    if int(input_zero) != EXPECTED_INPUT_QUANT[1]:
        raise ValueError(f"V3 input zero-point không khớp: {input_zero}")

    output_scale, output_zero = output_detail["quantization"]
    for record in records:
        input_tensor = record["tensor"].reshape(1, 40, 129, 1)
        interpreter.set_tensor(input_detail["index"], input_tensor)
        interpreter.invoke()
        raw_output = int(interpreter.get_tensor(output_detail["index"]).reshape(-1)[0])
        probability = float(np.clip((raw_output - output_zero) * output_scale, 0.0, 1.0))
        predicted_label = int(probability >= 0.5)
        record.update(
            {
                "class_name": "Asthma" if record["class_label"] == 0 else "Non_Asthma",
                "expected_output_int8": raw_output,
                "probability_non_asthma": probability,
                "predicted_label": predicted_label,
                "prediction_correct": int(predicted_label == record["class_label"]),
            }
        )

    output_model_header = OUTPUT_DIR / "Asthma_Model.h"
    output_tensor_header = OUTPUT_DIR / "Static_Test_Tensors.h"
    output_manifest = OUTPUT_DIR / "Static_Test_Tensors_Manifest.csv"
    output_metadata = OUTPUT_DIR / "deployment_manifest.json"

    write_model_header(model_bytes, model_sha, output_model_header)
    write_tensor_header(records, input_detail, output_detail, model_sha, output_tensor_header)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with output_manifest.open("w", newline="", encoding="utf-8-sig") as file:
        columns = [
            "test_index", "source_file", "class_label", "class_name",
            "expected_output_int8", "probability_non_asthma",
            "predicted_label", "prediction_correct", "tensor_name",
        ]
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows({key: record[key] for key in columns} for record in records)

    metadata = {
        "model": "V3_HelloEdge",
        "method": "PTQ_INT8",
        "source_tflite": MODEL_PATH.relative_to(WORKSPACE_DIR).as_posix(),
        "source_tflite_size_bytes": len(model_bytes),
        "source_tflite_sha256": model_sha,
        "input_shape": list(actual_shape),
        "input_dtype": "int8",
        "input_scale": float(input_scale),
        "input_zero_point": int(input_zero),
        "output_dtype": "int8",
        "output_scale": float(output_scale),
        "output_zero_point": int(output_zero),
        "static_tensor_count": len(records),
        "static_tensor_source": SOURCE_TENSOR_HEADER.relative_to(WORKSPACE_DIR).as_posix(),
        "python_correct": sum(record["prediction_correct"] for record in records),
    }
    output_metadata.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    DEPLOY_DIR.mkdir(parents=True, exist_ok=True)
    for source in (output_model_header, output_tensor_header, output_manifest, output_metadata):
        shutil.copy2(source, DEPLOY_DIR / source.name)

    print("V3 HelloEdge PTQ INT8 đã sẵn sàng cho static profiling")
    print(f"Model SHA-256 : {model_sha}")
    print(f"Model size    : {len(model_bytes)} bytes")
    print(f"Input         : {actual_shape}, scale={input_scale}, zero={input_zero}")
    print(f"Output        : scale={output_scale}, zero={output_zero}")
    print(f"Python correct: {metadata['python_correct']}/{len(records)}")
    print(f"Deploy        : {DEPLOY_DIR}")


if __name__ == "__main__":
    main()
