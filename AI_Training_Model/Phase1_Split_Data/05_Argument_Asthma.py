"""
===============================================================================
Tên script: 05_Argument_Asthma.py

Tác dụng:
- Đọc manifest của bước 00 để lấy đúng 228 Asthma Core thuộc Train.
- Không tăng cường 64 file Playback và không chạm vào Val/Test.
- Sinh đúng 695 file: 139 file cho mỗi phương pháp tăng cường.
- Đưa Asthma Train từ 292 lên 987 file, cân bằng với Non-Asthma Train.
- Ghi manifest và báo cáo để truy vết file cha, tham số và nguồn môi trường.

Chạy từ thư mục gốc dự án:
    python AI_Training_Model/Phase1_Split_Data/05_Argument_Asthma.py

Lưu ý:
- Script cố ý dừng nếu số lượng đầu vào khác thiết kế V2.
- Nếu đã có file AUGV2__*.wav, script dừng để tránh sinh trùng dữ liệu.
===============================================================================
"""

import csv
import hashlib
import random
import re
from collections import Counter
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

from Argument_Oversampling import (
    TARGET_SAMPLES,
    TARGET_SR,
    add_white_noise,
    fix_audio_length,
    mix_with_noise,
    pitch_shift,
    time_shift_on_silence,
    time_stretch,
)


SEED = 42
EXPECTED_CORE_TRAIN = 228
EXPECTED_PLAYBACK_TRAIN = 64
EXPECTED_BASE_ASTHMA_TRAIN = 292
EXPECTED_NON_ASTHMA_TRAIN = 987
FILES_PER_METHOD = 139

METHODS = (
    "mix_environment",
    "time_shift",
    "white_noise",
    "time_stretch",
    "pitch_shift",
)

SCRIPT_DIR = Path(__file__).resolve().parent
AI_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = AI_DIR.parent

CORE_MANIFEST = SCRIPT_DIR / "Output" / "00_Core_Split" / "core_split_manifest.csv"
ENV_MANIFEST = SCRIPT_DIR / "Output" / "04_Build_Dataset" / "environment_clip_manifest.csv"

ASTHMA_TRAIN_DIR = AI_DIR / "Dataset_Chia_V2" / "Asthma" / "train"
NON_ASTHMA_TRAIN_DIR = AI_DIR / "Dataset_Chia_V2" / "Non_Asthma_Disease" / "train"
REPORT_DIR = SCRIPT_DIR / "Output" / "05_Argument_Asthma"

RECORD_ENV_DIR = AI_DIR / "Dataset_TuThu_v_Kaggle" / "TuThu" / "Record_Env"
KEY_FAN_PATH = RECORD_ENV_DIR / "Mixed" / "key_fan_5min.wav"
SILENCE_PATH = RECORD_ENV_DIR / "Silence" / "silence_5min.wav"

AUGMENT_PREFIX = "AUGV2__"


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative_to_project(path):
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def read_csv(path):
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy file báo cáo: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def get_patient_id(file_name):
    match = re.match(r"(P\d+)", file_name)
    if not match:
        raise ValueError(f"Không đọc được mã bệnh nhân từ: {file_name}")
    return match.group(1)


def load_core_records():
    rows = read_csv(CORE_MANIFEST)
    records = []

    for row in rows:
        if row["label"] != "Asthma" or row["split"] != "train":
            continue

        path = ASTHMA_TRAIN_DIR / row["file_name"]
        if not path.is_file():
            raise FileNotFoundError(f"Thiếu Asthma Core Train: {path}")
        if sha256_file(path) != row["sha256"]:
            raise RuntimeError(f"Hash Core không khớp manifest: {path.name}")

        records.append(
            {
                "file_name": row["file_name"],
                "group_id": row["group_id"],
                "path": path,
            }
        )

    records.sort(key=lambda item: item["file_name"].lower())
    if len(records) != EXPECTED_CORE_TRAIN:
        raise RuntimeError(
            f"Asthma Core Train phải có {EXPECTED_CORE_TRAIN} file, "
            f"nhưng manifest hiện có {len(records)} file."
        )
    return records


def load_environment_train_paths():
    rows = read_csv(ENV_MANIFEST)
    paths = []

    for row in rows:
        if row["split"] != "train":
            continue
        # Bước 04 lưu đường dẫn tương đối từ AI_Training_Model.
        path = AI_DIR / Path(row["dataset_output_path"])
        if not path.is_file():
            raise FileNotFoundError(f"Thiếu clip môi trường Train: {path}")
        paths.append(path)

    # key_fan_5min là một session cũ chỉ dùng cho Train. Thêm 10 suất chọn để
    # nó có trọng số tương đương một session mới đã được bước 04 cắt 10 clip.
    if not KEY_FAN_PATH.is_file():
        raise FileNotFoundError(f"Thiếu nguồn mixed Train: {KEY_FAN_PATH}")
    paths.extend([KEY_FAN_PATH] * 10)

    if not paths:
        raise RuntimeError("Không có nguồn môi trường Train để trộn.")
    return sorted(paths, key=lambda path: path.as_posix().lower())


