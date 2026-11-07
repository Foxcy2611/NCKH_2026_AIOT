"""
===============================================================================
Tên script: Analyze_Model_Errors.py

Tác dụng:
- Không huấn luyện lại mô hình.
- Nạp Model_Asthma.keras cùng X/Y/Files của Validation và Test.
- Chuẩn hóa bằng đúng TRAIN_MIN/TRAIN_MAX đã dùng khi huấn luyện.
- Xuất toàn bộ dự đoán và tách riêng các mẫu dự đoán sai.
- Thống kê lỗi theo Core, Playback, Environment và từng bệnh/nhóm môi trường.

Quy ước:
- Nhãn 0 = Asthma, nhãn 1 = Non-Asthma.
- Đầu ra sigmoid là xác suất Non-Asthma.
- ASTHMA_FN: Asthma thật nhưng bị dự đoán thành Non-Asthma.
- NON_ASTHMA_FP: Non-Asthma thật nhưng bị báo nhầm thành Asthma.

Chạy từ bất kỳ thư mục nào:
    python AI_Training_Model/Phase2_Preprocess_&_Traning/Analyze_Model_Errors.py
===============================================================================
"""

import csv
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path, PurePath

os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import numpy as np
from keras import models


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


THRESHOLD = 0.5
LABEL_ASTHMA = 0
LABEL_NON_ASTHMA = 1

SCRIPT_DIR = Path(__file__).resolve().parent
ANALYSIS_ROOT = SCRIPT_DIR / "Output_Analysis_V1"
PREPROCESS_DIR = SCRIPT_DIR / "Output_Preprocess"
TRAIN_DIR = SCRIPT_DIR / "Output_Train_V1_SepConv2D_Flatten"
MODEL_PATH = TRAIN_DIR / "Model_Asthma.keras"
NORMALIZATION_PATH = TRAIN_DIR / "Normalization_Params.txt"
OUTPUT_DIR = ANALYSIS_ROOT / "Output_Analysis_Accu8931"

PREDICTION_COLUMNS = [
    "split",
    "sample_index",
    "file_path",
    "file_name",
    "source_type",
    "data_group",
    "subtype",
    "group_id",
    "true_label",
    "true_class",
    "predicted_label",
    "predicted_class",
    "probability_asthma",
    "probability_non_asthma",
    "predicted_confidence",
    "distance_from_threshold",
    "inside_device_unsure_band_045_065",
    "is_correct",
    "error_type",
]


def read_normalization_params():
    if not NORMALIZATION_PATH.is_file():
        raise FileNotFoundError(
            f"Không tìm thấy tham số chuẩn hóa: {NORMALIZATION_PATH}"
        )

    values = {}
    for line in NORMALIZATION_PATH.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = float(value.strip())

    if "TRAIN_MIN" not in values or "TRAIN_MAX" not in values:
        raise ValueError("Normalization_Params.txt thiếu TRAIN_MIN/TRAIN_MAX.")

    train_min = values["TRAIN_MIN"]
    train_max = values["TRAIN_MAX"]
    if train_max <= train_min:
        raise ValueError("TRAIN_MIN/TRAIN_MAX không hợp lệ.")
    return train_min, train_max


def load_split(split):
    paths = {
        "x": PREPROCESS_DIR / f"X_{split}_mel.npy",
        "y": PREPROCESS_DIR / f"Y_{split}_mel.npy",
        "files": PREPROCESS_DIR / f"Files_{split}.npy",
    }
    for name, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"Thiếu {name} của tập {split}: {path}")

    x_data = np.load(paths["x"])
    y_data = np.load(paths["y"]).astype(np.int64)
    files_data = np.load(paths["files"]).astype(str)

    if not (len(x_data) == len(y_data) == len(files_data)):
        raise ValueError(
            f"Tập {split} lệch số lượng: "
            f"X={len(x_data)}, Y={len(y_data)}, Files={len(files_data)}"
        )
    if x_data.shape[1:] != (64, 129, 1):
        raise ValueError(f"X_{split} sai kích thước: {x_data.shape}")
    if not set(np.unique(y_data)).issubset({0, 1}):
        raise ValueError(f"Y_{split} có nhãn ngoài 0 và 1.")
    if not np.isfinite(x_data).all():
        raise ValueError(f"X_{split} có NaN hoặc Inf.")
    return x_data, y_data, files_data


def class_name(label):
    return "Asthma" if int(label) == LABEL_ASTHMA else "Non_Asthma"


def get_file_name(file_path):
    # PurePath trên Windows hiện tại không tách được dấu gạch chéo ngược khi
    # script được chạy ở hệ điều hành khác, nên chuẩn hóa trước.
    normalized = str(file_path).replace("\\", "/")
    return PurePath(normalized).name


