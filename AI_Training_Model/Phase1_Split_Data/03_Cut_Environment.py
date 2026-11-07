"""
===============================================================================
Tên script: 03_Cut_Environment.py

Tác dụng:
- Quét 33 WAV session môi trường thực tế trong TuThu/Record_Env.
- Chia session bằng SEED = 42 theo quy tắc đã chốt:
  + Validation: 1 Podcast, 1 Fan, 1 Clap.
  + Test: 1 Knock, 1 Room noise, 1 Speech.
  + Train: 27 session còn lại.
- Chép nguyên session vào Out_Split_Session theo đúng split và nhóm.
- Tạo CSV và Markdown để 04_Build_Dataset.py dùng khi cắt clip.

Script này CHƯA cắt WAV. Mỗi session chỉ được khóa vào đúng một split.
Mỗi session được lên kế hoạch tạo 10 clip, mỗi clip dài 5 giây.

Không đưa vào bộ 33 session:
- key_fan_5min.wav: giữ riêng làm tài nguyên nhiễu/mixed.
- silence_5min.wav: giữ riêng cho Quality Check và augmentation Train.

Đầu vào:
AI_Training_Model/Dataset_TuThu_v_Kaggle/TuThu/Record_Env/<Nhóm>/*.wav

Đầu ra:
AI_Training_Model/Dataset_TuThu_v_Kaggle/Out_Split_Session/
|-- train/<Nhóm>/*.wav
|-- val/<Nhóm>/*.wav
`-- test/<Nhóm>/*.wav

AI_Training_Model/Phase1_Split_Data/Output/03_Cut_Environment/
|-- environment_session_split.csv
`-- environment_session_split.md
===============================================================================
"""

import csv
import hashlib
import random
import shutil
import wave
from collections import Counter
from pathlib import Path


SEED = 42
CLIP_SECONDS = 5.0
CLIPS_PER_SESSION = 10

SCRIPT_DIR = Path(__file__).resolve().parent
AI_ROOT = SCRIPT_DIR.parent
DATASET_ROOT = AI_ROOT / "Dataset_TuThu_v_Kaggle"
ENV_ROOT = (
    DATASET_ROOT
    / "TuThu"
    / "Record_Env"
)
OUTPUT_DIR = DATASET_ROOT / "Out_Split_Session"
REPORT_DIR = SCRIPT_DIR / "Output" / "03_Cut_Environment"
OUTPUT_CSV = REPORT_DIR / "environment_session_split.csv"
OUTPUT_MD = REPORT_DIR / "environment_session_split.md"

# Chỉ sáu nhóm này tham gia bộ 33 session.
SESSION_GROUPS = (
    ("podcast", "Podcast", "podcast_session_*.wav", 6),
    ("fan", "Fan", "fan_session_*.wav", 5),
    ("clap", "Clap", "clap_session_*.wav", 6),
    ("knock", "Knock", "knock_session_*.wav", 5),
    ("room_noise", "Room_Noise", "room_noise_session_*.wav", 6),
    ("speech", "Speech", "speech_session_*.wav", 5),
)

# podcast_5min.wav là session Podcast cũ, được tính cùng năm session mới.
SPECIAL_SESSIONS = {
    "podcast_5min.wav": {
        "session_id": "podcast_old_01",
        "subtype": "podcast",
    },
}

# Mỗi nhóm chọn đúng một session cho Val hoặc Test; tất cả phần còn lại là Train.
VALIDATION_GROUPS = {"podcast", "fan", "clap"}
TEST_GROUPS = {"knock", "room_noise", "speech"}

