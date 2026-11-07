"""Chuan bi 3 WAV Asthma + 3 WAV Non-Asthma de test playback tren ESP32-S3.

Uu tien su dung manifest RAW PCM16 cua Phase 4 vi manifest nay da do bien do
sau khi dua WAV ve dang PCM16/16 kHz dung cho pipeline deploy. Neu manifest
khong ton tai hoac khong du mau, script se quet tap Test va tu do WAV.

Script chi doc WAV va copy cac file duoc chon. Khong preprocess, khong sua WAV,
khong train va khong dung Test de thay doi threshold da chot.
"""

from __future__ import annotations

import csv
import math
import shutil
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np


# =============================================================================
# CAU HINH DE DOI TRUC TIEP
# =============================================================================

SAMPLES_PER_CLASS = 3
MIN_RMS_PCM16 = 1_000.0
MIN_PEAK_PCM16 = 5_000

# Chi uu tien mau ma ket qua Python Phase 4 dung nhan neu manifest co cot nay.
# Neu khong du 3 mau dung nhan, script tu dong bo sung bang mau bien do cao nhat.
PREFER_MODEL_CORRECT_SAMPLES = True

# Giu file Asthma so 1 da kich hoat VAD tot; cac vi tri con lai duoc chon theo
# RMS/peak cao nhất trong toàn bộ tập Test nhưng vẫn ưu tiên C4 QAT INT8 đoán đúng.
PINNED_SOURCE_FILES = {
    0: ("P47WheezingRS_232.wav",),
    1: (),
}


SCRIPT_DIR = Path(__file__).resolve().parent


def find_workspace_root(start: Path) -> Path:
    """Dò root dự án để script chạy được từ mọi working directory."""
    start = start.resolve()
    for candidate in (start, *start.parents):
        if (
            (candidate / "AI_Training_Model").is_dir()
            and (candidate / "Experiments_Benchmarking" / "Patient_Node").is_dir()
        ):
            return candidate
    raise FileNotFoundError(
        "Không tìm thấy root dự án chứa AI_Training_Model và "
        f"Experiments_Benchmarking từ: {start}"
    )


WORKSPACE_DIR = find_workspace_root(SCRIPT_DIR)
AI_DIR = WORKSPACE_DIR / "AI_Training_Model"

DATASET_DIR = AI_DIR / "Dataset_Chia_V2"
PHASE4_MANIFEST = (
    AI_DIR
    / "Phase4_Deployment_Artifacts"
    / "Output_LiveMic_PCM16_Test"
    / "LiveMic_PCM16_Test_Manifest.csv"
)
FINAL_MODEL_PREDICTIONS = (
    WORKSPACE_DIR
    / "Experiments_Benchmarking"
    / "Patient_Node"
    / "Frontend_Benchmarking"
    / "artifacts"
    / "D_Quantization"
    / "combo_pre0_mel40_fft2048__V1__s44"
    / "evaluation"
    / "QAT_INT8"
    / "test_predictions.csv"
)

OUTPUT_DIR = SCRIPT_DIR / "Playback_Calibration"
OUTPUT_MANIFEST = OUTPUT_DIR / "Playback_Calibration_Manifest.csv"
OUTPUT_README = OUTPUT_DIR / "README.md"

CLASS_CONFIG = {
    0: {
        "name": "Asthma",
        "scan_dir": DATASET_DIR / "Asthma" / "test",
    },
    1: {
        "name": "Non_Asthma",
        "scan_dir": DATASET_DIR / "Non_Asthma_Disease" / "test",
    },
}


@dataclass
class Candidate:
    class_label: int
    class_name: str
    source_path: Path
    source_relative_path: str
    rms_pcm16: float
    peak_pcm16: int
    expected_p_non_asthma: float | None = None
    expected_predicted_label: int | None = None
    metric_source: str = "measured_from_wav"

    @property
    def model_prediction_correct(self) -> bool | None:
        if self.expected_predicted_label is None:
            return None
        return self.expected_predicted_label == self.class_label

    @property
    def amplitude_pass(self) -> bool:
        return self.rms_pcm16 >= MIN_RMS_PCM16 and self.peak_pcm16 >= MIN_PEAK_PCM16


