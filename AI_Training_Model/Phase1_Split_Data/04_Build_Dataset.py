"""
===============================================================================
Tên script: 04_Build_Dataset.py

Tác dụng:
- Đọc 33 session đã khóa split bởi 03_Cut_Environment.py.
- Mỗi session cắt thành đúng 10 clip, mỗi clip dài đúng 5 giây.
- Các cửa sổ không chồng lấn và được phân bố đều trên toàn session.
- Giữ nguyên split của session cha.
- Thêm toàn bộ clip vào nhãn Non_Asthma_Disease của Dataset_Chia_V2.
- Sinh CSV và Markdown để truy vết từng clip về session cha.

Đầu vào:
AI_Training_Model/Dataset_TuThu_v_Kaggle/Out_Split_Session/
AI_Training_Model/Phase1_Split_Data/Output/03_Cut_Environment/
`-- environment_session_split.csv

Đầu ra WAV:
AI_Training_Model/Dataset_Chia_V2/Non_Asthma_Disease/{train,val,test}/

Đầu ra báo cáo:
AI_Training_Model/Phase1_Split_Data/Output/04_Build_Dataset/
|-- environment_clip_manifest.csv
`-- environment_clip_summary.md
===============================================================================
"""

import csv
import hashlib
import re
import wave
from collections import Counter
from pathlib import Path


EXPECTED_SAMPLE_RATE = 16000
EXPECTED_SAMPLE_WIDTH = 2
EXPECTED_CHANNELS = 1
EXPECTED_SESSION_COUNTS = Counter({"train": 27, "val": 3, "test": 3})
EXPECTED_CLIPS_PER_SESSION = 10
EXPECTED_CLIP_SECONDS = 5.0

SCRIPT_DIR = Path(__file__).resolve().parent
AI_ROOT = SCRIPT_DIR.parent
SESSION_ROOT = AI_ROOT / "Dataset_TuThu_v_Kaggle" / "Out_Split_Session"
SESSION_MANIFEST = (
    SCRIPT_DIR
    / "Output"
    / "03_Cut_Environment"
    / "environment_session_split.csv"
)
DATASET_OUTPUT = AI_ROOT / "Dataset_Chia_V2" / "Non_Asthma_Disease"
REPORT_DIR = SCRIPT_DIR / "Output" / "04_Build_Dataset"
CLIP_MANIFEST = REPORT_DIR / "environment_clip_manifest.csv"
SUMMARY_MD = REPORT_DIR / "environment_clip_summary.md"

CSV_COLUMNS = (
    "clip_file",
    "label",
    "subtype",
    "session_id",
    "split",
    "clip_index",
    "start_seconds",
    "end_seconds",
    "sample_rate",
    "sample_count",
    "source_session_path",
    "dataset_output_path",
    "source_sha256",
    "clip_sha256",
)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_session_manifest():
    if not SESSION_MANIFEST.is_file():
        raise FileNotFoundError(
            f"Không tìm thấy {SESSION_MANIFEST}. Hãy chạy bước 03 trước."
        )

    with SESSION_MANIFEST.open("r", newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))

    required = {
        "file_name",
        "session_id",
        "label",
        "subtype",
        "split",
        "output_relative_path",
        "sample_rate",
        "duration_seconds",
        "target_clip_count",
        "clip_seconds",
        "source_sha256",
    }
    missing = required.difference(rows[0].keys() if rows else ())
    if missing:
        raise RuntimeError(
            f"Manifest bước 03 thiếu cột: {', '.join(sorted(missing))}"
        )

    split_counts = Counter(row["split"] for row in rows)
    if split_counts != EXPECTED_SESSION_COUNTS:
        raise RuntimeError(
            f"Số session sai: thực tế={dict(split_counts)}, "
            f"mong đợi={dict(EXPECTED_SESSION_COUNTS)}"
        )

    session_ids = [row["session_id"] for row in rows]
    if len(session_ids) != len(set(session_ids)):
        raise RuntimeError("Manifest bước 03 có session_id bị lặp.")

    for row in rows:
        if row["label"] != "Non_Asthma_Disease":
            raise RuntimeError(
                f"Session {row['session_id']} không mang nhãn Non-Asthma."
            )
        if int(row["target_clip_count"]) != EXPECTED_CLIPS_PER_SESSION:
            raise RuntimeError(
                f"Session {row['session_id']} không có kế hoạch 10 clip."
            )
        if float(row["clip_seconds"]) != EXPECTED_CLIP_SECONDS:
            raise RuntimeError(
                f"Session {row['session_id']} không dùng clip 5 giây."
            )

    return rows


