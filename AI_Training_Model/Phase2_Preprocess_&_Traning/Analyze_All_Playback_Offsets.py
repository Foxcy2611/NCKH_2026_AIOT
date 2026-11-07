"""
===============================================================================
Tên script: Analyze_All_Playback_Offsets.py

Tác dụng:
- Giữ nguyên model baseline; không train, không sửa dữ liệu và không thu lại.
- Giai đoạn 1: quét toàn bộ Asthma Playback của Train + Validation với các
  offset 0/0.25/0.5/0.75/1.0/1.25/1.5 giây và phương án detect-onset.
- Ước lượng onset/lead-in của từng take bằng RMS để đo độ ổn định của delay.
- Giai đoạn 2: sau khi đã chốt bằng Train + Validation, chỉ chạy đúng một
  phương án đã chốt trên Test. Không quét nhiều offset trên Test.

Script tự chứa bản sao pipeline V2, không import/sửa Preprocess_Audio.py hoặc
Training_Model.py.

Cách dùng được ghi ở phần CẤU HÌNH bên dưới. Script không được tự động chạy
trong quá trình tạo file này.
===============================================================================
"""

import csv
import os
import sys
from collections import defaultdict
from pathlib import Path

os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import librosa
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from keras import models
from scipy.signal import butter, lfilter


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# =============================================================================
# CẤU HÌNH
# =============================================================================

# Chạy bước chọn bằng Train + Validation trước.
# Chỉ đổi thành "CONFIRM_TEST" sau khi đã đọc báo cáo và chốt phương án.
RUN_MODE = "SELECT_TRAIN_VAL"

# Chỉ dùng khi RUN_MODE = "CONFIRM_TEST".
# - "fixed": dùng CONFIRMED_FIXED_OFFSET_SECONDS.
# - "onset": detect onset rồi crop.
CONFIRMED_ALIGNMENT = ""
CONFIRMED_FIXED_OFFSET_SECONDS = None

FIXED_OFFSETS_SECONDS = (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5)
BINARY_THRESHOLD = 0.5

# Tham số phát hiện onset bằng RMS.
RMS_FRAME_MS = 25.0
RMS_HOP_MS = 10.0
RMS_SMOOTH_FRAMES = 5
MIN_ACTIVE_MS = 80.0
ONSET_DYNAMIC_RATIO = 0.20

# Điều kiện tham khảo để coi delay gần cố định.
FIXED_DELAY_MAX_STD_SECONDS = 0.15
FIXED_DELAY_MAX_P90_P10_SECONDS = 0.35
MIN_ONSET_DETECTION_RATE = 0.95


# =============================================================================
# PIPELINE V2 CỐ ĐỊNH
# =============================================================================

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


SCRIPT_DIR = Path(__file__).resolve().parent
AI_DIR = SCRIPT_DIR.parent
ANALYSIS_ROOT = SCRIPT_DIR / "Output_Analysis_V1"

TRAIN_DIR = SCRIPT_DIR / "Output_Train_V1_SepConv2D_Flatten"
MODEL_PATH = TRAIN_DIR / "Model_Asthma.keras"
NORMALIZATION_PATH = TRAIN_DIR / "Normalization_Params.txt"

SOURCE_LIST_PATH = (
    AI_DIR
    / "Phase1_Split_Data"
    / "Output"
    / "01_Random_Playback"
    / "Playback_Source_List.csv"
)
PLAYBACK_DIR = (
    AI_DIR
    / "Dataset_TuThu_v_Kaggle"
    / "TuThu"
    / "Playback_Raw"
    / "Asthma"
)

OUTPUT_ROOT = ANALYSIS_ROOT / "Output_Playback_Offset_Analysis"
TEST_OUTPUT = OUTPUT_ROOT / "Test_Confirmation"


