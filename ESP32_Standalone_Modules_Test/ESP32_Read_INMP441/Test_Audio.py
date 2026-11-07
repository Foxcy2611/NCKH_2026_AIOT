"""
===============================================================================
Tên script: Test_Audio.py

Tác dụng:
- Nhận tên WAV hoặc đường dẫn WAV cần kiểm tra.
- Không resample và không peak-normalize trước khi đo.
- Kiểm tra mono, PCM16, 16 kHz và thời lượng session.
- Tính Peak, RMS, MAV, dBFS, tỷ lệ clipping và tỷ lệ block hoạt động.
- Mô phỏng đúng thứ tự Quality Check hiện tại của Patient Node.
- Tự tìm WAV trong Dataset_TuThu_v_Kaggle và 03_VAD_Trigger/extra_validation.
- Lưu biểu đồ và CSV ngay trong ESP32_Read_INMP441/Test_Audio_Output.

Cách dùng:
- Chạy mặc định: python Test_Audio.py
- Chọn VAD: python Test_Audio.py "vad_silence_session_01.wav"
- Chọn dataset: python Test_Audio.py "TuThu/Record_Env/Silence/silence_5min.wav"
===============================================================================
"""

import argparse
import csv
import math
import os
import sys
import wave
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ======================== CẤU HÌNH CẦN ĐỔI ================================

# Chọn nguồn WAV khi chạy nhanh bằng Ctrl+Alt+N:
# - "VAD"    : WAV nghiên cứu VAD trong 03_VAD_Trigger/extra_validation.
# - "TUTHU" : dữ liệu tự thu trong Dataset_TuThu_v_Kaggle/TuThu.
# - "KAGGLE": dữ liệu gốc trong một trong các nhóm bệnh lý bên dưới.
AUDIO_SOURCE = "VAD"

# Đường dẫn tương đối tính từ thư mục 03_VAD_Trigger/extra_validation.
VAD_WAV_RELATIVE = "vad_silence_session_01.wav"

# Đường dẫn tương đối tính từ thư mục Dataset_TuThu_v_Kaggle/TuThu.
TUTHU_WAV_RELATIVE = os.path.join(
    "Record_Env", "Silence", "silence_5min.wav"
)

# Với nguồn KAGGLE, chọn nhóm và đường dẫn WAV tương đối trong nhóm đó.
# Các nhóm hợp lệ: asthma, bronchial, copd, healthy, pneumonia.
KAGGLE_GROUP = "asthma"
KAGGLE_WAV_RELATIVE = "P10AsthmaIE_49.wav"

# True: lưu ảnh và mở đồ thị. False: chỉ lưu ảnh, không bật cửa sổ.
SHOW_PLOT = True

# ========================================================================

EXPECTED_SAMPLE_RATE = 16000
EXPECTED_CHANNELS = 1
EXPECTED_SAMPLE_WIDTH = 2
RECOMMENDED_MIN_DURATION = 30.0
RECOMMENDED_MAX_DURATION = 90.0
VAD_MASTER_DURATION = 300.0
VAD_MASTER_TOLERANCE = 1.0

# Đồng bộ với Quality_Check.cpp của Patient Node hiện tại.
BLOCK_SIZE = 256
MIN_RMS = 20.0
MIN_ACTIVE_RATIO = 0.01
MAX_CLIPPED_RATIO = 0.01
CLIP_LEVEL = 32000
ACTIVE_BLOCK_THRESHOLD = 20

PROJECT_DIR_OS = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR_OS = os.path.abspath(
    os.path.join(PROJECT_DIR_OS, os.pardir, os.pardir)
)
DATASET_ROOT_OS = os.path.join(
    WORKSPACE_DIR_OS,
    "AI_Training_Model",
    "Dataset_TuThu_v_Kaggle",
)
TUTHU_DIR_OS = os.path.join(DATASET_ROOT_OS, "TuThu")
RECORD_ENV_ROOT_OS = os.path.join(TUTHU_DIR_OS, "Record_Env")
VAD_TRIGGER_DIR_OS = os.path.join(
    WORKSPACE_DIR_OS,
    "Experiments_Benchmarking",
    "Patient_Node",
    "Final_V1_Validation",
    "03_VAD_Trigger",
)
VAD_AUDIO_DIR_OS = os.path.join(VAD_TRIGGER_DIR_OS, "extra_validation")