def validate_dataset_before_augmentation(core_records):
    if not ASTHMA_TRAIN_DIR.is_dir() or not NON_ASTHMA_TRAIN_DIR.is_dir():
        raise RuntimeError("Chưa hoàn tất Dataset_Chia_V2 trước bước tăng cường.")

    existing_augmented = sorted(ASTHMA_TRAIN_DIR.glob(f"{AUGMENT_PREFIX}*.wav"))
    if existing_augmented:
        raise RuntimeError(
            f"Đã tồn tại {len(existing_augmented)} file {AUGMENT_PREFIX}*.wav. "
            "Không chạy chồng để tránh sinh dữ liệu trùng."
        )
    if REPORT_DIR.exists():
        raise RuntimeError(
            f"Thư mục báo cáo đã tồn tại: {REPORT_DIR}. "
            "Hãy kiểm tra đầu ra cũ trước khi chạy lại."
        )

    all_asthma = sorted(ASTHMA_TRAIN_DIR.glob("*.wav"))
    core_names = {record["file_name"] for record in core_records}
    playback = [path for path in all_asthma if path.name not in core_names]
    non_asthma_count = len(list(NON_ASTHMA_TRAIN_DIR.glob("*.wav")))

    if len(playback) != EXPECTED_PLAYBACK_TRAIN:
        raise RuntimeError(
            f"Playback Asthma Train phải có {EXPECTED_PLAYBACK_TRAIN} file, "
            f"nhưng hiện có {len(playback)} file."
        )
    if len(all_asthma) != EXPECTED_BASE_ASTHMA_TRAIN:
        raise RuntimeError(
            f"Asthma Train trước tăng cường phải có {EXPECTED_BASE_ASTHMA_TRAIN} "
            f"file, nhưng hiện có {len(all_asthma)} file."
        )
    if non_asthma_count != EXPECTED_NON_ASTHMA_TRAIN:
        raise RuntimeError(
            f"Non-Asthma Train phải có {EXPECTED_NON_ASTHMA_TRAIN} file, "
            f"nhưng hiện có {non_asthma_count} file."
        )


def build_balanced_schedule(core_records):
    """Mỗi phương pháp chọn 139 cha khác nhau; mỗi cha nhận tổng 3 hoặc 4 con."""
    rng = random.Random(SEED)
    child_count = Counter()
    schedule = []

    for method in METHODS:
        tie_break = {item["file_name"]: rng.random() for item in core_records}
        candidates = sorted(
            core_records,
            key=lambda item: (child_count[item["file_name"]], tie_break[item["file_name"]]),
        )
        selected = candidates[:FILES_PER_METHOD]
        for item in selected:
            child_count[item["file_name"]] += 1
            schedule.append((method, item))

    expected_total = FILES_PER_METHOD * len(METHODS)
    if len(schedule) != expected_total:
        raise RuntimeError("Lỗi nội bộ khi tạo lịch tăng cường.")
    if min(child_count.values()) != 3 or max(child_count.values()) != 4:
        raise RuntimeError("Phân bổ file con không đạt quy tắc 3-4 file/Core.")
    if sum(count == 4 for count in child_count.values()) != 11:
        raise RuntimeError("Phải có đúng 11 Core nhận 4 bản tăng cường.")
    return schedule, child_count


def load_five_second_segment(path, rng):
    """Đọc một đoạn 5 giây ngẫu nhiên; file 5 giây được dùng nguyên vẹn."""
    audio, _ = librosa.load(path, sr=TARGET_SR, mono=True)
    if len(audio) <= TARGET_SAMPLES:
        return fix_audio_length(audio), 0

    start = rng.randint(0, len(audio) - TARGET_SAMPLES)
    return fix_audio_length(audio[start:start + TARGET_SAMPLES]), start


def create_augmented_audio(method, source_audio, env_paths, item_rng, item_np_rng):
    noise_source = ""

    if method == "mix_environment":
        noise_path = item_rng.choice(env_paths)
        noise_audio, noise_start = load_five_second_segment(noise_path, item_rng)
        gain = item_rng.uniform(0.02, 0.10)
        result = mix_with_noise(source_audio, noise_audio, gain=gain)
        parameter = f"gain={gain:.8f};noise_start_sample={noise_start}"
        noise_source = relative_to_project(noise_path)

    elif method == "time_shift":
        if not SILENCE_PATH.is_file():
            raise FileNotFoundError(f"Thiếu file nền im lặng: {SILENCE_PATH}")
        silence_audio, silence_start = load_five_second_segment(SILENCE_PATH, item_rng)
        insert_index = item_rng.randint(0, TARGET_SAMPLES - 4 * TARGET_SR)
        result = time_shift_on_silence(
            source_audio,
            silence_audio,
            insert_index=insert_index,
        )
        parameter = (
            f"insert_sample={insert_index};"
            f"insert_seconds={insert_index / TARGET_SR:.6f};"
            f"silence_start_sample={silence_start}"
        )
        noise_source = relative_to_project(SILENCE_PATH)

    elif method == "white_noise":
        noise_level = 0.001
        result = add_white_noise(
            source_audio,
            noise_level=noise_level,
            np_rng=item_np_rng,
        )
        parameter = f"noise_level={noise_level:.6f}"

    elif method == "time_stretch":
        rate = item_rng.uniform(0.90, 1.10)
        result = time_stretch(source_audio, rate=rate)
        parameter = f"rate={rate:.8f}"

    elif method == "pitch_shift":
        n_steps = item_rng.uniform(-0.5, 0.5)
        result = pitch_shift(source_audio, n_steps=n_steps)
        parameter = f"n_steps={n_steps:.8f}"

    else:
        raise ValueError(f"Phương pháp không hợp lệ: {method}")

    return fix_audio_length(result), parameter, noise_source


