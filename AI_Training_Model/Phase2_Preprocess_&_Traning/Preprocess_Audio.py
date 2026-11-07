"""Tiền xử lý WAV của Dataset V2 thành tensor Log-Mel.

Đây là entry point độc lập của Phase 2: đọc riêng Train/Validation/Test đã chia ở
Phase 1, tạo X/Y/tên file và không phụ thuộc artifact hoặc SHA của thí nghiệm
Frontend. Muốn thử cấu hình khác chỉ cần đổi các hằng số DSP ở đầu file.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import librosa
import librosa.display
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from scipy.signal import butter, lfilter


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# Cấu hình mặc định. Đây là tham số của lần chạy, không phải khóa provenance.
PIPELINE_NAME = "Phase2_Default_LogMel"
SR = 16000
DURATION = 5.0
SAMPLES = int(SR * DURATION)

LOW_CUT = 100.0
HIGH_CUT = 2000.0
ORDER = 5
PRE_EMPHASIS = 0.0  # Không dùng Pre-emphasis

N_MELS = 40
HOP_LENGTH = 625
N_FFT = 2048
EXPECTED_MEL_SHAPE = (N_MELS, 1 + SAMPLES // HOP_LENGTH)
EXPECTED_INPUT_SHAPE = (*EXPECTED_MEL_SHAPE, 1)

# Khóa rõ các mặc định ảnh hưởng đến kết quả số học của librosa/scipy.
LOAD_DTYPE = np.float32
RESAMPLE_TYPE = "soxr_hq"
MEL_DTYPE = np.float32
POWER_AMIN = 1e-10
TOP_DB = 80.0

# Playback đã thu với khoảng lead-in khoảng 1 giây. Chỉ các take playback mới
# crop 1,0-6,0 giây; core/environment/augmentation vẫn dùng 0,0-5,0 giây.
PLAYBACK_OFFSET_SECONDS = 1.0
PLAYBACK_TAKE_SUFFIXES = ("__take01", "__take02")

LABEL_ASTHMA = 0
LABEL_NON_ASTHMA = 1

SCRIPT_DIR = Path(__file__).resolve().parent
AI_DIR = SCRIPT_DIR.parent
DATA_DIR = AI_DIR / "Dataset_Chia_V2"
OUTPUT_DIR = SCRIPT_DIR / "Output_Preprocess"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="darkgrid")


def butter_bandpass(lowcut, highcut, fs, order):
    nyquist = 0.5 * fs
    return butter(
        order,
        [lowcut / nyquist, highcut / nyquist],
        btype="band",
        analog=False,
        output="ba",
    )


def apply_bandpass_filter(audio):
    b, a = butter_bandpass(LOW_CUT, HIGH_CUT, SR, ORDER)
    return lfilter(b, a, audio, axis=-1, zi=None)


def is_playback_file(file_path):
    """Nhận diện WAV playback bằng hậu tố take, không phụ thuộc nhãn."""
    return Path(file_path).stem.casefold().endswith(PLAYBACK_TAKE_SUFFIXES)


def load_model_audio_window(file_path):
    """Đọc cửa sổ 5 giây dùng làm đầu vào model."""
    crop_start = PLAYBACK_OFFSET_SECONDS if is_playback_file(file_path) else 0.0
    audio, _ = librosa.load(
        str(file_path),
        sr=SR,
        mono=True,
        offset=crop_start,
        duration=DURATION,
        dtype=LOAD_DTYPE,
        res_type=RESAMPLE_TYPE,
    )
    return librosa.util.fix_length(
        audio,
        size=SAMPLES,
        axis=-1,
        mode="constant",
    )


def preprocess_audio_file(file_path):
    """Tạo một Log-Mel theo các tham số đang khai báo ở đầu file."""
    audio = load_model_audio_window(file_path)
    audio = librosa.util.normalize(
        audio,
        norm=np.inf,
        axis=0,
        threshold=None,
        fill=None,
    )
    audio = apply_bandpass_filter(audio)

    if PRE_EMPHASIS != 0.0:
        audio = librosa.effects.preemphasis(audio, coef=PRE_EMPHASIS)

    mel = librosa.feature.melspectrogram(
        y=audio,
        sr=SR,
        n_fft=N_FFT,
        hop_length=HOP_LENGTH,
        win_length=N_FFT,
        n_mels=N_MELS,
        fmin=LOW_CUT,
        fmax=HIGH_CUT,
        center=True,
        htk=False,
        norm="slaney",
        window="hann",
        pad_mode="constant",
        power=2.0,
        dtype=MEL_DTYPE,
    )
    mel_db = librosa.power_to_db(
        mel,
        ref=np.max,
        amin=POWER_AMIN,
        top_db=TOP_DB,
    )
    if mel_db.shape != EXPECTED_MEL_SHAPE:
        raise ValueError(
            f"Sai shape Mel của {Path(file_path).name}: "
            f"expected={EXPECTED_MEL_SHAPE}, actual={mel_db.shape}"
        )
    if not np.isfinite(mel_db).all():
        raise ValueError(f"Mel có NaN/Inf: {file_path}")
    return mel_db


def save_sample_image(mel_db, split, label, file_path):
    class_name = "Asthma" if label == LABEL_ASTHMA else "Non_Asthma"
    plt.figure(figsize=(10, 4))
    librosa.display.specshow(
        mel_db,
        x_axis="time",
        y_axis="mel",
        sr=SR,
        fmin=LOW_CUT,
        fmax=HIGH_CUT,
        hop_length=HOP_LENGTH,
        cmap="magma",
    )
    plt.colorbar(format="%+2.0f dB")
    plt.title(f"{split} - {class_name} - {file_path.name}")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / f"{split}_Class{label}_{file_path.stem}.png",
        dpi=150,
    )
    plt.close()


def process_split(split):
    """Đọc Asthma và Non-Asthma của đúng một split đã chia ở Phase 1."""
    features = []
    labels = []
    file_names = []
    class_folders = [
        (DATA_DIR / "Asthma" / split, LABEL_ASTHMA),
        (DATA_DIR / "Non_Asthma_Disease" / split, LABEL_NON_ASTHMA),
    ]

    for folder, label in class_folders:
        files = sorted(folder.glob("*.wav"))
        class_name = "Asthma" if label == LABEL_ASTHMA else "Non_Asthma"
        print(f"{split} - {class_name}: {len(files)} file")
        if not files:
            raise FileNotFoundError(f"Không tìm thấy WAV trong: {folder}")

        for index, file_path in enumerate(files):
            mel_db = preprocess_audio_file(file_path)
            features.append(mel_db)
            labels.append(label)
            file_names.append(file_path.relative_to(DATA_DIR).as_posix())

            if index < 3:
                save_sample_image(mel_db, split, label, file_path)
            if (index + 1) % 100 == 0:
                print(f"  Đã xử lý {index + 1}/{len(files)} file")

    x_data = np.asarray(features)[..., np.newaxis]
    y_data = np.asarray(labels, dtype=np.int64)
    files_data = np.asarray(file_names)

    if x_data.shape[1:] != EXPECTED_INPUT_SHAPE:
        raise RuntimeError(f"Sai shape X_{split}: {x_data.shape}")
    if len(x_data) != len(y_data) or len(y_data) != len(files_data):
        raise RuntimeError(f"X/Y/Files không khớp ở split {split}")
    if not np.isfinite(x_data).all():
        raise RuntimeError(f"X_{split} có NaN hoặc Inf")
    return x_data, y_data, files_data


def save_split(split, x_data, y_data, files_data):
    np.save(OUTPUT_DIR / f"X_{split}_mel.npy", x_data)
    np.save(OUTPUT_DIR / f"Y_{split}_mel.npy", y_data)
    np.save(OUTPUT_DIR / f"Files_{split}.npy", files_data)
    print(
        f"Đã lưu {split}: X={x_data.shape}, dtype={x_data.dtype}, "
        f"Asthma={int(np.sum(y_data == 0))}, "
        f"Non-Asthma={int(np.sum(y_data == 1))}, "
        f"min={x_data.min():.1f}, max={x_data.max():.1f}"
    )
    return {
        "shape": list(x_data.shape),
        "dtype": str(x_data.dtype),
        "asthma": int(np.sum(y_data == 0)),
        "non_asthma": int(np.sum(y_data == 1)),
    }


def main():
    if not DATA_DIR.is_dir():
        raise FileNotFoundError(f"Không tìm thấy Dataset_Chia_V2: {DATA_DIR}")

    print("BẮT ĐẦU TẠO LOG-MEL PHASE 2")
    print(f"Pipeline: {PIPELINE_NAME}")
    print(f"Input shape: {EXPECTED_INPUT_SHAPE}")

    split_metadata = {}
    for split in ["train", "val", "test"]:
        x_data, y_data, files_data = process_split(split)
        split_metadata[split] = save_split(split, x_data, y_data, files_data)

    metadata = {
        "pipeline_name": PIPELINE_NAME,
        "input_shape": list(EXPECTED_INPUT_SHAPE),
        "preprocess_config": {
            "sample_rate_hz": SR,
            "duration_seconds": DURATION,
            "low_cut_hz": LOW_CUT,
            "high_cut_hz": HIGH_CUT,
            "filter_order": ORDER,
            "pre_emphasis": PRE_EMPHASIS,
            "n_mels": N_MELS,
            "hop_length": HOP_LENGTH,
            "n_fft": N_FFT,
            "playback_offset_seconds": PLAYBACK_OFFSET_SECONDS,
        },
        "splits": split_metadata,
    }
    (OUTPUT_DIR / "Preprocess_Metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nHoàn thành. Kết quả được lưu tại: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
