"""Vẽ hai Asthma core với preset C4, F0 hoặc cấu hình DSP nhập từ CLI.

Script chỉ trực quan hóa, không huấn luyện và không ghi đè tensor dataset.

Ví dụ chạy từ root repository:
    # Cấu hình C4 hiện tại
    py -3.11 "AI_Training_Model/Phase2_Preprocess_&_Traning/Visualize_Two_Asthma_Core.py"

    # Baseline F0 của Frontend_Benchmarking
    py -3.11 "AI_Training_Model/Phase2_Preprocess_&_Traning/Visualize_Two_Asthma_Core.py" --preset f0

    # Vẽ cả C4 và F0
    py -3.11 "AI_Training_Model/Phase2_Preprocess_&_Traning/Visualize_Two_Asthma_Core.py" --preset both
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, replace
from pathlib import Path

import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import lfilter

import Preprocess_Audio as pipeline


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "Output_Preprocess"
ASTHMA_TRAIN_DIR = pipeline.DATA_DIR / "Asthma" / "train"
DEFAULT_CORE_NAMES = ("P14WheezingRS_68.wav", "P35WheezingIE_173.wav")


@dataclass(frozen=True)
class DSPConfig:
    name: str
    low_cut_hz: float
    high_cut_hz: float
    filter_order: int
    pre_emphasis: float
    n_mels: int
    hop_length: int
    n_fft: int

    @property
    def mel_shape(self) -> tuple[int, int]:
        return self.n_mels, 1 + pipeline.SAMPLES // self.hop_length


# F0 được đối chiếu trực tiếp với configs/candidates.csv của Frontend_Benchmarking.
PRESETS = {
    "c4": DSPConfig(
        name="C4",
        low_cut_hz=pipeline.LOW_CUT,
        high_cut_hz=pipeline.HIGH_CUT,
        filter_order=pipeline.ORDER,
        pre_emphasis=pipeline.PRE_EMPHASIS,
        n_mels=pipeline.N_MELS,
        hop_length=pipeline.HOP_LENGTH,
        n_fft=pipeline.N_FFT,
    ),
    "f0": DSPConfig(
        name="F0",
        low_cut_hz=100.0,
        high_cut_hz=2000.0,
        filter_order=5,
        pre_emphasis=0.97,
        n_mels=64,
        hop_length=625,
        n_fft=1024,
    ),
    "f0_noPre": DSPConfig(
        name="F0_noPre",
        low_cut_hz=100.0,
        high_cut_hz=2000.0,
        filter_order=5,
        pre_emphasis=0,
        n_mels=64,
        hop_length=625,
        n_fft=1024,
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Vẽ hai WAV Asthma core qua preset C4/F0 hoặc DSP tùy chỉnh."
    )
    parser.add_argument(
        "--preset",
        choices=("c4", "f0", "f0_noPre", "both"),
        default="c4",
        help=(
            "c4: cấu hình hiện tại; f0: baseline có pre-emphasis; "
            "f0_noPre: F0 nhưng bỏ pre-emphasis; both: vẽ C4 và F0."
        ),
    )
    parser.add_argument(
        "--files",
        nargs=2,
        metavar=("CORE_1", "CORE_2"),
        default=DEFAULT_CORE_NAMES,
        help=(
            "Hai tên WAV trong Dataset_Chia_V2/Asthma/train hoặc hai đường dẫn WAV. "
            "Mặc định: P14WheezingRS_68.wav và P35WheezingIE_173.wav."
        ),
    )
    parser.add_argument("--low-cut", type=float, default=None)
    parser.add_argument("--high-cut", type=float, default=None)
    parser.add_argument("--order", type=int, default=None)
    parser.add_argument("--pre-emphasis", type=float, default=None)
    parser.add_argument("--n-mels", type=int, default=None)
    parser.add_argument("--hop-length", type=int, default=None)
    parser.add_argument("--n-fft", type=int, default=None)
    parser.add_argument(
        "--tag",
        default=None,
        help="Nhãn ngắn gắn vào tên ảnh khi dùng tham số tùy chỉnh.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Thư mục lưu PNG; mặc định là Output_Preprocess.",
    )
    return parser.parse_args()


def safe_tag(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return cleaned.strip("_.-") or "custom"


def resolve_core_file(value: str) -> Path:
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    if candidate.is_file():
        return candidate.resolve()
    return (ASTHMA_TRAIN_DIR / candidate).resolve()


def has_manual_overrides(args: argparse.Namespace) -> bool:
    return any(
        value is not None
        for value in (
            args.low_cut,
            args.high_cut,
            args.order,
            args.pre_emphasis,
            args.n_mels,
            args.hop_length,
            args.n_fft,
        )
    )


def build_configs(args: argparse.Namespace) -> list[DSPConfig]:
    if args.preset == "both" and has_manual_overrides(args):
        raise ValueError(
            "Không dùng tham số override cùng --preset both. "
            "Hãy chọn riêng --preset c4 hoặc --preset f0."
        )

    preset_names = ("c4", "f0") if args.preset == "both" else (args.preset,)
    configs = []
    for preset_name in preset_names:
        config = PRESETS[preset_name]
        updates = {
            "low_cut_hz": args.low_cut,
            "high_cut_hz": args.high_cut,
            "filter_order": args.order,
            "pre_emphasis": args.pre_emphasis,
            "n_mels": args.n_mels,
            "hop_length": args.hop_length,
            "n_fft": args.n_fft,
        }
        updates = {key: value for key, value in updates.items() if value is not None}
        if updates:
            suffix = safe_tag(args.tag or f"{config.name}_custom")
            config = replace(config, name=suffix, **updates)
        elif args.tag:
            config = replace(config, name=safe_tag(args.tag))
        validate_config(config)
        configs.append(config)
    return configs


def validate_config(config: DSPConfig) -> None:
    nyquist = pipeline.SR / 2.0
    if not 0 < config.low_cut_hz < config.high_cut_hz < nyquist:
        raise ValueError(
            f"Band-pass không hợp lệ: cần 0 < low < high < {nyquist:g} Hz"
        )
    if config.filter_order < 1:
        raise ValueError("--order phải >= 1")
    if not 0.0 <= config.pre_emphasis < 1.0:
        raise ValueError("--pre-emphasis phải trong [0, 1)")
    if config.n_mels < 1 or config.hop_length < 1 or config.n_fft < 2:
        raise ValueError("n_mels, hop_length và n_fft phải là số dương hợp lệ")


def apply_pipeline_stages(file_path: Path, config: DSPConfig):
    """Chạy đúng thứ tự DSP Phase 2 với cấu hình được truyền vào."""
    window = pipeline.load_model_audio_window(file_path)
    normalized = librosa.util.normalize(
        window,
        norm=np.inf,
        axis=0,
        threshold=None,
        fill=None,
    )
    b, a = pipeline.butter_bandpass(
        config.low_cut_hz,
        config.high_cut_hz,
        pipeline.SR,
        config.filter_order,
    )
    filtered = lfilter(b, a, normalized, axis=-1, zi=None)
    model_audio = filtered
    if config.pre_emphasis != 0.0:
        model_audio = librosa.effects.preemphasis(
            filtered,
            coef=config.pre_emphasis,
        )

    mel = librosa.feature.melspectrogram(
        y=model_audio,
        sr=pipeline.SR,
        n_fft=config.n_fft,
        hop_length=config.hop_length,
        win_length=config.n_fft,
        n_mels=config.n_mels,
        fmin=config.low_cut_hz,
        fmax=config.high_cut_hz,
        center=True,
        htk=False,
        norm="slaney",
        window="hann",
        pad_mode="constant",
        power=2.0,
        dtype=pipeline.MEL_DTYPE,
    )
    mel_db = librosa.power_to_db(
        mel,
        ref=np.max,
        amin=pipeline.POWER_AMIN,
        top_db=pipeline.TOP_DB,
    )
    if mel_db.shape != config.mel_shape:
        raise ValueError(
            f"Sai shape Mel của {file_path.name}: "
            f"expected={config.mel_shape}, actual={mel_db.shape}"
        )
    if not np.isfinite(mel_db).all():
        raise ValueError(f"Mel có NaN/Inf: {file_path}")
    return window, model_audio, mel_db


def magnitude_db(audio: np.ndarray, reference: float | None = None):
    """Tính phổ biên độ một phía để minh họa tác dụng band-pass."""
    tapered = audio * np.hanning(len(audio))
    magnitude = np.abs(np.fft.rfft(tapered))
    if reference is None:
        reference = max(float(magnitude.max()), 1e-12)
    db = 20.0 * np.log10(np.maximum(magnitude, 1e-12) / reference)
    frequency = np.fft.rfftfreq(len(audio), d=1.0 / pipeline.SR)
    return frequency, db, reference


def draw_one(
    file_path: Path,
    index: int,
    config: DSPConfig,
    output_dir: Path,
) -> Path:
    if not file_path.is_file():
        raise FileNotFoundError(f"Không tìm thấy Asthma core: {file_path}")
    if "__take" in file_path.stem.casefold() or file_path.name.startswith("AUGV2__"):
        raise ValueError(f"File không phải core nguyên bản: {file_path.name}")

    window, model_audio, mel_db = apply_pipeline_stages(file_path, config)
    time_axis = np.arange(len(window)) / pipeline.SR
    freq_before, db_before, spectrum_ref = magnitude_db(window)
    freq_after, db_after, _ = magnitude_db(model_audio, spectrum_ref)

    fig, axes = plt.subplots(2, 2, figsize=(15, 8.5), facecolor="white")
    fig.suptitle(
        f"Tiền xử lý Asthma core {index} - {config.name}: {file_path.name}",
        fontsize=17,
        fontweight="bold",
        y=0.99,
    )

    axes[0, 0].plot(time_axis, window, color="#2563eb", linewidth=0.8)
    axes[0, 0].set_title("1. Cửa sổ model: mono, resample 16 kHz, crop/pad 5 s")
    axes[0, 0].set(xlabel="Thời gian (s)", ylabel="Biên độ")

    axes[0, 1].plot(time_axis, model_audio, color="#e11d48", linewidth=0.8)
    pre_text = (
        f", pre-emphasis={config.pre_emphasis:g}"
        if config.pre_emphasis != 0.0
        else ", không pre-emphasis"
    )
    axes[0, 1].set_title(
        f"2. Peak-normalize + Butterworth {config.low_cut_hz:g}-"
        f"{config.high_cut_hz:g} Hz, order={config.filter_order}{pre_text}"
    )
    axes[0, 1].set(xlabel="Thời gian (s)", ylabel="Biên độ")

    max_plot_hz = min(4000.0, pipeline.SR / 2.0)
    visible = freq_before <= max_plot_hz
    axes[1, 0].plot(
        freq_before[visible], db_before[visible],
        color="#64748b", linewidth=1.0, label="Trước lọc",
    )
    axes[1, 0].plot(
        freq_after[visible], db_after[visible],
        color="#f97316", linewidth=1.2, label="Sau lọc",
    )
    axes[1, 0].axvspan(
        config.low_cut_hz,
        config.high_cut_hz,
        color="#22c55e",
        alpha=0.12,
        label="Dải giữ lại",
    )
    for cutoff in (config.low_cut_hz, config.high_cut_hz):
        axes[1, 0].axvline(cutoff, color="#16a34a", linestyle="--", linewidth=1)
    axes[1, 0].set(
        title="3. Phổ biên độ trước và sau band-pass",
        xlabel="Tần số (Hz)",
        ylabel="Biên độ tương đối (dB)",
        xlim=(0, max_plot_hz),
        ylim=(-100, 5),
    )
    axes[1, 0].legend(loc="lower right")

    image = librosa.display.specshow(
        mel_db,
        x_axis="time",
        y_axis="mel",
        sr=pipeline.SR,
        fmin=config.low_cut_hz,
        fmax=config.high_cut_hz,
        hop_length=config.hop_length,
        cmap="magma",
        ax=axes[1, 1],
    )
    axes[1, 1].set_title(
        f"4. Log-Mel đầu vào model: {mel_db.shape[0]} × {mel_db.shape[1]} "
        f"(FFT={config.n_fft}, hop={config.hop_length})"
    )
    axes[1, 1].set(xlabel="Thời gian (s)", ylabel="Tần số Mel (Hz)")
    fig.colorbar(image, ax=axes[1, 1], format="%+2.0f dB", pad=0.02)

    for axis in axes.flat:
        axis.set_facecolor("#f8fafc")
        axis.grid(alpha=0.18)

    fig.tight_layout(rect=(0, 0, 1, 0.965))
    config_tag = safe_tag(config.name)
    output_path = output_dir / (
        f"Asthma_Core_{index:02d}_{file_path.stem}__{config_tag}_Preprocess.png"
    )
    fig.savefig(output_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path


def main() -> None:
    args = parse_args()
    configs = build_configs(args)
    core_files = [resolve_core_file(value) for value in args.files]
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print("VẼ HAI ASTHMA CORE THEO PIPELINE PHASE 2")
    for config in configs:
        print(
            f"[{config.name}] fs={pipeline.SR} Hz, duration={pipeline.DURATION:g} s, "
            f"band-pass={config.low_cut_hz:g}-{config.high_cut_hz:g} Hz/order "
            f"{config.filter_order}, pre-emphasis={config.pre_emphasis:g}, "
            f"Mel/FFT/hop={config.n_mels}/{config.n_fft}/{config.hop_length}, "
            f"shape={config.mel_shape}"
        )
        for index, file_path in enumerate(core_files, start=1):
            output_path = draw_one(file_path, index, config, output_dir)
            print(f"  [{index}/2] {file_path.name} -> {output_path}")


if __name__ == "__main__":
    main()
