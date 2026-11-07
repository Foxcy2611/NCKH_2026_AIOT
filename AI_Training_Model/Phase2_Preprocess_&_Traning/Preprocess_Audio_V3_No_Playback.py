"""
===============================================================================
Tên script: Preprocess_Audio_V3_No_Playback.py

Tác dụng:
- Đọc riêng train/val/test đã chia sẵn và biến mỗi WAV thành Log-Mel
  kích thước 40 x 129 x 1 theo cấu hình C4 đã chốt ở Frontend.
- Thực hiện: 16 kHz/5 giây, chuẩn hóa biên độ, Butterworth 100-2000 Hz,
  không pre-emphasis, FFT 2048, hop 625, Hann, Mel Slaney và dB gần [-80, 0].
- Nguồn là Dataset_Chia_V3 đã loại toàn bộ playback; mọi WAV đều dùng cửa sổ
  0,0-5,0 giây.
- Lưu X, Y và tên file riêng cho từng tập; nhãn 0=Asthma, 1=Non-Asthma.

Điểm tinh chỉnh so với model ban đầu:
- Không chia dữ liệu trong script này và không trộn lại các bản tăng cường.
- Ghi tường minh các tham số mặc định của librosa/scipy để Python và C++ dùng
  cùng một đặc tả, tránh thay đổi ngầm khi nâng phiên bản thư viện.
===============================================================================
"""

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


# Thông số phải giữ giống pipeline cũ và phần triển khai ESP32-S3.
# C4 đã được chốt từ Frontend_Benchmarking. Hash này lấy từ
# results/experiment_plan.csv và dùng để truy vết đúng cấu hình.
PIPELINE_NAME = "Dataset_V3_C4_No_Playback"
FRONTEND_VARIANT_ID = "combo_pre0_mel40_fft2048"
FRONTEND_CONFIG_SHA256 = (
    "5ae8a2c91c92b58653d899ddec056485787b6307db2cc0c350382b4ded2576f8"
)

SR = 16000
DURATION = 5.0
SAMPLES = int(SR * DURATION)

LOW_CUT = 100.0
HIGH_CUT = 2000.0
ORDER = 5
PRE_COEF = 0.0

N_MELS = 40
HOP_LENGTH = 625
N_FFT = 2048
EXPECTED_MEL_SHAPE = (N_MELS, 1 + SAMPLES // HOP_LENGTH)
EXPECTED_INPUT_SHAPE = (*EXPECTED_MEL_SHAPE, 1)

# Ghi tường minh các giá trị mặc định của librosa 0.11.0 đang dùng.
# Không để việc nâng cấp thư viện âm thầm làm thay đổi pipeline.
LOAD_DTYPE = np.float32
RESAMPLE_TYPE = "soxr_hq"
MEL_DTYPE = np.float32
POWER_AMIN = 1e-10
TOP_DB = 80.0

PLAYBACK_TAKE_SUFFIXES = ("__take01", "__take02")

LABEL_ASTHMA = 0
LABEL_NON_ASTHMA = 1

EXPECTED_COUNTS = {
    "train": {LABEL_ASTHMA: 923, LABEL_NON_ASTHMA: 923},
    "val": {LABEL_ASTHMA: 30, LABEL_NON_ASTHMA: 108},
    "test": {LABEL_ASTHMA: 30, LABEL_NON_ASTHMA: 113},
}

# Đường dẫn luôn bám theo vị trí script, không phụ thuộc working directory của
# PowerShell, VS Code hoặc nút Run trong IDE.
SCRIPT_DIR = Path(__file__).resolve().parent
AI_DIR = SCRIPT_DIR.parent
DATA_DIR = AI_DIR / "Dataset_Chia_V3"
OUTPUT_DIR = SCRIPT_DIR / "Output_Preprocess_V3_No_Playback"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="darkgrid")


def butter_bandpass(lowcut, highcut, fs, order):
    nyquist = 0.5 * fs
    return butter(
        order,
        [lowcut / nyquist, highcut / nyquist], # Yêu cầu tần số nằm trong [0 , 1]
        btype="band", # || low || high
        analog=False, # False dàng cho tín hiệu rời rạc
        output="ba" # Output dạng phân số 
    )


def apply_bandpass_filter(audio):
    b, a = butter_bandpass(LOW_CUT, HIGH_CUT, SR, ORDER)
    return lfilter(b, a, audio, axis=-1, zi=None)


def pre_emphasis(audio):
    """Hàm đối chiếu lịch sử; cấu hình C4 đặt hệ số bằng 0 nên không gọi."""
    return np.append(audio[0], audio[1:] - PRE_COEF * audio[:-1])


def load_model_audio_window(file_path):
    """Đọc cửa sổ 0-5 giây; file ngắn hơn được zero-pad."""
    audio, _ = librosa.load(
        file_path,
        sr=SR,
        mono=True,
        offset=0.0,
        duration=DURATION,
        dtype=LOAD_DTYPE,
        res_type=RESAMPLE_TYPE
    )

    audio = librosa.util.fix_length(
        audio,
        size=SAMPLES,
        axis=-1,
        mode="constant"
    )
    return audio


