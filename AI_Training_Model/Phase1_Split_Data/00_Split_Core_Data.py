"""
===============================================================================
Tên script: 00_Split_Core_Data.py

Tác dụng:
- Đọc trực tiếp các WAV Core trong Dataset_TuThu_v_Kaggle.
- Loại các WAV trùng hoàn toàn bằng SHA-256.
- Chia ngẫu nhiên gần 80/10/10 với SEED = 42.
- Chia theo bệnh nhân, không chia từng file, để một bệnh nhân chỉ nằm trong
  một tập train, val hoặc test.
- Chép WAV vào Dataset_Chia_V2 và tạo CSV báo cáo.

Script này hoàn toàn không đọc core_v1_manifest.csv và không dùng split V1.

Đầu vào:
AI_Training_Model/Dataset_TuThu_v_Kaggle/
|-- asthma/
|-- Bronchial/
|-- copd/
|-- healthy/
`-- pneumonia/

Đầu ra WAV:
AI_Training_Model/Dataset_Chia_V2/
|-- Asthma/{train,val,test}/
`-- Non_Asthma_Disease/{train,val,test}/

Đầu ra CSV:
AI_Training_Model/Phase1_Split_Data/Output/00_Core_Split/
|-- core_split_manifest.csv
`-- core_duplicates.csv
===============================================================================
"""

import csv
import hashlib
import random
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path


SEED = 42

SCRIPT_DIR = Path(__file__).resolve().parent
AI_ROOT = SCRIPT_DIR.parent
RAW_ROOT = AI_ROOT / "Dataset_TuThu_v_Kaggle"
DATASET_OUTPUT = AI_ROOT / "Dataset_Chia_V2"
REPORT_OUTPUT = SCRIPT_DIR / "Output" / "00_Core_Split"

# Thư mục nguồn, nhãn nhị phân và loại bệnh.
SOURCE_CONFIG = (
    ("asthma", "Asthma", "Asthma"),
    ("Bronchial", "Non_Asthma_Disease", "Bronchial"),
    ("copd", "Non_Asthma_Disease", "COPD"),
    ("healthy", "Non_Asthma_Disease", "Healthy"),
    ("pneumonia", "Non_Asthma_Disease", "Pneumonia"),
)


