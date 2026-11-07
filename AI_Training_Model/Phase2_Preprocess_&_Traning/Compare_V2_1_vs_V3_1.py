"""So sanh V2_1 co playback va V3_1 khong playback tren hai test khoa san.

Model A: V1 SepConv2D train bang Dataset_Chia_V2 (co playback).
Model B: V1 SepConv2D train bang Dataset_Chia_V3 (khong playback).

TEST 1 - COMMON RAW TEST:
    Toan bo 143 mau V3 test = 30 Asthma + 113 Non-Asthma.

TEST 2 - PLAYBACK-ONLY TEST:
    Hieu Files_test(V2) - Files_test(V3) = 16 playback
    = 8 Asthma + 8 Non-Asthma.

Script chi danh gia model da train, khong train va khong chon threshold.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# =============================================================================
# CAU HINH THI NGHIEM KHOA
# =============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
PHASE2_DIR = SCRIPT_DIR

MODEL_A_NAME = "V2_1_With_Playback"
MODEL_B_NAME = "V3_1_No_Playback"

MODEL_A_DIR = PHASE2_DIR / "Output_Train_V1_SepConv2D_Flatten"
MODEL_B_DIR = PHASE2_DIR / "Output_Train_V3_V1_No_Playback"
MODEL_A_PATH = MODEL_A_DIR / "Model_Asthma.keras"
MODEL_B_PATH = MODEL_B_DIR / "Model_Asthma_V3_V1_No_Playback.keras"
NORM_A_PATH = MODEL_A_DIR / "Normalization_Params.txt"
NORM_B_PATH = MODEL_B_DIR / "Normalization_Params.txt"

FEATURE_V2_DIR = PHASE2_DIR / "Output_Preprocess"
FEATURE_V3_DIR = PHASE2_DIR / "Output_Preprocess_V3_No_Playback"

OUTPUT_DIR = SCRIPT_DIR / "Output_Comparison_V2_1_vs_V3_1"
METRICS_CSV = OUTPUT_DIR / "metrics_summary.csv"
REPORT_MD = OUTPUT_DIR / "Comparison_Report.md"
METADATA_JSON = OUTPUT_DIR / "comparison_metadata.json"

BINARY_THRESHOLD = 0.5
LABEL_ASTHMA = 0
LABEL_NON_ASTHMA = 1
CLASS_NAMES = {
    LABEL_ASTHMA: "Asthma",
    LABEL_NON_ASTHMA: "Non_Asthma",
}

EXPECTED_TESTS = {
    "common_raw": {
        "sample_count": 143,
        "asthma_count": 30,
        "non_asthma_count": 113,
    },
    "playback_only": {
        "sample_count": 16,
        "asthma_count": 8,
        "non_asthma_count": 8,
    },
}

PREDICTION_COLUMNS = [
    "test_name",
    "file",
    "true_label",
    "true_class",
    "model_a",
    "model_a_p_non_asthma",
    "model_a_predicted_label",
    "model_a_predicted_class",
    "model_a_correct",
    "model_b",
    "model_b_p_non_asthma",
    "model_b_predicted_label",
    "model_b_predicted_class",
    "model_b_correct",
    "p_non_delta_b_minus_a",
]

METRIC_COLUMNS = [
    "test_name",
    "model",
    "sample_count",
    "asthma_count",
    "non_asthma_count",
    "accuracy",
    "asthma_precision",
    "asthma_recall",
    "asthma_f1",
    "non_asthma_precision",
    "non_asthma_recall",
    "non_asthma_f1",
    "true_asthma_pred_asthma",
    "true_asthma_pred_non_asthma",
    "true_non_asthma_pred_asthma",
    "true_non_asthma_pred_non_asthma",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_normalization(path: Path) -> tuple[float, float]:
    if not path.is_file():
        raise FileNotFoundError(f"Thieu normalization: {path}")

    values: dict[str, float] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = float(value.strip())

    if "TRAIN_MIN" not in values or "TRAIN_MAX" not in values:
        raise ValueError(f"Normalization thieu TRAIN_MIN/TRAIN_MAX: {path}")
    train_min = values["TRAIN_MIN"]
    train_max = values["TRAIN_MAX"]
    if not np.isfinite(train_min) or not np.isfinite(train_max):
        raise ValueError(f"Normalization co NaN/Inf: {path}")
    if train_max <= train_min:
        raise ValueError(f"TRAIN_MAX phai lon hon TRAIN_MIN: {path}")
    return train_min, train_max


def load_test_artifacts(feature_dir: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    paths = {
        "x": feature_dir / "X_test_mel.npy",
        "y": feature_dir / "Y_test_mel.npy",
        "files": feature_dir / "Files_test.npy",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("Thieu test artifact:\n- " + "\n- ".join(missing))

    x_data = np.load(paths["x"])
    y_data = np.load(paths["y"]).astype(np.int64)
    files_data = np.load(paths["files"], allow_pickle=False).astype(str)

    if x_data.shape[1:] != (64, 129, 1):
        raise ValueError(f"Sai feature shape trong {feature_dir}: {x_data.shape}")
    if not (len(x_data) == len(y_data) == len(files_data)):
        raise ValueError(f"X/Y/Files khong cung length trong {feature_dir}")
    if not set(np.unique(y_data)).issubset({0, 1}):
        raise ValueError(f"Nhan ngoai 0/1 trong {feature_dir}")
    if not np.isfinite(x_data).all():
        raise ValueError(f"Feature co NaN/Inf trong {feature_dir}")
    if len(set(files_data.tolist())) != len(files_data):
        raise ValueError(f"Files_test trung ten trong {feature_dir}")
    return x_data, y_data, files_data


def label_from_file(file_name: str) -> int:
    normalized = file_name.replace("\\", "/")
    if normalized.startswith("Asthma/test/"):
        return LABEL_ASTHMA
    if normalized.startswith("Non_Asthma_Disease/test/"):
        return LABEL_NON_ASTHMA
    raise ValueError(f"Khong suy ra class tu file: {file_name}")


def validate_test(
    test_name: str,
    x_data: np.ndarray,
    y_data: np.ndarray,
    files_data: np.ndarray,
) -> None:
    expected = EXPECTED_TESTS[test_name]
    actual = {
        "sample_count": len(y_data),
        "asthma_count": int(np.sum(y_data == LABEL_ASTHMA)),
        "non_asthma_count": int(np.sum(y_data == LABEL_NON_ASTHMA)),
    }
    if actual != expected:
        raise ValueError(f"Sai cau truc {test_name}: actual={actual}, expected={expected}")
    if len(x_data) != len(files_data):
        raise ValueError(f"X/Files khong khop trong {test_name}")
    for file_name, label in zip(files_data, y_data, strict=True):
        if label_from_file(str(file_name)) != int(label):
            raise ValueError(f"Nhan khong khop duong dan: {file_name} -> {label}")


def build_locked_tests() -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    x_v2, y_v2, files_v2 = load_test_artifacts(FEATURE_V2_DIR)
    x_v3, y_v3, files_v3 = load_test_artifacts(FEATURE_V3_DIR)

    v2_index = {file_name: index for index, file_name in enumerate(files_v2)}
    v3_set = set(files_v3.tolist())
    v2_set = set(files_v2.tolist())

    if not v3_set.issubset(v2_set):
        missing = sorted(v3_set - v2_set)
        raise ValueError(f"Common V3 test khong nam tron trong V2 test: {missing[:10]}")

    # Xac minh cung mot raw file co feature giong nhau trong hai lan preprocess.
    for v3_position, file_name in enumerate(files_v3):
        v2_position = v2_index[file_name]
        if int(y_v2[v2_position]) != int(y_v3[v3_position]):
            raise ValueError(f"Nhan V2/V3 khong khop: {file_name}")
        if not np.allclose(
            x_v2[v2_position], x_v3[v3_position], rtol=0.0, atol=1e-6
        ):
            max_delta = float(
                np.max(np.abs(x_v2[v2_position] - x_v3[v3_position]))
            )
            raise ValueError(
                f"Feature common raw V2/V3 khac nhau: {file_name}, "
                f"max_delta={max_delta}"
            )

    playback_indices = [
        index for index, file_name in enumerate(files_v2) if file_name not in v3_set
    ]
    x_playback = x_v2[playback_indices]
    y_playback = y_v2[playback_indices]
    files_playback = files_v2[playback_indices]
    if any(
        not (
            Path(file_name).stem.casefold().endswith("__take01")
            or Path(file_name).stem.casefold().endswith("__take02")
        )
        for file_name in files_playback
    ):
        raise ValueError("Hieu V2-V3 chua file khong phai playback")

    tests = {
        "common_raw": (x_v3, y_v3, files_v3),
        "playback_only": (x_playback, y_playback, files_playback),
    }
    for test_name, values in tests.items():
        validate_test(test_name, *values)
    return tests


def load_model(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"Thieu model: {path}")
    model = tf.keras.models.load_model(path)
    input_shape = tuple(model.input_shape[1:])
    if input_shape != (64, 129, 1):
        raise ValueError(f"Model {path.name} co input shape {model.input_shape}")
    output_shape = tuple(model.output_shape[1:])
    if output_shape != (1,):
        raise ValueError(f"Model {path.name} co output shape {model.output_shape}")
    return model


def normalize_for_model(
    x_data: np.ndarray,
    train_min: float,
    train_max: float,
) -> np.ndarray:
    # Giu dung cong thuc Training_Model.py, khong clip hoac normalize lai theo test.
    normalized = (x_data.astype(np.float32) - train_min) / (train_max - train_min)
    if not np.isfinite(normalized).all():
        raise ValueError("Normalized input co NaN/Inf")
    return normalized.astype(np.float32, copy=False)


def predict_p_non(
    model,
    x_data: np.ndarray,
    normalization: tuple[float, float],
) -> np.ndarray:
    train_min, train_max = normalization
    normalized = normalize_for_model(x_data, train_min, train_max)
    probabilities = np.asarray(model.predict(normalized, verbose=0)).reshape(-1)
    if len(probabilities) != len(x_data):
        raise ValueError("Model tra sai so prediction")
    if not np.isfinite(probabilities).all():
        raise ValueError("Prediction co NaN/Inf")
    return probabilities.astype(np.float64)


def calculate_metrics(
    test_name: str,
    model_name: str,
    y_true: np.ndarray,
    probabilities: np.ndarray,
) -> tuple[dict[str, str | int | float], np.ndarray, np.ndarray]:
    predictions = (probabilities >= BINARY_THRESHOLD).astype(np.int64)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        predictions,
        labels=[LABEL_ASTHMA, LABEL_NON_ASTHMA],
        zero_division=0,
    )
    matrix = confusion_matrix(
        y_true,
        predictions,
        labels=[LABEL_ASTHMA, LABEL_NON_ASTHMA],
    )
    row: dict[str, str | int | float] = {
        "test_name": test_name,
        "model": model_name,
        "sample_count": len(y_true),
        "asthma_count": int(np.sum(y_true == LABEL_ASTHMA)),
        "non_asthma_count": int(np.sum(y_true == LABEL_NON_ASTHMA)),
        "accuracy": f"{accuracy_score(y_true, predictions):.9f}",
        "asthma_precision": f"{precision[0]:.9f}",
        "asthma_recall": f"{recall[0]:.9f}",
        "asthma_f1": f"{f1[0]:.9f}",
        "non_asthma_precision": f"{precision[1]:.9f}",
        "non_asthma_recall": f"{recall[1]:.9f}",
        "non_asthma_f1": f"{f1[1]:.9f}",
        "true_asthma_pred_asthma": int(matrix[0, 0]),
        "true_asthma_pred_non_asthma": int(matrix[0, 1]),
        "true_non_asthma_pred_asthma": int(matrix[1, 0]),
        "true_non_asthma_pred_non_asthma": int(matrix[1, 1]),
    }
    return row, matrix, predictions


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def build_prediction_rows(
    test_name: str,
    y_true: np.ndarray,
    files_data: np.ndarray,
    p_a: np.ndarray,
    p_b: np.ndarray,
) -> list[dict[str, str | int]]:
    pred_a = (p_a >= BINARY_THRESHOLD).astype(np.int64)
    pred_b = (p_b >= BINARY_THRESHOLD).astype(np.int64)
    rows: list[dict[str, str | int]] = []
    for file_name, label, prob_a, class_a, prob_b, class_b in zip(
        files_data, y_true, p_a, pred_a, p_b, pred_b, strict=True
    ):
        true_label = int(label)
        class_a = int(class_a)
        class_b = int(class_b)
        rows.append(
            {
                "test_name": test_name,
                "file": str(file_name).replace("\\", "/"),
                "true_label": true_label,
                "true_class": CLASS_NAMES[true_label],
                "model_a": MODEL_A_NAME,
                "model_a_p_non_asthma": f"{float(prob_a):.9f}",
                "model_a_predicted_label": class_a,
                "model_a_predicted_class": CLASS_NAMES[class_a],
                "model_a_correct": int(class_a == true_label),
                "model_b": MODEL_B_NAME,
                "model_b_p_non_asthma": f"{float(prob_b):.9f}",
                "model_b_predicted_label": class_b,
                "model_b_predicted_class": CLASS_NAMES[class_b],
                "model_b_correct": int(class_b == true_label),
                "p_non_delta_b_minus_a": f"{float(prob_b - prob_a):+.9f}",
            }
        )
    return rows


def plot_confusion_matrices(
    matrices: dict[tuple[str, str], np.ndarray],
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10, 9), constrained_layout=True)
    tests = ["common_raw", "playback_only"]
    models = [MODEL_A_NAME, MODEL_B_NAME]
    for row_index, test_name in enumerate(tests):
        for column_index, model_name in enumerate(models):
            ax = axes[row_index, column_index]
            matrix = matrices[(test_name, model_name)]
            image = ax.imshow(matrix, cmap="Blues", vmin=0)
            for row in range(2):
                for column in range(2):
                    ax.text(
                        column,
                        row,
                        str(int(matrix[row, column])),
                        ha="center",
                        va="center",
                        color="black",
                        fontsize=13,
                    )
            ax.set_title(f"{test_name}\n{model_name}")
            ax.set_xticks([0, 1], ["Asthma", "Non-Asthma"])
            ax.set_yticks([0, 1], ["Asthma", "Non-Asthma"])
            ax.set_xlabel("Predicted")
            ax.set_ylabel("True")
            fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.savefig(OUTPUT_DIR / "confusion_matrices.png", dpi=170)
    plt.close(fig)


def plot_probability_comparison(
    predictions_by_test: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],
) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(14, 9), constrained_layout=True)
    for ax, (test_name, (y_true, p_a, p_b)) in zip(
        axes, predictions_by_test.items(), strict=True
    ):
        order = np.lexsort((p_a, y_true))
        indices = np.arange(len(y_true))
        ax.plot(indices, p_a[order], "o", markersize=3.5, label=MODEL_A_NAME)
        ax.plot(indices, p_b[order], "x", markersize=4.0, label=MODEL_B_NAME)
        ax.axhline(BINARY_THRESHOLD, color="black", linestyle="--", linewidth=1)
        asthma_count = int(np.sum(y_true == LABEL_ASTHMA))
        ax.axvline(asthma_count - 0.5, color="gray", linestyle=":", linewidth=1)
        ax.set_ylim(-0.03, 1.03)
        ax.set_title(f"{test_name}: p_non_asthma tung mau")
        ax.set_xlabel("Mau da sap xep: Asthma truoc, Non-Asthma sau")
        ax.set_ylabel("p_non_asthma")
        ax.grid(alpha=0.2)
        ax.legend()
    fig.savefig(OUTPUT_DIR / "p_non_comparison.png", dpi=170)
    plt.close(fig)


def write_markdown_report(metric_rows: list[dict[str, str | int | float]]) -> None:
    by_key = {(str(row["test_name"]), str(row["model"])): row for row in metric_rows}
    lines = [
        "# So sanh Model A V2_1 va Model B V3_1",
        "",
        f"- Model A: `{MODEL_A_NAME}` - train V2 co playback",
        f"- Model B: `{MODEL_B_NAME}` - train V3 khong playback",
        f"- Binary threshold: `{BINARY_THRESHOLD}` tren `p_non_asthma`",
        "- Nhan: `0=Asthma`, `1=Non-Asthma`",
        "",
    ]

    for test_name, description in (
        ("common_raw", "TEST 1 - COMMON RAW TEST (143 mau: 30/113)"),
        ("playback_only", "TEST 2 - PLAYBACK-ONLY TEST (16 mau: 8/8)"),
    ):
        lines.extend(
            [
                f"## {description}",
                "",
                "| Metric | Model A | Model B |",
                "|---|---:|---:|",
            ]
        )
        row_a = by_key[(test_name, MODEL_A_NAME)]
        row_b = by_key[(test_name, MODEL_B_NAME)]
        for label, key in (
            ("Accuracy", "accuracy"),
            ("Asthma Precision", "asthma_precision"),
            ("Asthma Recall", "asthma_recall"),
            ("Asthma F1", "asthma_f1"),
            ("Non-Asthma Precision", "non_asthma_precision"),
            ("Non-Asthma Recall", "non_asthma_recall"),
            ("Non-Asthma F1", "non_asthma_f1"),
        ):
            lines.append(f"| {label} | {row_a[key]} | {row_b[key]} |")

        lines.extend(
            [
                "",
                "Confusion matrix dùng thứ tự hàng/cột `[Asthma, Non-Asthma]`.",
                "",
                f"- Model A: `[[{row_a['true_asthma_pred_asthma']}, "
                f"{row_a['true_asthma_pred_non_asthma']}], "
                f"[{row_a['true_non_asthma_pred_asthma']}, "
                f"{row_a['true_non_asthma_pred_non_asthma']}]]`",
                f"- Model B: `[[{row_b['true_asthma_pred_asthma']}, "
                f"{row_b['true_asthma_pred_non_asthma']}], "
                f"[{row_b['true_non_asthma_pred_asthma']}, "
                f"{row_b['true_non_asthma_pred_non_asthma']}]]`",
                "",
            ]
        )

    lines.extend(
        [
            "## File chi tiet",
            "",
            "- `common_raw_predictions.csv`: p_non cua 143 raw cho ca hai model.",
            "- `playback_only_predictions.csv`: p_non cua 16 playback cho ca hai model.",
            "- `metrics_summary.csv`: metrics va confusion matrix dang bang.",
            "- `confusion_matrices.png`: 4 confusion matrix.",
            "- `p_non_comparison.png`: phan bo p_non theo tung test.",
            "",
            "> Test chi de danh gia sau khi hai model da train xong; script khong",
            "> dung test de chon threshold hoac thay doi model.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    print("=" * 72)
    print("COMPARE V2_1 WITH PLAYBACK VS V3_1 WITHOUT PLAYBACK")
    print("=" * 72)

    tests = build_locked_tests()
    norm_a = read_normalization(NORM_A_PATH)
    norm_b = read_normalization(NORM_B_PATH)
    print(f"Model A normalization: {norm_a}")
    print(f"Model B normalization: {norm_b}")

    print("Dang load hai model Keras...")
    model_a = load_model(MODEL_A_PATH)
    model_b = load_model(MODEL_B_PATH)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    metric_rows: list[dict[str, str | int | float]] = []
    matrices: dict[tuple[str, str], np.ndarray] = {}
    probabilities_for_plot: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}

    for test_name, (x_data, y_true, files_data) in tests.items():
        print(f"\nDang chay {test_name}: {len(y_true)} mau")
        p_a = predict_p_non(model_a, x_data, norm_a)
        p_b = predict_p_non(model_b, x_data, norm_b)

        row_a, matrix_a, _ = calculate_metrics(
            test_name, MODEL_A_NAME, y_true, p_a
        )
        row_b, matrix_b, _ = calculate_metrics(
            test_name, MODEL_B_NAME, y_true, p_b
        )
        metric_rows.extend([row_a, row_b])
        matrices[(test_name, MODEL_A_NAME)] = matrix_a
        matrices[(test_name, MODEL_B_NAME)] = matrix_b
        probabilities_for_plot[test_name] = (y_true, p_a, p_b)

        prediction_rows = build_prediction_rows(
            test_name, y_true, files_data, p_a, p_b
        )
        write_csv(
            OUTPUT_DIR / f"{test_name}_predictions.csv",
            PREDICTION_COLUMNS,
            prediction_rows,
        )
        print(
            f"  Model A accuracy={row_a['accuracy']} | "
            f"Model B accuracy={row_b['accuracy']}"
        )

    write_csv(METRICS_CSV, METRIC_COLUMNS, metric_rows)
    plot_confusion_matrices(matrices)
    plot_probability_comparison(probabilities_for_plot)
    write_markdown_report(metric_rows)

    metadata = {
        "model_a_name": MODEL_A_NAME,
        "model_a_path": str(MODEL_A_PATH),
        "model_a_sha256": sha256_file(MODEL_A_PATH),
        "model_a_normalization": {"train_min": norm_a[0], "train_max": norm_a[1]},
        "model_b_name": MODEL_B_NAME,
        "model_b_path": str(MODEL_B_PATH),
        "model_b_sha256": sha256_file(MODEL_B_PATH),
        "model_b_normalization": {"train_min": norm_b[0], "train_max": norm_b[1]},
        "binary_threshold": BINARY_THRESHOLD,
        "tests": EXPECTED_TESTS,
        "feature_common_raw": str(FEATURE_V3_DIR),
        "feature_playback_only": str(FEATURE_V2_DIR),
    }
    METADATA_JSON.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 72)
    print("HOAN THANH SO SANH")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