def infer_metadata(file_path, true_label):
    file_name = get_file_name(file_path)
    stem = Path(file_name).stem
    lower = stem.lower()

    patient_match = re.search(r"P\d+", stem, flags=re.IGNORECASE)
    patient_id = patient_match.group(0).upper() if patient_match else ""

    if stem.startswith("ENV__"):
        parts = stem.split("__")
        subtype = parts[1] if len(parts) > 1 else "environment"
        group_id = parts[2] if len(parts) > 2 else ""
        return "Environment", f"Environment_{subtype}", subtype, group_id

    is_playback = "__take" in lower
    source_type = "Playback" if is_playback else "Core"

    if int(true_label) == LABEL_ASTHMA:
        subtype = "asthma"
    elif "bronchial" in lower or stem.startswith("BRO_"):
        subtype = "bronchial"
    elif "copd" in lower or stem.startswith("COPD_"):
        subtype = "copd"
    elif "healthy" in lower or stem.startswith("HEA_"):
        subtype = "healthy"
    elif "pneumonia" in lower or stem.startswith("PNE_"):
        subtype = "pneumonia"
    else:
        subtype = "non_asthma_other"

    data_group = f"{subtype}_{source_type.lower()}"
    return source_type, data_group, subtype, patient_id


def get_error_type(true_label, predicted_label):
    if int(true_label) == int(predicted_label):
        return ""
    if int(true_label) == LABEL_ASTHMA:
        return "ASTHMA_FN"
    return "NON_ASTHMA_FP"


def make_prediction_rows(split, y_true, files_data, probabilities):
    rows = []

    for index, (true_label, file_path, probability_non) in enumerate(
        zip(y_true, files_data, probabilities)
    ):
        predicted_label = int(probability_non >= THRESHOLD)
        probability_asthma = 1.0 - float(probability_non)
        predicted_confidence = (
            probability_asthma
            if predicted_label == LABEL_ASTHMA
            else float(probability_non)
        )
        source_type, data_group, subtype, group_id = infer_metadata(
            file_path, true_label
        )
        error_type = get_error_type(true_label, predicted_label)

        rows.append(
            {
                "split": split,
                "sample_index": index,
                "file_path": str(file_path),
                "file_name": get_file_name(file_path),
                "source_type": source_type,
                "data_group": data_group,
                "subtype": subtype,
                "group_id": group_id,
                "true_label": int(true_label),
                "true_class": class_name(true_label),
                "predicted_label": predicted_label,
                "predicted_class": class_name(predicted_label),
                "probability_asthma": f"{probability_asthma:.9f}",
                "probability_non_asthma": f"{float(probability_non):.9f}",
                "predicted_confidence": f"{predicted_confidence:.9f}",
                "distance_from_threshold": f"{abs(float(probability_non) - THRESHOLD):.9f}",
                "inside_device_unsure_band_045_065": int(
                    0.45 < float(probability_non) < 0.65
                ),
                "is_correct": int(not error_type),
                "error_type": error_type,
            }
        )
    return rows


def write_csv(path, rows, columns):
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def create_group_summary(all_rows):
    grouped = defaultdict(list)
    for row in all_rows:
        grouped[(row["split"], row["data_group"])].append(row)

    summary_rows = []
    for (split, data_group), rows in sorted(grouped.items()):
        total = len(rows)
        correct = sum(int(row["is_correct"]) for row in rows)
        asthma_fn = sum(row["error_type"] == "ASTHMA_FN" for row in rows)
        non_asthma_fp = sum(
            row["error_type"] == "NON_ASTHMA_FP" for row in rows
        )
        summary_rows.append(
            {
                "split": split,
                "data_group": data_group,
                "total": total,
                "correct": correct,
                "errors": total - correct,
                "accuracy": f"{correct / total:.9f}",
                "asthma_fn": asthma_fn,
                "non_asthma_fp": non_asthma_fp,
            }
        )
    return summary_rows


def confusion_counts(rows):
    asthma_correct = sum(
        row["true_label"] == 0 and row["predicted_label"] == 0 for row in rows
    )
    asthma_fn = sum(row["error_type"] == "ASTHMA_FN" for row in rows)
    non_asthma_fp = sum(
        row["error_type"] == "NON_ASTHMA_FP" for row in rows
    )
    non_asthma_correct = sum(
        row["true_label"] == 1 and row["predicted_label"] == 1 for row in rows
    )
    return asthma_correct, asthma_fn, non_asthma_fp, non_asthma_correct


