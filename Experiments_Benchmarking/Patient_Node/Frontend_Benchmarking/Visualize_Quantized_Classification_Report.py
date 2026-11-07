"""Vẽ bảng metric Validation/Test của một model FP32 hoặc đã lượng tử.

Cách chạy ngắn nhất: sửa ``EVALUATION_FOLDER`` và ``DEFAULT_SPLIT`` ở phần
``CẤU HÌNH CHẠY NHANH`` bên dưới, sau đó chạy trực tiếp script::

    py -3.11 .\Visualize_Quantized_Classification_Report.py

Nếu cần ghi đè cấu hình mà không sửa file, vẫn có thể truyền folder qua CLI::

    py -3.11 .\Visualize_Quantized_Classification_Report.py ^
      .\artifacts\D_Quantization\F0__V1__s43\evaluation\PTQ_INT8 --split val

    py -3.11 .\Visualize_Quantized_Classification_Report.py ^
      .\artifacts\D_Quantization\F0__V1__s43\evaluation\QAT_INT8 --split test

Folder có thể là ``KERAS_FP32``, ``PTQ_INT8``, ``QAT_INT8`` hoặc
``PTQ_INT16x8``. Script đọc ``<split>_classification_report.txt`` và lưu ảnh
``<split>_classification_metrics.png`` trở lại chính folder được truyền vào.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


REPORT_TEMPLATE = "{split}_classification_report.txt"
FIGURE_TEMPLATE = "{split}_classification_metrics.png"
SPLIT_LABELS = {"val": "Validation", "test": "Test"}


# =============================================================================
# CẤU HÌNH CHẠY NHANH
# =============================================================================
# Chỉ cần thay đường dẫn folder bên dưới. Có thể dùng đường dẫn tương đối tính từ
# thư mục Frontend_Benchmarking hoặc đường dẫn tuyệt đối dạng Path(r"D:\\...").
# Folder đích phải chứa val_classification_report.txt và/hoặc
# test_classification_report.txt.
SCRIPT_DIR = Path(__file__).resolve().parent
EVALUATION_FOLDER = (
    SCRIPT_DIR
    / "artifacts"
    / "D_Quantization"
    / "combo_pre0_mel40_fft2048__V1__s44"
    / "evaluation"
    / "QAT_INT8"
)

# Chọn một trong ba giá trị: "val", "test", "both".
DEFAULT_SPLIT = "both"


def _find_value(pattern: str, text: str, field_name: str) -> str:
    match = re.search(pattern, text, flags=re.MULTILINE | re.IGNORECASE)
    if match is None:
        raise ValueError(f"Không tìm thấy {field_name} trong classification report.")
    return match.group(1)


def _parse_metric_row(text: str, row_name: str) -> dict[str, float | int]:
    pattern = (
        rf"^\s*{re.escape(row_name)}\s+"
        rf"([0-9]*\.?[0-9]+)\s+"
        rf"([0-9]*\.?[0-9]+)\s+"
        rf"([0-9]*\.?[0-9]+)\s+"
        rf"(\d+)\s*$"
    )
    match = re.search(pattern, text, flags=re.MULTILINE | re.IGNORECASE)
    if match is None:
        raise ValueError(f"Không đọc được dòng '{row_name}'.")
    return {
        "precision": float(match.group(1)),
        "recall": float(match.group(2)),
        "f1": float(match.group(3)),
        "support": int(match.group(4)),
    }


def parse_report(report_path: Path) -> dict[str, object]:
    text = report_path.read_text(encoding="utf-8-sig", errors="replace")
    normalized = text.replace("Non_Asthma", "Non-Asthma")
    rows = {
        "Asthma": _parse_metric_row(normalized, "Asthma"),
        "Non-Asthma": _parse_metric_row(normalized, "Non-Asthma"),
        "Macro avg": _parse_metric_row(normalized, "macro avg"),
        "Weighted avg": _parse_metric_row(normalized, "weighted avg"),
    }
    accuracy = float(
        _find_value(
            r"^\s*(?:Keras\s+(?:val|validation|test)\s+)?"
            r"Accuracy\s*:\s*([0-9]*\.?[0-9]+)\s*$",
            text,
            "Accuracy",
        )
    )
    total = int(rows["Macro avg"]["support"])
    return {
        "accuracy": accuracy,
        "correct": int(round(accuracy * total)),
        "total": total,
        "rows": rows,
    }


def identify_model(method_folder: Path) -> tuple[str, str]:
    """Suy ra trial và method từ layout ``<trial>/evaluation/<method>``."""
    if method_folder.parent.name.lower() == "evaluation":
        trial_id = method_folder.parent.parent.name
        method_id = method_folder.name
    else:
        # Hỗ trợ trực tiếp artifacts/models/<trial> cho Keras FP32.
        trial_id = method_folder.name
        method_id = "KERAS_FP32"
    return trial_id.replace("__", "_"), method_id.replace("_", " ")


def draw_report(
    data: dict[str, object],
    method_folder: Path,
    split: str,
    output_path: Path,
) -> None:
    row_names = ["Asthma", "Non-Asthma", "Macro avg", "Weighted avg"]
    metric_names = ["Precision", "Recall", "F1-score"]
    rows = data["rows"]
    matrix = np.array(
        [
            [rows[name]["precision"], rows[name]["recall"], rows[name]["f1"]]
            for name in row_names
        ],
        dtype=np.float64,
    )

    fig, ax = plt.subplots(figsize=(9.6, 6.0), facecolor="#f6f8fb")
    ax.set_facecolor("#f6f8fb")
    image = ax.imshow(matrix, cmap="YlGnBu", vmin=0.80, vmax=1.00, aspect="auto")
    ax.set_xticks(np.arange(3), labels=metric_names)
    ax.set_yticks(
        np.arange(4),
        labels=[f"{name}   ·   n = {rows[name]['support']}" for name in row_names],
    )
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", which="both", length=0, pad=12, labelsize=11)
    ax.tick_params(axis="y", which="both", length=0, pad=10, labelsize=10)

    for row_index in range(matrix.shape[0]):
        for col_index in range(matrix.shape[1]):
            value = matrix[row_index, col_index]
            ax.text(
                col_index,
                row_index,
                f"{value:.3f}\n{value * 100:.1f}%",
                ha="center",
                va="center",
                fontsize=11,
                fontweight="bold",
                color="white" if value >= 0.91 else "#17324d",
            )

    ax.axhline(1.5, color="white", linewidth=5)
    for spine in ax.spines.values():
        spine.set_visible(False)

    colorbar = fig.colorbar(image, ax=ax, fraction=0.035, pad=0.04)
    colorbar.set_label("Điểm metric", rotation=270, labelpad=16)
    colorbar.outline.set_visible(False)

    trial_name, method_name = identify_model(method_folder)
    fig.text(
        0.08,
        0.955,
        f"{trial_name} · {method_name} · {SPLIT_LABELS[split]}",
        ha="left",
        va="top",
        fontsize=14,
        fontweight="bold",
        color="#24364b",
    )
    fig.text(
        0.08,
        0.905,
        f"ACCURACY  {data['accuracy'] * 100:.2f}%    |    "
        f"ĐÚNG {data['correct']}/{data['total']}",
        ha="left",
        va="top",
        fontsize=11,
        fontweight="bold",
        color="#147a50",
        bbox={
            "boxstyle": "round,pad=0.38",
            "facecolor": "#e7f7ec",
            "edgecolor": "#a8dfb8",
        },
    )
    fig.text(
        0.08,
        0.855,
        "Giá trị càng gần 1.0 càng tốt · Support (n) là số mẫu nhãn thật "
        "· Thang màu 0.80-1.00",
        ha="left",
        va="top",
        fontsize=9,
        color="#6c7b8c",
    )
    fig.subplots_adjust(left=0.25, right=0.89, top=0.78, bottom=0.08)
    fig.savefig(output_path, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def resolve_folder(raw_path: str | Path) -> Path:
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = (SCRIPT_DIR / candidate).resolve()
    return candidate.resolve()


def render_split(method_folder: Path, split: str) -> Path:
    report_path = method_folder / REPORT_TEMPLATE.format(split=split)
    if not report_path.is_file():
        raise FileNotFoundError(f"Không tìm thấy report: {report_path}")
    output_path = method_folder / FIGURE_TEMPLATE.format(split=split)
    data = parse_report(report_path)
    draw_report(data, method_folder, split, output_path)
    print(f"{split.upper():4s} | {data['accuracy'] * 100:.2f}% "
          f"({data['correct']}/{data['total']}) | {output_path}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Vẽ classification metrics từ folder evaluation của một model."
    )
    parser.add_argument(
        "evaluation_folder",
        nargs="?",
        default=None,
        help="Folder KERAS_FP32/PTQ_INT8/QAT_INT8/PTQ_INT16x8 cần vẽ.",
    )
    parser.add_argument(
        "--split",
        choices=("val", "test", "both"),
        default=None,
        help=(
            "Chọn Validation, Test hoặc cả hai. Nếu bỏ trống, dùng "
            "DEFAULT_SPLIT trong script."
        ),
    )
    args = parser.parse_args()

    selected_folder = args.evaluation_folder or EVALUATION_FOLDER
    selected_split = args.split or DEFAULT_SPLIT

    method_folder = resolve_folder(selected_folder)
    if not method_folder.is_dir():
        raise FileNotFoundError(f"Không tồn tại folder evaluation: {method_folder}")

    splits = ("val", "test") if selected_split == "both" else (selected_split,)
    for split in splits:
        render_split(method_folder, split)


if __name__ == "__main__":
    main()