PREDICTION_COLUMNS = [
    "split",
    "source_id",
    "group_id",
    "source_file",
    "take_id",
    "playback_file",
    "alignment_method",
    "requested_offset_seconds",
    "applied_crop_start_seconds",
    "crop_end_seconds",
    "crop_start_was_clamped",
    "crop_was_padded",
    "detected_onset_seconds",
    "onset_found",
    "probability_non_asthma",
    "probability_asthma",
    "binary_result",
    "is_asthma_correct",
    "inside_device_unsure_band_045_065",
]


ONSET_COLUMNS = [
    "split",
    "source_id",
    "group_id",
    "take_id",
    "playback_file",
    "duration_seconds",
    "onset_found",
    "onset_seconds",
    "noise_floor_rms",
    "active_level_rms",
    "onset_threshold_rms",
    "onset_contrast_ratio",
]


def read_csv_clean(path):
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy CSV: {path}")

    rows = []
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            rows.append(
                {
                    str(key).strip(): value.strip() if isinstance(value, str) else value
                    for key, value in row.items()
                }
            )
    return rows


def write_csv(path, rows, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


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
    """Bản sao độc lập của pipeline Mel V2 đã dùng khi train."""
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


def load_asthma_playback_catalog(allowed_splits):
    rows = read_csv_clean(SOURCE_LIST_PATH)
    catalog = []

    for row in rows:
        if row.get("label") != "Asthma" or row.get("split") not in allowed_splits:
            continue

        for take_id, column in (("take01", "take_01_file"), ("take02", "take_02_file")):
            path = PLAYBACK_DIR / row[column]
            if not path.is_file():
                raise FileNotFoundError(f"Thiếu Playback: {path}")
            catalog.append(
                {
                    "split": row["split"],
                    "source_id": row["source_id"],
                    "group_id": row["group_id"],
                    "source_file": Path(row["source_relative_path"]).name,
                    "take_id": take_id,
                    "playback_file": row[column],
                    "path": path,
                }
            )

    if not catalog:
        raise RuntimeError("Không tìm thấy Asthma Playback trong split yêu cầu.")
    return catalog


def load_audio(path):
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


def moving_average(values, width):
    if width <= 1:
        return values
    kernel = np.ones(width, dtype=np.float64) / width
    return np.convolve(values, kernel, mode="same")


def first_consecutive_true(mask, required_count):
    run = 0
    for index, value in enumerate(mask):
        run = run + 1 if value else 0
        if run >= required_count:
            return index - required_count + 1
    return None


def estimate_onset(audio):
    """Ước lượng lead-in bằng RMS, có yêu cầu năng lượng duy trì liên tục."""
    frame_length = max(1, int(round(RMS_FRAME_MS * SR / 1000.0)))
    hop_length = max(1, int(round(RMS_HOP_MS * SR / 1000.0)))
    required_frames = max(1, int(np.ceil(MIN_ACTIVE_MS / RMS_HOP_MS)))

    rms = librosa.feature.rms(
        y=audio,
        frame_length=frame_length,
        hop_length=hop_length,
        center=False,
    )[0].astype(np.float64)
    rms = moving_average(rms, RMS_SMOOTH_FRAMES)

    if len(rms) == 0:
        return {
            "found": False,
            "seconds": None,
            "noise_floor": 0.0,
            "active_level": 0.0,
            "threshold": 0.0,
            "contrast_ratio": 0.0,
        }

    noise_floor = float(np.percentile(rms, 10.0))
    active_level = float(np.percentile(rms, 95.0))
    dynamic_range = max(active_level - noise_floor, 0.0)
    threshold = noise_floor + ONSET_DYNAMIC_RATIO * dynamic_range

    if dynamic_range <= 1e-10:
        onset_frame = None
    else:
        onset_frame = first_consecutive_true(rms >= threshold, required_frames)

    onset_seconds = (
        float(onset_frame * hop_length / SR)
        if onset_frame is not None
        else None
    )
    contrast_ratio = active_level / max(noise_floor, 1e-12)

    return {
        "found": onset_frame is not None,
        "seconds": onset_seconds,
        "noise_floor": noise_floor,
        "active_level": active_level,
        "threshold": threshold,
        "contrast_ratio": contrast_ratio,
    }


def crop_five_seconds(audio, requested_start_seconds):
    duration_seconds = len(audio) / SR
    max_full_start = max(0.0, duration_seconds - DURATION)
    applied_start = min(max(float(requested_start_seconds), 0.0), max_full_start)
    was_clamped = abs(applied_start - float(requested_start_seconds)) > 1e-9

    start_sample = int(round(applied_start * SR))
    crop = audio[start_sample:start_sample + SAMPLES]
    was_padded = len(crop) < SAMPLES
    crop = librosa.util.fix_length(crop, size=SAMPLES)

    return (
        np.asarray(crop, dtype=np.float32),
        applied_start,
        was_clamped,
        was_padded,
    )


def make_sample(record, audio, onset, method, requested_offset):
    if method == "onset":
        requested_start = onset["seconds"] if onset["found"] else 0.0
    else:
        requested_start = requested_offset

    crop, applied_start, was_clamped, was_padded = crop_five_seconds(
        audio, requested_start
    )
    mel_db = preprocess_audio_signal(crop)

    return {
        **record,
        "alignment_method": method,
        "requested_offset_seconds": requested_start,
        "applied_crop_start_seconds": applied_start,
        "crop_end_seconds": applied_start + DURATION,
        "crop_start_was_clamped": int(was_clamped),
        "crop_was_padded": int(was_padded),
        "detected_onset_seconds": onset["seconds"],
        "onset_found": int(onset["found"]),
        "mel_db": mel_db,
    }


def collect_samples(records, alignment_specs):
    samples = []
    onset_rows = []

    for index, record in enumerate(records, start=1):
        audio = load_audio(record["path"])
        onset = estimate_onset(audio)

        onset_rows.append(
            {
                "split": record["split"],
                "source_id": record["source_id"],
                "group_id": record["group_id"],
                "take_id": record["take_id"],
                "playback_file": record["playback_file"],
                "duration_seconds": f"{len(audio) / SR:.6f}",
                "onset_found": int(onset["found"]),
                "onset_seconds": (
                    f"{onset['seconds']:.6f}" if onset["found"] else ""
                ),
                "noise_floor_rms": f"{onset['noise_floor']:.12f}",
                "active_level_rms": f"{onset['active_level']:.12f}",
                "onset_threshold_rms": f"{onset['threshold']:.12f}",
                "onset_contrast_ratio": f"{onset['contrast_ratio']:.6f}",
            }
        )

        for method, offset in alignment_specs:
            samples.append(make_sample(record, audio, onset, method, offset))

        if index % 10 == 0 or index == len(records):
            print(f"Đã tiền xử lý {index}/{len(records)} playback")

    return samples, onset_rows


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
        sample["is_asthma_correct"] = int(probability_non < BINARY_THRESHOLD)
        sample["inside_device_unsure_band_045_065"] = int(
            0.45 < probability_non < 0.65
        )


def prediction_rows_for_csv(samples):
    rows = []
    for sample in samples:
        requested = sample["requested_offset_seconds"]
        onset_seconds = sample["detected_onset_seconds"]
        rows.append(
            {
                "split": sample["split"],
                "source_id": sample["source_id"],
                "group_id": sample["group_id"],
                "source_file": sample["source_file"],
                "take_id": sample["take_id"],
                "playback_file": sample["playback_file"],
                "alignment_method": sample["alignment_method"],
                "requested_offset_seconds": f"{requested:.6f}",
                "applied_crop_start_seconds": (
                    f"{sample['applied_crop_start_seconds']:.6f}"
                ),
                "crop_end_seconds": f"{sample['crop_end_seconds']:.6f}",
                "crop_start_was_clamped": sample["crop_start_was_clamped"],
                "crop_was_padded": sample["crop_was_padded"],
                "detected_onset_seconds": (
                    f"{onset_seconds:.6f}" if onset_seconds is not None else ""
                ),
                "onset_found": sample["onset_found"],
                "probability_non_asthma": (
                    f"{sample['probability_non_asthma']:.9f}"
                ),
                "probability_asthma": f"{sample['probability_asthma']:.9f}",
                "binary_result": sample["binary_result"],
                "is_asthma_correct": sample["is_asthma_correct"],
                "inside_device_unsure_band_045_065": sample[
                    "inside_device_unsure_band_045_065"
                ],
            }
        )
    return rows


def alignment_key(sample):
    if sample["alignment_method"] == "onset":
        return "onset"
    return f"fixed_{sample['requested_offset_seconds']:.2f}s"


def summarize_selection(samples):
    grouped = defaultdict(list)
    for sample in samples:
        grouped[(alignment_key(sample), sample["split"])].append(sample)

    alignments = sorted({key[0] for key in grouped})
    rows = []

    for alignment in alignments:
        metrics = {}
        for split in ("train", "val"):
            subset = grouped.get((alignment, split), [])
            if not subset:
                raise RuntimeError(f"Thiếu dữ liệu {split} cho {alignment}")
            probabilities = np.asarray(
                [item["probability_non_asthma"] for item in subset],
                dtype=np.float64,
            )
            correct = int(sum(item["is_asthma_correct"] for item in subset))
            metrics[split] = {
                "count": len(subset),
                "correct": correct,
                "recall": correct / len(subset),
                "mean_p_non": float(np.mean(probabilities)),
                "median_p_non": float(np.median(probabilities)),
                "p90_p_non": float(np.percentile(probabilities, 90.0)),
            }

        # Ưu tiên phương án ổn định trên cả hai tập; Validation dùng để phá hòa.
        selection_score = min(
            metrics["train"]["recall"], metrics["val"]["recall"]
        )
        rows.append(
            {
                "alignment": alignment,
                "train_count": metrics["train"]["count"],
                "train_correct": metrics["train"]["correct"],
                "train_asthma_recall": f"{metrics['train']['recall']:.9f}",
                "train_mean_p_non": f"{metrics['train']['mean_p_non']:.9f}",
                "train_median_p_non": f"{metrics['train']['median_p_non']:.9f}",
                "train_p90_p_non": f"{metrics['train']['p90_p_non']:.9f}",
                "val_count": metrics["val"]["count"],
                "val_correct": metrics["val"]["correct"],
                "val_asthma_recall": f"{metrics['val']['recall']:.9f}",
                "val_mean_p_non": f"{metrics['val']['mean_p_non']:.9f}",
                "val_median_p_non": f"{metrics['val']['median_p_non']:.9f}",
                "val_p90_p_non": f"{metrics['val']['p90_p_non']:.9f}",
                "selection_score_min_recall": f"{selection_score:.9f}",
            }
        )

    rows.sort(
        key=lambda row: (
            -float(row["selection_score_min_recall"]),
            -float(row["val_asthma_recall"]),
            -float(row["train_asthma_recall"]),
            float(row["val_mean_p_non"]),
            float(row["train_mean_p_non"]),
        )
    )
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


def summarize_onsets(onset_rows):
    rows = []
    for split in ("train", "val"):
        subset = [row for row in onset_rows if row["split"] == split]
        values = np.asarray(
            [float(row["onset_seconds"]) for row in subset if row["onset_found"] == 1],
            dtype=np.float64,
        )
        detected = len(values)
        total = len(subset)
        rows.append(
            {
                "split": split,
                "total_takes": total,
                "detected_takes": detected,
                "detection_rate": f"{detected / total:.9f}",
                "mean_onset_seconds": f"{np.mean(values):.9f}" if detected else "",
                "median_onset_seconds": (
                    f"{np.median(values):.9f}" if detected else ""
                ),
                "std_onset_seconds": f"{np.std(values):.9f}" if detected else "",
                "min_onset_seconds": f"{np.min(values):.9f}" if detected else "",
                "p10_onset_seconds": (
                    f"{np.percentile(values, 10.0):.9f}" if detected else ""
                ),
                "p90_onset_seconds": (
                    f"{np.percentile(values, 90.0):.9f}" if detected else ""
                ),
                "max_onset_seconds": f"{np.max(values):.9f}" if detected else "",
            }
        )
    return rows


def analyze_delay_pattern(onset_rows):
    values = np.asarray(
        [float(row["onset_seconds"]) for row in onset_rows if row["onset_found"] == 1],
        dtype=np.float64,
    )
    detection_rate = len(values) / len(onset_rows)
    if len(values) == 0:
        return {
            "fixed_like": False,
            "detection_rate": detection_rate,
            "median": None,
            "std": None,
            "p90_p10": None,
        }

    std = float(np.std(values))
    p90_p10 = float(np.percentile(values, 90.0) - np.percentile(values, 10.0))
    fixed_like = (
        detection_rate >= MIN_ONSET_DETECTION_RATE
        and std <= FIXED_DELAY_MAX_STD_SECONDS
        and p90_p10 <= FIXED_DELAY_MAX_P90_P10_SECONDS
    )
    return {
        "fixed_like": fixed_like,
        "detection_rate": detection_rate,
        "median": float(np.median(values)),
        "std": std,
        "p90_p10": p90_p10,
    }


def plot_offset_metrics(summary_rows, output_dir):
    fixed_rows = [row for row in summary_rows if row["alignment"].startswith("fixed_")]
    offsets = [float(row["alignment"].replace("fixed_", "").replace("s", "")) for row in fixed_rows]
    train_recall = [float(row["train_asthma_recall"]) for row in fixed_rows]
    val_recall = [float(row["val_asthma_recall"]) for row in fixed_rows]
    train_p = [float(row["train_mean_p_non"]) for row in fixed_rows]
    val_p = [float(row["val_mean_p_non"]) for row in fixed_rows]

    order = np.argsort(offsets)
    offsets = np.asarray(offsets)[order]
    train_recall = np.asarray(train_recall)[order]
    val_recall = np.asarray(val_recall)[order]
    train_p = np.asarray(train_p)[order]
    val_p = np.asarray(val_p)[order]

    figure, axes = plt.subplots(1, 2, figsize=(13, 5))
    axes[0].plot(offsets, train_recall, marker="o", label="Train")
    axes[0].plot(offsets, val_recall, marker="o", label="Validation")
    axes[0].set_title("Asthma recall theo fixed offset")
    axes[0].set_xlabel("Offset (s)")
    axes[0].set_ylabel("Asthma recall")
    axes[0].set_ylim(0.0, 1.05)
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()

    axes[1].plot(offsets, train_p, marker="o", label="Train")
    axes[1].plot(offsets, val_p, marker="o", label="Validation")
    axes[1].axhline(BINARY_THRESHOLD, color="red", linestyle="--", alpha=0.7)
    axes[1].set_title("P(Non-Asthma) trung bình theo fixed offset")
    axes[1].set_xlabel("Offset (s)")
    axes[1].set_ylabel("Mean P(Non-Asthma)")
    axes[1].set_ylim(0.0, 1.05)
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()

    figure.tight_layout()
    figure.savefig(output_dir / "Offset_Metrics_Train_Val.png", dpi=150)
    plt.close(figure)


def plot_onset_histogram(onset_rows, output_dir):
    figure, axis = plt.subplots(figsize=(10, 5))
    for split, color in (("train", "tab:blue"), ("val", "tab:orange")):
        values = [
            float(row["onset_seconds"])
            for row in onset_rows
            if row["split"] == split and row["onset_found"] == 1
        ]
        if values:
            axis.hist(values, bins=20, alpha=0.55, label=split, color=color)

    axis.set_title("Phân bố onset/lead-in của Asthma Playback")
    axis.set_xlabel("Onset (s)")
    axis.set_ylabel("Số take")
    axis.grid(True, alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output_dir / "Onset_Histogram_Train_Val.png", dpi=150)
    plt.close(figure)


def write_selection_report(summary_rows, onset_rows, output_dir):
    delay = analyze_delay_pattern(onset_rows)
    best = summary_rows[0]

    if delay["fixed_like"]:
        delay_conclusion = (
            "Onset tương đối tập trung; có thể cân nhắc fixed offset quanh "
            f"median `{delay['median']:.3f} s`, nhưng vẫn phải so với bảng model."
        )
    else:
        delay_conclusion = (
            "Onset dao động đáng kể hoặc phát hiện chưa đủ ổn định; ưu tiên "
            "đánh giá phương án `detect onset -> crop 5 s` thay vì hard-code 1 s."
        )

    lines = [
        "# Kết quả chọn alignment bằng Train + Validation",
        "",
        "Test chưa được sử dụng trong bước này.",
        "",
        "## Onset/lead-in",
        "",
        f"- Detection rate: `{delay['detection_rate']:.4f}`",
        f"- Median onset: `{delay['median']:.4f} s`" if delay["median"] is not None else "- Median onset: `N/A`",
        f"- Độ lệch chuẩn: `{delay['std']:.4f} s`" if delay["std"] is not None else "- Độ lệch chuẩn: `N/A`",
        f"- Khoảng P90-P10: `{delay['p90_p10']:.4f} s`" if delay["p90_p10"] is not None else "- Khoảng P90-P10: `N/A`",
        f"- Nhận xét tự động: {delay_conclusion}",
        "",
        "## Phương án đứng đầu theo Train + Validation",
        "",
        f"- Alignment: `{best['alignment']}`",
        f"- Train Asthma recall: `{best['train_asthma_recall']}`",
        f"- Validation Asthma recall: `{best['val_asthma_recall']}`",
        f"- Điểm min recall: `{best['selection_score_min_recall']}`",
        "",
        "Đây chỉ là đề xuất để xem xét, chưa tự động chốt Test.",
        "Muốn xác nhận Test, sửa cấu hình đầu script sang `CONFIRM_TEST` và chỉ",
        "khai báo đúng một phương án đã chốt.",
        "",
    ]
    (output_dir / "Train_Val_Alignment_Report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def run_select_train_val(model, train_min, train_max):
    records = load_asthma_playback_catalog({"train", "val"})
    alignment_specs = [("fixed", offset) for offset in FIXED_OFFSETS_SECONDS]
    alignment_specs.append(("onset", None))

    samples, onset_rows = collect_samples(records, alignment_specs)
    run_model(model, samples, train_min, train_max)

    prediction_rows = prediction_rows_for_csv(samples)
    summary_rows = summarize_selection(samples)
    onset_summary = summarize_onsets(onset_rows)

    summary_columns = [
        "rank",
        "alignment",
        "train_count",
        "train_correct",
        "train_asthma_recall",
        "train_mean_p_non",
        "train_median_p_non",
        "train_p90_p_non",
        "val_count",
        "val_correct",
        "val_asthma_recall",
        "val_mean_p_non",
        "val_median_p_non",
        "val_p90_p_non",
        "selection_score_min_recall",
    ]
    onset_summary_columns = [
        "split",
        "total_takes",
        "detected_takes",
        "detection_rate",
        "mean_onset_seconds",
        "median_onset_seconds",
        "std_onset_seconds",
        "min_onset_seconds",
        "p10_onset_seconds",
        "p90_onset_seconds",
        "max_onset_seconds",
    ]

    write_csv(
        OUTPUT_ROOT / "Playback_Offset_Predictions_Train_Val.csv",
        prediction_rows,
        PREDICTION_COLUMNS,
    )
    write_csv(
        OUTPUT_ROOT / "Playback_Onset_Estimates_Train_Val.csv",
        onset_rows,
        ONSET_COLUMNS,
    )
    write_csv(
        OUTPUT_ROOT / "Playback_Offset_Summary_Train_Val.csv",
        summary_rows,
        summary_columns,
    )
    write_csv(
        OUTPUT_ROOT / "Playback_Onset_Summary_Train_Val.csv",
        onset_summary,
        onset_summary_columns,
    )
    plot_offset_metrics(summary_rows, OUTPUT_ROOT)
    plot_onset_histogram(onset_rows, OUTPUT_ROOT)
    write_selection_report(summary_rows, onset_rows, OUTPUT_ROOT)

    print("Hoàn tất chọn alignment bằng Train + Validation.")
    print(f"Số Playback take: {len(records)}")
    print(f"Số lần suy luận: {len(samples)}")
    print(f"Kết quả: {OUTPUT_ROOT}")
    print("Test chưa được mở.")


def validate_test_confirmation_config():
    method = CONFIRMED_ALIGNMENT.strip().lower()
    if method not in {"fixed", "onset"}:
        raise ValueError(
            "CONFIRM_TEST yêu cầu CONFIRMED_ALIGNMENT là 'fixed' hoặc 'onset'."
        )

    if method == "fixed":
        if CONFIRMED_FIXED_OFFSET_SECONDS is None:
            raise ValueError("Chưa khai báo CONFIRMED_FIXED_OFFSET_SECONDS.")
        offset = float(CONFIRMED_FIXED_OFFSET_SECONDS)
        if offset < 0.0:
            raise ValueError("CONFIRMED_FIXED_OFFSET_SECONDS không được âm.")
        return method, offset

    return method, None


def run_confirm_test(model, train_min, train_max):
    method, offset = validate_test_confirmation_config()
    records = load_asthma_playback_catalog({"test"})
    samples, onset_rows = collect_samples(records, [(method, offset)])
    run_model(model, samples, train_min, train_max)

    prediction_rows = prediction_rows_for_csv(samples)
    correct = sum(sample["is_asthma_correct"] for sample in samples)
    probabilities = np.asarray(
        [sample["probability_non_asthma"] for sample in samples],
        dtype=np.float64,
    )

    write_csv(
        TEST_OUTPUT / "Playback_Test_Confirmation.csv",
        prediction_rows,
        PREDICTION_COLUMNS,
    )
    write_csv(
        TEST_OUTPUT / "Playback_Test_Onset_Estimates.csv",
        onset_rows,
        ONSET_COLUMNS,
    )

    report = "\n".join(
        [
            "# Xác nhận alignment trên Test",
            "",
            "Test chỉ chạy đúng một phương án đã chốt từ Train + Validation.",
            "",
            f"- Phương án: `{method}`",
            f"- Fixed offset: `{offset}`" if method == "fixed" else "- Fixed offset: `N/A`",
            f"- Tổng Playback Test: `{len(samples)}`",
            f"- Asthma đúng: `{correct}`",
            f"- Asthma bị bỏ sót: `{len(samples) - correct}`",
            f"- Asthma recall: `{correct / len(samples):.6f}`",
            f"- Mean P(Non-Asthma): `{np.mean(probabilities):.6f}`",
            f"- Median P(Non-Asthma): `{np.median(probabilities):.6f}`",
            "",
        ]
    )
    (TEST_OUTPUT / "Test_Confirmation_Report.md").write_text(
        report, encoding="utf-8"
    )

    print("Hoàn tất xác nhận đúng một alignment trên Test.")
    print(f"Phương án: {method}, offset={offset}")
    print(f"Asthma recall: {correct}/{len(samples)}")
    print(f"Kết quả: {TEST_OUTPUT}")


def main():
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"Không tìm thấy model baseline: {MODEL_PATH}")

    train_min, train_max = read_normalization_params()
    model = models.load_model(MODEL_PATH)

    mode = RUN_MODE.strip().upper()
    if mode == "SELECT_TRAIN_VAL":
        run_select_train_val(model, train_min, train_max)
    elif mode == "CONFIRM_TEST":
        run_confirm_test(model, train_min, train_max)
    else:
        raise ValueError(
            "RUN_MODE chỉ được là SELECT_TRAIN_VAL hoặc CONFIRM_TEST."
        )


if __name__ == "__main__":
    main()