# Dataset Kaggle được tổ chức trực tiếp theo các thư mục lớp tại dataset root.
KAGGLE_DIR_BY_GROUP_OS = {
    "asthma": os.path.join(DATASET_ROOT_OS, "asthma"),
    "bronchial": os.path.join(DATASET_ROOT_OS, "Bronchial"),
    "copd": os.path.join(DATASET_ROOT_OS, "copd"),
    "healthy": os.path.join(DATASET_ROOT_OS, "healthy"),
    "pneumonia": os.path.join(DATASET_ROOT_OS, "pneumonia"),
}

# Phần xử lý phía dưới vẫn dùng Path để duyệt file và tạo output thuận tiện.
PROJECT_DIR = Path(PROJECT_DIR_OS)
WORKSPACE_DIR = Path(WORKSPACE_DIR_OS)
DATASET_ROOT = Path(DATASET_ROOT_OS)
TUTHU_DIR = Path(TUTHU_DIR_OS)
RECORD_ENV_ROOT = Path(RECORD_ENV_ROOT_OS)
VAD_TRIGGER_DIR = Path(VAD_TRIGGER_DIR_OS)
VAD_AUDIO_DIR = Path(VAD_AUDIO_DIR_OS)
OUTPUT_DIR = PROJECT_DIR / "Test_Audio_Output"


def build_default_wav_path():
    """Dựng đường dẫn WAV mặc định từ nguồn được chọn ở đầu script."""
    source = AUDIO_SOURCE.strip().upper()

    if source == "VAD":
        return os.path.abspath(os.path.join(VAD_AUDIO_DIR_OS, VAD_WAV_RELATIVE))

    if source == "TUTHU":
        return os.path.abspath(os.path.join(TUTHU_DIR_OS, TUTHU_WAV_RELATIVE))

    if source == "KAGGLE":
        group = KAGGLE_GROUP.strip().casefold()
        if group not in KAGGLE_DIR_BY_GROUP_OS:
            valid_groups = ", ".join(KAGGLE_DIR_BY_GROUP_OS)
            raise ValueError(
                f"KAGGLE_GROUP='{KAGGLE_GROUP}' không hợp lệ. "
                f"Các nhóm hợp lệ: {valid_groups}."
            )
        return os.path.abspath(
            os.path.join(KAGGLE_DIR_BY_GROUP_OS[group], KAGGLE_WAV_RELATIVE)
        )

    raise ValueError(
        f"AUDIO_SOURCE='{AUDIO_SOURCE}' không hợp lệ. "
        "Chỉ dùng VAD, TUTHU hoặc KAGGLE."
    )


WAV_FILE = build_default_wav_path()


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Kiểm tra WAV PCM16 và mô phỏng Quality Gate. Có thể truyền đường dẫn "
            "tương đối từ dataset/03_VAD_Trigger hoặc chỉ truyền tên file."
        )
    )
    parser.add_argument(
        "wav",
        nargs="?",
        default=WAV_FILE,
        help="Tên WAV, đường dẫn tương đối trong dataset hoặc đường dẫn tuyệt đối.",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        default=SHOW_PLOT,
        help="Mở cửa sổ biểu đồ sau khi lưu.",
    )
    return parser.parse_args()


def resolve_wav_path(value):
    path = Path(str(value).strip()).expanduser()
    if not str(path):
        raise ValueError("Đường dẫn WAV đang trống.")

    direct_candidates = []
    if path.is_absolute():
        direct_candidates.append(path)
    else:
        direct_candidates.extend([
            Path.cwd() / path,
            PROJECT_DIR / path,
            DATASET_ROOT / path,
            TUTHU_DIR / path,
            RECORD_ENV_ROOT / path,
            VAD_TRIGGER_DIR / path,
            VAD_AUDIO_DIR / path,
        ])

    for candidate in direct_candidates:
        if candidate.is_file():
            return candidate.resolve()

    # Khi chỉ truyền tên file, tìm trong dataset và thư mục WAV nghiên cứu VAD.
    if len(path.parts) == 1:
        search_roots = [root for root in (DATASET_ROOT, VAD_AUDIO_DIR) if root.is_dir()]
        matches = sorted({
            candidate.resolve()
            for root in search_roots
            for candidate in root.rglob(path.name)
            if candidate.is_file()
        })
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            formatted = "\n".join(f"  - {item}" for item in matches)
            raise RuntimeError(
                f"Có nhiều WAV cùng tên '{path.name}' trong dataset:\n{formatted}\n"
                "Hãy truyền thêm đường dẫn tương đối để chọn chính xác."
            )

    checked = "\n".join(f"  - {candidate.resolve()}" for candidate in direct_candidates)
    raise FileNotFoundError(
        f"Không tìm thấy WAV '{value}'. Các vị trí đã kiểm tra:\n{checked}"
    )


