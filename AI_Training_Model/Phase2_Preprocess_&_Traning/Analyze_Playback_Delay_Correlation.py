"""
===============================================================================
Tên script: Analyze_Playback_Delay_Correlation.py

Mục đích:
- Ghép từng raw source Asthma với take01/take02 tương ứng.
- Dùng normalized cross-correlation để ước lượng playback trễ bao nhiêu giây.
- Chỉ phân tích Train + Validation; không dùng Test để chọn quy tắc crop.
- Xuất delay từng take, độ nhất quán giữa hai take và thống kê tổng hợp.
- Đề xuất dùng fixed offset hoặc căn riêng từng file theo delay.

Script KHÔNG train, KHÔNG gọi model và KHÔNG sửa/cắt/ghi đè WAV nguồn.
===============================================================================
"""

import csv
import math
import sys
from pathlib import Path

import librosa
import numpy as np
from scipy.signal import butter, correlate, sosfiltfilt


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# =============================================================================
# CẤU HÌNH
# =============================================================================

TARGET_SR = 16000
ANALYSIS_SPLITS = ("train", "val")

# Dải tần đang được Patient Node/model quan tâm. Band-pass giúp correlation bớt
# bị chi phối bởi DC, tiếng ù rất thấp và nhiễu cao tần.
LOW_CUT_HZ = 100.0
HIGH_CUT_HZ = 2000.0
FILTER_ORDER = 4

# Cross-correlation chỉ tìm delay playback không âm trong khoảng này.
MAX_DELAY_SECONDS = 2.0

# RMS envelope bền hơn waveform trước đáp ứng loa, micro và môi trường phòng.
RMS_FRAME_MS = 25.0
RMS_HOP_MS = 5.0
PEAK_EXCLUSION_SECONDS = 0.15

# Các ngưỡng chỉ dùng để đánh dấu kết quả correlation đáng tin cậy.
MIN_ENVELOPE_CORRELATION = 0.35
MIN_WAVEFORM_CORRELATION = 0.10
MIN_PEAK_MARGIN = 0.005
MAX_METHOD_DISAGREEMENT_SECONDS = 0.20

# Điều kiện tham khảo để kết luận delay đủ ổn định cho fixed offset.
MIN_RELIABLE_RATE = 0.80
FIXED_MAX_STD_SECONDS = 0.12
FIXED_MAX_P90_P10_SECONDS = 0.30
FIXED_MAX_PAIR_MEDIAN_DIFF_SECONDS = 0.15
FIXED_MAX_TRAIN_VAL_MEDIAN_DIFF_SECONDS = 0.20
FIXED_OFFSET_STEP_SECONDS = 0.25


SCRIPT_DIR = Path(__file__).resolve().parent
AI_DIR = SCRIPT_DIR.parent
ANALYSIS_ROOT = SCRIPT_DIR / "Output_Analysis_V1"

SOURCE_LIST_PATH = (
    AI_DIR
    / "Phase1_Split_Data"
    / "Output"
    / "01_Random_Playback"
    / "Playback_Source_List.csv"
)
DATASET_SOURCE_ROOT = AI_DIR / "Dataset_TuThu_v_Kaggle"
PLAYBACK_ROOT = (
    DATASET_SOURCE_ROOT
    / "TuThu"
    / "Playback_Raw"
    / "Asthma"
)

OUTPUT_DIR = ANALYSIS_ROOT / "Output_Playback_Delay_Correlation"
DETAIL_CSV = OUTPUT_DIR / "Playback_Delay_Per_Take.csv"
PAIR_CSV = OUTPUT_DIR / "Playback_Delay_Take_Pairs.csv"
SUMMARY_CSV = OUTPUT_DIR / "Playback_Delay_Summary.csv"
REPORT_MD = OUTPUT_DIR / "Playback_Delay_Correlation_Report.md"


DETAIL_COLUMNS = [
    "split",
    "source_id",
    "group_id",
    "source_file",
    "take_id",
    "playback_file",
    "raw_duration_seconds",
    "take_duration_seconds",
    "waveform_delay_seconds",
    "waveform_peak_correlation",
    "waveform_peak_margin",
    "envelope_delay_seconds",
    "envelope_peak_correlation",
    "envelope_peak_margin",
    "method_disagreement_seconds",
    "delay_seconds",
    "delay_method",
    "reliable",
    "status",
    "note",
]

