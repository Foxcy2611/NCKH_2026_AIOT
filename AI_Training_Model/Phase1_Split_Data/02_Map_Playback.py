"""
===============================================================================
Tên script: 02_Map_Playback.py

Tác dụng:
- Đọc Playback_Source_List.csv do 01_Random_Playback.py tạo.
- Tìm hai WAV take01/take02 đã thu qua loa -> INMP441 của mỗi source.
- Giữ nguyên split của source gốc; tuyệt đối không chia ngẫu nhiên lại.
- Chép playback Asthma và Non-Asthma vào đúng train/val/test của
  Dataset_Chia_V2.
- Tạo playback_map_manifest.csv để truy vết file nguồn và file đích.

Đầu vào:
AI_Training_Model/Phase1_Split_Data/Output/01_Random_Playback/
`-- Playback_Source_List.csv

AI_Training_Model/Dataset_TuThu_v_Kaggle/TuThu/Playback_Raw/
|-- Asthma/
`-- Non_Asthma/

Đầu ra WAV được bổ sung vào:
AI_Training_Model/Dataset_Chia_V2/
|-- Asthma/{train,val,test}/
`-- Non_Asthma_Disease/{train,val,test}/

Đầu ra báo cáo:
AI_Training_Model/Phase1_Split_Data/Output/02_Map_Playback/
`-- playback_map_manifest.csv
===============================================================================
"""

import csv
import hashlib
import shutil
import wave
from collections import Counter
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
AI_ROOT = SCRIPT_DIR.parent

SOURCE_LIST_CSV = (
    SCRIPT_DIR
    / "Output"
    / "01_Random_Playback"
    / "Playback_Source_List.csv"
)
PLAYBACK_ROOT = (
    AI_ROOT
    / "Dataset_TuThu_v_Kaggle"
    / "TuThu"
    / "Playback_Raw"
)
DATASET_OUTPUT = AI_ROOT / "Dataset_Chia_V2"
REPORT_OUTPUT = SCRIPT_DIR / "Output" / "02_Map_Playback"
MAP_MANIFEST = REPORT_OUTPUT / "playback_map_manifest.csv"

VALID_SPLITS = {"train", "val", "test"}
EXPECTED_SOURCE_COUNTS = {
    "Asthma": 40,
    "Bronchial": 10,
    "COPD": 10,
    "Healthy": 10,
    "Pneumonia": 10,
}

MAP_COLUMNS = (
    "source_id",
    "label",
    "subtype",
    "group_id",
    "split",
    "take_id",
    "playback_file",
    "playback_source_path",
    "dataset_output_path",
    "sample_rate",
    "duration_seconds",
    "sha256",
)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_source_list():
    if not SOURCE_LIST_CSV.is_file():
        raise FileNotFoundError(
            f"Không tìm thấy {SOURCE_LIST_CSV}. "
            "Hãy chạy 01_Random_Playback.py trước."
        )

    with SOURCE_LIST_CSV.open("r", newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))

    required = {
        "source_id",
        "label",
        "subtype",
        "group_id",
        "split",
        "playback_source_check",
        "take_01_file",
        "take_02_file",
    }
    missing = required.difference(rows[0].keys() if rows else ())
    if missing:
        raise RuntimeError(
            f"Playback_Source_List.csv thiếu cột: {', '.join(sorted(missing))}"
        )

    source_ids = [row["source_id"] for row in rows]
    if len(source_ids) != len(set(source_ids)):
        raise RuntimeError("Playback_Source_List.csv có source_id bị lặp.")

    actual_counts = Counter(row["subtype"] for row in rows)
    if actual_counts != Counter(EXPECTED_SOURCE_COUNTS):
        raise RuntimeError(
            "Số source playback không đúng kế hoạch: "
            f"thực tế={dict(actual_counts)}, "
            f"mong đợi={EXPECTED_SOURCE_COUNTS}"
        )

    return rows


