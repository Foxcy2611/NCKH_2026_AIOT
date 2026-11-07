"""
===============================================================================
Tên script: 01_Random_Playback.py

Tác dụng:
- Đọc kết quả chia Core do 00_Split_Core_Data.py tạo.
- Đo chất lượng các WAV nguồn trước khi chọn làm playback.
- Chọn ngẫu nhiên bằng SEED = 42:
  + 40 source Asthma;
  + 10 source Bronchial;
  + 10 source COPD;
  + 10 source Healthy;
  + 10 source Pneumonia.
- Mỗi source thuộc một bệnh nhân khác nhau và kế thừa split của Core.
- Sinh Playback_Source_List.csv tương thích với Record_Playback.py.

Script chỉ tạo danh sách nguồn, không phát âm thanh và không thu bằng INMP441.

Đầu vào:
AI_Training_Model/Phase1_Split_Data/Output/00_Core_Split/
`-- core_split_manifest.csv

Đầu ra:
AI_Training_Model/Phase1_Split_Data/Output/01_Random_Playback/
`-- Playback_Source_List.csv
===============================================================================
"""

import csv
import hashlib
import math
import random
import wave
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


SEED = 42

# Tiêu chí nguồn đủ rõ để phát qua loa và thu lại bằng INMP441.
MIN_DURATION_SECONDS = 4.5
MIN_PEAK_PCM = 5000
MIN_RMS_PCM = 1000.0
CLIP_LEVEL = 32000
MAX_CLIPPED_RATIO = 0.005

SCRIPT_DIR = Path(__file__).resolve().parent
AI_ROOT = SCRIPT_DIR.parent
DATASET_ROOT = AI_ROOT / "Dataset_TuThu_v_Kaggle"
CORE_MANIFEST = SCRIPT_DIR / "Output" / "00_Core_Split" / "core_split_manifest.csv"
OUTPUT_DIR = SCRIPT_DIR / "Output" / "01_Random_Playback"
OUTPUT_CSV = OUTPUT_DIR / "Playback_Source_List.csv"

SPLIT_ORDER = ("train", "val", "test")

# Phân bổ 80/10/10 theo đúng split Core.
SOURCE_PLAN = {
    "Asthma": {"train": 32, "val": 4, "test": 4},
    "Bronchial": {"train": 8, "val": 1, "test": 1},
    "COPD": {"train": 8, "val": 1, "test": 1},
    "Healthy": {"train": 8, "val": 1, "test": 1},
    "Pneumonia": {"train": 8, "val": 1, "test": 1},
}

SOURCE_PREFIX = {
    "Asthma": "AST",
    "Bronchial": "BRO",
    "COPD": "COPD",
    "Healthy": "HEA",
    "Pneumonia": "PNE",
}

CSV_COLUMNS = (
    "source_id",
    "label",
    "subtype",
    "group_id",
    "split",
    "source_relative_path",
    "source_sample_rate",
    "source_duration_seconds",
    "source_peak_pcm",
    "source_rms_pcm",
    "source_rms_dbfs",
    "source_clipped_ratio",
    "playback_source_check",
    "source_sha256",
    "take_01_file",
    "take_02_file",
)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_core_manifest():
    if not CORE_MANIFEST.is_file():
        raise FileNotFoundError(
            f"Không tìm thấy {CORE_MANIFEST}. Hãy chạy 00_Split_Core_Data.py trước."
        )

    with CORE_MANIFEST.open("r", newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))

    required = {
        "file_name",
        "label",
        "subtype",
        "group_id",
        "split",
        "source_path",
        "sha256",
    }
    missing = required.difference(rows[0].keys() if rows else ())
    if missing:
        raise RuntimeError(
            f"core_split_manifest.csv thiếu cột: {', '.join(sorted(missing))}"
        )

    return rows


def dbfs(value):
    if value <= 0:
        return float("-inf")
    return 20.0 * math.log10(value / 32768.0)


def analyze_wav(path):
    """Đọc WAV mono PCM16 và trả về các chỉ số dùng để lọc source."""
    try:
        with wave.open(str(path), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()
            compression = wav_file.getcomptype()
            raw_data = wav_file.readframes(frame_count)
    except (wave.Error, EOFError) as error:
        return None, f"WAV_ERROR: {error}"

    if channels != 1:
        return None, "NOT_MONO"
    if sample_width != 2 or compression != "NONE":
        return None, "NOT_PCM16"
    if sample_rate <= 0 or frame_count <= 0:
        return None, "EMPTY_WAV"

    samples = np.frombuffer(raw_data, dtype="<i2").astype(np.int32)
    if samples.size == 0:
        return None, "EMPTY_WAV"

    absolute = np.abs(samples)
    peak = int(absolute.max())
    rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))
    clipped_count = int(np.count_nonzero(absolute > CLIP_LEVEL))
    clipped_ratio = clipped_count / samples.size
    duration = frame_count / sample_rate

    metrics = {
        "sample_rate": sample_rate,
        "duration": duration,
        "peak": peak,
        "rms": rms,
        "rms_dbfs": dbfs(rms),
        "clipped_ratio": clipped_ratio,
    }

    if duration < MIN_DURATION_SECONDS:
        return metrics, "TOO_SHORT"
    if peak < MIN_PEAK_PCM:
        return metrics, "PEAK_TOO_LOW"
    if rms < MIN_RMS_PCM:
        return metrics, "RMS_TOO_LOW"
    if clipped_ratio > MAX_CLIPPED_RATIO:
        return metrics, "TOO_MUCH_CLIPPING"
    return metrics, "OK"