PAIR_COLUMNS = [
    "split",
    "source_id",
    "group_id",
    "source_file",
    "take01_delay_seconds",
    "take02_delay_seconds",
    "absolute_difference_seconds",
    "both_reliable",
]

SUMMARY_COLUMNS = [
    "split",
    "total_takes",
    "valid_takes",
    "reliable_takes",
    "reliable_rate",
    "mean_delay_seconds",
    "median_delay_seconds",
    "std_delay_seconds",
    "min_delay_seconds",
    "p10_delay_seconds",
    "p90_delay_seconds",
    "max_delay_seconds",
    "p90_minus_p10_seconds",
]


def read_csv_clean(path):
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy manifest: {path}")

    rows = []
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            rows.append(
                {
                    str(key).strip(): value.strip() if isinstance(value, str) else value
                    for key, value in row.items()
                }
            )
    return rows


def write_csv(path, rows, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def round_value(value, digits=6):
    if value is None or not np.isfinite(value):
        return ""
    return round(float(value), digits)


def load_audio(path):
    audio, _ = librosa.load(
        path,
        sr=TARGET_SR,
        mono=True,
        dtype=np.float32,
        res_type="soxr_hq",
    )
    if audio.size == 0:
        raise ValueError("WAV không chứa mẫu âm thanh")
    if not np.all(np.isfinite(audio)):
        raise ValueError("WAV chứa NaN hoặc Inf")
    return audio


def bandpass(audio):
    nyquist = TARGET_SR / 2.0
    sos = butter(
        FILTER_ORDER,
        [LOW_CUT_HZ / nyquist, HIGH_CUT_HZ / nyquist],
        btype="bandpass",
        output="sos",
    )
    return sosfiltfilt(sos, audio).astype(np.float32)


def rms_envelope(audio):
    frame_length = max(2, int(round(TARGET_SR * RMS_FRAME_MS / 1000.0)))
    hop_length = max(1, int(round(TARGET_SR * RMS_HOP_MS / 1000.0)))
    rms = librosa.feature.rms(
        y=audio,
        frame_length=frame_length,
        hop_length=hop_length,
        center=False,
    )[0]
    # Log compression giữ hình dạng năng lượng nhưng giảm ảnh hưởng của một peak lớn.
    return np.log1p(rms * 1000.0).astype(np.float32), hop_length


def normalized_valid_cross_correlation(reference, recorded, use_absolute=False):
    """Trượt toàn bộ reference trên recorded và trả correlation coefficient."""
    reference = np.asarray(reference, dtype=np.float64)
    recorded = np.asarray(recorded, dtype=np.float64)

    if reference.size < 2:
        raise ValueError("Reference quá ngắn để cross-correlation")
    if recorded.size < reference.size:
        raise ValueError("Playback ngắn hơn raw source")

    reference = reference - np.mean(reference)
    reference_energy = float(np.dot(reference, reference))
    if reference_energy <= 1e-12:
        raise ValueError("Reference gần như silence")

    window = reference.size
    numerator = correlate(recorded, reference, mode="valid", method="fft")

    cumulative = np.concatenate(([0.0], np.cumsum(recorded, dtype=np.float64)))
    cumulative_sq = np.concatenate(
        ([0.0], np.cumsum(recorded * recorded, dtype=np.float64))
    )
    window_sum = cumulative[window:] - cumulative[:-window]
    window_sum_sq = cumulative_sq[window:] - cumulative_sq[:-window]
    window_energy = window_sum_sq - (window_sum * window_sum / window)
    denominator = np.sqrt(np.maximum(window_energy * reference_energy, 1e-20))

    scores = numerator / denominator
    if use_absolute:
        scores = np.abs(scores)
    return np.clip(scores, -1.0, 1.0)


def select_peak(scores, seconds_per_step):
    if scores.size == 0:
        raise ValueError("Không có lag hợp lệ")

    max_steps = min(
        scores.size - 1,
        int(round(MAX_DELAY_SECONDS / seconds_per_step)),
    )
    limited = scores[: max_steps + 1]
    peak_index = int(np.argmax(limited))
    peak_value = float(limited[peak_index])

    exclusion = max(1, int(round(PEAK_EXCLUSION_SECONDS / seconds_per_step)))
    keep = np.ones(limited.size, dtype=bool)
    keep[max(0, peak_index - exclusion) : peak_index + exclusion + 1] = False
    second_peak = float(np.max(limited[keep])) if np.any(keep) else math.nan
    margin = peak_value - second_peak if np.isfinite(second_peak) else math.nan

    return peak_index * seconds_per_step, peak_value, margin


def estimate_delay(raw_audio, take_audio):
    raw_filtered = bandpass(raw_audio)
    take_filtered = bandpass(take_audio)

    waveform_scores = normalized_valid_cross_correlation(
        raw_filtered,
        take_filtered,
        use_absolute=True,
    )
    waveform_delay, waveform_peak, waveform_margin = select_peak(
        waveform_scores,
        1.0 / TARGET_SR,
    )

    raw_rms, hop_length = rms_envelope(raw_filtered)
    take_rms, _ = rms_envelope(take_filtered)
    envelope_scores = normalized_valid_cross_correlation(
        raw_rms,
        take_rms,
        use_absolute=False,
    )
    envelope_delay, envelope_peak, envelope_margin = select_peak(
        envelope_scores,
        hop_length / TARGET_SR,
    )

    waveform_ok = (
        waveform_peak >= MIN_WAVEFORM_CORRELATION
        and (not np.isfinite(waveform_margin) or waveform_margin >= MIN_PEAK_MARGIN)
    )
    envelope_ok = (
        envelope_peak >= MIN_ENVELOPE_CORRELATION
        and (not np.isfinite(envelope_margin) or envelope_margin >= MIN_PEAK_MARGIN)
    )
    disagreement = abs(waveform_delay - envelope_delay)

    # Envelope là kết quả chính vì playback qua loa/micro làm đổi pha waveform.
    if envelope_ok:
        delay = envelope_delay
        method = "rms_envelope_xcorr"
        reliable = (not waveform_ok) or disagreement <= MAX_METHOD_DISAGREEMENT_SECONDS
        note = ""
        if waveform_ok and not reliable:
            note = "Waveform và RMS envelope không đồng thuận"
    elif waveform_ok:
        delay = waveform_delay
        method = "waveform_xcorr_fallback"
        reliable = True
        note = "RMS envelope yếu; dùng waveform fallback"
    else:
        delay = envelope_delay
        method = "rms_envelope_xcorr_low_confidence"
        reliable = False
        note = "Correlation/peak margin thấp"

    return {
        "waveform_delay": waveform_delay,
        "waveform_peak": waveform_peak,
        "waveform_margin": waveform_margin,
        "envelope_delay": envelope_delay,
        "envelope_peak": envelope_peak,
        "envelope_margin": envelope_margin,
        "disagreement": disagreement,
        "delay": delay,
        "method": method,
        "reliable": reliable,
        "note": note,
    }


def source_path_from_manifest(row):
    relative = Path(row["source_relative_path"].replace("\\", "/"))
    return DATASET_SOURCE_ROOT / relative


def analyze_take(source_row, take_id, take_file):
    raw_path = source_path_from_manifest(source_row)
    playback_path = PLAYBACK_ROOT / take_file

    base = {
        "split": source_row["split"].lower(),
        "source_id": source_row["source_id"],
        "group_id": source_row.get("group_id", ""),
        "source_file": raw_path.name,
        "take_id": take_id,
        "playback_file": take_file,
    }

    try:
        if not raw_path.is_file():
            raise FileNotFoundError(f"Thiếu raw source: {raw_path}")
        if not playback_path.is_file():
            raise FileNotFoundError(f"Thiếu playback: {playback_path}")

        raw_audio = load_audio(raw_path)
        take_audio = load_audio(playback_path)
        result = estimate_delay(raw_audio, take_audio)

        return {
            **base,
            "raw_duration_seconds": round_value(raw_audio.size / TARGET_SR),
            "take_duration_seconds": round_value(take_audio.size / TARGET_SR),
            "waveform_delay_seconds": round_value(result["waveform_delay"]),
            "waveform_peak_correlation": round_value(result["waveform_peak"]),
            "waveform_peak_margin": round_value(result["waveform_margin"]),
            "envelope_delay_seconds": round_value(result["envelope_delay"]),
            "envelope_peak_correlation": round_value(result["envelope_peak"]),
            "envelope_peak_margin": round_value(result["envelope_margin"]),
            "method_disagreement_seconds": round_value(result["disagreement"]),
            "delay_seconds": round_value(result["delay"]),
            "delay_method": result["method"],
            "reliable": int(result["reliable"]),
            "status": "OK",
            "note": result["note"],
        }
    except Exception as error:
        return {
            **base,
            "raw_duration_seconds": "",
            "take_duration_seconds": "",
            "waveform_delay_seconds": "",
            "waveform_peak_correlation": "",
            "waveform_peak_margin": "",
            "envelope_delay_seconds": "",
            "envelope_peak_correlation": "",
            "envelope_peak_margin": "",
            "method_disagreement_seconds": "",
            "delay_seconds": "",
            "delay_method": "",
            "reliable": 0,
            "status": "ERROR",
            "note": str(error),
        }


def build_pair_rows(detail_rows):
    grouped = {}
    for row in detail_rows:
        key = (row["split"], row["source_id"])
        grouped.setdefault(key, {})[row["take_id"]] = row

    pair_rows = []
    for (_, _), takes in sorted(grouped.items()):
        take01 = takes.get("take01")
        take02 = takes.get("take02")
        if not take01 or not take02:
            continue

        both_reliable = bool(int(take01["reliable"])) and bool(int(take02["reliable"]))
        difference = ""
        if take01["delay_seconds"] != "" and take02["delay_seconds"] != "":
            difference = round_value(
                abs(float(take01["delay_seconds"]) - float(take02["delay_seconds"]))
            )

        pair_rows.append(
            {
                "split": take01["split"],
                "source_id": take01["source_id"],
                "group_id": take01["group_id"],
                "source_file": take01["source_file"],
                "take01_delay_seconds": take01["delay_seconds"],
                "take02_delay_seconds": take02["delay_seconds"],
                "absolute_difference_seconds": difference,
                "both_reliable": int(both_reliable),
            }
        )
    return pair_rows


def percentile(values, q):
    return float(np.percentile(np.asarray(values, dtype=np.float64), q))


def summarize_rows(detail_rows, split_name):
    selected = (
        detail_rows
        if split_name == "train_val"
        else [row for row in detail_rows if row["split"] == split_name]
    )
    valid = [row for row in selected if row["status"] == "OK"]
    reliable = [row for row in valid if int(row["reliable"]) == 1]
    delays = [float(row["delay_seconds"]) for row in reliable]

    summary = {
        "split": split_name,
        "total_takes": len(selected),
        "valid_takes": len(valid),
        "reliable_takes": len(reliable),
        "reliable_rate": round_value(len(reliable) / len(valid) if valid else 0.0),
        "mean_delay_seconds": "",
        "median_delay_seconds": "",
        "std_delay_seconds": "",
        "min_delay_seconds": "",
        "p10_delay_seconds": "",
        "p90_delay_seconds": "",
        "max_delay_seconds": "",
        "p90_minus_p10_seconds": "",
    }
    if delays:
        p10 = percentile(delays, 10)
        p90 = percentile(delays, 90)
        summary.update(
            {
                "mean_delay_seconds": round_value(np.mean(delays)),
                "median_delay_seconds": round_value(np.median(delays)),
                "std_delay_seconds": round_value(np.std(delays)),
                "min_delay_seconds": round_value(np.min(delays)),
                "p10_delay_seconds": round_value(p10),
                "p90_delay_seconds": round_value(p90),
                "max_delay_seconds": round_value(np.max(delays)),
                "p90_minus_p10_seconds": round_value(p90 - p10),
            }
        )
    return summary


def numeric(summary, key):
    value = summary.get(key, "")
    return float(value) if value != "" else math.nan


def make_decision(summary_rows, pair_rows):
    summaries = {row["split"]: row for row in summary_rows}
    overall = summaries["train_val"]
    train = summaries["train"]
    val = summaries["val"]

    pair_differences = [
        float(row["absolute_difference_seconds"])
        for row in pair_rows
        if int(row["both_reliable"]) == 1
        and row["absolute_difference_seconds"] != ""
    ]
    pair_median = float(np.median(pair_differences)) if pair_differences else math.nan

    train_val_median_diff = math.nan
    if np.isfinite(numeric(train, "median_delay_seconds")) and np.isfinite(
        numeric(val, "median_delay_seconds")
    ):
        train_val_median_diff = abs(
            numeric(train, "median_delay_seconds")
            - numeric(val, "median_delay_seconds")
        )

    checks = {
        "reliable_rate": numeric(overall, "reliable_rate") >= MIN_RELIABLE_RATE,
        "std": numeric(overall, "std_delay_seconds") <= FIXED_MAX_STD_SECONDS,
        "p90_p10": (
            numeric(overall, "p90_minus_p10_seconds")
            <= FIXED_MAX_P90_P10_SECONDS
        ),
        "take_pair": (
            np.isfinite(pair_median)
            and pair_median <= FIXED_MAX_PAIR_MEDIAN_DIFF_SECONDS
        ),
        "train_val": (
            np.isfinite(train_val_median_diff)
            and train_val_median_diff <= FIXED_MAX_TRAIN_VAL_MEDIAN_DIFF_SECONDS
        ),
    }

    median_delay = numeric(overall, "median_delay_seconds")
    fixed_offset = math.nan
    if np.isfinite(median_delay):
        fixed_offset = (
            round(median_delay / FIXED_OFFSET_STEP_SECONDS)
            * FIXED_OFFSET_STEP_SECONDS
        )

    use_fixed = all(checks.values())
    return {
        "decision": "FIXED_OFFSET" if use_fixed else "PER_FILE_ALIGNMENT",
        "fixed_offset": fixed_offset,
        "pair_median_diff": pair_median,
        "train_val_median_diff": train_val_median_diff,
        "checks": checks,
    }


def bool_mark(value):
    return "Đạt" if value else "Không đạt"


def write_report(summary_rows, pair_rows, decision, error_rows):
    summaries = {row["split"]: row for row in summary_rows}
    lines = [
        "# Báo cáo cross-correlation delay của Asthma playback",
        "",
        "## Phạm vi",
        "",
        "- Chỉ phân tích `Train + Validation`; Test được giữ kín.",
        "- Mỗi raw source được so với `take01` và `take02`.",
        "- Không train model, không sửa WAV.",
        "- `delay_seconds` ưu tiên normalized cross-correlation của RMS envelope; "
        "waveform correlation được dùng để đối chiếu/fallback.",
        "",
        "## Thống kê delay đáng tin cậy",
        "",
        "| Split | Tổng take | Reliable | Tỉ lệ | Median (s) | Std (s) | P10–P90 (s) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for split_name in ("train", "val", "train_val"):
        row = summaries[split_name]
        p10_p90 = "N/A"
        if row["p10_delay_seconds"] != "" and row["p90_delay_seconds"] != "":
            p10_p90 = f'{row["p10_delay_seconds"]}–{row["p90_delay_seconds"]}'
        lines.append(
            f'| {split_name} | {row["total_takes"]} | {row["reliable_takes"]} | '
            f'{row["reliable_rate"]} | {row["median_delay_seconds"] or "N/A"} | '
            f'{row["std_delay_seconds"] or "N/A"} | {p10_p90} |'
        )

    lines.extend(
        [
            "",
            "## Kiểm tra điều kiện fixed offset",
            "",
            f'- Reliable rate ≥ {MIN_RELIABLE_RATE:.2f}: '
            f'**{bool_mark(decision["checks"]["reliable_rate"])}**',
            f'- Std ≤ {FIXED_MAX_STD_SECONDS:.2f} s: '
            f'**{bool_mark(decision["checks"]["std"])}**',
            f'- P90 − P10 ≤ {FIXED_MAX_P90_P10_SECONDS:.2f} s: '
            f'**{bool_mark(decision["checks"]["p90_p10"])}**',
            f'- Median |take01 − take02| = '
            f'{round_value(decision["pair_median_diff"])} s, giới hạn '
            f'{FIXED_MAX_PAIR_MEDIAN_DIFF_SECONDS:.2f} s: '
            f'**{bool_mark(decision["checks"]["take_pair"])}**',
            f'- |Median Train − Median Val| = '
            f'{round_value(decision["train_val_median_diff"])} s, giới hạn '
            f'{FIXED_MAX_TRAIN_VAL_MEDIAN_DIFF_SECONDS:.2f} s: '
            f'**{bool_mark(decision["checks"]["train_val"])}**',
            "",
            "## Kết luận tự động",
            "",
        ]
    )

    if decision["decision"] == "FIXED_OFFSET":
        lines.extend(
            [
                "**Delay đủ ổn định: có thể dùng fixed offset.**",
                "",
                f'- Offset đề xuất (làm tròn theo bước {FIXED_OFFSET_STEP_SECONDS:.2f} s): '
                f'`{round_value(decision["fixed_offset"])} s`.',
                "- Trước khi rebuild dataset, vẫn cần xem các dòng `reliable = 0` và "
                "các outlier trong CSV chi tiết.",
            ]
        )
    else:
        lines.extend(
            [
                "**Delay chưa đủ ổn định: nên căn riêng từng playback theo delay.**",
                "",
                "- Không hard-code một offset chung chỉ dựa trên giá trị trung bình.",
                "- Khi rebuild, lưu delay/alignment của từng file vào manifest để tái lập.",
            ]
        )

    lines.extend(
        [
            "",
            "## File đầu ra",
            "",
            f'- `{DETAIL_CSV.name}`: delay và confidence của từng take.',
            f'- `{PAIR_CSV.name}`: độ lệch giữa take01 và take02 cùng source.',
            f'- `{SUMMARY_CSV.name}`: thống kê Train/Val/Train+Val.',
        ]
    )
    if error_rows:
        lines.extend(
            [
                "",
                "## Cảnh báo",
                "",
                f'- Có `{len(error_rows)}` take lỗi đọc/phân tích. Xem cột `note` trong CSV.',
            ]
        )

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    source_rows = read_csv_clean(SOURCE_LIST_PATH)
    selected = [
        row
        for row in source_rows
        if row.get("label", "").lower() == "asthma"
        and row.get("split", "").lower() in ANALYSIS_SPLITS
    ]
    if not selected:
        raise RuntimeError("Manifest không có Asthma source thuộc Train/Validation")

    detail_rows = []
    total_takes = len(selected) * 2
    print(f"Phân tích {len(selected)} source / {total_takes} take Asthma Train+Val...")

    for index, source_row in enumerate(selected, start=1):
        print(
            f'[{index:02d}/{len(selected):02d}] '
            f'{source_row["source_id"]} ({source_row["split"]})'
        )
        for take_id, column in (("take01", "take_01_file"), ("take02", "take_02_file")):
            take_file = source_row.get(column, "")
            if not take_file:
                detail_rows.append(
                    {
                        "split": source_row["split"].lower(),
                        "source_id": source_row["source_id"],
                        "group_id": source_row.get("group_id", ""),
                        "source_file": Path(source_row["source_relative_path"]).name,
                        "take_id": take_id,
                        "playback_file": "",
                        **{column_name: "" for column_name in DETAIL_COLUMNS[6:17]},
                        "reliable": 0,
                        "status": "ERROR",
                        "note": f"Manifest thiếu {column}",
                    }
                )
                continue
            detail_rows.append(analyze_take(source_row, take_id, take_file))

    pair_rows = build_pair_rows(detail_rows)
    summary_rows = [
        summarize_rows(detail_rows, "train"),
        summarize_rows(detail_rows, "val"),
        summarize_rows(detail_rows, "train_val"),
    ]
    decision = make_decision(summary_rows, pair_rows)
    error_rows = [row for row in detail_rows if row["status"] != "OK"]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(DETAIL_CSV, detail_rows, DETAIL_COLUMNS)
    write_csv(PAIR_CSV, pair_rows, PAIR_COLUMNS)
    write_csv(SUMMARY_CSV, summary_rows, SUMMARY_COLUMNS)
    write_report(summary_rows, pair_rows, decision, error_rows)

    print("\n========== KẾT QUẢ ==========")
    print(f"Quyết định: {decision['decision']}")
    if np.isfinite(decision["fixed_offset"]):
        print(f"Fixed offset tham khảo: {decision['fixed_offset']:.2f} s")
    print(f"Lỗi đọc/phân tích: {len(error_rows)}")
    print(f"Báo cáo: {REPORT_MD}")
    print("=============================")


if __name__ == "__main__":
    main()