def preprocess_audio_file(file_path):
    """Tạo một ma trận Log-Mel theo cấu hình C4: 40 x 129."""
    audio = load_model_audio_window(file_path)

    audio = librosa.util.normalize(
        audio,
        norm=np.inf,    # Chia về cho gttd max, đảm bảo biên độ về [-1.0, 1.0]
        axis=0,
        threshold=None,
        fill=None
    )

    audio = apply_bandpass_filter(audio)
    if PRE_COEF > 0.0:
        audio = pre_emphasis(audio)

    mel = librosa.feature.melspectrogram(
        y=audio,
        sr=SR,
        n_fft=N_FFT,            # Kích thước cửa sổ FFT
        hop_length=HOP_LENGTH,
        win_length=N_FFT,       # Kích thước cửa sổ phân tích
        n_mels=N_MELS,          # Số lượng dải tần MELS
        fmin=LOW_CUT,
        fmax=HIGH_CUT,
        center=True,
        htk=False,
        norm="slaney",          # Sử dụng chuẩn hóa Slaney thay vì HTK
        window="hann",
        pad_mode="constant",
        power=2.0,
        dtype=MEL_DTYPE
    )

    mel_db = librosa.power_to_db(
        mel,
        ref=np.max,
        amin=POWER_AMIN,
        top_db=TOP_DB
    )

    if mel_db.shape != EXPECTED_MEL_SHAPE:
        raise ValueError(
            f"Sai kích thước Mel của {file_path.name}: "
            f"actual={mel_db.shape}, expected={EXPECTED_MEL_SHAPE}"
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
        (DATA_DIR / "Non_Asthma_Disease" / split, LABEL_NON_ASTHMA),
    ]

    for folder, label in class_folders:
        files = sorted(folder.glob("*.wav"))
        class_name = "Asthma" if label == 0 else "Non_Asthma"
        print(f"{split} - {class_name}: {len(files)} file")

        if not files:
            raise FileNotFoundError(f"Không tìm thấy file WAV trong: {folder}")

        playback_files = [
            path.name
            for path in files
            if path.stem.casefold().endswith(PLAYBACK_TAKE_SUFFIXES)
        ]
        if playback_files:
            raise ValueError(
                f"Dataset_Chia_V3 vẫn chứa playback: {playback_files[:5]}"
            )

        expected_count = EXPECTED_COUNTS[split][label]
        if len(files) != expected_count:
            raise ValueError(
                f"Sai số WAV {split}/{class_name}: "
                f"actual={len(files)}, expected={expected_count}"
            )

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


def save_preprocess_metadata(split_summaries):
    """Lưu hợp đồng preprocessing để script train kiểm tra trước epoch đầu."""
    metadata = {
        "pipeline_name": PIPELINE_NAME,
        "dataset": "Dataset_Chia_V3",
        "playback_included": False,
        "frontend_variant_id": FRONTEND_VARIANT_ID,
        "frontend_config_sha256": FRONTEND_CONFIG_SHA256,
        "label_mapping": {
            "Asthma": LABEL_ASTHMA,
            "Non_Asthma": LABEL_NON_ASTHMA,
        },
        "input_shape": list(EXPECTED_INPUT_SHAPE),
        "preprocess_config": {
            "sample_rate_hz": SR,
            "duration_seconds": DURATION,
            "samples": SAMPLES,
            "low_cut_hz": LOW_CUT,
            "high_cut_hz": HIGH_CUT,
            "filter_order": ORDER,
            "pre_emphasis": PRE_COEF,
            "n_mels": N_MELS,
            "hop_length": HOP_LENGTH,
            "n_fft": N_FFT,
            "window": "hann",
            "center": True,
            "pad_mode": "constant",
            "power": 2.0,
            "mel_scale": "slaney",
            "top_db": TOP_DB,
        },
        "splits": split_summaries,
    }
    metadata_path = OUTPUT_DIR / "Preprocess_Metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Đã lưu hợp đồng preprocessing: {metadata_path}")


def main():
    print("BẮT ĐẦU TẠO MEL-SPECTROGRAM")
    print(
        f"Pipeline={PIPELINE_NAME} | C4={FRONTEND_CONFIG_SHA256[:12]}... | "
        f"input={EXPECTED_INPUT_SHAPE} | pre-emphasis={PRE_COEF}"
    )

    split_summaries = {}
    for split in ["train", "val", "test"]:
        x_data, y_data, files_data = process_split(split)
        save_split(split, x_data, y_data, files_data)
        split_summaries[split] = {
            "samples": int(len(y_data)),
            "asthma": int(np.sum(y_data == LABEL_ASTHMA)),
            "non_asthma": int(np.sum(y_data == LABEL_NON_ASTHMA)),
            "feature_shape": list(x_data.shape),
        }

    save_preprocess_metadata(split_summaries)

    print(f"\nHoàn thành. Kết quả được lưu tại: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
