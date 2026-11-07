"""Vẽ Log-Mel của hai WAV bệnh core theo đúng Front-End C4 đã chốt.

Script chỉ đọc hai WAV Validation, không train và không chạy model. Toàn bộ DSP
được gọi từ ``frontend_core.py`` để tránh viết lại công thức khác pipeline gốc.
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

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import librosa.display


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


SCRIPT_DIR = Path(__file__).resolve().parent


def find_frontend_dir(start: Path) -> Path:
    for candidate in (start.resolve(), *start.resolve().parents):
        if (candidate / "frontend_core.py").is_file():
            return candidate
    raise FileNotFoundError(f"Không tìm thấy Frontend_Benchmarking từ {start}")


def find_workspace_root(start: Path) -> Path:
    for candidate in (start.resolve(), *start.resolve().parents):
        if (candidate / "AI_Training_Model" / "Dataset_Chia_V2").is_dir():
            return candidate
    raise FileNotFoundError(f"Không tìm thấy workspace từ {start}")


def load_frontend_core(frontend_dir: Path):
    module_path = frontend_dir / "frontend_core.py"
    spec = importlib.util.spec_from_file_location("frontend_core_c4_plot", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Không thể import {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Vẽ Log-Mel C4 cho hai WAV bệnh core.")
    parser.add_argument(
        "--asthma",
        type=Path,
        default=Path("Asthma/val/P16WheezingRS_80.wav"),
        help="Đường dẫn tương đối từ Dataset_Chia_V2.",
    )
    parser.add_argument(
        "--non-asthma",
        type=Path,
        default=Path("Non_Asthma_Disease/val/P17BronchialTc_83.wav"),
        help="Đường dẫn tương đối từ Dataset_Chia_V2.",
    )
    parser.add_argument("--output-dir", type=Path, default=SCRIPT_DIR / "figures")
    return parser.parse_args()


def prepare(frontend, path: Path, config):
    raw = frontend.load_raw_window(path)
    filtered = frontend.process_wave(raw, config)
    mel_db = frontend.mel_from_wave(filtered, config)
    return raw, filtered, mel_db


def require_core_disease_wav(path: Path) -> None:
    """Không cho hình báo cáo vô tình lấy Playback hoặc environment."""
    name = path.name.casefold()
    if "__take" in name or name.startswith("env__"):
        raise ValueError(f"Chỉ chấp nhận WAV bệnh core, nhận: {path.name}")


def main() -> None:
    args = parse_args()
    frontend_dir = find_frontend_dir(SCRIPT_DIR)
    workspace_dir = find_workspace_root(SCRIPT_DIR)
    dataset_dir = workspace_dir / "AI_Training_Model" / "Dataset_Chia_V2"
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    frontend = load_frontend_core(frontend_dir)
    c4 = frontend.Frontend(
        low_cut_hz=100.0,
        high_cut_hz=2000.0,
        filter_order=5,
        pre_emphasis=0.0,
        n_mels=40,
        hop_length=625,
        n_fft=2048,
    )
    frontend.validate(c4)

    asthma_path = dataset_dir / args.asthma
    non_asthma_path = dataset_dir / args.non_asthma
    for path in (asthma_path, non_asthma_path):
        if not path.is_file():
            raise FileNotFoundError(path)
        require_core_disease_wav(path)

    print("Đang xử lý Asthma   :", asthma_path, flush=True)
    _, _, asthma_mel = prepare(frontend, asthma_path, c4)
    print("Đang xử lý Non-Asthma:", non_asthma_path, flush=True)
    _, _, non_asthma_mel = prepare(frontend, non_asthma_path, c4)
    print("Đang vẽ ảnh...", flush=True)

    # Một ảnh Log-Mel duy nhất gồm hai bệnh core, dùng chung thang màu để so sánh.
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(9.2, 6.2),
        sharex=True,
        sharey=True,
        facecolor="#f7f9fc",
    )
    panels = (
        (asthma_mel, "Asthma core - P16WheezingRS_80.wav"),
        (non_asthma_mel, "Non-Asthma core (Bronchial) - P17BronchialTc_83.wav"),
    )
    image = None
    for ax, (mel_db, title) in zip(axes, panels, strict=True):
        image = librosa.display.specshow(
            mel_db,
            sr=frontend.SR,
            hop_length=c4.hop_length,
            x_axis="time",
            y_axis="mel",
            fmin=c4.low_cut_hz,
            fmax=c4.high_cut_hz,
            htk=False,
            cmap="magma",
            vmin=-80.0,
            vmax=0.0,
            ax=ax,
        )
        ax.set_title(title, loc="left", weight="bold", fontsize=11)
        ax.set_ylabel("Tần số (Hz)")
    axes[-1].set_xlabel("Thời gian (s)")
    axes[0].set_xlabel("")
    fig.suptitle("Log-Mel Spectrogram theo Front-End C4", weight="bold", fontsize=14)
    colorbar = fig.colorbar(image, ax=axes, pad=0.02, fraction=0.025)
    colorbar.set_label("Công suất tương đối (dB, ref=max)")
    fig.text(
        0.5,
        0.012,
        "C4: 16 kHz | Butterworth 100-2000 Hz, order 5 | pre=0 | "
        "40 Mel | FFT 2048 | hop 625 | 40x129",
        ha="center",
        fontsize=9,
        color="#334155",
    )
    fig.subplots_adjust(left=0.09, right=0.88, top=0.90, bottom=0.10, hspace=0.30)
    logmel_path = output_dir / "F7_C4_LogMel_Disease_Comparison.png"
    fig.savefig(logmel_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    print("Frontend C4 SHA-256:", frontend.digest(c4))
    print("Asthma WAV          :", asthma_path)
    print("Non-Asthma WAV      :", non_asthma_path)
    print("Log-Mel shapes      :", asthma_mel.shape, non_asthma_mel.shape)
    print("Đã lưu              :", logmel_path)


if __name__ == "__main__":
    main()
