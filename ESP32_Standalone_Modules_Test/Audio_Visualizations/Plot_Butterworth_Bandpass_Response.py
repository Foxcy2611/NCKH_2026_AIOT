"""Vẽ đáp ứng tần số của bộ lọc Butterworth band-pass trong pipeline.

Mặc định khớp với Phase 2 và Patient Node:

- fs = 16 kHz;
- band-pass = 100-2000 Hz;
- order = 5.

Chạy tại root dự án::

    py -3.11 .\ESP32_Standalone_Modules_Test\Audio_Visualizations\Plot_Butterworth_Bandpass_Response.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter
from scipy.signal import butter, freqz


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "Butterworth_Filter_Visualization"


def calculate_response(
    sample_rate: float,
    low_cut: float,
    high_cut: float,
    order: int,
    frequency_points: int = 32768,
) -> tuple[np.ndarray, np.ndarray]:
    """Thiết kế Butterworth giống pipeline và trả về frequency/gain dB."""
    nyquist = sample_rate / 2.0
    if not 0.0 < low_cut < high_cut < nyquist:
        raise ValueError(
            "Yêu cầu 0 < low_cut < high_cut < fs/2; "
            f"nhận fs={sample_rate}, low={low_cut}, high={high_cut}."
        )
    if order < 1:
        raise ValueError("Order phải là số nguyên dương.")

    b, a = butter(
        order,
        [low_cut / nyquist, high_cut / nyquist],
        btype="band",
        analog=False,
        output="ba",
    )
    angular_frequency, response = freqz(b, a, worN=frequency_points, fs=sample_rate)
    gain_db = 20.0 * np.log10(np.maximum(np.abs(response), 1e-8))
    return angular_frequency, gain_db


def plot_response(
    sample_rate: float,
    low_cut: float,
    high_cut: float,
    order: int,
    output_dir: Path,
) -> tuple[Path, Path]:
    """Vẽ gain dB, passband và hai vạch dọc tại tần số cắt."""
    frequency, gain_db = calculate_response(sample_rate, low_cut, high_cut, order)
    output_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(13.5, 7.2), facecolor="#F4F7FB")
    ax.set_facecolor("#FBFCFE")
    ax.axvspan(
        low_cut,
        high_cut,
        color="#2E8B68",
        alpha=0.11,
        label=f"Passband {low_cut:.0f}-{high_cut:.0f} Hz",
    )
    # Bỏ bin DC vì trục log không biểu diễn được 0 Hz. Trục logarithmic giúp
    # giãn vùng tần số thấp để vạch 100 Hz không dính sát mép trái.
    positive_frequency = frequency > 0.0
    ax.plot(
        frequency[positive_frequency],
        gain_db[positive_frequency],
        color="#315C9B",
        linewidth=2.3,
        label="Butterworth band-pass",
    )

    cutoff_colors = ("#D35454", "#D58A18")
    for cutoff, color in zip((low_cut, high_cut), cutoff_colors):
        ax.axvline(
            cutoff,
            color=color,
            linestyle="--",
            linewidth=1.8,
            label=f"Cutoff {cutoff:.0f} Hz",
        )
        cutoff_gain = float(np.interp(cutoff, frequency, gain_db))
        ax.scatter([cutoff], [cutoff_gain], s=55, color=color, zorder=5)
        ax.annotate(
            f"{cutoff:.0f} Hz\n{cutoff_gain:.1f} dB",
            xy=(cutoff, cutoff_gain),
            xytext=(12, -38 if cutoff == low_cut else -52),
            textcoords="offset points",
            fontsize=9.5,
            fontweight="bold",
            color=color,
            arrowprops={"arrowstyle": "->", "color": color, "linewidth": 1.1},
        )

    ax.axhline(-3.0, color="#77869A", linestyle=":", linewidth=1.3, label="-3 dB")
    ax.set_xscale("log")
    ax.set_xlim(10.0, sample_rate / 2.0)
    major_ticks = [10, 20, 50, 100, 200, 500, 1000, 2000, 4000, 8000]
    major_ticks = [tick for tick in major_ticks if tick <= sample_rate / 2.0]
    ax.set_xticks(major_ticks)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}"))
    ax.set_ylim(-100.0, 5.0)
    ax.set_xlabel("Frequency (Hz)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Magnitude / Gain (dB)", fontsize=11, fontweight="bold")
    ax.set_title(
        "Đáp ứng tần số bộ lọc Butterworth band-pass",
        loc="left",
        fontsize=17,
        fontweight="bold",
        color="#172B4D",
        pad=20,
    )
    ax.text(
        0.0,
        1.015,
        f"order = {order}   ·   fs = {sample_rate / 1000:.0f} kHz   ·   "
        f"cutoff = {low_cut:.0f}-{high_cut:.0f} Hz",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=10.5,
        color="#5D6B82",
    )
    ax.grid(True, which="both", linestyle="--", linewidth=0.75, alpha=0.38)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="lower right", frameon=True, framealpha=0.94, fontsize=9.5)
    fig.tight_layout()

    png_path = output_dir / "Butterworth_Bandpass_100_2000Hz_Order5.png"
    svg_path = output_dir / "Butterworth_Bandpass_100_2000Hz_Order5.svg"
    fig.savefig(png_path, dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(svg_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return png_path, svg_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Vẽ đáp ứng Butterworth band-pass theo gain dB."
    )
    parser.add_argument("--fs", type=float, default=16000.0, help="Sample rate (Hz).")
    parser.add_argument("--low", type=float, default=100.0, help="Low cutoff (Hz).")
    parser.add_argument("--high", type=float, default=2000.0, help="High cutoff (Hz).")
    parser.add_argument("--order", type=int, default=5, help="Bậc Butterworth.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Thư mục lưu PNG và SVG.",
    )
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = (SCRIPT_DIR / output_dir).resolve()

    png_path, svg_path = plot_response(
        sample_rate=args.fs,
        low_cut=args.low,
        high_cut=args.high,
        order=args.order,
        output_dir=output_dir,
    )
    print(f"Đã lưu PNG: {png_path}")
    print(f"Đã lưu SVG: {svg_path}")


if __name__ == "__main__":
    main()