def read_pcm16_wav(path):
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy WAV: {path}")

    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
        compression = wav_file.getcomptype()
        raw_data = wav_file.readframes(frame_count)

    if compression != "NONE":
        raise ValueError(f"WAV đang nén ({compression}), yêu cầu PCM không nén.")
    if sample_width != EXPECTED_SAMPLE_WIDTH:
        raise ValueError(
            f"WAV không phải PCM16: sample width={sample_width * 8} bit."
        )

    audio = np.frombuffer(raw_data, dtype="<i2").copy()
    if channels > 1:
        audio = audio.reshape(-1, channels)

    return audio, channels, sample_width, sample_rate, frame_count


def dbfs_from_pcm(value):
    if value <= 0:
        return float("-inf")
    return 20.0 * math.log10(float(value) / 32768.0)


def calculate_quality_metrics(audio_mono):
    values = audio_mono.astype(np.int32, copy=False)
    abs_values = np.abs(values)

    peak = int(abs_values.max()) if values.size else 0
    rms = (
        float(np.sqrt(np.mean(np.square(values, dtype=np.float64))))
        if values.size
        else 0.0
    )
    mav = float(np.mean(abs_values)) if values.size else 0.0
    dc_offset = float(np.mean(values)) if values.size else 0.0

    clipped_samples = int(np.count_nonzero(abs_values > CLIP_LEVEL))
    clipped_ratio = clipped_samples / values.size if values.size else 0.0

    block_mav_values = []
    active_blocks = 0
    for start in range(0, values.size, BLOCK_SIZE):
        block = abs_values[start : start + BLOCK_SIZE]
        block_mav = int(np.sum(block, dtype=np.int64) // len(block))
        block_mav_values.append(block_mav)
        if block_mav > ACTIVE_BLOCK_THRESHOLD:
            active_blocks += 1

    total_blocks = len(block_mav_values)
    active_ratio = active_blocks / total_blocks if total_blocks else 0.0

    if active_ratio < MIN_ACTIVE_RATIO:
        quality = "AUDIO_INACTIVE"
    elif clipped_ratio > MAX_CLIPPED_RATIO:
        quality = "AUDIO_TOO_LOUD"
    elif rms < MIN_RMS:
        quality = "AUDIO_TOO_WEAK"
    else:
        quality = "AUDIO_OK"

    return {
        "peak_pcm": peak,
        "rms_pcm": rms,
        "mav_pcm": mav,
        "dc_offset_pcm": dc_offset,
        "peak_dbfs": dbfs_from_pcm(peak),
        "rms_dbfs": dbfs_from_pcm(rms),
        "clipped_samples": clipped_samples,
        "clipped_ratio": clipped_ratio,
        "active_blocks": active_blocks,
        "total_blocks": total_blocks,
        "active_ratio": active_ratio,
        "quality_result": quality,
        "block_mav_values": np.asarray(block_mav_values, dtype=np.float32),
    }


def save_metrics_csv(path, metadata, metrics):
    csv_path = OUTPUT_DIR / f"{path.stem}_metrics.csv"
    row = {
        **metadata,
        **{key: value for key, value in metrics.items() if key != "block_mav_values"},
    }

    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=row.keys())
        writer.writeheader()
        writer.writerow(row)
    return csv_path


def save_plot(path, audio_mono, sample_rate, metrics):
    # Giảm số điểm chỉ để vẽ; mọi metric phía trên vẫn dùng toàn bộ mẫu gốc.
    max_plot_points = 200000
    step = max(1, math.ceil(audio_mono.size / max_plot_points))
    plot_audio = audio_mono[::step].astype(np.float32) / 32768.0
    plot_time = np.arange(plot_audio.size, dtype=np.float64) * step / sample_rate

    block_mav = metrics["block_mav_values"]
    block_time = np.arange(block_mav.size, dtype=np.float64) * BLOCK_SIZE / sample_rate

    fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=True)
    axes[0].plot(plot_time, plot_audio, color="#2563eb", linewidth=0.45)
    axes[0].set_ylabel("Biên độ [-1, 1]")
    axes[0].set_title(f"Waveform raw — {path.name}")
    axes[0].grid(alpha=0.2)

    axes[1].plot(block_time, block_mav, color="#dc2626", linewidth=0.8)
    axes[1].axhline(
        ACTIVE_BLOCK_THRESHOLD,
        color="#111827",
        linestyle="--",
        linewidth=1.0,
        label=f"Ngưỡng active={ACTIVE_BLOCK_THRESHOLD}",
    )
    axes[1].set_xlabel("Thời gian (giây)")
    axes[1].set_ylabel("MAV PCM/block")
    axes[1].set_title("Mức hoạt động theo block 256 mẫu")
    axes[1].grid(alpha=0.2)
    axes[1].legend()

    fig.suptitle(
        f"RMS={metrics['rms_pcm']:.2f} | Peak={metrics['peak_pcm']} | "
        f"Active={metrics['active_ratio'] * 100:.2f}% | "
        f"Clipped={metrics['clipped_ratio'] * 100:.4f}% | "
        f"{metrics['quality_result']}"
    )
    fig.tight_layout()

    image_path = OUTPUT_DIR / f"{path.stem}_waveform.png"
    fig.savefig(image_path, dpi=170, bbox_inches="tight")
    return fig, image_path


