"""
===============================================================================
Tên script: Preprocess_Audio.py

Tác dụng:
- Đọc riêng train/val/test đã chia sẵn và biến mỗi WAV thành Mel-Spectrogram
  kích thước 64 x 129 x 1.
- Thực hiện: 16 kHz/5 giây, chuẩn hóa biên độ, Butterworth 100-2000 Hz,
  pre-emphasis 0,97, Hann, Mel Slaney và dB trong khoảng gần [-80, 0].
- Lưu X, Y và tên file riêng cho từng tập; nhãn 0=Asthma, 1=Non-Asthma.

Điểm tinh chỉnh so với model ban đầu:
- Không chia dữ liệu trong script này và không trộn lại các bản tăng cường.
- Ghi tường minh các tham số mặc định của librosa/scipy để Python và C++ dùng
  cùng một đặc tả, tránh thay đổi ngầm khi nâng phiên bản thư viện.
===============================================================================
"""

import os
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


# Thông số phải giữ giống pipeline cũ và phần triển khai ESP32-S3.
SR = 16000
DURATION = 5.0
SAMPLES = int(SR * DURATION)

LOW_CUT = 100.0
HIGH_CUT = 2000.0
ORDER = 5
PRE_COEF = 0.97

N_MELS = 64
HOP_LENGTH = 625
N_FFT = 1024

# Ghi tường minh các giá trị mặc định của librosa 0.11.0 đang dùng.
# Không để việc nâng cấp thư viện âm thầm làm thay đổi pipeline.
LOAD_DTYPE = np.float32
RESAMPLE_TYPE = "soxr_hq"
MEL_DTYPE = np.float32
POWER_AMIN = 1e-10
TOP_DB = 80.0

LABEL_ASTHMA = 0
LABEL_NON_ASTHMA = 1

# Đường dẫn mặc định khi chạy từ thư mục gốc NCKH_2026_AIOT.
DATA_DIR = Path(os.path.join("AI_Training_Model", "Dataset_Chia"))
OUTPUT_DIR = Path(os.path.join(
    "AI_Training_Model",
    "P2_Preprocess_&_Traning_Model",
    "Output_Preprocess"
))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="darkgrid")


def butter_bandpass(lowcut, highcut, fs, order):
    nyquist = 0.5 * fs
    return butter(
        order,
        [lowcut / nyquist, highcut / nyquist],
        btype="band",
        analog=False,
        output="ba"
    )


def apply_bandpass_filter(audio):
    b, a = butter_bandpass(LOW_CUT, HIGH_CUT, SR, ORDER)
    return lfilter(b, a, audio, axis=-1, zi=None)


def pre_emphasis(audio):
    return np.append(audio[0], audio[1:] - PRE_COEF * audio[:-1])


def preprocess_audio_file(file_path):
    """Tạo một ma trận Mel-Spectrogram kích thước 64 x 129."""
    audio, _ = librosa.load(
        file_path,
        sr=SR,
        mono=True,
        offset=0.0,
        duration=None,
        dtype=LOAD_DTYPE,
        res_type=RESAMPLE_TYPE
    )
    audio = librosa.util.fix_length(
        audio,
        size=SAMPLES,
        axis=-1,
        mode="constant"
    )
    audio = librosa.util.normalize(
        audio,
        norm=np.inf,
        axis=0,
        threshold=None,
        fill=None
    )
    audio = apply_bandpass_filter(audio)
    audio = pre_emphasis(audio)

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
        window="hann",
        pad_mode="constant",
        power=2.0,
        norm="slaney",
        dtype=MEL_DTYPE
    )

    mel_db = librosa.power_to_db(
        mel,
        ref=np.max,
        amin=POWER_AMIN,
        top_db=TOP_DB
    )

    if mel_db.shape != (64, 129):
        raise ValueError(
            f"Sai kích thước Mel của {file_path.name}: {mel_db.shape}"
        )

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
        cmap="magma"
    )
    plt.colorbar(format="%+2.0f dB")
    plt.title(f"{split} - {class_name} - {file_path.name}")
    plt.tight_layout()

    image_name = f"{split}_Class{label}_{file_path.stem}.png"
    plt.savefig(OUTPUT_DIR / image_name, dpi=150)
    plt.close()


def process_split(split):
    """Đọc Asthma và Non_Asthma của đúng một tập."""
    features = []
    labels = []
    file_names = []

    class_folders = [
        (DATA_DIR / "Asthma" / split, LABEL_ASTHMA),
        (DATA_DIR / "Non_Asthma" / split, LABEL_NON_ASTHMA),
    ]

    for folder, label in class_folders:
        files = sorted(folder.glob("*.wav"))
        class_name = "Asthma" if label == 0 else "Non_Asthma"
        print(f"{split} - {class_name}: {len(files)} file")

        if not files:
            raise FileNotFoundError(f"Không tìm thấy file WAV trong: {folder}")

        for index, file_path in enumerate(files):
            mel_db = preprocess_audio_file(file_path)
            features.append(mel_db)
            labels.append(label)
            file_names.append(str(file_path.relative_to(DATA_DIR)))

            if index < 3:
                save_sample_image(mel_db, split, label, file_path)

            if (index + 1) % 100 == 0:
                print(f"  Đã xử lý {index + 1}/{len(files)} file")

    x_data = np.asarray(features)[..., np.newaxis]
    y_data = np.asarray(labels, dtype=np.int64)
    files_data = np.asarray(file_names)

    if len(x_data) != len(y_data) or len(y_data) != len(files_data):
        raise RuntimeError(f"X, Y và tên file không khớp ở tập {split}")

    if np.isnan(x_data).any() or np.isinf(x_data).any():
        raise RuntimeError(f"Tập {split} có giá trị NaN hoặc Inf")

    return x_data, y_data, files_data


def save_split(split, x_data, y_data, files_data):
    np.save(OUTPUT_DIR / f"X_{split}_mel.npy", x_data)
    np.save(OUTPUT_DIR / f"Y_{split}_mel.npy", y_data)
    np.save(OUTPUT_DIR / f"Files_{split}.npy", files_data)

    asthma_count = int(np.sum(y_data == LABEL_ASTHMA))
    non_asthma_count = int(np.sum(y_data == LABEL_NON_ASTHMA))

    print(
        f"Đã lưu {split}: X={x_data.shape}, Y={y_data.shape}, "
        f"Asthma={asthma_count}, Non_Asthma={non_asthma_count}, "
        f"min={x_data.min():.1f}, max={x_data.max():.1f}"
    )


def main():
    print("BẮT ĐẦU TẠO MEL-SPECTROGRAM")

    for split in ["train", "val", "test"]:
        x_data, y_data, files_data = process_split(split)
        save_split(split, x_data, y_data, files_data)

    print(f"\nHoàn thành. Kết quả được lưu tại: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
