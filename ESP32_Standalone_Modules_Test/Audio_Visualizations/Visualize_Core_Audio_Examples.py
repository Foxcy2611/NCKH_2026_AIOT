"""Vẽ waveform và Log-Mel của bốn bản ghi đại diện.

Mặc định script chọn:

- Asthma core: ``P14WheezingRS_68.wav``;
- Non-Asthma core: ``P16COPDPr_127.wav`` (COPD);
- Asthma playback: ``AST_004__P14WheezingRS_68__take01.wav``;
- Environment: ``ENV__room_noise__room_noise_session_06__clip01.wav``.

Waveform được vẽ từ đúng cửa sổ 5 giây sau resample/fix-length, chuẩn hóa đỉnh
và Butterworth C4. Log-Mel được tạo bằng chính các hàm trong
``Phase2_Preprocess_&_Traning/Preprocess_Audio.py`` để giữ đúng pipeline model
C4: 100–2000 Hz/order 5, pre-emphasis 0, 40 Mel, FFT 2048 và hop 625.

Chạy tại root dự án::

    py -3.11 .\ESP32_Standalone_Modules_Test\Audio_Visualizations\Visualize_Core_Audio_Examples.py

Có thể chỉ định WAV khác bằng ``--asthma``, ``--non-asthma``, ``--playback``
và ``--environment``.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault(
    "NUMBA_CACHE_DIR",
    str(Path(tempfile.gettempdir()) / "nckh_numba_cache"),
)

import librosa
import librosa.display
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
AI_DIR = PROJECT_ROOT / "AI_Training_Model"
DATASET_DIR = AI_DIR / "Dataset_Chia_V2"
PHASE2_PREPROCESS_PATH = (
    AI_DIR / "Phase2_Preprocess_&_Traning" / "Preprocess_Audio.py"
)
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "Core_Audio_Visualization"

DEFAULT_ASTHMA = (
    DATASET_DIR / "Asthma" / "train" / "P14WheezingRS_68.wav"
)
DEFAULT_NON_ASTHMA = (
    DATASET_DIR
    / "Non_Asthma_Disease"
    / "train"
    / "P16COPDPr_127.wav"
)
DEFAULT_PLAYBACK = (
    DATASET_DIR
    / "Asthma"
    / "train"
    / "AST_004__P14WheezingRS_68__take01.wav"
)
DEFAULT_ENVIRONMENT = (
    DATASET_DIR
    / "Non_Asthma_Disease"
    / "test"
    / "ENV__room_noise__room_noise_session_06__clip01.wav"
)

AUGMENTATION_MARKERS = (
    "mix_environment",
    "time_shift",
    "white_noise",
    "time_stretch",
    "pitch_shift",
)

C4_EXPECTED = {
    "SR": 16000,
    "SAMPLES": 80000,
    "LOW_CUT": 100.0,
    "HIGH_CUT": 2000.0,
    "ORDER": 5,
    "PRE_EMPHASIS": 0.0,
    "N_MELS": 40,
    "N_FFT": 2048,
    "HOP_LENGTH": 625,
    "TOP_DB": 80.0,
}


def load_phase2_preprocess():
    """Nạp module Phase 2 theo đường dẫn tuyệt đối mà không chạy hàm main()."""
    if not PHASE2_PREPROCESS_PATH.is_file():
        raise FileNotFoundError(
            f"Không tìm thấy pipeline Phase 2: {PHASE2_PREPROCESS_PATH}"
        )

    spec = importlib.util.spec_from_file_location(
        "phase2_preprocess_for_visualization",
        PHASE2_PREPROCESS_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Không thể nạp module: {PHASE2_PREPROCESS_PATH}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    actual = {name: getattr(module, name, None) for name in C4_EXPECTED}
    mismatches = {
        name: (expected, actual[name])
        for name, expected in C4_EXPECTED.items()
        if actual[name] != expected
    }
    if mismatches:
        raise ValueError(
            "Pipeline Phase 2 không còn khớp cấu hình C4 đã khóa: "
            f"{mismatches}"
        )
    if tuple(module.EXPECTED_MEL_SHAPE) != (40, 129):
        raise ValueError(
            "C4 phải tạo Log-Mel (40, 129), nhận: "
            f"{module.EXPECTED_MEL_SHAPE}"
        )
    return module


def is_core_wav(path: Path) -> bool:
    """Loại playback, environment và năm kiểu augmentation khỏi mẫu minh họa."""
    stem = path.stem.casefold()
    return (
        path.suffix.casefold() == ".wav"
        and "__take01" not in stem
        and "__take02" not in stem
        and not stem.startswith("env__")
        and not any(marker in stem for marker in AUGMENTATION_MARKERS)
    )


def resolve_wav(argument: str | None, default_path: Path, class_dir: Path) -> Path:
    """Giải đường dẫn CLI; nếu mẫu mặc định thiếu thì chọn core đầu tiên ổn định."""
    if argument:
        candidate = Path(argument).expanduser()
        if not candidate.is_absolute():
            root_candidate = (PROJECT_ROOT / candidate).resolve()
            dataset_candidate = (class_dir / candidate).resolve()
            candidate = root_candidate if root_candidate.is_file() else dataset_candidate
    else:
        candidate = default_path

    if candidate.is_file():
        candidate = candidate.resolve()
    elif argument:
        raise FileNotFoundError(f"Không tìm thấy WAV đã chọn: {candidate}")
    else:
        fallback = sorted(path for path in class_dir.glob("*.wav") if is_core_wav(path))
        if not fallback:
            raise FileNotFoundError(f"Không tìm thấy WAV core trong: {class_dir}")
        candidate = fallback[0].resolve()

    if not is_core_wav(candidate):
        raise ValueError(
            "Mẫu minh họa phải là WAV core; không dùng playback, environment "
            f"hoặc augmentation: {candidate.name}"
        )
    return candidate


def resolve_any_wav(argument: str | None, default_path: Path) -> Path:
    """Giải một WAV playback/environment mà không áp dụng điều kiện WAV core."""
    candidate = Path(argument).expanduser() if argument else default_path
    if not candidate.is_absolute():
        candidate = (PROJECT_ROOT / candidate).resolve()
    if not candidate.is_file():
        raise FileNotFoundError(f"Không tìm thấy WAV đã chọn: {candidate}")
    if candidate.suffix.casefold() != ".wav":
        raise ValueError(f"Đầu vào phải là file WAV: {candidate}")
    return candidate.resolve()


def build_c4_waveform(path: Path, pipeline) -> np.ndarray:
    """Trả waveform sau đúng DSP C4, ngay trước phép tạo Mel."""
    audio = pipeline.load_model_audio_window(path)
    audio = librosa.util.normalize(
        audio,
        norm=np.inf,
        axis=0,
        threshold=None,
        fill=None,
    )
    audio = pipeline.apply_bandpass_filter(audio)
    if pipeline.PRE_EMPHASIS != 0.0:
        audio = librosa.effects.preemphasis(
            audio,
            coef=pipeline.PRE_EMPHASIS,
        )
    return np.asarray(audio, dtype=np.float32)


def build_original_pcm16_waveform(path: Path, pipeline) -> np.ndarray:
    """Trả cửa sổ đầu vào trước peak-normalize/DSP ở thang PCM16 tương đương.

    ``load_model_audio_window()`` vẫn thực hiện đúng quy ước đầu vào của model:
    mono, resample 16 kHz, crop playback từ giây thứ nhất và fix-length 5 giây.
    Hàm này không peak-normalize, không Butterworth và không tạo Log-Mel.
    """
    audio = np.asarray(pipeline.load_model_audio_window(path), dtype=np.float32)
    return np.clip(audio * 32768.0, -32768.0, 32767.0)


def build_normalized_waveform_before_dsp(path: Path, pipeline) -> np.ndarray:
    """Trả waveform đã peak-normalize nhưng chưa qua Butterworth/Log-Mel."""
    audio = np.asarray(pipeline.load_model_audio_window(path), dtype=np.float32)
    normalized = librosa.util.normalize(
        audio,
        norm=np.inf,
        axis=0,
        threshold=None,
        fill=None,
    )
    return np.asarray(normalized, dtype=np.float32)


def style_axis(ax) -> None:
    ax.set_facecolor("#F8FAFD")
    ax.grid(True, color="#D6DEE9", linestyle="--", linewidth=0.7, alpha=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#8A99AE")
    ax.spines["bottom"].set_color("#8A99AE")


def plot_waveforms(
    samples: list[dict],
    sample_rate: int,
    output_path: Path,
) -> None:
    """Vẽ bốn waveform sau DSP C4 với chung giới hạn trục biên độ."""
    fig, axes = plt.subplots(
        len(samples),
        1,
        figsize=(12, 11.0),
        sharex=True,
        sharey=True,
    )
    fig.patch.set_facecolor("#F3F6FA")
    colors = ["#386CB0", "#D95F59", "#7A57A5", "#2A9D8F"]
    shared_limit = max(
        float(np.max(np.abs(sample["waveform"])))
        for sample in samples
    )
    shared_limit = max(shared_limit * 1.05, 1e-3)

    for ax, sample, color in zip(axes, samples, colors):
        audio = sample["waveform"]
        time_axis = np.arange(audio.size, dtype=np.float32) / sample_rate
        ax.plot(time_axis, audio, color=color, linewidth=0.75)
        ax.fill_between(time_axis, audio, 0, color=color, alpha=0.18)
        ax.set_ylim(-shared_limit, shared_limit)
        ax.set_ylabel("Biên độ sau DSP C4")
        ax.set_title(
            f"{sample['label']} · {sample['path'].name}",
            loc="left",
            fontsize=12,
            fontweight="bold",
            color="#172B4D",
        )
        style_axis(ax)

    axes[-1].set_xlabel("Thời gian (giây)")
    fig.suptitle(
        "Waveform của bốn nhóm âm thanh sau DSP C4",
        x=0.07,
        y=0.985,
        ha="left",
        fontsize=17,
        fontweight="bold",
        color="#172B4D",
    )
    fig.text(
        0.07,
        0.945,
        "Cửa sổ 0–5 giây · 16 kHz · peak normalize · Butterworth 100–2000 Hz/order 5 · pre=0",
        ha="left",
        fontsize=10,
        color="#5D6B82",
    )
    fig.tight_layout(rect=(0.04, 0.04, 0.99, 0.91), h_pad=2.1)
    fig.savefig(output_path, dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def plot_original_waveforms(
    samples: list[dict],
    sample_rate: int,
    output_path: Path,
) -> None:
    """Vẽ biên độ đầu vào trước chuẩn hóa và DSP, dùng chung trục PCM16."""
    fig, axes = plt.subplots(
        len(samples),
        1,
        figsize=(12, 11.0),
        sharex=True,
        sharey=True,
    )
    fig.patch.set_facecolor("#F3F6FA")
    colors = ["#386CB0", "#D95F59", "#7A57A5", "#2A9D8F"]
    shared_limit = max(
        float(np.max(np.abs(sample["original_pcm16"])))
        for sample in samples
    )
    shared_limit = max(shared_limit * 1.05, 1.0)

    for ax, sample, color in zip(axes, samples, colors):
        audio = sample["original_pcm16"]
        time_axis = np.arange(audio.size, dtype=np.float32) / sample_rate
        ax.plot(time_axis, audio, color=color, linewidth=0.75)
        ax.fill_between(time_axis, audio, 0, color=color, alpha=0.16)
        ax.set_ylim(-shared_limit, shared_limit)
        ax.set_ylabel("Biên độ PCM16")
        ax.set_title(
            f"{sample['label']} · {sample['path'].name}",
            loc="left",
            fontsize=12,
            fontweight="bold",
            color="#172B4D",
        )
        style_axis(ax)

    axes[-1].set_xlabel("Thời gian (giây)")
    fig.suptitle(
        "Biên độ đầu vào của bốn nhóm âm thanh",
        x=0.07,
        y=0.985,
        ha="left",
        fontsize=17,
        fontweight="bold",
        color="#172B4D",
    )
    fig.text(
        0.07,
        0.945,
        (
            "Cửa sổ 0–5 giây · mono/resample 16 kHz · PCM16 tương đương · "
            "chưa peak-normalize · chưa Butterworth"
        ),
        ha="left",
        fontsize=10,
        color="#5D6B82",
    )
    fig.tight_layout(rect=(0.04, 0.04, 0.99, 0.91), h_pad=2.1)
    fig.savefig(output_path, dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def plot_normalized_waveforms_before_dsp(
    samples: list[dict],
    sample_rate: int,
    output_path: Path,
) -> None:
    """Vẽ waveform peak-normalize [-1, 1], trước Butterworth và Log-Mel."""
    fig, axes = plt.subplots(
        len(samples),
        1,
        figsize=(12, 11.0),
        sharex=True,
        sharey=True,
    )
    fig.patch.set_facecolor("#F3F6FA")
    colors = ["#386CB0", "#D95F59", "#7A57A5", "#2A9D8F"]

    for ax, sample, color in zip(axes, samples, colors):
        audio = sample["normalized_before_dsp"]
        time_axis = np.arange(audio.size, dtype=np.float32) / sample_rate
        ax.plot(time_axis, audio, color=color, linewidth=0.75)
        ax.fill_between(time_axis, audio, 0, color=color, alpha=0.16)
        ax.set_ylim(-1.05, 1.05)
        ax.set_ylabel("Biên độ chuẩn hóa")
        ax.set_title(
            f"{sample['label']} · {sample['path'].name}",
            loc="left",
            fontsize=12,
            fontweight="bold",
            color="#172B4D",
        )
        style_axis(ax)

    axes[-1].set_xlabel("Thời gian (giây)")
    fig.suptitle(
        "Waveform chuẩn hóa của bốn nhóm âm thanh",
        x=0.07,
        y=0.985,
        ha="left",
        fontsize=17,
        fontweight="bold",
        color="#172B4D",
    )
    fig.text(
        0.07,
        0.945,
        (
            "Cửa sổ 0–5 giây · mono/resample 16 kHz · crop/fix-length · "
            "peak-normalize [-1, 1] · chưa Butterworth/Log-Mel"
        ),
        ha="left",
        fontsize=10,
        color="#5D6B82",
    )
    fig.tight_layout(rect=(0.04, 0.04, 0.99, 0.91), h_pad=2.1)
    fig.savefig(output_path, dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def plot_log_mels(
    samples: list[dict],
    pipeline,
    output_path: Path,
) -> None:
    """Vẽ bốn Log-Mel sau toàn bộ pipeline DSP Python của Phase 2."""
    fig, axes = plt.subplots(
        len(samples),
        1,
        figsize=(12, 13.0),
        sharex=True,
        sharey=True,
    )
    fig.patch.set_facecolor("#F3F6FA")
    image = None

    for ax, sample in zip(axes, samples):
        image = librosa.display.specshow(
            sample["mel_db"],
            x_axis="time",
            y_axis="mel",
            sr=pipeline.SR,
            hop_length=pipeline.HOP_LENGTH,
            fmin=pipeline.LOW_CUT,
            fmax=pipeline.HIGH_CUT,
            cmap="magma",
            vmin=-pipeline.TOP_DB,
            vmax=0.0,
            ax=ax,
        )
        ax.set_title(
            f"{sample['label']} · {sample['path'].name}",
            loc="left",
            fontsize=12,
            fontweight="bold",
            color="#172B4D",
        )
        ax.set_ylabel("Tần số Mel (Hz)")

    axes[-1].set_xlabel("Thời gian (giây)")
    colorbar = fig.colorbar(image, ax=axes, fraction=0.025, pad=0.025)
    colorbar.set_label("Công suất tương đối (dB)")
    colorbar.outline.set_visible(False)

    fig.suptitle(
        "Log-Mel Spectrogram sau pipeline tiền xử lý",
        x=0.07,
        y=0.985,
        ha="left",
        fontsize=17,
        fontweight="bold",
        color="#172B4D",
    )
    fig.text(
        0.07,
        0.945,
        (
            f"Butterworth {pipeline.LOW_CUT:.0f}–{pipeline.HIGH_CUT:.0f} Hz "
            f"(order {pipeline.ORDER}) · pre-emphasis {pipeline.PRE_EMPHASIS:.2f} · "
            f"{pipeline.N_MELS} Mel bins · FFT {pipeline.N_FFT} · "
            f"hop {pipeline.HOP_LENGTH} · Slaney · [{-pipeline.TOP_DB:.0f}, 0] dB"
        ),
        ha="left",
        fontsize=9.7,
        color="#5D6B82",
    )
    fig.subplots_adjust(left=0.08, right=0.91, bottom=0.08, top=0.89, hspace=0.30)
    fig.savefig(output_path, dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Vẽ waveform và Log-Mel của Asthma core, Non-Asthma core, "
            "playback và environment."
        )
    )
    parser.add_argument(
        "--asthma",
        help="WAV Asthma core; mặc định dùng P14WheezingRS_68.wav.",
    )
    parser.add_argument(
        "--non-asthma",
        help="WAV Non-Asthma core; mặc định dùng P16COPDPr_127.wav.",
    )
    parser.add_argument(
        "--playback",
        help=(
            "WAV playback; mặc định dùng "
            "AST_004__P14WheezingRS_68__take01.wav."
        ),
    )
    parser.add_argument(
        "--environment",
        help=(
            "WAV environment; mặc định dùng "
            "ENV__room_noise__room_noise_session_06__clip01.wav."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Thư mục lưu hai ảnh output.",
    )
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args()
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = (PROJECT_ROOT / output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    asthma_path = resolve_wav(
        args.asthma,
        DEFAULT_ASTHMA,
        DATASET_DIR / "Asthma" / "train",
    )
    non_asthma_path = resolve_wav(
        args.non_asthma,
        DEFAULT_NON_ASTHMA,
        DATASET_DIR / "Non_Asthma_Disease" / "train",
    )
    playback_path = resolve_any_wav(args.playback, DEFAULT_PLAYBACK)
    environment_path = resolve_any_wav(args.environment, DEFAULT_ENVIRONMENT)
    pipeline = load_phase2_preprocess()

    samples = []
    for label, path in (
        ("Asthma core (Wheezing)", asthma_path),
        ("Non-Asthma core (COPD)", non_asthma_path),
        ("Asthma playback qua loa - micro", playback_path),
        ("Environment (Room noise)", environment_path),
    ):
        samples.append(
            {
                "label": label,
                "path": path,
                "original_pcm16": build_original_pcm16_waveform(path, pipeline),
                "normalized_before_dsp": build_normalized_waveform_before_dsp(
                    path,
                    pipeline,
                ),
                "waveform": build_c4_waveform(path, pipeline),
                "mel_db": pipeline.preprocess_audio_file(path),
            }
        )

    original_path = output_dir / "00_Four_Groups_Original_Waveform_PCM16.png"
    normalized_path = (
        output_dir / "00B_Four_Groups_Normalized_Waveform_Before_DSP.png"
    )
    waveform_path = output_dir / "01_Four_Groups_Waveform_C4.png"
    mel_path = output_dir / "02_Four_Groups_LogMel_C4.png"
    plot_original_waveforms(samples, pipeline.SR, original_path)
    plot_normalized_waveforms_before_dsp(samples, pipeline.SR, normalized_path)
    plot_waveforms(samples, pipeline.SR, waveform_path)
    plot_log_mels(samples, pipeline, mel_path)

    print("Bốn WAV đã chọn:")
    print(f"  Asthma core     : {asthma_path}")
    print(f"  Non-Asthma core : {non_asthma_path}")
    print(f"  Playback        : {playback_path}")
    print(f"  Environment     : {environment_path}")
    print(f"Đã lưu biên độ gốc: {original_path}")
    print(f"Đã lưu waveform chuẩn hóa trước DSP: {normalized_path}")
    print(f"Đã lưu waveform: {waveform_path}")
    print(f"Đã lưu Log-Mel : {mel_path}")
    print("C4 Log-Mel shape:", samples[0]["mel_db"].shape)


if __name__ == "__main__":
    main()
