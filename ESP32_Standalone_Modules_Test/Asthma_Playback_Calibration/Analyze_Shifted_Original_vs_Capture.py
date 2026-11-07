"""Doi chung temporal shift cua WAV goc voi WAV thu lai qua loa -> INMP441.

Quy trinh:
1. Doc offset da do boi Analyze_Capture_Offset.py.
2. Resample WAV goc bang dung cau hinh cua Preprocess_Audio.py.
3. Crop dung 5 giay tai tung offset.
4. Chay tung crop qua cung Python preprocessing + V1 PTQ INT8.
5. So p_non_shifted_python voi p_non_capture_python cua cung trial.

Script khong train va khong thay doi capture/calibration CSV goc.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.io import wavfile

try:
    from .Run_Playback_Calibration import PythonV1Runner
except ImportError:
    from Run_Playback_Calibration import PythonV1Runner


# =============================================================================
# CAU HINH
# =============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parents[1]

TARGET_FILE = "Playback_Calibration/Asthma/01__P47WheezingRS_232.wav"

EXPERIMENT_DIR = (
    WORKSPACE_DIR
    / "Experiments_Benchmarking"
    / "Patient_Node"
    / "Final_V1_Validation"
    / "01_Classification_Threshold"
)
SOURCE_WAV = EXPERIMENT_DIR / TARGET_FILE

OFFSET_ANALYSIS_DIR = (
    SCRIPT_DIR
    / "calibration_results"
    / "offset_analysis"
    / Path(TARGET_FILE).stem
)
OFFSET_CSV = OFFSET_ANALYSIS_DIR / "capture_offset_results.csv"
OUTPUT_DIR = OFFSET_ANALYSIS_DIR / "shift_vs_capture"
CROP_DIR = OUTPUT_DIR / "shifted_original_crops"
RESULT_CSV = OUTPUT_DIR / "shift_vs_capture_results.csv"

SAMPLE_RATE = 16_000
WINDOW_SECONDS = 5.0
WINDOW_SAMPLES = int(SAMPLE_RATE * WINDOW_SECONDS)

# Nguong chi dung de sinh ket luan goi y, khong phai threshold model.
NEAR_ASTHMA_P_NON = 0.20
HIGH_P_NON = 0.50
SIMILAR_PROBABILITY_DELTA = 0.15

CSV_COLUMNS = [
    "file",
    "trial",
    "offset_samples",
    "offset_seconds",
    "offset_ms",
    "p_non_original_python",
    "p_non_shifted_python",
    "p_non_capture_python",
    "p_non_esp32",
    "delta_shifted_minus_original",
    "delta_capture_minus_shifted",
    "absolute_shifted_capture_gap",
    "crop_file",
    "capture_file",
]


def configure_target(target_file: str) -> None:
    """Cho phep script batch doi file ma khong sua source bang tay."""
    global TARGET_FILE, SOURCE_WAV
    global OFFSET_ANALYSIS_DIR, OFFSET_CSV
    global OUTPUT_DIR, CROP_DIR, RESULT_CSV

    TARGET_FILE = target_file
    SOURCE_WAV = EXPERIMENT_DIR / TARGET_FILE
    OFFSET_ANALYSIS_DIR = (
        SCRIPT_DIR
        / "calibration_results"
        / "offset_analysis"
        / Path(TARGET_FILE).stem
    )
    OFFSET_CSV = OFFSET_ANALYSIS_DIR / "capture_offset_results.csv"
    OUTPUT_DIR = OFFSET_ANALYSIS_DIR / "shift_vs_capture"
    CROP_DIR = OUTPUT_DIR / "shifted_original_crops"
    RESULT_CSV = OUTPUT_DIR / "shift_vs_capture_results.csv"


def load_offset_rows() -> list[dict[str, str]]:
    if not OFFSET_CSV.is_file():
        raise FileNotFoundError(
            f"Chua co {OFFSET_CSV}. Hay chay Analyze_Capture_Offset.py truoc."
        )

    with OFFSET_CSV.open("r", newline="", encoding="utf-8-sig") as file:
        rows = [row for row in csv.DictReader(file) if row["file"] == TARGET_FILE]

    if len(rows) != 3:
        raise ValueError(f"Can dung 3 offset cua {TARGET_FILE}, dang co {len(rows)}")
    rows.sort(key=lambda row: float(row["source_offset_seconds"]))
    return rows


def load_original_resampled(runner: PythonV1Runner) -> np.ndarray:
    if not SOURCE_WAV.is_file():
        raise FileNotFoundError(f"Khong tim thay WAV goc: {SOURCE_WAV}")

    preprocess = runner.preprocess
    audio, _ = preprocess.librosa.load(
        SOURCE_WAV,
        sr=preprocess.SR,
        mono=True,
        offset=0.0,
        duration=None,
        dtype=preprocess.LOAD_DTYPE,
        res_type=preprocess.RESAMPLE_TYPE,
    )
    audio = np.asarray(audio, dtype=np.float32)
    if audio.size == 0 or not np.isfinite(audio).all():
        raise ValueError("WAV goc rong hoac co NaN/Inf sau resample")
    if preprocess.SR != SAMPLE_RATE:
        raise ValueError(
            f"Preprocess SR={preprocess.SR}, script dang yeu cau {SAMPLE_RATE}"
        )
    return audio


def crop_exact_window(audio: np.ndarray, start_sample: int) -> np.ndarray:
    if start_sample < 0:
        raise ValueError(f"Offset am: {start_sample}")
    stop_sample = start_sample + WINDOW_SAMPLES
    crop = audio[start_sample:stop_sample]
    if crop.size < WINDOW_SAMPLES:
        crop = np.pad(crop, (0, WINDOW_SAMPLES - crop.size), mode="constant")
    if crop.size != WINDOW_SAMPLES:
        raise RuntimeError(f"Crop khong dung {WINDOW_SAMPLES} mau: {crop.size}")
    return np.asarray(crop, dtype=np.float32)


def write_results(rows: list[dict[str, str | int | float]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with RESULT_CSV.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def plot_probabilities(rows: list[dict[str, str | int | float]]) -> None:
    offsets_ms = np.asarray([float(row["offset_ms"]) for row in rows])
    shifted = np.asarray([float(row["p_non_shifted_python"]) for row in rows])
    captured = np.asarray([float(row["p_non_capture_python"]) for row in rows])
    esp32 = np.asarray([float(row["p_non_esp32"]) for row in rows])
    original = float(rows[0]["p_non_original_python"])

    fig, ax = plt.subplots(figsize=(10, 5.5), constrained_layout=True)
    ax.axhline(
        original,
        color="black",
        linestyle="--",
        linewidth=1.2,
        label=f"Original 0 ms: {original:.4f}",
    )
    ax.plot(offsets_ms, shifted, "o-", linewidth=1.8, label="Shifted original / Python")
    ax.plot(offsets_ms, captured, "s-", linewidth=1.8, label="Capture / Python")
    ax.plot(offsets_ms, esp32, "^-", linewidth=1.4, label="Capture / ESP32")
    ax.set_ylim(-0.03, 1.03)
    ax.set_xlabel("Offset crop cua WAV goc (ms)")
    ax.set_ylabel("p_non_asthma")
    ax.set_title("Anh huong temporal shift va duong truyen loa -> INMP441")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(OUTPUT_DIR / "shift_vs_capture_probability.png", dpi=170)
    plt.close(fig)


def make_conclusion(rows: list[dict[str, str | int | float]]) -> tuple[str, dict[str, float]]:
    original = float(rows[0]["p_non_original_python"])
    shifted = np.asarray(
        [float(row["p_non_shifted_python"]) for row in rows], dtype=np.float64
    )
    captured = np.asarray(
        [float(row["p_non_capture_python"]) for row in rows], dtype=np.float64
    )

    shifted_mean = float(np.mean(shifted))
    capture_mean = float(np.mean(captured))
    mean_gap = float(np.mean(np.abs(captured - shifted)))
    alignment_rise = shifted_mean - original
    acoustic_rise = capture_mean - shifted_mean

    if float(np.max(shifted)) <= NEAR_ASTHMA_P_NON and capture_mean >= HIGH_P_NON:
        conclusion = (
            "LOA -> INMP441 CHIEM UU THE: cac crop bi shift van giu p_non gan Asthma, "
            "nhung capture that tang cao."
        )
    elif shifted_mean >= HIGH_P_NON and mean_gap <= SIMILAR_PROBABILITY_DELTA:
        conclusion = (
            "ALIGNMENT CHIEM UU THE: shifted original cung tang p_non cao va nam gan "
            "capture that."
        )
    elif alignment_rise > 0.10 and acoustic_rise > 0.10:
        conclusion = (
            "CA HAI CUNG GOP PHAN: temporal shift lam p_non tang, va duong truyen "
            "loa -> INMP441 lam tang them dang ke."
        )
    else:
        conclusion = (
            "CHUA TAC BACH RO: can xem tung trial, waveform va co the lap lai voi "
            "hai file Asthma con lai."
        )

    metrics = {
        "p_non_original": original,
        "p_non_shifted_mean": shifted_mean,
        "p_non_shifted_min": float(np.min(shifted)),
        "p_non_shifted_max": float(np.max(shifted)),
        "p_non_capture_mean": capture_mean,
        "p_non_capture_min": float(np.min(captured)),
        "p_non_capture_max": float(np.max(captured)),
        "mean_absolute_shifted_capture_gap": mean_gap,
        "alignment_rise_vs_original": alignment_rise,
        "acoustic_rise_vs_shifted": acoustic_rise,
    }
    return conclusion, metrics


def write_summary(
    rows: list[dict[str, str | int | float]],
    conclusion: str,
    metrics: dict[str, float],
) -> None:
    lines = [
        "# Shifted original vs capture",
        "",
        f"- Source: `{TARGET_FILE}`",
        f"- Model: V1 PTQ INT8",
        f"- Moi crop: {WINDOW_SECONDS:.1f} giay tai {SAMPLE_RATE} Hz",
        "- So sanh chinh: Python shifted-original vs Python capture.",
        "",
        "| Trial | Offset (ms) | Original | Shifted original | Capture Python | ESP32 | Capture - shifted |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['trial']} | {float(row['offset_ms']):.3f} | "
            f"{float(row['p_non_original_python']):.9f} | "
            f"{float(row['p_non_shifted_python']):.9f} | "
            f"{float(row['p_non_capture_python']):.9f} | "
            f"{float(row['p_non_esp32']):.9f} | "
            f"{float(row['delta_capture_minus_shifted']):+.9f} |"
        )

    lines.extend(
        [
            "",
            "## Tong hop",
            "",
            f"- Original p_non: {metrics['p_non_original']:.9f}",
            f"- Shifted mean: {metrics['p_non_shifted_mean']:.9f}",
            f"- Capture mean: {metrics['p_non_capture_mean']:.9f}",
            f"- Alignment rise: {metrics['alignment_rise_vs_original']:+.9f}",
            f"- Acoustic path rise: {metrics['acoustic_rise_vs_shifted']:+.9f}",
            f"- Mean |capture - shifted|: {metrics['mean_absolute_shifted_capture_gap']:.9f}",
            "",
            f"**Ket luan goi y:** {conclusion}",
            "",
            "> Day la phep tach nguyen nhan thuc nghiem, khong phai phep chung minh",
            "> nhan qua tuyet doi. Neu ket qua khong dong nhat, lap lai tren hai WAV",
            "> Asthma con lai truoc khi sua VAD hoac retrain.",
        ]
    )
    (OUTPUT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def analyze_target(
    target_file: str,
    runner: PythonV1Runner | None = None,
) -> Path:
    configure_target(target_file)
    offset_rows = load_offset_rows()
    if runner is None:
        print("Dang tai Python preprocessing + V1 PTQ INT8...")
        runner = PythonV1Runner()
    original_audio = load_original_resampled(runner)
    p_non_original = runner.infer(SOURCE_WAV)

    CROP_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, str | int | float]] = []

    for offset_row in offset_rows:
        trial = int(offset_row["trial"])
        offset_seconds = float(offset_row["source_offset_seconds"])
        offset_samples = int(round(offset_seconds * SAMPLE_RATE))
        crop = crop_exact_window(original_audio, offset_samples)
        crop_path = (
            CROP_DIR
            / f"{SOURCE_WAV.stem}__offset_{offset_samples:05d}_samples__trial{trial}.wav"
        )

        # IEEE float32 WAV giu nguyen crop sau resample, tranh them mot lan PCM16 quantize.
        wavfile.write(crop_path, SAMPLE_RATE, crop.astype(np.float32))
        p_non_shifted = runner.infer(crop_path)
        p_non_capture = float(offset_row["p_non_capture_python"])
        p_non_esp32 = float(offset_row["p_non_esp32"])

        result: dict[str, str | int | float] = {
            "file": TARGET_FILE,
            "trial": trial,
            "offset_samples": offset_samples,
            "offset_seconds": offset_samples / SAMPLE_RATE,
            "offset_ms": offset_samples * 1000.0 / SAMPLE_RATE,
            "p_non_original_python": f"{p_non_original:.9f}",
            "p_non_shifted_python": f"{p_non_shifted:.9f}",
            "p_non_capture_python": f"{p_non_capture:.9f}",
            "p_non_esp32": f"{p_non_esp32:.9f}",
            "delta_shifted_minus_original": f"{p_non_shifted - p_non_original:+.9f}",
            "delta_capture_minus_shifted": f"{p_non_capture - p_non_shifted:+.9f}",
            "absolute_shifted_capture_gap": f"{abs(p_non_capture - p_non_shifted):.9f}",
            "crop_file": crop_path.relative_to(SCRIPT_DIR).as_posix(),
            "capture_file": offset_row["capture_file"],
        }
        results.append(result)
        print(
            f"Offset={float(result['offset_ms']):.3f} ms | "
            f"original={p_non_original:.9f} | shifted={p_non_shifted:.9f} | "
            f"capture={p_non_capture:.9f} | esp32={p_non_esp32:.9f}"
        )

    write_results(results)
    plot_probabilities(results)
    conclusion, metrics = make_conclusion(results)
    write_summary(results, conclusion, metrics)

    print("\n" + conclusion)
    print(f"Output: {OUTPUT_DIR}")
    return OUTPUT_DIR


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    analyze_target(TARGET_FILE)


if __name__ == "__main__":
    main()