def portable_path(path: Path) -> str:
    path = path.resolve()
    try:
        return path.relative_to(WORKSPACE_DIR).as_posix()
    except ValueError:
        return path.as_posix()


def parse_optional_float(value: str | None) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def parse_optional_int(value: str | None) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    return int(value)


def pcm_bytes_to_float64(raw: bytes, sample_width: int) -> np.ndarray:
    """Doc PCM WAV 8/16/24/32-bit va dua ve mien [-1, 1]."""
    if sample_width == 1:
        values = np.frombuffer(raw, dtype=np.uint8).astype(np.float64)
        return (values - 128.0) / 128.0

    if sample_width == 2:
        return np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0

    if sample_width == 3:
        bytes_3 = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        values = (
            bytes_3[:, 0].astype(np.int32)
            | (bytes_3[:, 1].astype(np.int32) << 8)
            | (bytes_3[:, 2].astype(np.int32) << 16)
        )
        values = np.where(values & 0x800000, values - 0x1000000, values)
        return values.astype(np.float64) / 8_388_608.0

    if sample_width == 4:
        return np.frombuffer(raw, dtype="<i4").astype(np.float64) / 2_147_483_648.0

    raise ValueError(f"Khong ho tro WAV sample width={sample_width} byte")


def measure_wav_pcm16_equivalent(path: Path) -> tuple[float, int]:
    """Tinh RMS/peak quy doi ve thang PCM16, khong thay doi file goc."""
    with wave.open(str(path), "rb") as wav_file:
        if wav_file.getcomptype() != "NONE":
            raise ValueError(f"Chi ho tro PCM WAV, file dang nen: {path}")
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        raw = wav_file.readframes(wav_file.getnframes())

    samples = pcm_bytes_to_float64(raw, sample_width)
    if samples.size == 0:
        return 0.0, 0

    if channels > 1:
        if samples.size % channels != 0:
            raise ValueError(f"So mau khong chia het cho {channels} kenh: {path}")
        samples = samples.reshape(-1, channels).mean(axis=1)

    samples = np.nan_to_num(samples, nan=0.0, posinf=1.0, neginf=-1.0)
    rms = math.sqrt(float(np.mean(np.square(samples)))) * 32768.0
    peak = int(round(float(np.max(np.abs(samples))) * 32768.0))
    return rms, min(peak, 32768)


def resolve_manifest_source(relative_path: str) -> Path:
    source = DATASET_DIR / Path(relative_path)
    if not source.is_file():
        raise FileNotFoundError(f"Manifest tro toi WAV khong ton tai: {source}")
    return source


