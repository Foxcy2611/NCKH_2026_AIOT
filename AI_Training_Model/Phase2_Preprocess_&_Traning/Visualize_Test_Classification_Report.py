"""Vẽ bảng chỉ số Test từ ``Test_Report.txt`` của một thư mục output model.

Cách dùng ngắn gọn từ thư mục ``Phase2_Preprocess_&_Traning``::

    py -3.11 .\Visualize_Test_Classification_Report.py \
        .\Output_Train_V1_SepConv2D_Flatten

Muốn vẽ model khác chỉ cần thay đường dẫn folder. Script tự đọc
``<folder>/Test_Report.txt`` và lưu ``<folder>/Test_Classification_Metrics.png``.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_FOLDER = SCRIPT_DIR / "Output_Train_V1_SepConv2D_Flatten"
REPORT_FILE_NAME = "Test_Report.txt"
FIGURE_FILE_NAME = "Test_Classification_Metrics.png"


def _find_value(pattern: str, text: str, field_name: str) -> str:
    match = re.search(pattern, text, flags=re.MULTILINE | re.IGNORECASE)
    if match is None:
        raise ValueError(f"Không tìm thấy {field_name} trong {REPORT_FILE_NAME}.")
    return match.group(1)


def _parse_metric_row(text: str, row_name: str) -> dict[str, float | int]:
    escaped_name = re.escape(row_name)
    pattern = (
        rf"^\s*{escaped_name}\s+"
        rf"([0-9]*\.?[0-9]+)\s+"
        rf"([0-9]*\.?[0-9]+)\s+"
        rf"([0-9]*\.?[0-9]+)\s+"
        rf"(\d+)\s*$"
    )
    match = re.search(pattern, text, flags=re.MULTILINE | re.IGNORECASE)
    if match is None:
        raise ValueError(f"Không đọc được dòng '{row_name}' trong {REPORT_FILE_NAME}.")
    return {
        "precision": float(match.group(1)),
        "recall": float(match.group(2)),
        "f1": float(match.group(3)),
        "support": int(match.group(4)),
    }


def parse_test_report(report_path: Path) -> dict[str, object]:
    text = report_path.read_text(encoding="utf-8-sig", errors="replace")
    # Các report lịch sử dùng cả ``Non_Asthma`` và ``Non-Asthma``.
    normalized_text = text.replace("Non_Asthma", "Non-Asthma")
    rows = {
        "Asthma": _parse_metric_row(normalized_text, "Asthma"),
        "Non-Asthma": _parse_metric_row(normalized_text, "Non-Asthma"),
        "Macro avg": _parse_metric_row(normalized_text, "macro avg"),
        "Weighted avg": _parse_metric_row(normalized_text, "weighted avg"),
    }

    accuracy = float(
        _find_value(
            r"^\s*(?:Test\s+)?Accuracy\s*:\s*([0-9]*\.?[0-9]+)\s*$",
            text,
            "Test Accuracy",
        )
    )
    variant_match = re.search(r"^\s*Variant\s*:\s*(.+?)\s*$", text, re.MULTILINE)
    variant = variant_match.group(1).strip() if variant_match else "không ghi variant"
    total = int(rows["Macro avg"]["support"])
    correct = int(round(accuracy * total))

    return {
        "accuracy": accuracy,
        "correct": correct,
        "total": total,
        "variant": variant,
        "rows": rows,
    }


def _display_model_name(folder: Path) -> str:
    name = folder.name
    return name.removeprefix("Output_Train_").replace("_", " ")


def draw_report(data: dict[str, object], folder: Path, output_path: Path) -> None:
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

    ax.set_xticks(np.arange(len(metric_names)), labels=metric_names)
    labels = [f"{name}   ·   n = {rows[name]['support']}" for name in row_names]
    ax.set_yticks(np.arange(len(row_names)), labels=labels)
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", which="both", length=0, pad=12, labelsize=11)
    ax.tick_params(axis="y", which="both", length=0, pad=10, labelsize=10)

    for row_index in range(matrix.shape[0]):
        for col_index in range(matrix.shape[1]):
            value = matrix[row_index, col_index]
            color = "white" if value >= 0.91 else "#17324d"
            ax.text(
                col_index,
                row_index,
                f"{value:.3f}\n{value * 100:.1f}%",
                ha="center",
                va="center",
                fontsize=11,
                fontweight="bold",
                color=color,
            )

    # Tách hai lớp thật khỏi hai hàng trung bình để bảng dễ đọc.
    ax.axhline(1.5, color="white", linewidth=5)
    for spine in ax.spines.values():
        spine.set_visible(False)

    colorbar = fig.colorbar(image, ax=ax, fraction=0.035, pad=0.04)
    colorbar.set_label("Điểm metric", rotation=270, labelpad=16)
    colorbar.outline.set_visible(False)

    model_name = _display_model_name(folder)
    fig.text(
        0.08,
        0.955,
        f"{model_name} · {data['variant']} · Test",
        ha="left",
        va="top",
        fontsize=15,
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


def resolve_folder(raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        cwd_candidate = (Path.cwd() / candidate).resolve()
        script_candidate = (SCRIPT_DIR / candidate).resolve()
        candidate = cwd_candidate if cwd_candidate.is_dir() else script_candidate
    return candidate.resolve()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Đọc <output_folder>/Test_Report.txt và vẽ ảnh chỉ số Test "
            "ngay trong folder đó."
        )
    )
    parser.add_argument(
        "output_folder",
        nargs="?",
        default=str(DEFAULT_OUTPUT_FOLDER),
        help="Folder output model; mặc định là Output_Train_V1_SepConv2D_Flatten.",
    )
    args = parser.parse_args()

    folder = resolve_folder(args.output_folder)
    if not folder.is_dir():
        raise FileNotFoundError(f"Không tồn tại folder output: {folder}")

    report_path = folder / REPORT_FILE_NAME
    if not report_path.is_file():
        raise FileNotFoundError(f"Không tìm thấy report: {report_path}")

    output_path = folder / FIGURE_FILE_NAME
    data = parse_test_report(report_path)
    draw_report(data, folder, output_path)

    print(f"Report : {report_path}")
    print(f"Image  : {output_path}")
    print(
        f"Test Accuracy: {data['accuracy'] * 100:.2f}% "
        f"({data['correct']}/{data['total']})"
    )


if __name__ == "__main__":
    main()