CSV_COLUMNS = (
    "file_name",
    "session_id",
    "label",
    "subtype",
    "split",
    "source_relative_path",
    "output_relative_path",
    "sample_rate",
    "duration_seconds",
    "target_clip_count",
    "clip_seconds",
    "source_sha256",
)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_wav(path):
    """Kiểm tra session là WAV mono PCM16 và đọc thông số thực tế."""
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
        raise RuntimeError(f"Session không phải WAV mono PCM16: {path}")
    if sample_rate <= 0 or frame_count <= 0:
        raise RuntimeError(f"Session rỗng hoặc sample rate sai: {path}")

    duration = frame_count / sample_rate
    minimum_duration = CLIP_SECONDS * CLIPS_PER_SESSION
    if duration < minimum_duration:
        raise RuntimeError(
            f"Session {path.name} chỉ dài {duration:.3f}s, "
            f"không đủ kế hoạch {minimum_duration:.1f}s."
        )
    return sample_rate, duration


def session_id_from_path(path):
    special = SPECIAL_SESSIONS.get(path.name)
    if special:
        return special["session_id"]
    return path.stem


def collect_sessions():
    """Quét WAV thật; không yêu cầu số ID session phải liên tục."""
    records = []

    for subtype, folder_name, pattern, expected_count in SESSION_GROUPS:
        source_folder = ENV_ROOT / folder_name
        paths = sorted(
            source_folder.glob(pattern),
            key=lambda item: item.name.lower(),
        )

        if subtype == "podcast":
            old_podcast = source_folder / "podcast_5min.wav"
            if not old_podcast.is_file():
                raise FileNotFoundError(f"Thiếu session Podcast cũ: {old_podcast}")
            paths.insert(0, old_podcast)

        if len(paths) != expected_count:
            raise RuntimeError(
                f"Nhóm {subtype} phải có {expected_count} session, "
                f"nhưng tìm thấy {len(paths)}: {[path.name for path in paths]}"
            )

        for path in paths:
            sample_rate, duration = inspect_wav(path)
            records.append({
                "file_name": path.name,
                "session_id": session_id_from_path(path),
                "label": "Non_Asthma_Disease",
                "subtype": subtype,
                "split": "",
                "source_relative_path": path.relative_to(ENV_ROOT).as_posix(),
                "sample_rate": sample_rate,
                "duration_seconds": f"{duration:.3f}",
                "target_clip_count": CLIPS_PER_SESSION,
                "clip_seconds": f"{CLIP_SECONDS:.1f}",
                "source_sha256": sha256_file(path),
            })

    session_ids = [row["session_id"] for row in records]
    if len(session_ids) != len(set(session_ids)):
        raise RuntimeError("Có session_id bị lặp trong bộ Environment.")
    if len(records) != 33:
        raise RuntimeError(f"Bộ Environment phải có đúng 33 session, hiện có {len(records)}.")

    return records


def assign_splits(records):
    """Chọn 3 Val, 3 Test bằng seed 42; 27 session còn lại vào Train."""
    rng = random.Random(SEED)

    for subtype, _, _, _ in SESSION_GROUPS:
        group_rows = [row for row in records if row["subtype"] == subtype]
        group_rows.sort(key=lambda row: row["session_id"].lower())
        rng.shuffle(group_rows)

        selected_split = None
        if subtype in VALIDATION_GROUPS:
            selected_split = "val"
        elif subtype in TEST_GROUPS:
            selected_split = "test"

        for index, row in enumerate(group_rows):
            row["split"] = selected_split if index == 0 else "train"

    output_folders = {
        subtype: folder_name
        for subtype, folder_name, _, _ in SESSION_GROUPS
    }
    for row in records:
        row["output_relative_path"] = (
            Path(row["split"])
            / output_folders[row["subtype"]]
            / row["file_name"]
        ).as_posix()


def validate_split(records):
    expected = Counter({"train": 27, "val": 3, "test": 3})
    actual = Counter(row["split"] for row in records)
    if actual != expected:
        raise RuntimeError(
            f"Số session theo split sai: thực tế={dict(actual)}, "
            f"mong đợi={dict(expected)}"
        )

    val_subtypes = {
        row["subtype"] for row in records if row["split"] == "val"
    }
    test_subtypes = {
        row["subtype"] for row in records if row["split"] == "test"
    }
    if val_subtypes != VALIDATION_GROUPS:
        raise RuntimeError(f"Nhóm Validation sai: {sorted(val_subtypes)}")
    if test_subtypes != TEST_GROUPS:
        raise RuntimeError(f"Nhóm Test sai: {sorted(test_subtypes)}")

    output_paths = [row["output_relative_path"] for row in records]
    if len(output_paths) != len(set(output_paths)):
        raise RuntimeError("Có hai session trùng đường dẫn output.")


