"""Áp dụng Butterworth band-pass lên một WAV thật và vẽ trước/sau.

Script dùng trực tiếp các hàm trong pipeline Phase 2 để bảo đảm cùng:

- resample 16 kHz và cửa sổ 5 giây;
- peak normalization;
- Butterworth band-pass 100-2000 Hz, order 5;
- ``scipy.signal.lfilter`` với hệ số ``b, a`` giống huấn luyện.

Mặc định thử trên ``P14WheezingRS_68.wav``. Script không ghi đè WAV nguồn.

Chạy tại root repository::

    py -3.11 .\ESP32_Standalone_Modules_Test\Audio_Visualizations\Apply_Butterworth_To_Audio.py
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf
from scipy.integrate import trapezoid
from scipy.signal import welch


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
AI_DIR = PROJECT_ROOT / "AI_Training_Model"
PHASE2_PREPROCESS_PATH = (
    AI_DIR / "Phase2_Preprocess_&_Traning" / "Preprocess_Audio.py"
)
DEFAULT_INPUT = (
    AI_DIR
    / "Dataset_Chia_V2"
    / "Asthma"
    / "train"
    / "P14WheezingRS_68.wav"
)
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "Butterworth_Audio_Experiment"


def load_phase2_preprocess():
    """Nạp đúng module preprocess Phase 2 nhưng không chạy process toàn dataset."""
    if not PHASE2_PREPROCESS_PATH.is_file():
        raise FileNotFoundError(
            f"Không tìm thấy pipeline Phase 2: {PHASE2_PREPROCESS_PATH}"
        )
    spec = importlib.util.spec_from_file_location(
        "phase2_preprocess_for_butterworth_experiment",
        PHASE2_PREPROCESS_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Không thể nạp module: {PHASE2_PREPROCESS_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def resolve_input(path_argument: str | None) -> Path:
    """Giải WAV từ đường dẫn tuyệt đối, tương đối root hoặc tên file mặc định."""
    if not path_argument:
        candidate = DEFAULT_INPUT
    else:
        candidate = Path(path_argument).expanduser()
        if not candidate.is_absolute():
            candidate = (PROJECT_ROOT / candidate).resolve()

    if not candidate.is_file():
        raise FileNotFoundError(f"Không tìm thấy WAV input: {candidate}")
    if candidate.suffix.casefold() != ".wav":
        raise ValueError(f"Input phải là WAV: {candidate}")
    return candidate.resolve()


def peak_normalize_like_pipeline(audio: np.ndarray) -> np.ndarray:
    """Chuẩn hóa L-infinity tương đương bước Librosa trong pipeline Phase 2."""
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak <= np.finfo(np.float32).eps:
        return audio.astype(np.float32, copy=True)
    return (audio / peak).astype(np.float32, copy=False)


def calculate_psd(audio: np.ndarray, sample_rate: int) -> tuple[np.ndarray, np.ndarray]:
    """Tính Welch PSD để phổ dễ đọc hơn FFT thô."""
    frequency, power = welch(
        audio,
        fs=sample_rate,
        window="hann",
        nperseg=2048,
        noverlap=1024,
        detrend="constant",
        scaling="density",
    )
    return frequency, power


def band_energy_ratio(
    frequency: np.ndarray,
    power: np.ndarray,
    low_cut: float,
    high_cut: float,
) -> float:
    """Tính tỷ lệ năng lượng PSD nằm trong passband."""
    total = float(trapezoid(power, frequency))
    mask = (frequency >= low_cut) & (frequency <= high_cut)
    inside = float(trapezoid(power[mask], frequency[mask]))
    return inside / total if total > 0.0 else 0.0


def plot_before_after(
    original: np.ndarray,
    filtered: np.ndarray,
    sample_rate: int,
    input_path: Path,
    pipeline,
    output_path: Path,
) -> dict[str, float]:
    """Vẽ waveform trước/sau và PSD Welch dùng chung mốc dB."""
    time_axis = np.arange(original.size, dtype=np.float32) / sample_rate
    frequency_before, power_before = calculate_psd(original, sample_rate)
    frequency_after, power_after = calculate_psd(filtered, sample_rate)
    common_reference = max(float(power_before.max()), float(power_after.max()), 1e-20)
    before_db = 10.0 * np.log10(np.maximum(power_before / common_reference, 1e-12))
    after_db = 10.0 * np.log10(np.maximum(power_after / common_reference, 1e-12))

    before_ratio = band_energy_ratio(
        frequency_before,
        power_before,
        pipeline.LOW_CUT,
        pipeline.HIGH_CUT,
    )
    after_ratio = band_energy_ratio(
        frequency_after,
        power_after,
        pipeline.LOW_CUT,
        pipeline.HIGH_CUT,
    )
    rms_before = float(np.sqrt(np.mean(np.square(original))))
    rms_after = float(np.sqrt(np.mean(np.square(filtered))))

    fig = plt.figure(figsize=(14, 10), facecolor="#F4F7FB")
    grid = fig.add_gridspec(3, 1, height_ratios=[1, 1, 1.35], hspace=0.40)
    axes = [fig.add_subplot(grid[index, 0]) for index in range(3)]

    waveform_specs = (
        (original, "Trước Butterworth", "#3B6FB6", rms_before),
        (filtered, "Sau Butterworth 100–2000 Hz", "#27845B", rms_after),
    )
    for ax, (audio, title, color, rms) in zip(axes[:2], waveform_specs):
        ax.plot(time_axis, audio, color=color, linewidth=0.65)
        ax.fill_between(time_axis, audio, 0.0, color=color, alpha=0.15)
        ax.set_xlim(0.0, len(audio) / sample_rate)
        ax.set_ylim(-1.05, 1.05)
        ax.set_ylabel("Biên độ")
        ax.set_title(
            f"{title} · RMS = {rms:.4f}",
            loc="left",
            fontsize=11.5,
            fontweight="bold",
            color="#172B4D",
        )
        ax.grid(True, linestyle="--", linewidth=0.7, alpha=0.32)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[1].set_xlabel("Thời gian (giây)")

    spectrum_ax = axes[2]
    positive = frequency_before >= 10.0
    spectrum_ax.semilogx(
        frequency_before[positive],
        before_db[positive],
        color="#7B8797",
        linewidth=1.35,
        alpha=0.9,
        label=f"Trước lọc · in-band {before_ratio:.1%}",
    )
    spectrum_ax.semilogx(
        frequency_after[positive],
        after_db[positive],
        color="#27845B",
        linewidth=1.8,
        label=f"Sau lọc · in-band {after_ratio:.1%}",
    )
    spectrum_ax.axvspan(
        pipeline.LOW_CUT,
        pipeline.HIGH_CUT,
        color="#2E8B68",
        alpha=0.10,
        label="Passband",
    )
    for cutoff, color in (
        (pipeline.LOW_CUT, "#D35454"),
        (pipeline.HIGH_CUT, "#D58A18"),
    ):
        spectrum_ax.axvline(
            cutoff,
            color=color,
            linestyle="--",
            linewidth=1.5,
            label=f"{cutoff:.0f} Hz",
        )
    spectrum_ax.set_xlim(10.0, sample_rate / 2.0)
    spectrum_ax.set_ylim(-100.0, 5.0)
    spectrum_ax.set_xlabel("Frequency (Hz)")
    spectrum_ax.set_ylabel("PSD tương đối (dB)")
    spectrum_ax.set_title(
        "Phổ Welch trước và sau lọc",
        loc="left",
        fontsize=11.5,
        fontweight="bold",
        color="#172B4D",
    )
    spectrum_ax.grid(True, which="both", linestyle="--", linewidth=0.7, alpha=0.32)
    spectrum_ax.spines["top"].set_visible(False)
    spectrum_ax.spines["right"].set_visible(False)
    spectrum_ax.legend(loc="lower right", ncols=2, fontsize=8.7)

    fig.suptitle(
        "Thử nghiệm Butterworth band-pass trên WAV thật",
        x=0.07,
        y=0.985,
        ha="left",
        fontsize=17,
        fontweight="bold",
        color="#172B4D",
    )
    fig.text(
        0.07,
        0.955,
        (
            f"{input_path.name} · fs = {sample_rate / 1000:.0f} kHz · "
            f"cutoff = {pipeline.LOW_CUT:.0f}–{pipeline.HIGH_CUT:.0f} Hz · "
            f"order = {pipeline.ORDER} · scipy.signal.lfilter"
        ),
        ha="left",
        fontsize=9.8,
        color="#5D6B82",
    )
    fig.subplots_adjust(left=0.075, right=0.98, bottom=0.065, top=0.91)
    fig.savefig(output_path, dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    return {
        "rms_before": rms_before,
        "rms_after": rms_after,
        "in_band_energy_ratio_before": before_ratio,
        "in_band_energy_ratio_after": after_ratio,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Áp dụng Butterworth 100–2000 Hz lên WAV thật và vẽ trước/sau."
    )
    parser.add_argument(
        "--input",
        help="Đường dẫn WAV; mặc định dùng Asthma core P14WheezingRS_68.wav.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Thư mục lưu ảnh, WAV đã lọc và metadata.",
    )
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args()
    input_path = resolve_input(args.input)
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = (SCRIPT_DIR / output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    pipeline = load_phase2_preprocess()
    model_window = pipeline.load_model_audio_window(input_path)
    normalized = peak_normalize_like_pipeline(model_window)
    filtered = np.asarray(
        pipeline.apply_bandpass_filter(normalized),
        dtype=np.float32,
    )

    stem = input_path.stem
    image_path = output_dir / f"{stem}_Butterworth_Before_After.png"
    wav_path = output_dir / f"{stem}_Butterworth_100_2000Hz_Order5.wav"
    metadata_path = output_dir / f"{stem}_Butterworth_Metrics.json"

    metrics = plot_before_after(
        normalized,
        filtered,
        pipeline.SR,
        input_path,
        pipeline,
        image_path,
    )
    # Không chuẩn hóa lại sau lọc: WAV phản ánh đúng đầu ra lfilter của pipeline.
    sf.write(
        wav_path,
        np.clip(filtered, -1.0, 1.0),
        pipeline.SR,
        subtype="PCM_16",
    )
    metadata = {
        "input_wav": str(input_path),
        "sample_rate_hz": pipeline.SR,
        "duration_seconds": pipeline.DURATION,
        "low_cut_hz": pipeline.LOW_CUT,
        "high_cut_hz": pipeline.HIGH_CUT,
        "butterworth_order": pipeline.ORDER,
        "filter_function": "scipy.signal.lfilter",
        **metrics,
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Input         : {input_path}")
    print(f"Ảnh trước/sau: {image_path}")
    print(f"WAV đã lọc   : {wav_path}")
    print(f"Metrics JSON : {metadata_path}")


if __name__ == "__main__":
    main()