def write_markdown_summary(rows_by_split, train_min, train_max):
    lines = [
        "# Phân tích lỗi Model Asthma V2",
        "",
        "Script chỉ thực hiện suy luận, không huấn luyện lại mô hình.",
        "",
        f"- Model: `{MODEL_PATH.name}`",
        f"- Ngưỡng phân lớp: `{THRESHOLD}`",
        f"- TRAIN_MIN: `{train_min}`",
        f"- TRAIN_MAX: `{train_max}`",
        "- Nhãn `0 = Asthma`, `1 = Non-Asthma`.",
        "- Xác suất đầu ra là xác suất `Non-Asthma`.",
        "",
    ]

    for split in ("val", "test"):
        rows = rows_by_split[split]
        correct = sum(int(row["is_correct"]) for row in rows)
        asthma_correct, asthma_fn, non_asthma_fp, non_asthma_correct = (
            confusion_counts(rows)
        )
        error_groups = Counter(
            row["data_group"] for row in rows if row["error_type"]
        )

        lines.extend(
            [
                f"## {split.upper()}",
                "",
                f"- Tổng mẫu: `{len(rows)}`",
                f"- Đúng: `{correct}`",
                f"- Sai: `{len(rows) - correct}`",
                f"- Accuracy: `{correct / len(rows):.4f}`",
                f"- Asthma đúng: `{asthma_correct}`",
                f"- Asthma FN: `{asthma_fn}`",
                f"- Non-Asthma FP: `{non_asthma_fp}`",
                f"- Non-Asthma đúng: `{non_asthma_correct}`",
                "",
                "Ma trận theo thứ tự `[Asthma, Non-Asthma]`:",
                "",
                "```text",
                f"[[{asthma_correct:3d}, {asthma_fn:3d}],",
                f" [{non_asthma_fp:3d}, {non_asthma_correct:3d}]]",
                "```",
                "",
                "Lỗi theo nhóm dữ liệu:",
                "",
            ]
        )
        if error_groups:
            for group, count in sorted(error_groups.items()):
                lines.append(f"- `{group}`: `{count}`")
        else:
            lines.append("- Không có lỗi.")
        lines.append("")

    lines.extend(
        [
            "## Cách đọc hai loại lỗi",
            "",
            "- `ASTHMA_FN`: bỏ sót Asthma, nhãn thật 0 nhưng dự đoán 1.",
            "- `NON_ASTHMA_FP`: cảnh báo nhầm Asthma, nhãn thật 1 nhưng dự đoán 0.",
            "",
        ]
    )
    (OUTPUT_DIR / "Analysis_Summary.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main():
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"Không tìm thấy model: {MODEL_PATH}")

    train_min, train_max = read_normalization_params()
    model = models.load_model(MODEL_PATH)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows_by_split = {}
    all_rows = []

    for split, output_name in (
        ("val", "Val_Predictions.csv"),
        ("test", "Test_Predictions.csv"),
    ):
        x_data, y_data, files_data = load_split(split)
        x_normalized = (
            (x_data.astype(np.float32) - train_min) / (train_max - train_min)
        ).astype(np.float32)

        probabilities = model.predict(
            x_normalized,
            batch_size=32,
            verbose=0,
        ).reshape(-1)

        rows = make_prediction_rows(split, y_data, files_data, probabilities)
        error_rows = [row for row in rows if row["error_type"]]

        write_csv(OUTPUT_DIR / output_name, rows, PREDICTION_COLUMNS)
        write_csv(
            OUTPUT_DIR / f"{split.capitalize()}_Errors.csv",
            error_rows,
            PREDICTION_COLUMNS,
        )

        rows_by_split[split] = rows
        all_rows.extend(rows)

        asthma_correct, asthma_fn, non_asthma_fp, non_asthma_correct = (
            confusion_counts(rows)
        )
        print(f"\n{split.upper()}: {len(rows)} mẫu")
        print(
            "Ma trận [Asthma, Non-Asthma]: "
            f"[[{asthma_correct}, {asthma_fn}], "
            f"[{non_asthma_fp}, {non_asthma_correct}]]"
        )
        print(f"Asthma FN       : {asthma_fn}")
        print(f"Non-Asthma FP   : {non_asthma_fp}")

    group_rows = create_group_summary(all_rows)
    write_csv(
        OUTPUT_DIR / "Error_Group_Summary.csv",
        group_rows,
        [
            "split",
            "data_group",
            "total",
            "correct",
            "errors",
            "accuracy",
            "asthma_fn",
            "non_asthma_fp",
        ],
    )
    write_markdown_summary(rows_by_split, train_min, train_max)

    print(f"\nĐã lưu kết quả tại: {OUTPUT_DIR}")
    print("Không có bước huấn luyện nào được thực hiện.")


if __name__ == "__main__":
    main()