def inspect_playback_wav(path):
    """Kiểm tra WAV thu lại đúng định dạng PCM16 mono và đọc thông số."""
    try:
        with wave.open(str(path), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()
            compression = wav_file.getcomptype()
    except (wave.Error, EOFError) as error:
        raise RuntimeError(f"WAV lỗi {path}: {error}") from error

    if channels != 1 or sample_width != 2 or compression != "NONE":
        raise RuntimeError(f"Playback không phải WAV mono PCM16: {path}")
    if sample_rate <= 0 or frame_count <= 0:
        raise RuntimeError(f"Playback rỗng hoặc sample rate sai: {path}")

    return sample_rate, frame_count / sample_rate


def safe_file_name(value):
    """Chặn tên file có đường dẫn ngoài thư mục playback."""
    name = Path(value)
    if not value or name.name != value:
        raise RuntimeError(f"Tên playback không hợp lệ trong CSV: {value}")
    return value


def build_map_rows(source_rows):
    """Tạo toàn bộ ánh xạ và kiểm tra trước khi chép bất kỳ WAV nào."""
    map_rows = []
    seen_destinations = set()

    for source in source_rows:
        if source["split"] not in VALID_SPLITS:
            raise RuntimeError(
                f"Split không hợp lệ của {source['source_id']}: {source['split']}"
            )
        if source["label"] not in {
            "Asthma", "Non_Asthma", "Non_Asthma_Disease"
        }:
            raise RuntimeError(
                f"Nhãn không hợp lệ của {source['source_id']}: {source['label']}"
            )
        if source["playback_source_check"] != "OK":
            raise RuntimeError(
                f"Source chưa đạt chuẩn playback: {source['source_id']}"
            )

        is_asthma = source["label"] == "Asthma"
        source_folder = "Asthma" if is_asthma else "Non_Asthma"
        output_label = "Asthma" if is_asthma else "Non_Asthma_Disease"

        for take_number in (1, 2):
            take_id = f"take{take_number:02d}"
            file_name = safe_file_name(source[f"take_{take_number:02d}_file"])
            playback_path = PLAYBACK_ROOT / source_folder / file_name
            destination = (
                DATASET_OUTPUT / output_label / source["split"] / file_name
            )

            if not playback_path.is_file():
                raise FileNotFoundError(
                    f"Thiếu playback {source['source_id']} {take_id}: "
                    f"{playback_path}"
                )
            if destination.exists():
                raise FileExistsError(
                    f"File đích đã tồn tại, không ghi đè: {destination}"
                )
            if destination in seen_destinations:
                raise RuntimeError(f"Hai take trùng file đích: {destination}")
            seen_destinations.add(destination)

            sample_rate, duration = inspect_playback_wav(playback_path)
            map_rows.append({
                "source_id": source["source_id"],
                "label": output_label,
                "subtype": source["subtype"],
                "group_id": source["group_id"],
                "split": source["split"],
                "take_id": take_id,
                "playback_file": file_name,
                "playback_source_path": (
                    playback_path.relative_to(AI_ROOT).as_posix()
                ),
                "dataset_output_path": (
                    destination.relative_to(AI_ROOT).as_posix()
                ),
                "sample_rate": sample_rate,
                "duration_seconds": f"{duration:.3f}",
                "sha256": sha256_file(playback_path),
                "source_path_object": playback_path,
                "destination_path_object": destination,
            })

    return map_rows


def copy_playback_files(map_rows):
    for row in map_rows:
        destination = row["destination_path_object"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(row["source_path_object"], destination)

        if sha256_file(destination) != row["sha256"]:
            raise RuntimeError(f"SHA-256 sau khi chép không khớp: {destination}")


def write_map_manifest(map_rows):
    REPORT_OUTPUT.mkdir(parents=True, exist_ok=False)
    clean_rows = [
        {column: row[column] for column in MAP_COLUMNS}
        for row in map_rows
    ]

    with MAP_MANIFEST.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=MAP_COLUMNS)
        writer.writeheader()
        writer.writerows(clean_rows)


def print_summary(map_rows):
    print("\n========== MAP PLAYBACK HOÀN TẤT ==========")
    print(f"Tổng source         : {len(map_rows) // 2}")
    print(f"Tổng WAV playback   : {len(map_rows)}")

    for label in ("Asthma", "Non_Asthma_Disease"):
        selected = [row for row in map_rows if row["label"] == label]
        counts = Counter(row["split"] for row in selected)
        print(
            f"{label}: train={counts['train']} | "
            f"val={counts['val']} | test={counts['test']}"
        )

    print(f"Dataset output      : {DATASET_OUTPUT}")
    print(f"CSV map             : {MAP_MANIFEST}")
    print("===========================================")


def main():
    if REPORT_OUTPUT.exists():
        print(f"Đầu ra đã tồn tại, script không ghi đè: {REPORT_OUTPUT}")
        return

    source_rows = read_source_list()
    map_rows = build_map_rows(source_rows)
    copy_playback_files(map_rows)
    write_map_manifest(map_rows)
    print_summary(map_rows)


if __name__ == "__main__":
    main()
