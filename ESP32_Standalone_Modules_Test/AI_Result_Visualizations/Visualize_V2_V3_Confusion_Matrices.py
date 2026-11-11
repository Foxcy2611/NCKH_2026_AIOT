"""Vẽ 4 ma trận nhầm lẫn so sánh Dataset V2.1 và V3.1.

Nguồn mặc định:
    AI_Training_Model/Phase2_Preprocess_&_Traning/
    Output_Comparison_V2_1_vs_V3_1/metrics_summary.csv

Bốn bảng gồm:
    - Common RAW: V2.1 có Playback và V3.1 không Playback.
    - Playback-only: V2.1 có Playback và V3.1 không Playback.

Chạy nhanh tại root dự án:
    py -3.11 .\ESP32_Standalone_Modules_Test\AI_Result_Visualizations\Visualize_V2_V3_Confusion_Matrices.py

Có thể đổi nguồn và ảnh đầu ra:
    py -3.11 .\ESP32_Standalone_Modules_Test\AI_Result_Visualizations\Visualize_V2_V3_Confusion_Matrices.py ^
        --metrics "duong_dan/metrics_summary.csv" ^
        --output "duong_dan/anh.png"
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


SCRIPT_DIR = Path(__file__).resolve().parent


def find_project_root() -> Path:
    """Tìm root repository thay vì phụ thuộc vị trí cố định của script."""
    for candidate in (SCRIPT_DIR, *SCRIPT_DIR.parents):
        if (
            (candidate / "AI_Training_Model").is_dir()
            and (candidate / "Experiments_Benchmarking").is_dir()
        ):
            return candidate
    raise FileNotFoundError("Không xác định được root của repository")


PROJECT_ROOT = find_project_root()
DEFAULT_METRICS = (
    PROJECT_ROOT
    / "AI_Training_Model"
    / "Phase2_Preprocess_&_Traning"
    / "Output_Comparison_V2_1_vs_V3_1"
    / "metrics_summary.csv"
)
DEFAULT_OUTPUT = SCRIPT_DIR / "V2_V3_Confusion_Matrices_Comparison.png"

TEST_ORDER = ("common_raw", "playback_only")
MODEL_ORDER = ("V2_1_With_Playback", "V3_1_No_Playback")

TEST_TITLES = {
    "common_raw": "Common RAW",
    "playback_only": "Playback-only",
}
MODEL_TITLES = {
    "V2_1_With_Playback": "V2.1 - có Playback",
    "V3_1_No_Playback": "V3.1 - không Playback",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Vẽ 4 confusion matrix so sánh V2.1 và V3.1."
    )
    parser.add_argument(
        "--metrics",
        type=Path,
        default=DEFAULT_METRICS,
        help="Đường dẫn tới metrics_summary.csv.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Đường dẫn ảnh PNG đầu ra.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=180,
        help="Độ phân giải ảnh đầu ra (mặc định: 180).",
    )
    return parser.parse_args()


def load_rows(metrics_path: Path) -> dict[tuple[str, str], dict[str, str]]:
    if not metrics_path.is_file():
        raise FileNotFoundError(f"Không tìm thấy file metrics: {metrics_path}")

    with metrics_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    indexed = {(row["test_name"], row["model"]): row for row in rows}
    expected = {
        (test_name, model_name)
        for test_name in TEST_ORDER
        for model_name in MODEL_ORDER
    }
    missing = sorted(expected - set(indexed))
    if missing:
        raise ValueError(f"metrics_summary.csv thiếu các dòng: {missing}")
    return indexed


def matrix_from_row(row: dict[str, str]) -> np.ndarray:
    """Khôi phục ma trận theo thứ tự nhãn [Asthma, Non-Asthma]."""
    return np.asarray(
        [
            [
                int(row["true_asthma_pred_asthma"]),
                int(row["true_asthma_pred_non_asthma"]),
            ],
            [
                int(row["true_non_asthma_pred_asthma"]),
                int(row["true_non_asthma_pred_non_asthma"]),
            ],
        ],
        dtype=np.int64,
    )


def annotate_matrix(ax: plt.Axes, matrix: np.ndarray, color_limit: float) -> None:
    row_totals = matrix.sum(axis=1, keepdims=True)
    row_percent = np.divide(
        matrix,
        row_totals,
        out=np.zeros_like(matrix, dtype=np.float64),
        where=row_totals != 0,
    )

    for row_index in range(2):
        for column_index in range(2):
            value = int(matrix[row_index, column_index])
            percent = 100.0 * row_percent[row_index, column_index]
            color = "white" if value > color_limit * 0.52 else "#10233f"
            ax.text(
                column_index,
                row_index,
                f"{value}\n{percent:.1f}%",
                ha="center",
                va="center",
                color=color,
                fontsize=11,
                fontweight="bold",
            )


def draw_figure(
    indexed_rows: dict[tuple[str, str], dict[str, str]],
    output_path: Path,
    dpi: int,
) -> None:
    matrices = {
        key: matrix_from_row(row)
        for key, row in indexed_rows.items()
        if key[0] in TEST_ORDER and key[1] in MODEL_ORDER
    }
    color_limit = max(float(matrix.max()) for matrix in matrices.values())

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.titleweight": "bold",
            "axes.labelcolor": "#24344d",
            "xtick.color": "#24344d",
            "ytick.color": "#24344d",
        }
    )
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 8.8), constrained_layout=True)
    fig.patch.set_facecolor("#f6f8fc")

    image = None
    for row_index, test_name in enumerate(TEST_ORDER):
        for column_index, model_name in enumerate(MODEL_ORDER):
            ax = axes[row_index, column_index]
            row = indexed_rows[(test_name, model_name)]
            matrix = matrices[(test_name, model_name)]
            accuracy = 100.0 * float(row["accuracy"])

            ax.set_facecolor("white")
            image = ax.imshow(
                matrix,
                cmap="Blues",
                vmin=0,
                vmax=color_limit,
                interpolation="nearest",
            )
            annotate_matrix(ax, matrix, color_limit)

            ax.set_title(
                f"{TEST_TITLES[test_name]} | {MODEL_TITLES[model_name]}\n"
                f"Accuracy: {accuracy:.2f}% | n = {int(row['sample_count'])}",
                fontsize=11.5,
                color="#13213a",
                pad=10,
            )
            ax.set_xticks([0, 1], ["Asthma", "Non-Asthma"])
            ax.set_yticks([0, 1], ["Asthma", "Non-Asthma"])
            ax.set_xlabel("Nhãn dự đoán")
            ax.set_ylabel("Nhãn thực tế")

            for spine in ax.spines.values():
                spine.set_color("#b7c2d4")

    fig.suptitle(
        "So sánh ma trận nhầm lẫn: Dataset V2.1 và V3.1",
        fontsize=16,
        fontweight="bold",
        color="#10233f",
    )
    if image is not None:
        colorbar = fig.colorbar(image, ax=axes, shrink=0.78, pad=0.025)
        colorbar.set_label("Số mẫu")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> None:
    args = parse_args()
    metrics_path = args.metrics.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    indexed_rows = load_rows(metrics_path)
    draw_figure(indexed_rows, output_path, args.dpi)

    print(f"Nguồn dữ liệu : {metrics_path}")
    print(f"Đã lưu ảnh    : {output_path}")


if __name__ == "__main__":
    main()
