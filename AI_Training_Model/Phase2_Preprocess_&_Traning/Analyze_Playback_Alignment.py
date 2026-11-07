"""
===============================================================================
Tên script: Analyze_Playback_Alignment.py

Tác dụng:
- Không huấn luyện lại model.
- Đọc Val_Errors.csv và Test_Errors.csv để tìm các Playback Asthma bị sai.
- Chọn tự động 3 source lỗi chính theo số take sai và độ tin nhầm.
- Với mỗi source, lấy đủ raw/take01/take02 và thử ba crop:
  0.0-5.0 s, 0.5-5.5 s, 1.0-6.0 s.
- Mỗi crop đi qua đúng pipeline trong Preprocess_Audio.py và model hiện tại.
- Xuất waveform, Mel-Spectrogram và CSV so sánh xác suất.

Chạy từ bất kỳ thư mục nào:
    python AI_Training_Model/Phase2_Preprocess_&_Traning/Analyze_Playback_Alignment.py
===============================================================================
"""

import csv
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import librosa
import librosa.display
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf
from keras import models
from scipy.signal import butter, lfilter


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# Bản sao cố định của pipeline V2. Script phân tích không import hoặc sửa hai
# script lõi Preprocess_Audio.py và Training_Model.py.
SR = 16000
DURATION = 5.0
SAMPLES = int(SR * DURATION)

LOW_CUT = 100.0
HIGH_CUT = 2000.0
FILTER_ORDER = 5
PRE_EMPHASIS_COEF = 0.97

N_MELS = 64
HOP_LENGTH = 625
N_FFT = 1024

LOAD_DTYPE = np.float32
RESAMPLE_TYPE = "soxr_hq"
MEL_DTYPE = np.float32
POWER_AMIN = 1e-10
TOP_DB = 80.0

TOP_SOURCE_COUNT = 3
BINARY_THRESHOLD = 0.5
CROPS = (
    ("0.0-5.0", 0.0, 5.0),
    ("0.5-5.5", 0.5, 5.5),
    ("1.0-6.0", 1.0, 6.0),
)

SCRIPT_DIR = Path(__file__).resolve().parent
AI_DIR = SCRIPT_DIR.parent
ANALYSIS_ROOT = SCRIPT_DIR / "Output_Analysis_V1"

ERROR_DIR = ANALYSIS_ROOT / "Output_Analysis_Accu8931"
PREPROCESS_DIR = SCRIPT_DIR / "Output_Preprocess"
TRAIN_DIR = SCRIPT_DIR / "Output_Train_V1_SepConv2D_Flatten"
OUTPUT_DIR = ANALYSIS_ROOT / "Output_Playback_Alignment"

MODEL_PATH = TRAIN_DIR / "Model_Asthma.keras"
NORMALIZATION_PATH = TRAIN_DIR / "Normalization_Params.txt"
SOURCE_LIST_PATH = (
    AI_DIR
    / "Phase1_Split_Data"
    / "Output"
    / "01_Random_Playback"
    / "Playback_Source_List.csv"
)
DATASET_SOURCE_DIR = AI_DIR / "Dataset_TuThu_v_Kaggle"
PLAYBACK_DIR = DATASET_SOURCE_DIR / "TuThu" / "Playback_Raw" / "Asthma"

CSV_COLUMNS = [
    "source_rank",
    "source_id",
    "source_file",
    "source_split",
    "playback_error_count",
    "mean_error_probability_non_asthma",
    "variant",
    "crop",
    "crop_start_seconds",
    "crop_end_seconds",
    "audio_path",
    "original_sample_rate",
    "original_duration_seconds",
    "crop_was_padded",
    "crop_peak_before_normalize",
    "crop_rms_before_normalize",
    "probability_non_asthma",
    "probability_asthma",
    "binary_result",
    "inside_device_unsure_band_045_065",
]