def copy_sessions(records):
    """Chép nguyên WAV session; bước này chưa cắt thành clip 5 giây."""
    for row in records:
        source = ENV_ROOT / Path(row["source_relative_path"])
        destination = OUTPUT_DIR / Path(row["output_relative_path"])
        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists():
            raise FileExistsError(f"Không ghi đè session output: {destination}")

        shutil.copy2(source, destination)
        if sha256_file(destination) != row["source_sha256"]:
            raise RuntimeError(
                f"SHA-256 sau khi chép không khớp: {destination}"
            )


def write_csv_report(records):
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(records)


def write_markdown_report(records):
    split_counts = Counter(row["split"] for row in records)
    lines = [
        "# Phân chia session Environment V2",
        "",
        f"- Seed: `{SEED}`",
        f"- Tổng: `{len(records)}` session",
        f"- Train: `{split_counts['train']}` session",
        f"- Validation: `{split_counts['val']}` session",
        f"- Test: `{split_counts['test']}` session",
        f"- Kế hoạch cắt: `{CLIPS_PER_SESSION}` clip × `{CLIP_SECONDS:.1f}` giây/session",
        "- `key_fan_5min.wav` và `silence_5min.wav` không thuộc bộ 33 session.",
        f"- Thư mục session đã chia: `{OUTPUT_DIR}`",
        "",
        "## Session Validation",
        "",
        "| Nhóm | Session | File |",
        "|---|---|---|",
    ]

    for row in records:
        if row["split"] == "val":
            lines.append(
                f"| {row['subtype']} | {row['session_id']} | {row['file_name']} |"
            )

    lines.extend([
        "",
        "## Session Test",
        "",
        "| Nhóm | Session | File |",
        "|---|---|---|",
    ])
    for row in records:
        if row["split"] == "test":
            lines.append(
                f"| {row['subtype']} | {row['session_id']} | {row['file_name']} |"
            )

    lines.extend([
        "",
        "## Toàn bộ phân chia",
        "",
        "| Split | Nhóm | Session | File | Số clip dự kiến |",
        "|---|---|---|---|---:|",
    ])
    split_order = {"train": 0, "val": 1, "test": 2}
    for row in sorted(
        records,
        key=lambda item: (
            split_order[item["split"]],
            item["subtype"],
            item["session_id"],
        ),
    ):
        lines.append(
            f"| {row['split']} | {row['subtype']} | {row['session_id']} | "
            f"{row['file_name']} | {row['target_clip_count']} |"
        )

    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_summary(records):
    counts = Counter(row["split"] for row in records)
    print("\n========== CHIA SESSION ENVIRONMENT HOÀN TẤT ==========")
    print(f"Seed                : {SEED}")
    print(f"Tổng session        : {len(records)}")
    print(f"Train / Val / Test  : {counts['train']} / {counts['val']} / {counts['test']}")
    print(f"Session output      : {OUTPUT_DIR}")
    print(f"CSV                 : {OUTPUT_CSV}")
    print(f"Markdown            : {OUTPUT_MD}")
    print("=======================================================")


def main():
    existing_outputs = [
        path for path in (OUTPUT_DIR, REPORT_DIR) if path.exists()
    ]
    if existing_outputs:
        print("Đầu ra đã tồn tại, script không ghi đè:")
        for path in existing_outputs:
            print(f"- {path}")
        return

    records = collect_sessions()
    assign_splits(records)
    validate_split(records)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    REPORT_DIR.mkdir(parents=True, exist_ok=False)
    copy_sessions(records)
    write_csv_report(records)
    write_markdown_report(records)
    print_summary(records)


if __name__ == "__main__":
    main()
