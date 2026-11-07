"""So sanh 3 capture cua cung mot WAV Asthma bang cross-correlation.

Mac dinh chon file Asthma dau tien trong bo calibration vi file nay co bien
dong p_non_capture lon nhat. Doi TARGET_FILE neu muon phan tich file khac.
"""

from __future__ import annotations

import csv
import math
import sys
import wave
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal


# =============================================================================
# CAU HINH
# =============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parents[1]
RESULT_CSV = SCRIPT_DIR / "calibration_results" / "playback_calibration_results.csv"

TARGET_FILE = "Playback_Calibration/Asthma/01__P47WheezingRS_232.wav"
SAMPLE_RATE = 16_000
LOW_CUT_HZ = 100.0
HIGH_CUT_HZ = 1_800.0

# VAD xu ly theo chunk 256 mau = 16 ms. Cho phep toi da hai chunk sai khac.
STABLE_SPREAD_SECONDS = 0.032
MIN_RELIABLE_CORRELATION = 0.10

EXPERIMENT_DIR = (
    WORKSPACE_DIR
    / "Experiments_Benchmarking"
    / "Patient_Node"
    / "Final_V1_Validation"
    / "01_Classification_Threshold"
)
OUTPUT_DIR = (
    SCRIPT_DIR
    / "calibration_results"
    / "offset_analysis"
    / Path(TARGET_FILE).stem
)


def configure_target(target_file: str) -> None:
    """Cho phep script batch doi file ma khong sua source bang tay."""
    global TARGET_FILE, OUTPUT_DIR
    TARGET_FILE = target_file
    OUTPUT_DIR = (
        SCRIPT_DIR
        / "calibration_results"
        / "offset_analysis"
        / Path(TARGET_FILE).stem
    )


def load_target_rows() -> list[dict[str, str]]:
    if not RESULT_CSV.is_file():
        raise FileNotFoundError(f"Khong tim thay calibration CSV: {RESULT_CSV}")

    with RESULT_CSV.open("r", newline="", encoding="utf-8-sig") as file:
        rows = [
            row
            for row in csv.DictReader(file)
            if row["file"] == TARGET_FILE and row["true_class"] == "Asthma"
        ]

    rows.sort(key=lambda row: int(row["trial"]))
    if len(rows) != 3 or [int(row["trial"]) for row in rows] != [1, 2, 3]:
        raise ValueError(
            f"Can dung trial 1/2/3 cua {TARGET_FILE}, nhung tim thay "
            f"{[row.get('trial') for row in rows]}"
        )
    return rows


def load_audio(path: Path) -> np.ndarray:
    if not path.is_file():
        raise FileNotFoundError(f"Khong tim thay WAV: {path}")

    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        source_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
        compression = wav_file.getcomptype()
        pcm_bytes = wav_file.readframes(frame_count)

    if channels != 1 or sample_width != 2 or compression != "NONE":
        raise ValueError(
            f"Chi ho tro mono PCM16: {path} "
            f"(channels={channels}, width={sample_width}, type={compression})"
        )

    audio = np.frombuffer(pcm_bytes, dtype="<i2").astype(np.float64) / 32768.0
    if source_rate != SAMPLE_RATE:
        common_divisor = math.gcd(source_rate, SAMPLE_RATE)
        audio = signal.resample_poly(
            audio,
            up=SAMPLE_RATE // common_divisor,
            down=source_rate // common_divisor,
        )
    audio = np.asarray(audio, dtype=np.float32)
    if audio.size == 0 or not np.isfinite(audio).all():
        raise ValueError(f"Audio rong hoac co NaN/Inf: {path}")
    return audio


def bandpass_for_alignment(audio: np.ndarray) -> np.ndarray:
    sos = signal.butter(
        5,
        [LOW_CUT_HZ, HIGH_CUT_HZ],
        btype="bandpass",
        fs=SAMPLE_RATE,
        output="sos",
    )
    filtered = signal.sosfiltfilt(sos, audio.astype(np.float64))
    filtered -= np.mean(filtered)
    scale = np.std(filtered)
    if scale <= np.finfo(np.float64).eps:
        raise ValueError("Tin hieu gan nhu silence sau bandpass")
    return filtered / scale