def sha256_file(path):
    """Tính SHA-256 mà không nạp toàn bộ WAV vào RAM."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def get_patient_id(file_name):
    """Lấy mã bệnh nhân P<number> ở đầu tên WAV."""
    match = re.match(r"^(P\d+)", file_name, flags=re.IGNORECASE)
    if match is None:
        raise ValueError(
            f"Tên WAV không bắt đầu bằng mã bệnh nhân P<số>: {file_name}"
        )
    return match.group(1).upper()


def collect_core_files():
    """Quét toàn bộ WAV Core, không đọc manifest V1."""
    records = []

    for folder_name, label, subtype in SOURCE_CONFIG:
        folder = RAW_ROOT / folder_name
        if not folder.is_dir():
            raise FileNotFoundError(f"Không tìm thấy thư mục Core: {folder}")

        wav_files = sorted(folder.glob("*.wav"), key=lambda path: path.name.lower())
        if not wav_files:
            raise RuntimeError(f"Thư mục Core không có WAV: {folder}")

        for path in wav_files:
            patient_id = get_patient_id(path.name)
            group_id = (
                patient_id
                if label == "Asthma"
                else f"{subtype}_{patient_id}"
            )
            records.append({
                "path": path,
                "file_name": path.name,
                "label": label,
                "subtype": subtype,
                "patient_id": patient_id,
                "group_id": group_id,
                "source_path": path.relative_to(RAW_ROOT).as_posix(),
            })

    return records


def remove_duplicates(records):
    """Giữ WAV xuất hiện đầu tiên và ghi lại các bản trùng hoàn toàn."""
    unique_records = []
    duplicate_rows = []
    seen_hashes = {}

    for record in records:
        file_hash = sha256_file(record["path"])
        record["sha256"] = file_hash

        kept = seen_hashes.get(file_hash)
        if kept is None:
            seen_hashes[file_hash] = record
            unique_records.append(record)
            continue

        if kept["label"] != record["label"]:
            raise RuntimeError(
                "Một WAV trùng nội dung nhưng mang hai nhãn khác nhau:\n"
                f"- {kept['path']} ({kept['label']})\n"
                f"- {record['path']} ({record['label']})"
            )

        duplicate_rows.append({
            "file_bo_qua": record["source_path"],
            "trung_voi_file": kept["source_path"],
            "sha256": file_hash,
        })

    return unique_records, duplicate_rows


def split_group_names(group_names, rng):
    """Xáo nhóm rồi chia gần 80/10/10."""
    group_names = sorted(group_names)
    rng.shuffle(group_names)

    total = len(group_names)
    train_count = round(total * 0.8)
    val_count = (total - train_count) // 2
    test_count = total - train_count - val_count

    if min(train_count, val_count, test_count) <= 0:
        raise RuntimeError(
            f"Chỉ có {total} nhóm, không đủ để tạo train/val/test."
        )

    split_by_group = {}
    for group_id in group_names[:train_count]:
        split_by_group[group_id] = "train"
    for group_id in group_names[train_count:train_count + val_count]:
        split_by_group[group_id] = "val"
    for group_id in group_names[train_count + val_count:]:
        split_by_group[group_id] = "test"
    return split_by_group


def assign_random_splits(records):
    """Chia Asthma riêng và từng loại Non-Asthma riêng bằng SEED = 42."""
    rng = random.Random(SEED)
    split_by_group = {}

    asthma_groups = {
        row["group_id"] for row in records if row["label"] == "Asthma"
    }
    split_by_group.update(split_group_names(asthma_groups, rng))

    for subtype in ("Bronchial", "COPD", "Healthy", "Pneumonia"):
        disease_groups = {
            row["group_id"]
            for row in records
            if row["label"] == "Non_Asthma_Disease"
            and row["subtype"] == subtype
        }
        split_by_group.update(split_group_names(disease_groups, rng))

    for row in records:
        row["split"] = split_by_group[row["group_id"]]
        row["output_path"] = (
            Path(row["label"]) / row["split"] / row["file_name"]
        ).as_posix()


def validate_no_group_leakage(records):
    """Bảo đảm một nhóm bệnh nhân không xuất hiện ở nhiều tập."""
    group_splits = defaultdict(set)
    for row in records:
        group_splits[(row["label"], row["group_id"])].add(row["split"])

    leaked_groups = [
        key for key, split_set in group_splits.items() if len(split_set) > 1
    ]
    if leaked_groups:
        raise RuntimeError(f"Nhóm bị rò rỉ giữa các tập: {leaked_groups[0]}")


def check_output_paths():
    """Dừng nếu đầu ra cũ tồn tại để không vô tình ghi đè dataset."""
    paths = (
        DATASET_OUTPUT / "Asthma",
        DATASET_OUTPUT / "Non_Asthma_Disease",
        REPORT_OUTPUT,
    )
    existing = [path for path in paths if path.exists()]
    if not existing:
        return True

    print("Không chạy vì đã tồn tại đầu ra:")
    for path in existing:
        print(f"- {path}")
    print("Hãy kiểm tra và tự di chuyển/xóa đầu ra cũ trước khi chạy lại.")
    return False


def copy_wav_files(records):
    """Chép từng WAV vào đúng nhãn và tập vừa được bốc ngẫu nhiên."""
    for row in records:
        destination = DATASET_OUTPUT / row["output_path"]
        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists():
            raise RuntimeError(f"Trùng tên WAV đầu ra: {destination}")
        shutil.copy2(row["path"], destination)


def write_csv(path, rows, columns):
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_reports(records, duplicate_rows):
    """Tạo CSV truy vết lần chia mới."""
    REPORT_OUTPUT.mkdir(parents=True, exist_ok=False)

    manifest_rows = [{
        "file_name": row["file_name"],
        "label": row["label"],
        "subtype": row["subtype"],
        "patient_id": row["patient_id"],
        "group_id": row["group_id"],
        "split": row["split"],
        "source_path": row["source_path"],
        "output_path": row["output_path"],
        "sha256": row["sha256"],
    } for row in records]

    write_csv(
        REPORT_OUTPUT / "core_split_manifest.csv",
        manifest_rows,
        [
            "file_name", "label", "subtype", "patient_id", "group_id",
            "split", "source_path", "output_path", "sha256",
        ],
    )
    write_csv(
        REPORT_OUTPUT / "core_duplicates.csv",
        duplicate_rows,
        ["file_bo_qua", "trung_voi_file", "sha256"],
    )


def print_summary(records, raw_count, duplicate_count):
    print("\n========== CHIA CORE HOÀN TẤT ==========")
    print(f"Seed               : {SEED}")
    print(f"WAV quét được      : {raw_count}")
    print(f"WAV trùng bỏ qua   : {duplicate_count}")
    print(f"WAV hợp lệ         : {len(records)}")

    for label in ("Asthma", "Non_Asthma_Disease"):
        label_rows = [row for row in records if row["label"] == label]
        counts = Counter(row["split"] for row in label_rows)
        print(
            f"{label}: train={counts['train']} | "
            f"val={counts['val']} | test={counts['test']}"
        )

    print(f"WAV output         : {DATASET_OUTPUT}")
    print(f"CSV report         : {REPORT_OUTPUT}")
    print("========================================")


def main():
    if not check_output_paths():
        return

    raw_records = collect_core_files()
    core_records, duplicate_rows = remove_duplicates(raw_records)
    assign_random_splits(core_records)
    validate_no_group_leakage(core_records)

    copy_wav_files(core_records)
    write_reports(core_records, duplicate_rows)
    print_summary(core_records, len(raw_records), len(duplicate_rows))


if __name__ == "__main__":
    main()