def load_phase4_candidates() -> list[Candidate]:
    if not PHASE4_MANIFEST.is_file():
        return []

    candidates: list[Candidate] = []
    with PHASE4_MANIFEST.open("r", newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            label = int(row["class_label"])
            if label not in CLASS_CONFIG:
                continue

            source = resolve_manifest_source(row["source_relative_path"])
            candidates.append(
                Candidate(
                    class_label=label,
                    class_name=CLASS_CONFIG[label]["name"],
                    source_path=source,
                    source_relative_path=row["source_relative_path"],
                    rms_pcm16=float(row["rms_pcm16"]),
                    peak_pcm16=int(row["peak_pcm16"]),
                    expected_p_non_asthma=parse_optional_float(
                        row.get("expected_probability_non_asthma")
                    ),
                    expected_predicted_label=parse_optional_int(
                        row.get("expected_predicted_label")
                    ),
                    metric_source="phase4_live_mic_manifest",
                )
            )
    return candidates


def load_final_int8_predictions() -> dict[str, tuple[float, int]]:
    if not FINAL_MODEL_PREDICTIONS.is_file():
        return {}

    predictions: dict[str, tuple[float, int]] = {}
    with FINAL_MODEL_PREDICTIONS.open("r", newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            source_name = Path(row["file"].replace("\\", "/")).name
            predictions[source_name] = (
                float(row["p_non_asthma"]),
                int(row["predicted_label"]),
            )
    return predictions


def scan_dataset_candidates(
    existing_paths: set[Path],
    labels_to_scan: set[int],
    predictions: dict[str, tuple[float, int]],
) -> list[Candidate]:
    candidates: list[Candidate] = []
    for label, config in CLASS_CONFIG.items():
        if label not in labels_to_scan:
            continue
        scan_dir = Path(config["scan_dir"])
        if not scan_dir.is_dir():
            raise FileNotFoundError(f"Khong tim thay folder Test: {scan_dir}")

        for source in sorted(scan_dir.rglob("*.wav"), key=lambda p: p.as_posix().casefold()):
            resolved = source.resolve()
            if resolved in existing_paths:
                continue
            try:
                rms, peak = measure_wav_pcm16_equivalent(source)
            except (EOFError, ValueError, wave.Error) as error:
                print(f"[BO QUA] {source.name}: {error}")
                continue

            prediction = predictions.get(source.name)

            candidates.append(
                Candidate(
                    class_label=label,
                    class_name=str(config["name"]),
                    source_path=source,
                    source_relative_path=source.relative_to(DATASET_DIR).as_posix(),
                    rms_pcm16=rms,
                    peak_pcm16=peak,
                    expected_p_non_asthma=(
                        prediction[0] if prediction is not None else None
                    ),
                    expected_predicted_label=(
                        prediction[1] if prediction is not None else None
                    ),
                )
            )
    return candidates


def choose_class_candidates(candidates: list[Candidate], label: int) -> list[Candidate]:
    class_candidates = [item for item in candidates if item.class_label == label]
    if len(class_candidates) < SAMPLES_PER_CLASS:
        raise ValueError(
            f"Class {CLASS_CONFIG[label]['name']} chi co {len(class_candidates)} WAV hop le"
        )

    def rank_key(item: Candidate) -> tuple[int, int, float, int, str]:
        correct_priority = int(item.model_prediction_correct is True)
        return (
            int(item.amplitude_pass),
            correct_priority if PREFER_MODEL_CORRECT_SAMPLES else 0,
            item.rms_pcm16,
            item.peak_pcm16,
            item.source_path.name.casefold(),
        )

    ranked = sorted(class_candidates, key=rank_key, reverse=True)

    selected: list[Candidate] = []
    pinned_names = PINNED_SOURCE_FILES.get(label, ())
    for pinned_name in pinned_names:
        pinned = next(
            (item for item in class_candidates if item.source_path.name == pinned_name),
            None,
        )
        if pinned is None:
            raise FileNotFoundError(
                f"Khong tim thay WAV da pin cho {CLASS_CONFIG[label]['name']}: "
                f"{pinned_name}"
            )
        selected.append(pinned)

    selected_paths = {item.source_path.resolve() for item in selected}
    selected.extend(
        item
        for item in ranked
        if item.source_path.resolve() not in selected_paths
    )
    selected = selected[:SAMPLES_PER_CLASS]
    if any(not item.amplitude_pass for item in selected):
        weak = ", ".join(item.source_path.name for item in selected if not item.amplitude_pass)
        raise ValueError(
            "Khong du WAV vuot nguong bien do offline. "
            f"Mau yeu trong top {SAMPLES_PER_CLASS}: {weak}"
        )
    return selected


def copy_selection(selection: list[Candidate]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for label in sorted(CLASS_CONFIG):
        class_name = str(CLASS_CONFIG[label]["name"])
        class_dir = OUTPUT_DIR / class_name
        class_dir.mkdir(parents=True, exist_ok=True)

        # Chi xoa cac WAV mang mau ten do chinh script nay tao, tranh de lai
        # file cu khi danh sach calibration thay doi giua hai lan chay.
        for old_copy in class_dir.glob("[0-9][0-9]__*.wav"):
            old_copy.unlink()

        selected_class = [item for item in selection if item.class_label == label]
        for rank, item in enumerate(selected_class, start=1):
            destination = class_dir / f"{rank:02d}__{item.source_path.name}"
            shutil.copy2(item.source_path, destination)
            rows.append(
                {
                    "class_label": label,
                    "class_name": class_name,
                    "rank_in_class": rank,
                    "source_file": item.source_path.name,
                    "source_relative_path": item.source_relative_path,
                    "copied_file": destination.relative_to(SCRIPT_DIR).as_posix(),
                    "rms_pcm16": f"{item.rms_pcm16:.6f}",
                    "peak_pcm16": item.peak_pcm16,
                    "amplitude_pass": int(item.amplitude_pass),
                    "metric_source": item.metric_source,
                    "expected_p_non_asthma": (
                        "" if item.expected_p_non_asthma is None
                        else f"{item.expected_p_non_asthma:.9f}"
                    ),
                    "expected_predicted_label": (
                        "" if item.expected_predicted_label is None
                        else item.expected_predicted_label
                    ),
                    "model_prediction_correct": (
                        "" if item.model_prediction_correct is None
                        else int(item.model_prediction_correct)
                    ),
                }
            )
    return rows


def write_manifest(rows: list[dict[str, object]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_MANIFEST.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_readme(rows: list[dict[str, object]]) -> None:
    lines = [
        "# Playback Calibration",
        "",
        "Bộ WAV này dùng để phát qua loa và đo `p_non_asthma` từ",
        "`Deploy_Model/3_Model_Complete`. Các file chỉ được copy, không bị sửa.",
        "",
        "> RMS/peak của WAV chỉ giúp chọn trước file đủ mạnh. Việc kích hoạt VAD thật",
        "> còn phụ thuộc âm lượng loa, khoảng cách, hướng loa và nhiễu phòng.",
        "",
        "## Cách test",
        "",
        "1. Giữ cố định loa, âm lượng và khoảng cách tới INMP441.",
        "2. Chờ Serial báo bộ đệm 1 giây đã sẵn sàng.",
        "3. Phát từng WAV từ đầu, không tua vào giữa file.",
        "4. Ghi lại log `[VAD]` và `[AI] p_non_asthma=...` cho từng file.",
        "5. Mỗi WAV nên phát ít nhất 3 lần để quan sát độ dao động thực tế.",
        "",
        "## Danh sách đã chọn",
        "",
        "| Class | File | RMS PCM16 | Peak PCM16 | p_non Python |",
        "|---|---|---:|---:|---:|",
    ]
    for row in rows:
        expected = row["expected_p_non_asthma"] or "N/A"
        lines.append(
            f"| {row['class_name']} | `{row['copied_file']}` | "
            f"{row['rms_pcm16']} | {row['peak_pcm16']} | {expected} |"
        )
    lines.append("")
    OUTPUT_README.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    candidates = load_phase4_candidates()
    existing_paths = {item.source_path.resolve() for item in candidates}
    predictions = load_final_int8_predictions()

    # Quet toan bo Asthma Test de co the thay cac mau Phase 4 qua nho. Non-Asthma
    # van giu tap Phase 4 da chon; neu manifest thieu thi moi quet bo sung class do.
    labels_to_scan = {0}
    for label in CLASS_CONFIG:
        count = sum(item.class_label == label for item in candidates)
        if count < SAMPLES_PER_CLASS:
            labels_to_scan.add(label)
    candidates.extend(
        scan_dataset_candidates(existing_paths, labels_to_scan, predictions)
    )

    selection: list[Candidate] = []
    for label in sorted(CLASS_CONFIG):
        selection.extend(choose_class_candidates(candidates, label))

    rows = copy_selection(selection)
    write_manifest(rows)
    write_readme(rows)

    print("=" * 72)
    print("PLAYBACK CALIBRATION SET")
    print("=" * 72)
    for row in rows:
        print(
            f"[{row['class_name']:<10}] RMS={float(row['rms_pcm16']):8.2f} | "
            f"peak={int(row['peak_pcm16']):5d} | {row['source_file']}"
        )
    print("-" * 72)
    print(f"Output  : {portable_path(OUTPUT_DIR)}")
    print(f"Manifest: {portable_path(OUTPUT_MANIFEST)}")
    print("Luu y  : Can xac nhan lai VAD bang loa + INMP441 thuc te.")


if __name__ == "__main__":
    main()