def normalized_valid_correlation(
    source: np.ndarray,
    capture: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """NCC tai moi vi tri ma capture nam tron trong source."""
    if source.size < capture.size:
        raise ValueError(
            f"WAV goc ngan hon capture: {source.size} < {capture.size} mau"
        )

    template = capture - np.mean(capture)
    template_energy = float(np.sum(np.square(template)))
    if template_energy <= np.finfo(np.float64).eps:
        raise ValueError("Capture khong co du nang luong de correlation")

    numerator = signal.correlate(source, template, mode="valid", method="fft")
    # Rolling sum O(N), nhanh hon viec FFT-convolve voi mot cua so 80000 so 1.
    cumulative = np.concatenate(([0.0], np.cumsum(source, dtype=np.float64)))
    cumulative_square = np.concatenate(
        ([0.0], np.cumsum(np.square(source), dtype=np.float64))
    )
    window_sum = cumulative[capture.size :] - cumulative[: -capture.size]
    window_square_sum = (
        cumulative_square[capture.size :] - cumulative_square[: -capture.size]
    )
    source_energy = window_square_sum - np.square(window_sum) / capture.size
    denominator = np.sqrt(np.maximum(source_energy, 0.0) * template_energy)
    ncc = np.divide(
        numerator,
        denominator,
        out=np.zeros_like(numerator),
        where=denominator > np.finfo(np.float64).eps,
    )
    offsets = np.arange(ncc.size, dtype=np.int64)
    return offsets, ncc


def analyze_trial(
    source_filtered: np.ndarray,
    row: dict[str, str],
) -> tuple[dict[str, str | int | float], np.ndarray, np.ndarray, np.ndarray]:
    capture_path = SCRIPT_DIR / row["capture_file"]
    capture = load_audio(capture_path)
    if capture.size != 80_000:
        raise ValueError(f"Capture phai co 80000 mau: {capture_path}")
    capture_filtered = bandpass_for_alignment(capture)

    offset_samples, ncc = normalized_valid_correlation(
        source_filtered, capture_filtered
    )
    peak_index = int(np.argmax(np.abs(ncc)))
    best_offset_samples = int(offset_samples[peak_index])
    signed_correlation = float(ncc[peak_index])

    result: dict[str, str | int | float] = {
        "file": row["file"],
        "trial": int(row["trial"]),
        "capture_file": row["capture_file"],
        "source_offset_samples": best_offset_samples,
        "source_offset_seconds": best_offset_samples / SAMPLE_RATE,
        "correlation_signed": signed_correlation,
        "correlation_abs": abs(signed_correlation),
        "polarity": "normal" if signed_correlation >= 0.0 else "inverted",
        "p_non_capture_python": float(row["p_non_capture_python"]),
        "p_non_esp32": float(row["p_non_esp32"]),
        "pcm_rms": float(row["pcm_rms"]),
        "pcm_peak": int(row["pcm_peak"]),
    }
    return result, capture, offset_samples, ncc


def write_csv(path: Path, rows: list[dict[str, str | int | float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_waveforms(
    source: np.ndarray,
    captures: list[np.ndarray],
    results: list[dict[str, str | int | float]],
) -> None:
    decimation = 8
    fig, axes = plt.subplots(2, 1, figsize=(14, 9), constrained_layout=True)

    source_norm = source / max(float(np.max(np.abs(source))), 1e-12)
    source_time = np.arange(source.size) / SAMPLE_RATE
    axes[0].plot(
        source_time[::decimation],
        source_norm[::decimation],
        color="black",
        linewidth=0.7,
        label="Original",
    )
    axes[0].set_title("Waveform goc sau resample 16 kHz")
    axes[0].set_xlabel("Thoi gian trong WAV goc (s)")
    axes[0].set_ylabel("Bien do chuan hoa")
    axes[0].grid(alpha=0.25)
    axes[0].legend()

    colors = ["tab:blue", "tab:orange", "tab:green"]
    axes[1].plot(
        source_time[::decimation],
        source_norm[::decimation],
        color="black",
        linewidth=0.8,
        alpha=0.7,
        label="Original",
    )
    for capture, result, color in zip(captures, results, colors, strict=True):
        capture_norm = capture / max(float(np.max(np.abs(capture))), 1e-12)
        offset = float(result["source_offset_seconds"])
        capture_time = offset + np.arange(capture.size) / SAMPLE_RATE
        axes[1].plot(
            capture_time[::decimation],
            capture_norm[::decimation],
            color=color,
            linewidth=0.55,
            alpha=0.70,
            label=(
                f"Trial {result['trial']} | offset={offset * 1000.0:.2f} ms | "
                f"|r|={float(result['correlation_abs']):.3f}"
            ),
        )
    axes[1].set_title("Ba capture dat tai offset tim boi cross-correlation")
    axes[1].set_xlabel("Thoi gian trong WAV goc (s)")
    axes[1].set_ylabel("Bien do chuan hoa")
    axes[1].grid(alpha=0.25)
    axes[1].legend(loc="upper right")

    fig.savefig(OUTPUT_DIR / "waveform_alignment.png", dpi=170)
    plt.close(fig)


def plot_correlations(
    correlations: list[tuple[np.ndarray, np.ndarray]],
    results: list[dict[str, str | int | float]],
) -> None:
    fig, ax = plt.subplots(figsize=(12, 5), constrained_layout=True)
    colors = ["tab:blue", "tab:orange", "tab:green"]
    for (offset_samples, ncc), result, color in zip(
        correlations, results, colors, strict=True
    ):
        offset_seconds = offset_samples / SAMPLE_RATE
        ax.plot(
            offset_seconds,
            np.abs(ncc),
            color=color,
            linewidth=1.0,
            label=f"Trial {result['trial']}",
        )
        ax.axvline(
            float(result["source_offset_seconds"]),
            color=color,
            linestyle="--",
            linewidth=0.9,
        )
    ax.set_title("Normalized cross-correlation: WAV goc vs tung capture")
    ax.set_xlabel("Offset bat dau trong WAV goc (s)")
    ax.set_ylabel("|NCC|")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(OUTPUT_DIR / "cross_correlation.png", dpi=170)
    plt.close(fig)


def write_summary(results: list[dict[str, str | int | float]]) -> None:
    offsets = np.asarray(
        [float(row["source_offset_seconds"]) for row in results], dtype=np.float64
    )
    correlations = np.asarray(
        [float(row["correlation_abs"]) for row in results], dtype=np.float64
    )
    p_non = np.asarray(
        [float(row["p_non_capture_python"]) for row in results], dtype=np.float64
    )

    offset_mean = float(np.mean(offsets))
    offset_std = float(np.std(offsets))
    offset_spread = float(np.ptp(offsets))
    correlation_reliable = bool(np.min(correlations) >= MIN_RELIABLE_CORRELATION)

    if not correlation_reliable:
        verdict = (
            "CHUA THE KET LUAN: it nhat mot capture co cross-correlation qua yeu; "
            "can xem waveform/loa/micro hoac dung envelope alignment."
        )
    elif offset_spread <= STABLE_SPREAD_SECONDS:
        verdict = (
            "OFFSET ON DINH: spread khong vuot 32 ms (hai VAD chunk). "
            "Bien dong p_non kho co the quy hoan toan cho VAD/window start."
        )
    else:
        verdict = (
            "OFFSET KHONG ON DINH: spread vuot 32 ms. VAD/window start la mot "
            "nguyen nhan can uu tien kiem tra."
        )

    lines = [
        "# Phan tich offset capture Asthma",
        "",
        f"- File: `{TARGET_FILE}`",
        f"- Sample rate phan tich: {SAMPLE_RATE} Hz",
        f"- Bandpass alignment: {LOW_CUT_HZ:.0f}-{HIGH_CUT_HZ:.0f} Hz",
        "- Quy uoc offset: vi tri trong WAV goc tuong ung voi mau dau capture.",
        "",
        "| Trial | Offset (sample) | Offset (ms) | |NCC| | p_non Python | p_non ESP32 |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in results:
        lines.append(
            f"| {row['trial']} | {row['source_offset_samples']} | "
            f"{float(row['source_offset_seconds']) * 1000.0:.3f} | "
            f"{float(row['correlation_abs']):.6f} | "
            f"{float(row['p_non_capture_python']):.9f} | "
            f"{float(row['p_non_esp32']):.9f} |"
        )

    lines.extend(
        [
            "",
            "## Tong hop",
            "",
            f"- Offset mean: {offset_mean * 1000.0:.3f} ms",
            f"- Offset std: {offset_std * 1000.0:.3f} ms",
            f"- Offset spread max-min: {offset_spread * 1000.0:.3f} ms",
            f"- NCC nho nhat: {float(np.min(correlations)):.6f}",
            f"- p_non Python spread: {float(np.ptp(p_non)):.9f}",
            "",
            f"**Ket luan tu dong:** {verdict}",
            "",
            "> Cross-correlation chi danh gia do lech thoi gian. No khong chung minh",
            "> bien do, dap ung tan so loa/micro hay nhieu phong giong WAV goc.",
        ]
    )
    (OUTPUT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def analyze_target(target_file: str) -> Path:
    configure_target(target_file)
    rows = load_target_rows()
    source_path = EXPERIMENT_DIR / TARGET_FILE
    source = load_audio(source_path)
    source_filtered = bandpass_for_alignment(source)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, str | int | float]] = []
    captures: list[np.ndarray] = []
    correlations: list[tuple[np.ndarray, np.ndarray]] = []

    for row in rows:
        print(f"Dang phan tich trial {row['trial']}...", flush=True)
        result, capture, offset_samples, ncc = analyze_trial(source_filtered, row)
        results.append(result)
        captures.append(capture)
        correlations.append((offset_samples, ncc))
        print(
            f"Trial {result['trial']}: "
            f"offset={float(result['source_offset_seconds']) * 1000.0:.3f} ms | "
            f"NCC={float(result['correlation_abs']):.6f} | "
            f"p_non={float(result['p_non_capture_python']):.9f}"
        , flush=True)

    median_offset = float(
        np.median([float(row["source_offset_seconds"]) for row in results])
    )
    for result in results:
        result["delta_from_median_ms"] = (
            float(result["source_offset_seconds"]) - median_offset
        ) * 1000.0

    write_csv(OUTPUT_DIR / "capture_offset_results.csv", results)
    plot_waveforms(source, captures, results)
    plot_correlations(correlations, results)
    write_summary(results)

    spread_ms = (
        max(float(row["source_offset_seconds"]) for row in results)
        - min(float(row["source_offset_seconds"]) for row in results)
    ) * 1000.0
    print(f"Offset spread: {spread_ms:.3f} ms")
    print(f"Output: {OUTPUT_DIR}")
    return OUTPUT_DIR


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    analyze_target(TARGET_FILE)


if __name__ == "__main__":
    main()