def write_reports(rows, child_count):
    REPORT_DIR.mkdir(parents=True, exist_ok=False)
    manifest_path = REPORT_DIR / "asthma_augmentation_manifest.csv"
    columns = [
        "augmented_file",
        "parent_file",
        "patient_id",
        "method",
        "seed",
        "parameters",
        "noise_source",
        "output_path",
        "output_sha256",
    ]
    with manifest_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    method_counts = Counter(row["method"] for row in rows)
    parent_counts = Counter(child_count.values())
    summary = REPORT_DIR / "asthma_augmentation_summary.md"
    summary.write_text(
        "\n".join(
            [
                "# Báo cáo tăng cường Asthma Train V2",
                "",
                f"- Seed: `{SEED}`",
                f"- Asthma Core Train được dùng làm cha: `{EXPECTED_CORE_TRAIN}`",
                f"- Playback Asthma Train không tăng cường: `{EXPECTED_PLAYBACK_TRAIN}`",
                f"- Tổng file tăng cường: `{len(rows)}`",
                f"- Asthma Train sau tăng cường: `{EXPECTED_BASE_ASTHMA_TRAIN + len(rows)}`",
                f"- Non-Asthma Train đối chiếu: `{EXPECTED_NON_ASTHMA_TRAIN}`",
                "",
                "## Số file theo phương pháp",
                "",
                *[f"- `{method}`: `{method_counts[method]}`" for method in METHODS],
                "",
                "## Phân bổ theo file Core cha",
                "",
                f"- Core nhận 3 file con: `{parent_counts[3]}`",
                f"- Core nhận 4 file con: `{parent_counts[4]}`",
                "",
                "Val/Test và Playback không bị thay đổi.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main():
    core_records = load_core_records()
    validate_dataset_before_augmentation(core_records)
    env_paths = load_environment_train_paths()
    schedule, child_count = build_balanced_schedule(core_records)

    rows = []
    method_index = Counter()

    for global_index, (method, parent) in enumerate(schedule, start=1):
        method_index[method] += 1
        seed = SEED + global_index
        item_rng = random.Random(seed)
        item_np_rng = np.random.default_rng(seed)

        source_audio, _ = librosa.load(parent["path"], sr=TARGET_SR, mono=True)
        source_audio = fix_audio_length(source_audio)
        result, parameters, noise_source = create_augmented_audio(
            method,
            source_audio,
            env_paths,
            item_rng,
            item_np_rng,
        )

        new_name = (
            f"{AUGMENT_PREFIX}{method_index[method]:03d}__"
            f"{method}__{Path(parent['file_name']).stem}.wav"
        )
        output_path = ASTHMA_TRAIN_DIR / new_name
        sf.write(output_path, result, TARGET_SR, subtype="PCM_16")

        rows.append(
            {
                "augmented_file": new_name,
                "parent_file": parent["file_name"],
                "patient_id": parent["group_id"] or get_patient_id(parent["file_name"]),
                "method": method,
                "seed": seed,
                "parameters": parameters,
                "noise_source": noise_source,
                "output_path": relative_to_project(output_path),
                "output_sha256": sha256_file(output_path),
            }
        )

    if len(rows) != FILES_PER_METHOD * len(METHODS):
        raise RuntimeError("Số file đã ghi không đúng 695.")

    final_asthma_count = len(list(ASTHMA_TRAIN_DIR.glob("*.wav")))
    if final_asthma_count != EXPECTED_NON_ASTHMA_TRAIN:
        raise RuntimeError(
            f"Asthma Train sau tăng cường là {final_asthma_count}, "
            f"không bằng target {EXPECTED_NON_ASTHMA_TRAIN}."
        )

    write_reports(rows, child_count)

    print("========== HOÀN TẤT TĂNG CƯỜNG ASTHMA V2 ==========")
    print(f"Core Asthma Train       : {EXPECTED_CORE_TRAIN}")
    print(f"Playback không augment  : {EXPECTED_PLAYBACK_TRAIN}")
    for method in METHODS:
        print(f"{method:24}: {method_index[method]}")
    print(f"Tổng file tăng cường    : {len(rows)}")
    print(f"Asthma Train cuối       : {final_asthma_count}")
    print(f"Non-Asthma Train        : {EXPECTED_NON_ASTHMA_TRAIN}")
    print(f"Báo cáo                 : {REPORT_DIR}")
    print("====================================================")


if __name__ == "__main__":
    main()
