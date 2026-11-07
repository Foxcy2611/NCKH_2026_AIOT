"""Tao Dataset_Chia_V3 tu V2, giu tat ca WAV tru playback.

Nguyen tac:
- Giu nguyen cau truc Asthma/Non_Asthma_Disease va train/val/test.
- Chi copy file .wav; khong di chuyen hoac sua Dataset_Chia_V2.
- Playback duoc xac dinh boi manifest buoc 02 va suffix __take01/__take02.
- Hai cach nhan dien phai cho cung mot tap file truoc khi script copy.
- Script co the chay lai: file dich dung size se duoc bo qua, file khac size se bao loi.
"""

from __future__ import annotations

import csv
import hashlib
import shutil
import sys
from collections import Counter
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
AI_ROOT = SCRIPT_DIR.parent

SOURCE_ROOT = AI_ROOT / "Dataset_Chia_V2"
DESTINATION_ROOT = AI_ROOT / "Dataset_Chia_V3"
PLAYBACK_MANIFEST = (
    SCRIPT_DIR / "Output" / "02_Map_Playback" / "playback_map_manifest.csv"
)
REPORT_DIR = SCRIPT_DIR / "Output" / "06_Dataset_V3_Without_Playback"
OUTPUT_MANIFEST = REPORT_DIR / "dataset_v3_manifest.csv"
OUTPUT_SUMMARY = REPORT_DIR / "dataset_v3_summary.md"

EXPECTED_CLASSES = {"Asthma", "Non_Asthma_Disease"}
EXPECTED_SPLITS = {"train", "val", "test"}
PLAYBACK_SUFFIXES = ("__take01", "__take02")

MANIFEST_COLUMNS = [
    "relative_path",
    "class_name",
    "split",
    "file_name",
    "size_bytes",
    "sha256",
    "copy_action",
]


def normalize_relative_path(value: str) -> str:
    path = Path(value.replace("\\", "/"))
    parts = path.parts
    if not parts or "Dataset_Chia_V2" not in parts:
        raise ValueError(f"Sai dataset_output_path trong playback manifest: {value}")
    dataset_index = parts.index("Dataset_Chia_V2")
    relative = Path(*parts[dataset_index + 1 :])
    if not relative.parts or ".." in relative.parts:
        raise ValueError(f"Duong dan playback khong an toan: {value}")
    return relative.as_posix()


def load_playback_manifest_paths() -> set[str]:
    if not PLAYBACK_MANIFEST.is_file():
        raise FileNotFoundError(f"Thieu playback manifest: {PLAYBACK_MANIFEST}")

    paths: set[str] = set()
    with PLAYBACK_MANIFEST.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        if "dataset_output_path" not in (reader.fieldnames or []):
            raise ValueError("Playback manifest thieu cot dataset_output_path")
        for row in reader:
            relative = normalize_relative_path(row["dataset_output_path"])
            if relative in paths:
                raise ValueError(f"Playback manifest trung duong dan: {relative}")
            paths.add(relative)

    if not paths:
        raise ValueError("Playback manifest rong")
    return paths


def validate_dataset_path(relative_path: Path) -> tuple[str, str]:
    if len(relative_path.parts) != 3:
        raise ValueError(
            "WAV trong V2 phai co dang <class>/<split>/<file.wav>: "
            f"{relative_path.as_posix()}"
        )
    class_name, split, _ = relative_path.parts
    if class_name not in EXPECTED_CLASSES:
        raise ValueError(f"Class khong hop le: {relative_path.as_posix()}")
    if split not in EXPECTED_SPLITS:
        raise ValueError(f"Split khong hop le: {relative_path.as_posix()}")
    return class_name, split


def is_playback_suffix(path: Path) -> bool:
    return path.stem.casefold().endswith(PLAYBACK_SUFFIXES)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_and_validate() -> tuple[list[Path], set[str], list[Path]]:
    if not SOURCE_ROOT.is_dir():
        raise FileNotFoundError(f"Khong tim thay Dataset_Chia_V2: {SOURCE_ROOT}")

    all_wavs = sorted(
        (path for path in SOURCE_ROOT.rglob("*.wav") if path.is_file()),
        key=lambda path: path.relative_to(SOURCE_ROOT).as_posix().casefold(),
    )
    if not all_wavs:
        raise ValueError("Dataset_Chia_V2 khong co WAV")

    manifest_playback = load_playback_manifest_paths()
    suffix_playback = {
        path.relative_to(SOURCE_ROOT).as_posix()
        for path in all_wavs
        if is_playback_suffix(path)
    }
    actual_relative = {
        path.relative_to(SOURCE_ROOT).as_posix() for path in all_wavs
    }

    missing_manifest_files = manifest_playback - actual_relative
    if missing_manifest_files:
        raise FileNotFoundError(
            "Playback manifest tro toi file khong con trong V2:\n- "
            + "\n- ".join(sorted(missing_manifest_files))
        )
    if manifest_playback != suffix_playback:
        only_manifest = sorted(manifest_playback - suffix_playback)
        only_suffix = sorted(suffix_playback - manifest_playback)
        raise ValueError(
            "Manifest playback va suffix __take01/__take02 khong dong nhat.\n"
            f"Chi trong manifest: {only_manifest[:10]}\n"
            f"Chi theo suffix: {only_suffix[:10]}"
        )

    kept_files: list[Path] = []
    excluded_files: list[Path] = []
    for source_path in all_wavs:
        relative_path = source_path.relative_to(SOURCE_ROOT)
        validate_dataset_path(relative_path)
        if relative_path.as_posix() in manifest_playback:
            excluded_files.append(source_path)
        else:
            kept_files.append(source_path)

    return kept_files, manifest_playback, excluded_files


