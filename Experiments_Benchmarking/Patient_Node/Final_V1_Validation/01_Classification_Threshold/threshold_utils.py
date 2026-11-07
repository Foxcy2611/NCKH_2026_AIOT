"""Hàm hậu xử lý và đánh giá vùng ASTHMA / UNSURE / NON-ASTHMA.

Module không chạy TFLite và không tự chọn threshold bằng Test.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


LABEL_ASTHMA = 0
LABEL_NON_ASTHMA = 1
PRED_ASTHMA = 0
PRED_NON_ASTHMA = 1
PRED_UNSURE = 2

PREDICTION_NAMES = {
    PRED_ASTHMA: "ASTHMA",
    PRED_NON_ASTHMA: "NON_ASTHMA",
    PRED_UNSURE: "UNSURE",
}

METRIC_COLUMNS = [
    "low_threshold",
    "high_threshold",
    "total",
    "asthma_total",
    "non_asthma_total",
    "asthma_to_asthma",
    "asthma_to_unsure",
    "asthma_to_non_asthma",
    "non_asthma_to_asthma",
    "non_asthma_to_unsure",
    "non_asthma_to_non_asthma",
    "asthma_precision",
    "asthma_recall",
    "asthma_f1",
    "asthma_miss_rate",
    "asthma_unsure_rate",
    "non_asthma_false_alarm_rate",
    "non_asthma_unsure_rate",
    "overall_unsure_rate",
    "coverage",
    "accepted_accuracy",
    "strict_accuracy",
    "decision_pattern_sha256",
]


def safe_divide(numerator: int | float, denominator: int | float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def validate_thresholds(low: float, high: float) -> tuple[float, float]:
    low = float(low)
    high = float(high)
    if not (0.0 <= low < high <= 1.0):
        raise ValueError(f"Cần 0 <= LOW < HIGH <= 1, nhận LOW={low}, HIGH={high}")
    return low, high


def apply_thresholds(
    p_non_asthma: Sequence[float] | np.ndarray,
    low: float,
    high: float,
) -> np.ndarray:
    low, high = validate_thresholds(low, high)
    probabilities = np.asarray(p_non_asthma, dtype=np.float64)
    if probabilities.ndim != 1:
        probabilities = probabilities.reshape(-1)
    if not np.isfinite(probabilities).all():
        raise ValueError("Probability có NaN hoặc Inf")

    predictions = np.full(probabilities.shape, PRED_UNSURE, dtype=np.int8)
    predictions[probabilities <= low] = PRED_ASTHMA
    predictions[probabilities >= high] = PRED_NON_ASTHMA
    return predictions


def compute_metrics(
    y_true: Sequence[int] | np.ndarray,
    p_non_asthma: Sequence[float] | np.ndarray,
    low: float,
    high: float,
) -> dict[str, int | float | str]:
    low, high = validate_thresholds(low, high)
    truth = np.asarray(y_true, dtype=np.int64).reshape(-1)
    probabilities = np.asarray(p_non_asthma, dtype=np.float64).reshape(-1)
    if len(truth) != len(probabilities):
        raise ValueError("y_true và p_non_asthma không cùng số phần tử")
    if not set(np.unique(truth)).issubset({LABEL_ASTHMA, LABEL_NON_ASTHMA}):
        raise ValueError("y_true chỉ được chứa nhãn 0/1")

    predictions = apply_thresholds(probabilities, low, high)
    asthma_mask = truth == LABEL_ASTHMA
    non_mask = truth == LABEL_NON_ASTHMA

    a_to_a = int(np.sum(asthma_mask & (predictions == PRED_ASTHMA)))
    a_to_u = int(np.sum(asthma_mask & (predictions == PRED_UNSURE)))
    a_to_n = int(np.sum(asthma_mask & (predictions == PRED_NON_ASTHMA)))
    n_to_a = int(np.sum(non_mask & (predictions == PRED_ASTHMA)))
    n_to_u = int(np.sum(non_mask & (predictions == PRED_UNSURE)))
    n_to_n = int(np.sum(non_mask & (predictions == PRED_NON_ASTHMA)))

    total = len(truth)
    asthma_total = int(np.sum(asthma_mask))
    non_total = int(np.sum(non_mask))
    unsure_total = a_to_u + n_to_u
    accepted_total = total - unsure_total

    precision = safe_divide(a_to_a, a_to_a + n_to_a)
    recall = safe_divide(a_to_a, asthma_total)
    f1 = safe_divide(2.0 * precision * recall, precision + recall)

    return {
        "low_threshold": low,
        "high_threshold": high,
        "total": total,
        "asthma_total": asthma_total,
        "non_asthma_total": non_total,
        "asthma_to_asthma": a_to_a,
        "asthma_to_unsure": a_to_u,
        "asthma_to_non_asthma": a_to_n,
        "non_asthma_to_asthma": n_to_a,
        "non_asthma_to_unsure": n_to_u,
        "non_asthma_to_non_asthma": n_to_n,
        "asthma_precision": precision,
        "asthma_recall": recall,
        "asthma_f1": f1,
        "asthma_miss_rate": safe_divide(a_to_n, asthma_total),
        "asthma_unsure_rate": safe_divide(a_to_u, asthma_total),
        "non_asthma_false_alarm_rate": safe_divide(n_to_a, non_total),
        "non_asthma_unsure_rate": safe_divide(n_to_u, non_total),
        "overall_unsure_rate": safe_divide(unsure_total, total),
        "coverage": safe_divide(accepted_total, total),
        "accepted_accuracy": safe_divide(a_to_a + n_to_n, accepted_total),
        "strict_accuracy": safe_divide(a_to_a + n_to_n, total),
        "decision_pattern_sha256": hashlib.sha256(predictions.tobytes()).hexdigest(),
    }


def load_predictions(path: Path | str) -> pd.DataFrame:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path)
    required = {"true_label", "p_non_asthma", "file_name"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Prediction CSV thiếu cột: {missing}")
    frame["true_label"] = pd.to_numeric(frame["true_label"], errors="raise").astype(int)
    frame["p_non_asthma"] = pd.to_numeric(
        frame["p_non_asthma"], errors="raise"
    ).astype(float)
    return frame


def compare_candidates(
    predictions: pd.DataFrame,
    candidates: Iterable[tuple[float, float]],
) -> pd.DataFrame:
    rows = [
        compute_metrics(
            predictions["true_label"].to_numpy(),
            predictions["p_non_asthma"].to_numpy(),
            low,
            high,
        )
        for low, high in candidates
    ]
    return pd.DataFrame(rows, columns=METRIC_COLUMNS)


def threshold_grid_sweep(
    predictions: pd.DataFrame,
    low_values: Iterable[float] | None = None,
    high_values: Iterable[float] | None = None,
) -> pd.DataFrame:
    if low_values is None:
        low_values = np.round(np.arange(0.05, 0.61, 0.01), 2)
    if high_values is None:
        high_values = np.round(np.arange(0.40, 0.96, 0.01), 2)

    candidates = [
        (float(low), float(high))
        for low in low_values
        for high in high_values
        if float(low) < float(high)
    ]
    result = compare_candidates(predictions, candidates)
    result["duplicate_decision_pattern"] = result.duplicated(
        subset=["decision_pattern_sha256"], keep="first"
    )
    return result


def rank_candidates(
    sweep: pd.DataFrame,
    max_asthma_miss_rate: float | None = None,
    max_overall_unsure_rate: float | None = None,
    max_non_asthma_false_alarm_rate: float | None = None,
) -> pd.DataFrame:
    filtered = sweep.copy()
    if max_asthma_miss_rate is not None:
        filtered = filtered[filtered["asthma_miss_rate"] <= max_asthma_miss_rate]
    if max_overall_unsure_rate is not None:
        filtered = filtered[filtered["overall_unsure_rate"] <= max_overall_unsure_rate]
    if max_non_asthma_false_alarm_rate is not None:
        filtered = filtered[
            filtered["non_asthma_false_alarm_rate"]
            <= max_non_asthma_false_alarm_rate
        ]
    if filtered.empty:
        raise ValueError("Không có candidate nào thỏa các constraint đã đặt")

    return filtered.sort_values(
        by=[
            "asthma_miss_rate",
            "overall_unsure_rate",
            "non_asthma_false_alarm_rate",
            "asthma_recall",
            "asthma_f1",
            "accepted_accuracy",
        ],
        ascending=[True, True, True, False, False, False],
    ).reset_index(drop=True)


def annotate_predictions(
    predictions: pd.DataFrame,
    low: float,
    high: float,
) -> pd.DataFrame:
    result = predictions.copy()
    tri_state = apply_thresholds(result["p_non_asthma"].to_numpy(), low, high)
    result["final_predicted_label"] = tri_state
    result["final_predicted_class"] = [PREDICTION_NAMES[int(value)] for value in tri_state]
    result["final_correct"] = np.where(
        tri_state == PRED_UNSURE,
        "UNSURE",
        np.where(tri_state == result["true_label"].to_numpy(), "CORRECT", "WRONG"),
    )
    return result


def probability_to_int8_threshold(
    probability: float,
    output_scale: float,
    output_zero_point: int,
) -> int:
    if output_scale <= 0:
        raise ValueError("output_scale phải > 0")
    quantized = int(np.rint(float(probability) / output_scale + output_zero_point))
    return int(np.clip(quantized, -128, 127))



def probability_to_int8_decision_bounds(
    low: float,
    high: float,
    output_scale: float,
    output_zero_point: int,
) -> tuple[int, int]:
    """Ngưỡng raw INT8 CHÍNH XÁC theo rule Python, không làm tròn gần nhất.

    So sánh tại firmware (raw được ép lên int):
    raw <= low_raw -> ASTHMA
    raw >= high_raw -> NON-ASTHMA
    còn lại -> UNSURE.

    Dùng quét 256 giá trị vì output quantized, tự xử lý cả biên không thể đạt.
    """
    low, high = validate_thresholds(low, high)
    if output_scale <= 0 or not np.isfinite(output_scale):
        raise ValueError("output_scale phải hữu hạn và > 0")
    raw = np.arange(-128, 128, dtype=np.int32)
    p_non = np.clip((raw - int(output_zero_point)) * output_scale, 0.0, 1.0)
    a_candidates = raw[p_non <= low]
    n_candidates = raw[p_non >= high]
    low_raw = int(a_candidates.max()) if a_candidates.size else -129
    high_raw = int(n_candidates.min()) if n_candidates.size else 128
    predicted_raw = np.where(raw <= low_raw, PRED_ASTHMA,
                             np.where(raw >= high_raw, PRED_NON_ASTHMA, PRED_UNSURE))
    predicted_float = apply_thresholds(p_non, low, high)
    if not np.array_equal(predicted_raw, predicted_float):
        raise AssertionError("Biên INT8 không trùng quyết định float trên toàn bộ 256 giá trị")
    return low_raw, high_raw


def export_final_config(
    path: Path | str,
    low: float,
    high: float,
    validation_metrics: dict,
    prediction_metadata: dict,
    selection_note: str,
) -> Path:
    low, high = validate_thresholds(low, high)
    path = Path(path)
    output_scale = float(prediction_metadata["output_scale"])
    output_zero = int(prediction_metadata["output_zero_point"])

    low_raw, high_raw = probability_to_int8_decision_bounds(
        low, high, output_scale, output_zero
    )

    payload = {
        "status": "FROZEN",
        "experiment": "Patient_Node_Final_V1_Classification_Threshold",
        "model": prediction_metadata.get(
            "model", "combo_pre0_mel40_fft2048__V1__s44_QAT_INT8"
        ),
        "trial_id": prediction_metadata.get(
            "trial_id", "combo_pre0_mel40_fft2048__V1__s44"
        ),
        "model_sha256": prediction_metadata["model_sha256"],
        "selection_split": "validation",
        "test_used_for_selection": False,
        "probability_semantics": "p_non_asthma",
        "rule": {
            "asthma": "p_non_asthma <= LOW",
            "unsure": "LOW < p_non_asthma < HIGH",
            "non_asthma": "p_non_asthma >= HIGH",
        },
        "low_threshold": low,
        "high_threshold": high,
        "low_output_int8_inclusive": low_raw,
        "high_output_int8_inclusive": high_raw,
        "int8_decision_rule": "raw <= LOW_RAW -> ASTHMA; raw >= HIGH_RAW -> NON_ASTHMA; else UNSURE",
        "output_scale": output_scale,
        "output_zero_point": output_zero,
        "validation_metrics": validation_metrics,
        "selection_note": selection_note,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if str(existing.get("status", "")).upper() == "FROZEN":
            same_identity = (
                existing.get("model_sha256") == payload["model_sha256"]
                and float(existing.get("low_threshold", -1)) == low
                and float(existing.get("high_threshold", -1)) == high
            )
            if same_identity:
                if (existing.get("low_output_int8_inclusive") != low_raw
                        or existing.get("high_output_int8_inclusive") != high_raw):
                    raise FileExistsError(
                        "final_threshold.json FROZEN cũ thiếu biên INT8 inclusive "
                        "hoặc chứa biên không khớp. Hãy sao lưu file cũ, "
                        "kiểm tra lại đúng model và cùng cặp LOW/HIGH, "
                        "rồi tạo lại JSON với schema mới; không đổi ngưỡng theo Test."
                    )
                # Khóa đã đóng: không ghi đè, kể cả khi lời ghi chú bị thay đổi.
                return path
            raise FileExistsError(
                "final_threshold.json đã FROZEN với model/LOW/HIGH khác. "
                "Không ghi đè để tránh điều chỉnh ngưỡng sau khi xem Test."
            )
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def load_final_config(path: Path | str) -> dict:
    path = Path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if str(payload.get("status", "")).upper() != "FROZEN":
        raise ValueError("Final config chưa có status=FROZEN")
    validate_thresholds(payload["low_threshold"], payload["high_threshold"])
    return payload


def write_metrics_csv(path: Path | str, metrics: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(metrics.keys()))
        writer.writeheader()
        writer.writerow(metrics)
    return path