def main():
    args = parse_args()
    if not str(args.wav).strip():
        raise ValueError("Tên WAV đang trống. Hãy nhập tên hoặc đường dẫn file WAV.")

    wav_path = resolve_wav_path(args.wav)
    audio, channels, sample_width, sample_rate, frame_count = read_pcm16_wav(
        wav_path
    )

    if channels == 1:
        audio_mono = audio
    else:
        # Chỉ dùng để báo cáo file sai chuẩn; không sửa WAV gốc.
        audio_mono = np.mean(audio.astype(np.float64), axis=1).astype(np.int16)

    duration = frame_count / sample_rate if sample_rate else 0.0
    format_ok = (
        channels == EXPECTED_CHANNELS
        and sample_width == EXPECTED_SAMPLE_WIDTH
        and sample_rate == EXPECTED_SAMPLE_RATE
    )
    duration_recommended = (
        RECOMMENDED_MIN_DURATION <= duration <= RECOMMENDED_MAX_DURATION
    )
    duration_vad_master = (
        abs(duration - VAD_MASTER_DURATION) <= VAD_MASTER_TOLERANCE
    )

    metrics = calculate_quality_metrics(audio_mono)
    metadata = {
        "file_path": str(wav_path),
        "file_name": wav_path.name,
        "channels": channels,
        "sample_width_bits": sample_width * 8,
        "sample_rate_hz": sample_rate,
        "frames": frame_count,
        "duration_seconds": duration,
        "format_ok": format_ok,
        "duration_30_90s": duration_recommended,
        "duration_vad_5min": duration_vad_master,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = save_metrics_csv(wav_path, metadata, metrics)
    figure, image_path = save_plot(wav_path, audio_mono, sample_rate, metrics)

    print("\n========== PHÂN TÍCH ENVIRONMENT SESSION ==========")
    print(f"File          : {wav_path}")
    print(f"Định dạng     : {channels} kênh, PCM{sample_width * 8}, {sample_rate} Hz")
    print(f"Thời lượng    : {duration:.3f} giây")
    print(f"Peak          : {metrics['peak_pcm']} ({metrics['peak_dbfs']:.2f} dBFS)")
    print(f"RMS           : {metrics['rms_pcm']:.2f} ({metrics['rms_dbfs']:.2f} dBFS)")
    print(f"MAV           : {metrics['mav_pcm']:.2f}")
    print(f"DC offset     : {metrics['dc_offset_pcm']:.2f}")
    print(f"Active ratio  : {metrics['active_ratio'] * 100:.2f}%")
    print(f"Clipped ratio : {metrics['clipped_ratio'] * 100:.4f}%")
    print(f"Quality Check : {metrics['quality_result']}")
    print(f"Format chuẩn  : {'ĐẠT' if format_ok else 'KHÔNG ĐẠT'}")
    print(
        "Độ dài 30–90s: "
        f"{'ĐẠT KHUYẾN NGHỊ' if duration_recommended else 'NGOÀI KHOẢNG KHUYẾN NGHỊ'}"
    )
    print(
        "Master VAD 5p : "
        f"{'ĐÚNG 300 GIÂY' if duration_vad_master else 'KHÔNG PHẢI MASTER 5 PHÚT'}"
    )
    print(f"Biểu đồ       : {image_path}")
    print(f"CSV           : {csv_path}")
    print("====================================================")
    print(
        "Lưu ý: Quality Check hiện tại chưa phải ngưỡng Final; "
        "không tự động xóa WAV chỉ vì kết quả fail."
    )

    if args.show:
        plt.show()
    else:
        plt.close(figure)


if __name__ == "__main__":
    main()