def copy_and_verify(kept_files: list[Path]) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    for index, source_path in enumerate(kept_files, start=1):
        relative_path = source_path.relative_to(SOURCE_ROOT)
        class_name, split = validate_dataset_path(relative_path)
        destination_path = DESTINATION_ROOT / relative_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        if destination_path.exists():
            if not destination_path.is_file():
                raise RuntimeError(f"Dich ton tai nhung khong phai file: {destination_path}")
            if destination_path.stat().st_size != source_path.stat().st_size:
                raise RuntimeError(
                    f"File dich khac size, khong tu ghi de: {destination_path}"
                )
            action = "verified_existing"
        else:
            shutil.copy2(source_path, destination_path)
            action = "copied"

        source_hash = sha256_file(source_path)
        destination_hash = sha256_file(destination_path)
        if source_hash != destination_hash:
            raise IOError(f"SHA256 khong khop sau copy: {relative_path.as_posix()}")

        rows.append(
            {
                "relative_path": relative_path.as_posix(),
                "class_name": class_name,
                "split": split,
                "file_name": source_path.name,
                "size_bytes": source_path.stat().st_size,
                "sha256": source_hash,
                "copy_action": action,
            }
        )
        if index % 100 == 0 or index == len(kept_files):
            print(f"Da xu ly {index}/{len(kept_files)} WAV", flush=True)
    return rows


def verify_destination(expected_rows: list[dict[str, str | int]]) -> None:
    expected = {str(row["relative_path"]) for row in expected_rows}
    actual_paths = sorted(
        path for path in DESTINATION_ROOT.rglob("*.wav") if path.is_file()
    )
    actual = {
        path.relative_to(DESTINATION_ROOT).as_posix() for path in actual_paths
    }

    if expected != actual:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        raise RuntimeError(
            "Dataset_Chia_V3 khong khop danh sach mong doi.\n"
            f"Thieu: {missing[:10]}\n"
            f"Du: {unexpected[:10]}"
        )
    playback_left = [path for path in actual_paths if is_playback_suffix(path)]
    if playback_left:
        raise RuntimeError(
            "V3 van con playback:\n- "
            + "\n- ".join(str(path) for path in playback_left[:10])
        )


def write_reports(
    rows: list[dict[str, str | int]],
    source_total: int,
    playback_total: int,
) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_MANIFEST.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    counts = Counter((str(row["class_name"]), str(row["split"])) for row in rows)
    copied = sum(row["copy_action"] == "copied" for row in rows)
    verified = sum(row["copy_action"] == "verified_existing" for row in rows)
    total_bytes = sum(int(row["size_bytes"]) for row in rows)

    lines = [
        "# Dataset_Chia_V3 - Loai bo Playback",
        "",
        f"- Nguon: `{SOURCE_ROOT.relative_to(AI_ROOT).as_posix()}`",
        f"- Dich: `{DESTINATION_ROOT.relative_to(AI_ROOT).as_posix()}`",
        f"- Tong WAV V2: {source_total}",
        f"- Playback loai bo: {playback_total}",
        f"- WAV giu lai trong V3: {len(rows)}",
        f"- Dung luong V3: {total_bytes} byte",
        f"- Copy moi trong lan chay nay: {copied}",
        f"- File cu da verify: {verified}",
        "",
        "| Class | Split | So WAV |",
        "|---|---|---:|",
    ]
    for class_name in sorted(EXPECTED_CLASSES):
        for split in ("train", "val", "test"):
            lines.append(f"| {class_name} | {split} | {counts[(class_name, split)]} |")
    lines.extend(
        [
            "",
            "## Quy tac",
            "",
            "- Khong copy bat ky WAV nao co trong playback manifest buoc 02.",
            "- Manifest va suffix `__take01`/`__take02` phai trung khop tuyet doi.",
            "- Moi WAV V3 duoc doi chieu SHA256 voi WAV V2.",
            "- Dataset_Chia_V2 khong bi sua hoac di chuyen.",
        ]
    )
    OUTPUT_SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 72)
    print("BUILD DATASET_CHIA_V3 WITHOUT PLAYBACK")
    print("=" * 72)

    kept_files, playback_paths, excluded_files = scan_and_validate()
    source_total = len(kept_files) + len(excluded_files)
    print(f"Tong WAV V2       : {source_total}")
    print(f"Playback loai bo  : {len(playback_paths)}")
    print(f"WAV giu lai cho V3: {len(kept_files)}")
    print(f"Dich               : {DESTINATION_ROOT}")

    rows = copy_and_verify(kept_files)
    verify_destination(rows)
    write_reports(rows, source_total, len(playback_paths))

    print("=" * 72)
    print("HOAN THANH DATASET_CHIA_V3")
    print(f"WAV V3   : {len(rows)}")
    print(f"Manifest : {OUTPUT_MANIFEST}")
    print(f"Summary  : {OUTPUT_SUMMARY}")


if __name__ == "__main__":
    main()