def inspect_session(path, expected_hash):
    if not path.is_file():
        raise FileNotFoundError(f"Thiếu WAV session đã chia: {path}")
    if sha256_file(path) != expected_hash:
        raise RuntimeError(f"SHA-256 session không khớp bước 03: {path}")

    try:
        with wave.open(str(path), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()
            compression = wav_file.getcomptype()
    except (wave.Error, EOFError) as error:
        raise RuntimeError(f"WAV session lỗi {path}: {error}") from error

    if (
        channels != EXPECTED_CHANNELS
        or sample_width != EXPECTED_SAMPLE_WIDTH
        or sample_rate != EXPECTED_SAMPLE_RATE
        or compression != "NONE"
    ):
        raise RuntimeError(
            f"Session phải là mono PCM16 {EXPECTED_SAMPLE_RATE} Hz: {path}"
        )

    return frame_count


def safe_session_id(value):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise RuntimeError(f"session_id không an toàn để đặt tên file: {value}")
    return value


def calculate_start_frames(frame_count, clip_frames, clip_count):
    """Rải đều 10 cửa sổ trên toàn session và không cho chúng chồng lấn."""
    minimum_frames = clip_frames * clip_count
    if frame_count < minimum_frames:
        raise RuntimeError(
            f"Session chỉ có {frame_count} frame, cần ít nhất {minimum_frames}."
        )

    if clip_count == 1:
        return [0]

    available_start = frame_count - clip_frames
    starts = [
        round(index * available_start / (clip_count - 1))
        for index in range(clip_count)
    ]

    for previous, current in zip(starts, starts[1:]):
        if current < previous + clip_frames:
            raise RuntimeError("Các cửa sổ 5 giây đang bị chồng lấn.")
    return starts


def build_clip_plan(session_rows):
    """Kiểm tra toàn bộ nguồn và file đích trước khi cắt clip đầu tiên."""
    plan = []
    clip_frames = round(EXPECTED_SAMPLE_RATE * EXPECTED_CLIP_SECONDS)
    seen_destinations = set()

    for session in session_rows:
        session_id = safe_session_id(session["session_id"])
        source = SESSION_ROOT / Path(session["output_relative_path"])
        frame_count = inspect_session(source, session["source_sha256"])
        starts = calculate_start_frames(
            frame_count,
            clip_frames,
            EXPECTED_CLIPS_PER_SESSION,
        )

        for clip_index, start_frame in enumerate(starts, start=1):
            clip_file = (
                f"ENV__{session['subtype']}__{session_id}__"
                f"clip{clip_index:02d}.wav"
            )
            destination = DATASET_OUTPUT / session["split"] / clip_file
            if destination.exists():
                raise FileExistsError(
                    f"Clip Environment đã tồn tại, không ghi đè: {destination}"
                )
            if destination in seen_destinations:
                raise RuntimeError(f"Hai clip trùng đường dẫn: {destination}")
            seen_destinations.add(destination)

            plan.append({
                "clip_file": clip_file,
                "label": "Non_Asthma_Disease",
                "subtype": session["subtype"],
                "session_id": session_id,
                "split": session["split"],
                "clip_index": clip_index,
                "start_frame": start_frame,
                "clip_frames": clip_frames,
                "start_seconds": f"{start_frame / EXPECTED_SAMPLE_RATE:.6f}",
                "end_seconds": (
                    f"{(start_frame + clip_frames) / EXPECTED_SAMPLE_RATE:.6f}"
                ),
                "sample_rate": EXPECTED_SAMPLE_RATE,
                "sample_count": clip_frames,
                "source_session_path": source.relative_to(AI_ROOT).as_posix(),
                "dataset_output_path": destination.relative_to(AI_ROOT).as_posix(),
                "source_sha256": session["source_sha256"],
                "clip_sha256": "",
                "source_path_object": source,
                "destination_path_object": destination,
            })

    expected_clip_counts = Counter({"train": 270, "val": 30, "test": 30})
    actual_clip_counts = Counter(row["split"] for row in plan)
    if actual_clip_counts != expected_clip_counts:
        raise RuntimeError(
            f"Số clip sai: thực tế={dict(actual_clip_counts)}, "
            f"mong đợi={dict(expected_clip_counts)}"
        )
    return plan


def write_clips(plan):
    """Cắt trực tiếp từ session PCM16; không resample hoặc normalize."""
    plans_by_source = {}
    for item in plan:
        plans_by_source.setdefault(item["source_path_object"], []).append(item)

    for source, source_plan in plans_by_source.items():
        with wave.open(str(source), "rb") as input_wav:
            for item in source_plan:
                input_wav.setpos(item["start_frame"])
                raw_clip = input_wav.readframes(item["clip_frames"])
                expected_bytes = item["clip_frames"] * EXPECTED_SAMPLE_WIDTH
                if len(raw_clip) != expected_bytes:
                    raise RuntimeError(
                        f"Clip đọc thiếu byte từ {source}: "
                        f"{len(raw_clip)} != {expected_bytes}"
                    )

                destination = item["destination_path_object"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                with wave.open(str(destination), "wb") as output_wav:
                    output_wav.setnchannels(EXPECTED_CHANNELS)
                    output_wav.setsampwidth(EXPECTED_SAMPLE_WIDTH)
                    output_wav.setframerate(EXPECTED_SAMPLE_RATE)
                    output_wav.writeframes(raw_clip)

                item["clip_sha256"] = sha256_file(destination)


def write_clip_manifest(plan):
    clean_rows = [
        {column: item[column] for column in CSV_COLUMNS}
        for item in plan
    ]
    with CLIP_MANIFEST.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(clean_rows)


def write_summary(plan):
    split_counts = Counter(item["split"] for item in plan)
    subtype_counts = Counter(item["subtype"] for item in plan)
    lines = [
        "# Tổng kết clip Environment V2",
        "",
        f"- Tổng session: `{len(plan) // EXPECTED_CLIPS_PER_SESSION}`",
        f"- Tổng clip: `{len(plan)}`",
        f"- Mỗi session: `{EXPECTED_CLIPS_PER_SESSION}` clip × "
        f"`{EXPECTED_CLIP_SECONDS:.1f}` giây",
        f"- Train: `{split_counts['train']}` clip",
        f"- Validation: `{split_counts['val']}` clip",
        f"- Test: `{split_counts['test']}` clip",
        "- Nhãn: `Non_Asthma_Disease`",
        "- Không resample, normalize hoặc augmentation tại bước 04.",
        "",
        "## Số clip theo nhóm",
        "",
        "| Nhóm | Số clip |",
        "|---|---:|",
    ]
    for subtype, count in sorted(subtype_counts.items()):
        lines.append(f"| {subtype} | {count} |")

    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_summary(plan):
    counts = Counter(item["split"] for item in plan)
    print("\n========== BUILD ENVIRONMENT HOÀN TẤT ==========")
    print(f"Tổng clip           : {len(plan)}")
    print(f"Train / Val / Test  : {counts['train']} / {counts['val']} / {counts['test']}")
    print(f"Dataset output      : {DATASET_OUTPUT}")
    print(f"CSV manifest        : {CLIP_MANIFEST}")
    print(f"Markdown            : {SUMMARY_MD}")
    print("================================================")


def main():
    if REPORT_DIR.exists():
        print(f"Báo cáo bước 04 đã tồn tại, script không ghi đè: {REPORT_DIR}")
        return

    session_rows = read_session_manifest()
    plan = build_clip_plan(session_rows)

    write_clips(plan)
    REPORT_DIR.mkdir(parents=True, exist_ok=False)
    write_clip_manifest(plan)
    write_summary(plan)
    print_summary(plan)


if __name__ == "__main__":
    main()