def butter_bandpass(lowcut, highcut, sample_rate, order):
    nyquist = 0.5 * sample_rate
    return butter(
        order,
        [lowcut / nyquist, highcut / nyquist],
        btype="band",
        analog=False,
        output="ba",
    )


def apply_bandpass_filter(audio):
    b, a = butter_bandpass(LOW_CUT, HIGH_CUT, SR, FILTER_ORDER)
    return lfilter(b, a, audio, axis=-1, zi=None)


def pre_emphasis(audio):
    return np.append(
        audio[0],
        audio[1:] - PRE_EMPHASIS_COEF * audio[:-1],
    )


def preprocess_audio_signal(audio):
    """Bản độc lập nhưng giữ đúng pipeline đã dùng để tạo dữ liệu train."""
    audio = librosa.util.fix_length(
        np.asarray(audio, dtype=LOAD_DTYPE),
        size=SAMPLES,
        axis=-1,
        mode="constant",
    )
    audio = librosa.util.normalize(
        audio,
        norm=np.inf,
        axis=0,
        threshold=None,
        fill=None,
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
    if mel_db.shape != (N_MELS, 129):
        raise ValueError(f"Sai kích thước Mel: {mel_db.shape}")
    return mel_db


def read_csv(path):
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy CSV: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        # Chấp nhận cả CSV chuẩn và CSV đã được công cụ xem file căn thêm
        # khoảng trắng ở tên cột/giá trị.
        rows = []
        for row in csv.DictReader(file):
            rows.append(
                {
                    str(key).strip(): value.strip() if isinstance(value, str) else value
                    for key, value in row.items()
                }
            )
        return rows


def read_normalization_params():
    if not NORMALIZATION_PATH.is_file():
        raise FileNotFoundError(
            f"Không tìm thấy tham số chuẩn hóa: {NORMALIZATION_PATH}"
        )

    values = {}
    for line in NORMALIZATION_PATH.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = float(value.strip())

    train_min = values.get("TRAIN_MIN")
    train_max = values.get("TRAIN_MAX")
    if train_min is None or train_max is None or train_max <= train_min:
        raise ValueError("TRAIN_MIN/TRAIN_MAX không hợp lệ.")
    return train_min, train_max


def extract_source_id(file_name):
    match = re.match(r"(AST_\d+)__", file_name)
    return match.group(1) if match else ""


def select_main_error_sources():
    """Chọn theo số take sai giảm dần, sau đó xác suất nhầm giảm dần."""
    grouped = defaultdict(list)

    for csv_name in ("Val_Errors.csv", "Test_Errors.csv"):
        for row in read_csv(ERROR_DIR / csv_name):
            if (
                row.get("source_type") != "Playback"
                or row.get("error_type") != "ASTHMA_FN"
            ):
                continue

            source_id = extract_source_id(row.get("file_name", ""))
            if source_id:
                grouped[source_id].append(row)

    ranked = []
    for source_id, rows in grouped.items():
        probabilities = [float(row["probability_non_asthma"]) for row in rows]
        ranked.append(
            {
                "source_id": source_id,
                "error_count": len(rows),
                "mean_error_probability": float(np.mean(probabilities)),
                "error_files": ";".join(row["file_name"] for row in rows),
            }
        )

    ranked.sort(
        key=lambda item: (
            -item["error_count"],
            -item["mean_error_probability"],
            item["source_id"],
        )
    )
    if len(ranked) < TOP_SOURCE_COUNT:
        raise RuntimeError(
            f"Chỉ tìm thấy {len(ranked)} source Playback lỗi; "
            f"cần ít nhất {TOP_SOURCE_COUNT}."
        )
    return ranked[:TOP_SOURCE_COUNT]


def get_source_catalog():
    rows = read_csv(SOURCE_LIST_PATH)
    catalog = {row["source_id"]: row for row in rows}
    return catalog


def resolve_variants(selected_source, catalog):
    source_id = selected_source["source_id"]
    if source_id not in catalog:
        raise KeyError(f"Không tìm thấy {source_id} trong Playback_Source_List.csv")

    row = catalog[source_id]
    raw_path = DATASET_SOURCE_DIR / Path(row["source_relative_path"])
    take01_path = PLAYBACK_DIR / row["take_01_file"]
    take02_path = PLAYBACK_DIR / row["take_02_file"]

    variants = {
        "raw": raw_path,
        "take01": take01_path,
        "take02": take02_path,
    }
    for variant, path in variants.items():
        if not path.is_file():
            raise FileNotFoundError(
                f"Thiếu {variant} của {source_id}: {path}"
            )
    return row, variants


def load_resampled_audio(path):
    audio, _ = librosa.load(
        path,
        sr=SR,
        mono=True,
        offset=0.0,
        duration=None,
        dtype=LOAD_DTYPE,
        res_type=RESAMPLE_TYPE,
    )
    return np.asarray(audio, dtype=np.float32)


def crop_audio(audio, start_seconds, end_seconds):
    start_sample = int(round(start_seconds * SR))
    end_sample = int(round(end_seconds * SR))
    crop = audio[start_sample:end_sample]
    was_padded = len(crop) < SAMPLES
    crop = librosa.util.fix_length(crop, size=SAMPLES)
    return np.asarray(crop, dtype=np.float32), was_padded


def normalize_waveform_for_plot(audio):
    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    if peak <= 0.0:
        return np.asarray(audio, dtype=np.float32)
    return np.asarray(audio / peak, dtype=np.float32)


def collect_source_samples(source_rank, selected_source, source_row, variants):
    samples = []

    for variant, path in variants.items():
        info = sf.info(path)
        audio = load_resampled_audio(path)

        for crop_name, start_seconds, end_seconds in CROPS:
            crop, was_padded = crop_audio(audio, start_seconds, end_seconds)
            peak = float(np.max(np.abs(crop)))
            rms = float(np.sqrt(np.mean(np.square(crop, dtype=np.float64))))
            mel_db = preprocess_audio_signal(crop)

            samples.append(
                {
                    "source_rank": source_rank,
                    "source_id": selected_source["source_id"],
                    "source_file": Path(source_row["source_relative_path"]).name,
                    "source_split": source_row["split"],
                    "playback_error_count": selected_source["error_count"],
                    "mean_error_probability_non_asthma": selected_source[
                        "mean_error_probability"
                    ],
                    "variant": variant,
                    "crop": crop_name,
                    "crop_start_seconds": start_seconds,
                    "crop_end_seconds": end_seconds,
                    "audio_path": path,
                    "original_sample_rate": info.samplerate,
                    "original_duration_seconds": info.duration,
                    "crop_was_padded": int(was_padded),
                    "crop_peak_before_normalize": peak,
                    "crop_rms_before_normalize": rms,
                    "waveform": normalize_waveform_for_plot(crop),
                    "mel_db": mel_db,
                }
            )
    return samples


def run_model(model, samples, train_min, train_max):
    x_data = np.asarray([sample["mel_db"] for sample in samples])
    x_data = x_data[..., np.newaxis]
    x_data = (
        (x_data.astype(np.float32) - train_min) / (train_max - train_min)
    ).astype(np.float32)

    probabilities = model.predict(x_data, batch_size=32, verbose=0).reshape(-1)
    for sample, probability_non in zip(samples, probabilities):
        probability_non = float(probability_non)
        sample["probability_non_asthma"] = probability_non
        sample["probability_asthma"] = 1.0 - probability_non
        sample["binary_result"] = (
            "Non_Asthma" if probability_non >= BINARY_THRESHOLD else "Asthma"
        )
        sample["inside_device_unsure_band_045_065"] = int(
            0.45 < probability_non < 0.65
        )


def plot_waveforms(source_id, samples, output_folder):
    variants = ("raw", "take01", "take02")
    time_axis = np.arange(SAMPLES, dtype=np.float32) / SR
    figure, axes = plt.subplots(3, 3, figsize=(18, 10), sharex=True, sharey=True)

    for row_index, variant in enumerate(variants):
        variant_samples = [s for s in samples if s["variant"] == variant]
        for column_index, sample in enumerate(variant_samples):
            axis = axes[row_index, column_index]
            axis.plot(time_axis, sample["waveform"], linewidth=0.55)
            axis.set_title(
                f"{variant} | crop {sample['crop']} | "
                f"p_non={sample['probability_non_asthma']:.4f}"
            )
            axis.set_ylim(-1.05, 1.05)
            axis.grid(True, alpha=0.25)
            if column_index == 0:
                axis.set_ylabel("Biên độ chuẩn hóa")
            if row_index == 2:
                axis.set_xlabel("Thời gian trong crop (s)")

    figure.suptitle(f"Waveform alignment - {source_id}", fontsize=15)
    figure.tight_layout(rect=(0, 0, 1, 0.97))
    figure.savefig(output_folder / "Waveform_Comparison.png", dpi=150)
    plt.close(figure)


def plot_mels(source_id, samples, output_folder):
    variants = ("raw", "take01", "take02")
    figure, axes = plt.subplots(3, 3, figsize=(18, 11), sharex=True, sharey=True)
    image = None

    for row_index, variant in enumerate(variants):
        variant_samples = [s for s in samples if s["variant"] == variant]
        for column_index, sample in enumerate(variant_samples):
            axis = axes[row_index, column_index]
            image = librosa.display.specshow(
                sample["mel_db"],
                sr=SR,
                hop_length=HOP_LENGTH,
                fmin=LOW_CUT,
                fmax=HIGH_CUT,
                x_axis="time",
                y_axis="mel",
                cmap="magma",
                vmin=-80.0,
                vmax=0.0,
                ax=axis,
            )
            axis.set_title(
                f"{variant} | crop {sample['crop']} | "
                f"p_non={sample['probability_non_asthma']:.4f}"
            )
            if column_index != 0:
                axis.set_ylabel("")
            if row_index != 2:
                axis.set_xlabel("")

    if image is not None:
        figure.colorbar(image, ax=axes, format="%+2.0f dB", shrink=0.75)
    figure.suptitle(f"Mel-Spectrogram alignment - {source_id}", fontsize=15)
    figure.subplots_adjust(left=0.07, right=0.91, bottom=0.07, top=0.91,
                           wspace=0.18, hspace=0.30)
    figure.savefig(output_folder / "Mel_Spectrogram_Comparison.png", dpi=150)
    plt.close(figure)


def make_csv_rows(samples):
    rows = []
    for sample in samples:
        rows.append(
            {
                "source_rank": sample["source_rank"],
                "source_id": sample["source_id"],
                "source_file": sample["source_file"],
                "source_split": sample["source_split"],
                "playback_error_count": sample["playback_error_count"],
                "mean_error_probability_non_asthma": (
                    f"{sample['mean_error_probability_non_asthma']:.9f}"
                ),
                "variant": sample["variant"],
                "crop": sample["crop"],
                "crop_start_seconds": f"{sample['crop_start_seconds']:.3f}",
                "crop_end_seconds": f"{sample['crop_end_seconds']:.3f}",
                "audio_path": str(sample["audio_path"]),
                "original_sample_rate": sample["original_sample_rate"],
                "original_duration_seconds": (
                    f"{sample['original_duration_seconds']:.6f}"
                ),
                "crop_was_padded": sample["crop_was_padded"],
                "crop_peak_before_normalize": (
                    f"{sample['crop_peak_before_normalize']:.9f}"
                ),
                "crop_rms_before_normalize": (
                    f"{sample['crop_rms_before_normalize']:.9f}"
                ),
                "probability_non_asthma": (
                    f"{sample['probability_non_asthma']:.9f}"
                ),
                "probability_asthma": f"{sample['probability_asthma']:.9f}",
                "binary_result": sample["binary_result"],
                "inside_device_unsure_band_045_065": sample[
                    "inside_device_unsure_band_045_065"
                ],
            }
        )
    return rows


def write_csv(path, rows, columns):
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(selected_sources, all_samples):
    lines = [
        "# Phân tích căn chỉnh Playback",
        "",
        "Không huấn luyện lại model. Mọi crop dùng đúng pipeline V2.",
        "",
        "## Ba source được chọn",
        "",
        "| Hạng | Source | Số take sai | P(Non-Asthma) trung bình khi sai |",
        "|---:|---|---:|---:|",
    ]
    for rank, source in enumerate(selected_sources, start=1):
        lines.append(
            f"| {rank} | `{source['source_id']}` | {source['error_count']} | "
            f"{source['mean_error_probability']:.6f} |"
        )

    lines.extend(
        [
            "",
            "## Kết quả theo source",
            "",
        ]
    )
    for source in selected_sources:
        source_samples = [
            sample
            for sample in all_samples
            if sample["source_id"] == source["source_id"]
        ]
        lines.extend(
            [
                f"### {source['source_id']}",
                "",
                "| Variant | Crop | P(Non-Asthma) | Kết luận |",
                "|---|---|---:|---|",
            ]
        )
        for sample in source_samples:
            lines.append(
                f"| {sample['variant']} | {sample['crop']} | "
                f"{sample['probability_non_asthma']:.6f} | "
                f"{sample['binary_result']} |"
            )
        lines.append("")

    (OUTPUT_DIR / "Playback_Alignment_Summary.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main():
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"Không tìm thấy model: {MODEL_PATH}")

    selected_sources = select_main_error_sources()
    catalog = get_source_catalog()
    train_min, train_max = read_normalization_params()
    model = models.load_model(MODEL_PATH)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_samples = []
    selected_rows = []

    for rank, selected_source in enumerate(selected_sources, start=1):
        source_row, variants = resolve_variants(selected_source, catalog)
        samples = collect_source_samples(
            rank, selected_source, source_row, variants
        )
        run_model(model, samples, train_min, train_max)
        all_samples.extend(samples)

        source_output = OUTPUT_DIR / selected_source["source_id"]
        source_output.mkdir(parents=True, exist_ok=True)
        plot_waveforms(selected_source["source_id"], samples, source_output)
        plot_mels(selected_source["source_id"], samples, source_output)

        selected_rows.append(
            {
                "source_rank": rank,
                "source_id": selected_source["source_id"],
                "source_file": Path(source_row["source_relative_path"]).name,
                "split": source_row["split"],
                "playback_error_count": selected_source["error_count"],
                "mean_error_probability_non_asthma": (
                    f"{selected_source['mean_error_probability']:.9f}"
                ),
                "error_files": selected_source["error_files"],
            }
        )

    comparison_rows = make_csv_rows(all_samples)
    write_csv(
        OUTPUT_DIR / "Playback_Alignment_Comparison.csv",
        comparison_rows,
        CSV_COLUMNS,
    )
    write_csv(
        OUTPUT_DIR / "Selected_Error_Sources.csv",
        selected_rows,
        [
            "source_rank",
            "source_id",
            "source_file",
            "split",
            "playback_error_count",
            "mean_error_probability_non_asthma",
            "error_files",
        ],
    )
    write_summary(selected_sources, all_samples)

    print("========== PHÂN TÍCH PLAYBACK ALIGNMENT ==========")
    for row in selected_rows:
        print(
            f"Hạng {row['source_rank']}: {row['source_id']} | "
            f"source={row['source_file']} | "
            f"take sai={row['playback_error_count']}"
        )
    print(f"Tổng phép so sánh: {len(comparison_rows)}")
    print(f"Kết quả: {OUTPUT_DIR}")
    print("Không có bước huấn luyện nào được thực hiện.")
    print("=================================================")


if __name__ == "__main__":
    main()
