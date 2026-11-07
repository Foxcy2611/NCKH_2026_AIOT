"""Sinh prediction reproducible cho thí nghiệm Classification Threshold.

Baseline bị khóa:
- Feature: Phase2/Output_Preprocess.
- Normalization: Output_Train_V1_SepConv2D_Flatten.
- Model: V1_PTQ_INT8.tflite.

Script không train, không preprocess lại WAV và không chọn threshold. Validation
được phép chạy trực tiếp. Test chỉ được mở sau khi final_threshold.json có trạng
thái FROZEN.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

import tensorflow as tf


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


LABEL_ASTHMA = 0
LABEL_NON_ASTHMA = 1
CLASS_NAMES = {
    LABEL_ASTHMA: "Asthma",
    LABEL_NON_ASTHMA: "Non_Asthma",
}
BINARY_THRESHOLD = 0.5

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parents[3]
AI_DIR = WORKSPACE_DIR / "AI_Training_Model"
PHASE2_DIR = AI_DIR / "Phase2_Preprocess_&_Traning"
FEATURE_DIR = PHASE2_DIR / "Output_Preprocess"
TRAIN_DIR = PHASE2_DIR / "Output_Train_V1_SepConv2D_Flatten"
NORMALIZATION_PATH = TRAIN_DIR / "Normalization_Params.txt"
MODEL_PATH = (
    AI_DIR
    / "Phase3_Quantization_Model"
    / "Output_Quantize_V1"
    / "models"
    / "V1_PTQ_INT8.tflite"
)
RESULTS_DIR = SCRIPT_DIR / "results"
FINAL_CONFIG_PATH = RESULTS_DIR / "final_threshold.json"

CSV_COLUMNS = [
    "split",
    "sample_index",
    "file_path",
    "file_name",
    "true_label",
    "true_class",
    "input_scale",
    "input_zero_point",
    "output_scale",
    "output_zero_point",
    "output_int8",
    "p_non_asthma",
    "p_asthma",
    "binary_pred_0_5",
    "binary_class_0_5",
    "binary_correct_0_5",
    "model_sha256",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_normalization_params(path: Path) -> tuple[float, float]:
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy normalization: {path}")

    params: dict[str, float] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        params[key.strip()] = float(value.strip())

    if "TRAIN_MIN" not in params or "TRAIN_MAX" not in params:
        raise ValueError("Normalization_Params.txt thiếu TRAIN_MIN/TRAIN_MAX")

    train_min = params["TRAIN_MIN"]
    train_max = params["TRAIN_MAX"]
    if not np.isfinite(train_min) or not np.isfinite(train_max):
        raise ValueError("TRAIN_MIN/TRAIN_MAX không hữu hạn")
    if train_max <= train_min:
        raise ValueError("TRAIN_MAX phải lớn hơn TRAIN_MIN")
    return train_min, train_max


def load_split(split: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    split = split.casefold()
    if split not in {"val", "test"}:
        raise ValueError("Threshold experiment chỉ cho phép split val hoặc test")

    paths = {
        "x": FEATURE_DIR / f"X_{split}_mel.npy",
        "y": FEATURE_DIR / f"Y_{split}_mel.npy",
        "files": FEATURE_DIR / f"Files_{split}.npy",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("Thiếu artifact preprocess:\n- " + "\n- ".join(missing))

    x_data = np.load(paths["x"])
    y_data = np.load(paths["y"])
    files_data = np.load(paths["files"], allow_pickle=False)

    if x_data.shape[1:] != (64, 129, 1):
        raise ValueError(f"Sai input shape {split}: {x_data.shape}")
    if not (len(x_data) == len(y_data) == len(files_data)):
        raise ValueError(
            f"X/Y/Files không cùng số mẫu: {len(x_data)}/{len(y_data)}/{len(files_data)}"
        )
    if not set(np.unique(y_data)).issubset({LABEL_ASTHMA, LABEL_NON_ASTHMA}):
        raise ValueError(f"Split {split} có nhãn ngoài 0/1")
    if not np.isfinite(x_data).all():
        raise ValueError(f"X_{split} có NaN hoặc Inf")
    return x_data, y_data.astype(np.int64), files_data.astype(str)


def require_frozen_config(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(
            "Không được mở Test trước khi freeze threshold. Thiếu file: " + str(path)
        )
    config = json.loads(path.read_text(encoding="utf-8"))
    if str(config.get("status", "")).upper() != "FROZEN":
        raise ValueError("final_threshold.json phải có status=FROZEN trước khi chạy Test")
    if "low_threshold" not in config or "high_threshold" not in config:
        raise ValueError("final_threshold.json thiếu low_threshold/high_threshold")
    return config


def create_interpreter(model_path: Path):
    if not model_path.is_file():
        raise FileNotFoundError(f"Không tìm thấy V1 PTQ INT8: {model_path}")

    interpreter = tf.lite.Interpreter(model_path=str(model_path))
    interpreter.allocate_tensors()
    input_detail = interpreter.get_input_details()[0]
    output_detail = interpreter.get_output_details()[0]

    if input_detail["dtype"] != np.int8 or output_detail["dtype"] != np.int8:
        raise TypeError(
            "Baseline phải là Full INT8, "
            f"nhưng input={input_detail['dtype']}, output={output_detail['dtype']}"
        )
    if tuple(int(v) for v in input_detail["shape"]) != (1, 64, 129, 1):
        raise ValueError(f"Model input shape không phải [1,64,129,1]: {input_detail['shape']}")

    input_scale, input_zero = input_detail["quantization"]
    output_scale, output_zero = output_detail["quantization"]
    if input_scale <= 0.0 or output_scale <= 0.0:
        raise ValueError("Scale quantization của model không hợp lệ")
    return interpreter, input_detail, output_detail


def quantize_input(
    mel_db: np.ndarray,
    train_min: float,
    train_max: float,
    input_scale: float,
    input_zero_point: int,
) -> np.ndarray:
    normalized = np.clip(
        (mel_db.astype(np.float32) - train_min) / (train_max - train_min),
        0.0,
        1.0,
    )
    quantized = np.rint(normalized / input_scale + input_zero_point)
    return np.clip(quantized, -128, 127).astype(np.int8)


def dequantize_output(raw: int, output_scale: float, output_zero_point: int) -> float:
    probability = (raw - output_zero_point) * output_scale
    return float(np.clip(probability, 0.0, 1.0))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def generate_predictions(
    split: str = "val",
    output_path: Path | None = None,
    final_config_path: Path = FINAL_CONFIG_PATH,
) -> Path:
    split = split.casefold()
    if split == "test":
        require_frozen_config(final_config_path)

    x_data, y_data, files_data = load_split(split)
    train_min, train_max = read_normalization_params(NORMALIZATION_PATH)
    interpreter, input_detail, output_detail = create_interpreter(MODEL_PATH)

    input_scale, input_zero = input_detail["quantization"]
    output_scale, output_zero = output_detail["quantization"]
    model_hash = sha256_file(MODEL_PATH)
    rows: list[dict] = []

    for index, (mel_db, true_label, file_path) in enumerate(
        zip(x_data, y_data, files_data, strict=True)
    ):
        quantized = quantize_input(
            mel_db,
            train_min,
            train_max,
            float(input_scale),
            int(input_zero),
        )
        interpreter.set_tensor(input_detail["index"], quantized[np.newaxis, ...])
        interpreter.invoke()

        raw = int(interpreter.get_tensor(output_detail["index"]).reshape(-1)[0])
        p_non = dequantize_output(raw, float(output_scale), int(output_zero))
        binary_pred = int(p_non >= BINARY_THRESHOLD)
        true_label = int(true_label)

        rows.append(
            {
                "split": split,
                "sample_index": index,
                "file_path": str(file_path).replace("\\", "/"),
                "file_name": Path(file_path).name,
                "true_label": true_label,
                "true_class": CLASS_NAMES[true_label],
                "input_scale": f"{float(input_scale):.12g}",
                "input_zero_point": int(input_zero),
                "output_scale": f"{float(output_scale):.12g}",
                "output_zero_point": int(output_zero),
                "output_int8": raw,
                "p_non_asthma": f"{p_non:.9f}",
                "p_asthma": f"{1.0 - p_non:.9f}",
                "binary_pred_0_5": binary_pred,
                "binary_class_0_5": CLASS_NAMES[binary_pred],
                "binary_correct_0_5": int(binary_pred == true_label),
                "model_sha256": model_hash,
            }
        )

    if output_path is None:
        name = "validation_predictions.csv" if split == "val" else "test_predictions.csv"
        output_path = RESULTS_DIR / name
    output_path = Path(output_path)
    write_csv(output_path, rows)

    metadata = {
        "split": split,
        "sample_count": len(rows),
        "asthma_count": int(np.sum(y_data == LABEL_ASTHMA)),
        "non_asthma_count": int(np.sum(y_data == LABEL_NON_ASTHMA)),
        "model": "V1_PTQ_INT8",
        "model_path": str(MODEL_PATH.relative_to(WORKSPACE_DIR)).replace("\\", "/"),
        "model_sha256": model_hash,
        "normalization_path": str(NORMALIZATION_PATH.relative_to(WORKSPACE_DIR)).replace(
            "\\", "/"
        ),
        "train_min": train_min,
        "train_max": train_max,
        "input_scale": float(input_scale),
        "input_zero_point": int(input_zero),
        "output_scale": float(output_scale),
        "output_zero_point": int(output_zero),
        "binary_threshold": BINARY_THRESHOLD,
        "prediction_csv": output_path.name,
    }
    metadata_path = output_path.with_name(output_path.stem + "_metadata.json")
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Đã tạo {len(rows)} prediction cho split={split}: {output_path}")
    print(f"Metadata: {metadata_path}")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sinh prediction bằng baseline V1 PTQ Full INT8."
    )
    parser.add_argument(
        "--split",
        choices=("val", "test"),
        default="val",
        help="Mặc định chỉ chạy Validation. Test yêu cầu final_threshold.json FROZEN.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Đường dẫn CSV tùy chọn.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_predictions(args.split, args.output)


if __name__ == "__main__":
    main()