def build_eligible_candidates(manifest_rows):
    """Kiểm tra đường dẫn, mã băm và chất lượng tất cả source Core."""
    candidates = []
    rejection_counts = Counter()

    for row in manifest_rows:
        source_path = DATASET_ROOT / Path(row["source_path"])
        if not source_path.is_file():
            raise FileNotFoundError(f"Thiếu WAV Core: {source_path}")

        actual_hash = sha256_file(source_path)
        if actual_hash != row["sha256"]:
            raise RuntimeError(f"SHA-256 không khớp manifest: {source_path}")

        metrics, status = analyze_wav(source_path)
        if status != "OK":
            rejection_counts[status] += 1
            continue

        candidate = dict(row)
        candidate["source_path_object"] = source_path
        candidate["metrics"] = metrics
        candidates.append(candidate)

    return candidates, rejection_counts


def select_one_source_per_group(candidates, subtype, split, amount, rng):
    """Chọn ngẫu nhiên các bệnh nhân rồi chọn một WAV của mỗi bệnh nhân."""
    grouped = defaultdict(list)
    for row in candidates:
        if row["subtype"] == subtype and row["split"] == split:
            grouped[row["group_id"]].append(row)

    group_ids = sorted(grouped)
    rng.shuffle(group_ids)
    if len(group_ids) < amount:
        raise RuntimeError(
            f"Không đủ source hợp lệ cho {subtype}/{split}: "
            f"cần {amount} bệnh nhân, hiện có {len(group_ids)}."
        )

    selected = []
    for group_id in group_ids[:amount]:
        files = sorted(grouped[group_id], key=lambda row: row["file_name"].lower())
        selected.append(rng.choice(files))
    return selected


def select_playback_sources(candidates):
    rng = random.Random(SEED)
    selected_by_subtype = defaultdict(list)

    for subtype, split_plan in SOURCE_PLAN.items():
        for split in SPLIT_ORDER:
            selected_by_subtype[subtype].extend(
                select_one_source_per_group(
                    candidates,
                    subtype,
                    split,
                    split_plan[split],
                    rng,
                )
            )

    return selected_by_subtype


def make_output_rows(selected_by_subtype):
    rows = []

    for subtype in SOURCE_PLAN:
        prefix = SOURCE_PREFIX[subtype]
        for index, source in enumerate(selected_by_subtype[subtype], start=1):
            source_id = f"{prefix}_{index:03d}"
            stem = Path(source["file_name"]).stem
            metrics = source["metrics"]
            output_label = "Asthma" if subtype == "Asthma" else "Non_Asthma"

            rows.append({
                "source_id": source_id,
                "label": output_label,
                "subtype": subtype,
                "group_id": source["group_id"],
                "split": source["split"],
                "source_relative_path": source["source_path"],
                "source_sample_rate": metrics["sample_rate"],
                "source_duration_seconds": f"{metrics['duration']:.3f}",
                "source_peak_pcm": metrics["peak"],
                "source_rms_pcm": f"{metrics['rms']:.3f}",
                "source_rms_dbfs": f"{metrics['rms_dbfs']:.3f}",
                "source_clipped_ratio": f"{metrics['clipped_ratio']:.6f}",
                "playback_source_check": "OK",
                "source_sha256": source["sha256"],
                "take_01_file": f"{source_id}__{stem}__take01.wav",
                "take_02_file": f"{source_id}__{stem}__take02.wav",
            })

    return rows


def write_output(rows):
    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"Đầu ra đã tồn tại, không ghi đè: {OUTPUT_DIR}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows, candidate_count, rejection_counts):
    print("\n========== CHỌN NGUỒN PLAYBACK HOÀN TẤT ==========")
    print(f"Seed                : {SEED}")
    print(f"Source đạt chuẩn    : {candidate_count}")
    print(f"Source được chọn    : {len(rows)}")

    for subtype in SOURCE_PLAN:
        subtype_rows = [row for row in rows if row["subtype"] == subtype]
        split_counts = Counter(row["split"] for row in subtype_rows)
        print(
            f"{subtype}: {len(subtype_rows)} source | "
            f"train={split_counts['train']} | "
            f"val={split_counts['val']} | test={split_counts['test']}"
        )

    if rejection_counts:
        print("Source bị loại:")
        for reason, count in sorted(rejection_counts.items()):
            print(f"- {reason}: {count}")

    print(f"CSV output          : {OUTPUT_CSV}")
    print("==================================================")


def main():
    if OUTPUT_DIR.exists():
        print(f"Đầu ra đã tồn tại, script không ghi đè: {OUTPUT_DIR}")
        return

    manifest_rows = read_core_manifest()
    candidates, rejection_counts = build_eligible_candidates(manifest_rows)
    selected_by_subtype = select_playback_sources(candidates)
    output_rows = make_output_rows(selected_by_subtype)
    write_output(output_rows)
    print_summary(output_rows, len(candidates), rejection_counts)


if __name__ == "__main__":
    main()
