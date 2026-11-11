"""Vẽ đối chiếu FP32 và QAT INT8 của C4 / V1 / seed 44.

Nguồn số liệu là bảng Test do bước D của Frontend_Benchmarking tạo:

- Test: ``results/D_Quantization/Test/test_summary.csv``

Ảnh gồm Test Accuracy, Test Asthma Recall và số mẫu Asthma bị bỏ sót (FN). Script chỉ
đọc artifact đã có, không train, không lượng tử và không chạy inference lại.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent


def find_repo_root() -> Path:
    """Tìm root repository để script vẫn chạy đúng sau khi được di chuyển."""
    for candidate in (SCRIPT_DIR, *SCRIPT_DIR.parents):
        if (
            (candidate / "AI_Training_Model").is_dir()
            and (candidate / "Experiments_Benchmarking").is_dir()
        ):
            return candidate
    raise FileNotFoundError("Không xác định được root của repository")


REPO_ROOT = find_repo_root()
FRONTEND_ROOT = (
    REPO_ROOT
    / "Experiments_Benchmarking"
    / "Patient_Node"
    / "Frontend_Benchmarking"
)
D_RESULTS = FRONTEND_ROOT / "results" / "D_Quantization"

DEFAULT_TRIAL_ID = "combo_pre0_mel40_fft2048__V1__s44"
METHOD_ORDER = ["KERAS_FP32", "QAT_INT8"]
METHOD_LABELS = {
    "KERAS_FP32": "Keras FP32",
    "QAT_INT8": "QAT INT8",
}
COLORS = {
    "KERAS_FP32": "#3B82F6",
    "QAT_INT8": "#8B5CF6",
}


def load_results(trial_id: str) -> pd.DataFrame:
    """Đọc đúng tập Test và hai phương pháp cần đối chiếu."""
    sources = {
        "Test": D_RESULTS / "Test" / "test_summary.csv",
    }
    frames: list[pd.DataFrame] = []

    for split_label, path in sources.items():
        if not path.is_file():
            raise FileNotFoundError(f"Không tìm thấy bảng kết quả: {path}")

        table = pd.read_csv(path)
        required = {"trial_id", "method_id", "accuracy", "asthma_recall", "asthma_fn"}
        missing = required.difference(table.columns)
        if missing:
            raise ValueError(f"{path.name} thiếu cột: {sorted(missing)}")

        selected = table[
            table["trial_id"].eq(trial_id)
            & table["method_id"].isin(METHOD_ORDER)
        ].copy()
        selected["split_label"] = split_label
        frames.append(selected)

    result = pd.concat(frames, ignore_index=True)
    expected = {("Test", method) for method in METHOD_ORDER}
    actual = set(zip(result["split_label"], result["method_id"]))
    if actual != expected or result.duplicated(["split_label", "method_id"]).any():
        raise ValueError(
            "Kết quả không đủ duy nhất 2 dòng Test × FP32/QAT. "
            f"Thiếu={sorted(expected - actual)}, thừa={sorted(actual - expected)}"
        )

    result["accuracy_pct"] = pd.to_numeric(result["accuracy"]) * 100.0
    result["asthma_recall_pct"] = pd.to_numeric(result["asthma_recall"]) * 100.0
    result["asthma_fn"] = pd.to_numeric(result["asthma_fn"]).astype(int)
    return result


def value_matrix(data: pd.DataFrame, column: str) -> np.ndarray:
    """Trả ma trận [method, split] theo thứ tự cố định để vẽ."""
    values = []
    for method in METHOD_ORDER:
        row = []
        for split in ("Validation", "Test"):
            match = data[data["method_id"].eq(method) & data["split_label"].eq(split)]
            row.append(float(match.iloc[0][column]))
        values.append(row)
    return np.asarray(values)


def annotate_bars(ax, bars, suffix: str, decimals: int = 2) -> None:
    for bar in bars:
        value = bar.get_height()
        label = f"{value:.{decimals}f}{suffix}"
        ax.annotate(
            label,
            (bar.get_x() + bar.get_width() / 2, value),
            xytext=(0, 6),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
            color="#172033",
        )


def draw_comparison(data: pd.DataFrame, output_path: Path, dpi: int) -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.titleweight": "bold",
            "axes.edgecolor": "#CBD5E1",
            "axes.labelcolor": "#334155",
            "xtick.color": "#334155",
            "ytick.color": "#334155",
        }
    )

    # Grouped column chart: bố cục gần vuông, phù hợp chèn cạnh ảnh
    # classification report trong báo cáo hoặc slide.
    fig, (ax_pct, ax_fn) = plt.subplots(
        1,
        2,
        figsize=(7.6, 4.4),
        gridspec_kw={"width_ratios": [1.9, 1.0]},
        facecolor="#F8FAFC",
    )

    percentage_rows = [
        ("Accuracy", "Test", "accuracy_pct"),
        ("Asthma Recall", "Test", "asthma_recall_pct"),
    ]
    x_pct = np.arange(len(percentage_rows))
    bar_width = 0.34
    pct_values: dict[str, list[float]] = {method: [] for method in METHOD_ORDER}
    for _, split, column in percentage_rows:
        for method in METHOD_ORDER:
            match = data[data["split_label"].eq(split) & data["method_id"].eq(method)]
            pct_values[method].append(float(match.iloc[0][column]))

    for method_index, method in enumerate(METHOD_ORDER):
        offset = (method_index - 0.5) * bar_width
        bars = ax_pct.bar(
            x_pct + offset,
            pct_values[method],
            bar_width,
            color=COLORS[method],
            edgecolor="white",
            linewidth=1.0,
            label=METHOD_LABELS[method],
            zorder=3,
        )
        annotate_bars(ax_pct, bars, suffix="%", decimals=2)

    pct_min = min(min(values) for values in pct_values.values())
    ax_pct.set_ylim(max(70.0, pct_min - 6.0), 104.0)
    ax_pct.set_xticks(x_pct, [row[0] for row in percentage_rows])
    ax_pct.set_ylabel("Kết quả (%)")
    ax_pct.set_title("Accuracy và Asthma Recall", pad=10, color="#0F172A")
    ax_pct.grid(axis="y", color="#E2E8F0", linewidth=0.8, zorder=0)
    ax_pct.spines[["top", "right"]].set_visible(False)

    fn_rows = [("Test", "Test")]
    x_fn = np.arange(len(fn_rows))
    fn_values: dict[str, list[int]] = {method: [] for method in METHOD_ORDER}
    for _, split in fn_rows:
        for method in METHOD_ORDER:
            match = data[data["split_label"].eq(split) & data["method_id"].eq(method)]
            fn_values[method].append(int(match.iloc[0]["asthma_fn"]))

    for method_index, method in enumerate(METHOD_ORDER):
        offset = (method_index - 0.5) * bar_width
        bars = ax_fn.bar(
            x_fn + offset,
            fn_values[method],
            bar_width,
            color=COLORS[method],
            edgecolor="white",
            linewidth=1.0,
            zorder=3,
        )
        annotate_bars(ax_fn, bars, suffix="", decimals=0)

    ax_fn.set_ylim(0, max(max(values) for values in fn_values.values()) + 2.0)
    ax_fn.set_xticks(x_fn, [row[0] for row in fn_rows])
    ax_fn.set_ylabel("Số mẫu FN")
    ax_fn.set_title("Asthma bị bỏ sót", pad=10, color="#0F172A")
    ax_fn.grid(axis="y", color="#E2E8F0", linewidth=0.8, zorder=0)
    ax_fn.spines[["top", "right"]].set_visible(False)
    ax_fn.yaxis.get_major_locator().set_params(integer=True)

    handles, labels = ax_pct.get_legend_handles_labels()
    fig.legend(
        handles, labels,
        loc="upper center", bbox_to_anchor=(0.5, 0.855), ncol=2,
        frameon=False, fontsize=9.5, columnspacing=2.0, handletextpad=0.6,
    )
    fig.suptitle(
        "C4 · V1 · seed 44 — FP32 và QAT INT8 trên Test (n=159)",
        fontsize=16,
        fontweight="bold",
        color="#0F172A",
        y=0.985,
    )
    fig.text(
        0.5,
        0.925,
        "Quy tắc đánh giá nhị phân: p(Non-Asthma) ≥ 0.5 → Non-Asthma",
        ha="center",
        color="#64748B",
        fontsize=9.5,
    )
    fig.subplots_adjust(top=0.70, bottom=0.15, left=0.09, right=0.98, wspace=0.36)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> None:
    # PowerShell/Windows có thể mặc định dùng cp1252; ép UTF-8 để note tiếng
    # Việt không làm script lỗi sau khi ảnh đã được lưu.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trial-id", default=DEFAULT_TRIAL_ID)
    parser.add_argument(
        "--output",
        type=Path,
        default=SCRIPT_DIR / "C4_V1_s44_FP32_vs_QAT_INT8.png",
        help="Đường dẫn ảnh PNG đầu ra.",
    )
    parser.add_argument("--dpi", type=int, default=110)
    args = parser.parse_args()

    data = load_results(args.trial_id)
    output_path = args.output.expanduser()
    if not output_path.is_absolute():
        output_path = REPO_ROOT / output_path
    output_path = output_path.resolve()

    draw_comparison(data, output_path, args.dpi)
    print(data[["split_label", "method_id", "accuracy_pct", "asthma_recall_pct", "asthma_fn"]].to_string(index=False))
    print(f"\nĐã lưu ảnh: {output_path}")


if __name__ == "__main__":
    main()
