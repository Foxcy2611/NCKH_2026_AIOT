"""
Kiểm tra cơ sở lựa chọn Butterworth 100-2000 Hz cho Frontend NCKH.

Mục đích:
- Phân tích chỉ WAV Core thuộc tập TRAIN, tách hai nhãn Asthma / Non-Asthma.
- Kiểm tra PSD trước lọc, chia nhỏ 0–2000 Hz và so sánh các dải ứng viên.
- So sánh tác động lọc trên cùng một WAV và đáp ứng Butterworth bậc 3/5/7.
- Phân tầng theo sample rate GỐC để nhận diện nguy cơ lệch miền dữ liệu.
- Nêu cơ sở tham khảo từ nghiên cứu về wheeze (KHÔNG coi là tối ưu trên dữ liệu hiện tại).

KHÔNG:
- Sử dụng Validation/Test để chọn tham số.
- Huấn luyện/suy luận, kết luận băng thông tối ưu cho Accuracy.
- Đánh đồng phổ do resample từ 4 kHz với phổ gốc có thông tin >2 kHz.

Yêu cầu: numpy, scipy, soundfile, matplotlib và frontend_core.py của dự án.
Chạy:
    python 00b_Bandpass_Frontend_Evidence.py
    python 00b_Bandpass_Frontend_Evidence.py --dataset-root "D:/.../dataset" --raw-per-class 12
    python 00b_Bandpass_Frontend_Evidence.py --all-raw
    python 00b_Bandpass_Frontend_Evidence.py --all-raw --filter-mode causal

Đầu ra:
    results/A_scientific_frontend_evidence/bandpass_justification/figures/
    results/A_scientific_frontend_evidence/bandpass_justification/tables/
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import warnings
from collections import defaultdict
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[2]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfreqz, sosfilt, sosfiltfilt, welch

from frontend_core import RESULTS, SR, dataset_root, list_split, load_raw_window

DEFAULT_DATASET_ROOT = PROJECT_ROOT / "AI_Training_Model" / "Dataset_Chia_V2"
DEFAULT_OUTPUT_DIR = (
    RESULTS
    / "A_scientific_frontend_evidence"
    / "bandpass_justification"
)

# Các miền nhỏ chỉ để diễn giải phổ, không phải tham số mới của mô hình.
SUBBANDS = [(0, 50), (50, 100), (100, 200), (200, 400), (400, 800),
            (800, 1200), (1200, 1600), (1600, 2000)]
# 150–2000 Hz là dải dùng trong Pramono et al. (2019), KHÔNG phải 100–2000 Hz.
CANDIDATE_BANDS = [(50, 2000), (80, 2000), (100, 1500), (100, 2000),
                   (150, 2000), (100, 3000)]
DEFAULT_BANDS = sorted(set(SUBBANDS + CANDIDATE_BANDS + [(0, 100), (100, 4000)]))

REFERENCES = [
    {"title": "Evaluation of features for classification of wheezes and normal respiratory sounds",
     "authors": "Pramono, Imtiaz & Rodriguez-Villegas", "year": 2019,
     "doi": "10.1371/journal.pone.0213659",
     "url": "https://doi.org/10.1371/journal.pone.0213659",
     "supported_point": "Dùng Butterworth bậc 5, band-pass 150–2000 Hz cho phân loại wheeze."},
    {"title": "Analysis of Respiratory Sounds: State of the Art",
     "authors": "Reichert et al.", "year": 2008,
     "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC2990233/",
     "supported_point": "Wheeze được mô tả trong khoảng ~100–2500 Hz; tần số cơ bản thường từ vài trăm đến trên 1000 Hz; tùy nguồn."},
]


def resolve_dataset_path(argument: Path | None) -> Path:
    """Giải dataset độc lập với thư mục PowerShell đang đứng."""
    if argument is None:
        candidate = DEFAULT_DATASET_ROOT
    else:
        candidate = argument.expanduser()
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate
    candidate = candidate.resolve()
    if not candidate.is_dir():
        raise FileNotFoundError(f"Không tìm thấy dataset: {candidate}")
    return candidate


def resolve_output_path(argument: Path | None) -> Path:
    """Đặt output tương đối dưới Frontend_Benchmarking, không phụ thuộc CWD."""
    if argument is None:
        return DEFAULT_OUTPUT_DIR.resolve()
    candidate = argument.expanduser()
    if not candidate.is_absolute():
        candidate = SCRIPT_DIR / candidate
    return candidate.resolve()


def is_raw_core(path: Path) -> bool:
    """Loại augmentation / environment / playback, giữ nguyên WAV Core."""
    name = path.stem.casefold()
    return (not name.startswith(("augv2__", "env__"))
            and not name.endswith(("__take01", "__take02")))


def raw_non_asthma_group(path: Path) -> str:
    stem = path.stem.casefold()
    for keyword in ("bronchial", "copd", "healthy", "pneumonia"):
        if keyword in stem:
            return keyword
    return "other"


def sample_train_raw(root: Path, per_class: int, all_raw: bool, seed: int):
    """Cố định seed, phân tầng Non-Asthma để tránh tập con chỉ toàn COPD."""
    pools: dict[int, list[Path]] = {0: [], 1: []}
    for path, label in list_split(root, "train"):
        path = Path(path)
        if label in (0, 1) and is_raw_core(path):
            pools[label].append(path)
    rng = np.random.default_rng(seed)
    if not pools[0] or not pools[1]:
        raise RuntimeError("Không tìm thấy WAV Core của cả hai nhãn trong TRAIN.")

    if all_raw:
        return sorted(pools[0]), sorted(pools[1])

    n = min(per_class, len(pools[0]), len(pools[1]))
    ast = rng.choice(len(pools[0]), n, replace=False)
    asthma = [pools[0][i] for i in ast]

    groups: dict[str, list[Path]] = defaultdict(list)
    for path in pools[1]:
        groups[raw_non_asthma_group(path)].append(path)
    for group in groups.values():
        rng.shuffle(group)
    non = []
    keys = sorted(groups)
    while len(non) < n:
        changed = False
        for key in keys:
            if groups[key] and len(non) < n:
                non.append(groups[key].pop())
                changed = True
        if not changed:
            break
    return asthma, non


def write_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.DictWriter(fp, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def psd_integral(freq: np.ndarray, power: np.ndarray, lo: float, hi: float):
    mask = (freq >= lo) & (freq <= hi)
    if mask.sum() < 2:
        return 0.0
    return float(np.trapezoid(power[mask], freq[mask]))


def safe_stats(values):
    arr = np.asarray([v for v in values if np.isfinite(v)], dtype=float)
    if arr.size == 0:
        return {"n": 0, "median": None, "q25": None, "q75": None}
    return {
        "n": int(arr.size),
        "median": round(float(np.median(arr)), 3),
        "q25": round(float(np.quantile(arr, 0.25)), 3),
        "q75": round(float(np.quantile(arr, 0.75)), 3),
    }


def native_fs_group(sr: int) -> str:
    # Tần số 4000 Hz là Nyquist của đầu vào 8000 Hz, không phải dải dư.
    return "source ≤4 kHz" if sr <= 4000 else "source >4 kHz"


def bandpass(x: np.ndarray, lo: float, hi: float, order: int,
             filter_mode: str = "zero_phase"):
    """SOS ổn định số học; zero_phase chỉ là minh họa nếu pipeline dùng causal."""
    sos = butter(order, [lo, hi], btype="bandpass", fs=SR, output="sos")
    if filter_mode == "zero_phase":
        return sosfiltfilt(sos, x)
    if filter_mode == "causal":
        return sosfilt(sos, x)
    raise ValueError("filter_mode phải là zero_phase hoặc causal")


def analyse_wavs(root: Path, asthma: list[Path], non_asthma: list[Path],
                 bands: list[tuple[int, int]], order: int):
    """Chỉ sử dụng phổ RAW; phần > Nyquist gốc được đánh dấu thiếu, không gán 0."""
    rows, spectra, examples = [], {0: [], 1: []}, {}
    freq_ref = None
    selected = [(p, 0) for p in asthma] + [(p, 1) for p in non_asthma]
    for idx, (path, label) in enumerate(selected, start=1):
        info = sf.info(str(path))
        native_sr = int(info.samplerate)
        native_nyquist = native_sr / 2.0

        # Hàm này thuộc frontend_core của dự án: xử lý mono/resample/cửa sổ 5 s.
        raw = np.asarray(load_raw_window(path), dtype=np.float64).ravel()
        if raw.size == 0 or not np.all(np.isfinite(raw)):
            warnings.warn(f"Bỏ qua WAV rỗng/lỗi: {path}")
            continue

        peak = max(float(np.max(np.abs(raw))), 1e-10)
        x = raw / peak
        nperseg = min(2048, len(x))
        f, pxx = welch(x, fs=SR, window="hann", nperseg=nperseg,
                       noverlap=nperseg // 2, scaling="density")
        freq_ref = f
        original_valid = (f <= min(native_nyquist, SR / 2))
        total = psd_integral(f, pxx, 0, min(native_nyquist, SR / 2))
        total = max(total, 1e-30)

        display_psd = pxx.copy()
        display_psd[~original_valid] = np.nan
        spectra[label].append(display_psd)
        examples.setdefault(label, (path, x, f, pxx))
        for lo, hi in bands:
            supported = hi <= native_nyquist and hi <= SR / 2
            # Không công bố năng lượng của dải vượt giới hạn nguồn WAV.
            portion = (100 * psd_integral(f, pxx, lo, hi) / total
                       if supported else float("nan"))
            rows.append({
                "wav": str(path.relative_to(root)),
                "label": "Asthma" if label == 0 else "Non-Asthma",
                "source_group": native_fs_group(native_sr),
                "native_sr_hz": native_sr,
                "native_nyquist_hz": native_nyquist,
                "band_hz": f"{lo}-{hi}",
                "native_band_supported": supported,
                "energy_pct_native_available": round(portion, 5)
                if np.isfinite(portion) else "",
            })
        if idx % 50 == 0:
            print(f"Đã xử lý {idx}/{len(selected)} WAV")
    return rows, spectra, freq_ref, examples


def plot_psd(spectra, freq, output: Path, lo: int, hi: int):
    fig, ax = plt.subplots(figsize=(11, 5))
    for label, title in ((0, "Asthma RAW"), (1, "Non-Asthma RAW")):
        if not spectra[label]:
            continue
        psds = np.asarray(spectra[label], dtype=float)
        valid = np.sum(np.isfinite(psds), axis=0)
        enough = valid >= 3
        # Tránh cảnh báo do miền tần số không có mẫu hợp lệ.
        middle = np.full(len(freq), np.nan)
        lower = middle.copy()
        upper = middle.copy()
        for j in np.flatnonzero(enough):
            v = psds[:, j]
            v = v[np.isfinite(v)]
            middle[j] = np.median(v)
            lower[j], upper[j] = np.quantile(v, [0.25, 0.75])
        line, = ax.plot(freq, 10 * np.log10(middle + 1e-15),
                        label=f"{title} n={len(psds)}")
        ax.fill_between(freq, 10 * np.log10(lower + 1e-15),
                        10 * np.log10(upper + 1e-15),
                        color=line.get_color(), alpha=0.15)
    ax.axvspan(lo, hi, color="grey", alpha=0.13,
               label=f"Dải khảo sát {lo}–{hi} Hz")
    ax.axvline(2000, ls="--", lw=1, color="grey", alpha=0.8)
    ax.set(xlim=(0, 4000), xlabel="Tần số (Hz)",
           ylabel="Welch PSD (dB tương đối)",
           title="Phổ WAV Core TRAIN trước lọc — trung vị và IQR")
    ax.grid(alpha=0.2)
    ax.legend(loc="best")
    fig.text(0.5, 0.01,
             "Không hiển thị thành phần trên Nyquist của WAV gốc; n có thể giảm ở tần số cao.",
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_energy_by_fs(rows, output: Path, target_band: str):
    fig, ax = plt.subplots(figsize=(9, 5))
    rng = np.random.default_rng(123)
    combinations = [
        ("Asthma", "source ≤4 kHz"),
        ("Asthma", "source >4 kHz"),
        ("Non-Asthma", "source ≤4 kHz"),
        ("Non-Asthma", "source >4 kHz"),
    ]
    for i, (lab, group) in enumerate(combinations):
        vals = np.array([
            float(r["energy_pct_native_available"])
            for r in rows if r["label"] == lab and r["source_group"] == group
            and r["band_hz"] == target_band and r["native_band_supported"]
        ], dtype=float)
        if len(vals):
            ax.scatter(i + rng.uniform(-.12, .12, len(vals)), vals, s=22,
                       alpha=.55)
            ax.plot([i - .23, i + .23],
                    [np.median(vals)] * 2, color="black", lw=2)
        ax.text(i, 103, f"n={len(vals)}", ha="center", fontsize=9)
    ax.set_xticks(range(4))
    ax.set_xticklabels(["Asthma\n≤4 kHz", "Asthma\n>4 kHz",
                        "Non-Asthma\n≤4 kHz", "Non-Asthma\n>4 kHz"])
    ax.set(ylim=(-5, 109), ylabel="Tỷ lệ năng lượng PSD (%)",
           title=f"Năng lượng trong dải {target_band} Hz theo nhãn và sample rate gốc")
    ax.grid(axis="y", alpha=.2)
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_example(example, out: Path, lo: int, hi: int, order: int,
                 filter_mode: str):
    path, x, _, _ = example
    y = bandpass(x, lo, hi, order, filter_mode)
    before = float(np.sqrt(np.mean(x * x)))
    after = float(np.sqrt(np.mean(y * y)))
    tb = np.arange(len(x)) / SR
    f1, p1 = welch(x, fs=SR, nperseg=2048, noverlap=1024)
    f2, p2 = welch(y, fs=SR, nperseg=2048, noverlap=1024)

    fig, axs = plt.subplots(3, 1, figsize=(11, 9))
    axs[0].plot(tb, x, lw=.65)
    axs[0].set(title=f"WAV trước lọc — RMS={before:.5f}", ylabel="Biên độ")
    axs[1].plot(tb, y, lw=.65)
    axs[1].set(title=f"Sau Butterworth {lo}–{hi} Hz — RMS={after:.5f}",
               ylabel="Biên độ")
    # Sử dụng cùng giới hạn biên độ để không che giấu suy giảm RMS.
    yscale = max(float(np.max(np.abs(x))), float(np.max(np.abs(y))), 1e-6)
    axs[0].set_ylim(-yscale, yscale)
    axs[1].set_ylim(-yscale, yscale)
    axs[2].plot(f1, 10 * np.log10(p1 + 1e-15), label="Trước lọc")
    axs[2].plot(f2, 10 * np.log10(p2 + 1e-15), label="Sau lọc")
    axs[2].axvspan(lo, hi, alpha=.12, color="grey")
    axs[2].set(xlim=(0, 4000), xlabel="Tần số (Hz)", ylabel="Welch PSD (dB)",
               title="Phổ trước và sau lọc trên cùng WAV")
    axs[2].legend()
    for ax in axs:
        ax.grid(alpha=.2)
    fig.suptitle(f"{path.name} | {filter_mode} | RMS sau/trước = "
                 f"{100 * after/max(before, 1e-12):.2f}%", fontsize=12)
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return {"example_wav": str(path), "filter_mode": filter_mode,
            "rms_before": before, "rms_after": after,
            "rms_after_over_before_pct": round(100 * after/max(before, 1e-12), 4)}


def plot_filter_orders(out: Path, lo: int, hi: int, filter_mode: str):
    """Vẽ đúng biên độ hiệu dụng: |H| khi causal, |H|^2 khi filtfilt."""
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for order in (3, 5, 7):
        sos = butter(order, [lo, hi], btype="bandpass", fs=SR, output="sos")
        f, h = sosfreqz(sos, worN=8192, fs=SR)
        mag = np.abs(h)
        if filter_mode == "zero_phase":
            mag = mag ** 2
        ax.plot(f, 20 * np.log10(np.maximum(mag, 1e-10)),
                label=f"Bậc {order}")
    ax.axvline(lo, ls="--", color="grey")
    ax.axvline(hi, ls="--", color="grey")
    ax.set(xlim=(0, 4000), ylim=(-100, 5), xlabel="Tần số (Hz)",
           ylabel="Biên độ đáp ứng hiệu dụng (dB)",
           title=f"Butterworth {lo}–{hi} Hz, bậc 3/5/7 — {filter_mode}")
    ax.grid(alpha=.2)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def subband_profile(rows: list[dict], output_csv: Path, output_fig: Path):
    """Tỷ lệ năng lượng *bên trong* 100–2000 Hz, tách theo sample rate nguồn.

    Đây là phổ của WAV mang nhãn, không chứng minh đoạn đó thực sự chứa wheeze.
    """
    by_file: dict[str, dict[str, dict]] = defaultdict(dict)
    for r in rows:
        by_file[r["wav"]][r["band_hz"]] = r
    subbands = [(a, b) for a, b in SUBBANDS if a >= 100]
    groups = ("source ≤4 kHz", "source >4 kHz")
    fractions: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list))
    for file_rows in by_file.values():
        ref = file_rows.get("100-2000")
        if ref is None or not ref["native_band_supported"]:
            continue
        # Không chia cho số rất nhỏ / năng lượng bị làm tròn về 0.
        denominator = float(ref["energy_pct_native_available"] or 0)
        if denominator <= 1e-8:
            continue
        for low, high in subbands:
            key = f"{low}-{high}"
            r = file_rows[key]
            if r["native_band_supported"]:
                share = 100 * float(r["energy_pct_native_available"]) / denominator
                fractions[(r["label"], r["source_group"])][key].append(share)
    results = []
    for group in groups:
        for label in ("Asthma", "Non-Asthma"):
            for low, high in subbands:
                band = f"{low}-{high}"
                results.append({"label": label, "source_group": group,
                                "subband_hz": band,
                                **safe_stats(fractions[(label, group)][band])})
    write_csv(output_csv, results)
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.7), sharey=True)
    labels = [f"{a}–{b}" for a, b in subbands]
    xx = np.arange(len(labels))
    for ax, group in zip(axs, groups):
        for lab, offset, color in (("Asthma", -.17, "#377db8"),
                                   ("Non-Asthma", .17, "#e27921")):
            stats = [safe_stats(fractions[(lab, group)][f"{a}-{b}"])
                     for a, b in subbands]
            ax.bar(xx + offset,
                   [v["median"] if v["median"] is not None else 0 for v in stats],
                   width=.33, color=color, label=f"{lab} (n={stats[0]['n']})")
        ax.set_xticks(xx, labels, rotation=30, ha="right")
        ax.set_title(group)
        ax.grid(axis="y", alpha=.2)
    axs[0].set_ylabel("Trung vị tỷ lệ trong 100–2000 Hz (%)")
    axs[1].legend()
    fig.suptitle("Phân bố phổ trong passband (phân tầng theo sample rate gốc)")
    fig.text(.5, .01, "Phổ trước lọc; nhãn Asthma không chứng minh có tiếng rít ở từng WAV.",
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .04, 1, .96))
    fig.savefig(output_fig, dpi=180)
    plt.close(fig)


def plot_candidate_bands(rows: list[dict], output: Path):
    """Đối chiếu phân bố % năng lượng; không dùng phép so sánh để chọn Accuracy."""
    bands = ["50-2000", "80-2000", "100-1500", "100-2000", "150-2000", "100-3000"]
    # Vẽ riêng nhóm nguồn để không vô tình gộp Nyquist khác nhau.
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.8), sharey=True)
    for ax, group in zip(axs, ("source ≤4 kHz", "source >4 kHz")):
        for lab, offset, color in (("Asthma", -.16, "#377db8"),
                                   ("Non-Asthma", .16, "#e27921")):
            mids, counts = [], []
            for band in bands:
                vals = [float(r["energy_pct_native_available"])
                        for r in rows if r["label"] == lab
                        and r["source_group"] == group
                        and r["band_hz"] == band and r["native_band_supported"]]
                mids.append(float(np.median(vals)) if vals else np.nan)
                counts.append(len(vals))
            ax.scatter(np.arange(len(bands)) + offset, mids, label=lab,
                       s=42, color=color)
            for i, (mid, n) in enumerate(zip(mids, counts)):
                if n and np.isfinite(mid):
                    ax.annotate(f"n={n}", (i + offset, mid),
                                textcoords="offset points", xytext=(0, 5),
                                ha="center", fontsize=7)
        ax.set_xticks(np.arange(len(bands)), bands, rotation=45, ha="right")
        ax.set_title(group)
        ax.grid(axis="y", alpha=.2)
        ax.set_yscale("symlog", linthresh=.1)
    axs[0].set_ylabel("Trung vị % PSD so với băng thông nguồn (thang symlog)")
    axs[1].legend()
    fig.suptitle("Các dải band-pass ứng viên — mô tả phổ, không tối ưu mô hình")
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path,
                        help=(
                            "Thư mục Dataset_Chia_V2; đường dẫn tương đối được "
                            "tính từ root repository."
                        ))
    parser.add_argument("--raw-per-class", type=int, default=12,
                        help="Số WAV Core mỗi nhãn (mặc định 12).")
    parser.add_argument("--all-raw", action="store_true",
                        help="Phân tích toàn bộ WAV Core trong TRAIN.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--low", type=int, default=100)
    parser.add_argument("--high", type=int, default=2000)
    parser.add_argument("--order", type=int, default=5)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--filter-mode", choices=("zero_phase", "causal"),
                        default="zero_phase",
                        help="Mặc định sosfiltfilt (minh họa); causal dùng sosfilt. "
                             "Chỉ tuyên bố parity khi đã kiểm tra pipeline thật.")
    args = parser.parse_args()
    if not (0 < args.low < args.high < SR/2):
        parser.error(f"Cần 0 < low < high < {SR/2} (Nyquist sau resample).")
    if args.raw_per_class < 1:
        parser.error("--raw-per-class phải >= 1.")
    root = dataset_root(resolve_dataset_path(args.dataset_root))
    out = resolve_output_path(args.output_dir)
    fig_dir, table_dir = out / "figures", out / "tables"
    fig_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)

    asthma, nonasthma = sample_train_raw(root, args.raw_per_class,
                                        args.all_raw, args.seed)
    print(f"TRAIN RAW: {len(asthma)} Asthma; {len(nonasthma)} Non-Asthma")
    bands = sorted(set(DEFAULT_BANDS + [(args.low, args.high)]))
    rows, spectra, freq, examples = analyse_wavs(
        root, asthma, nonasthma, bands, args.order)
    write_csv(table_dir / "per_file_band_energy.csv", rows)

    summary = []
    for label in ("Asthma", "Non-Asthma"):
        for group in ("source ≤4 kHz", "source >4 kHz"):
            for lo, hi in bands:
                matched = [r for r in rows
                           if r["label"] == label and r["source_group"] == group
                           and r["band_hz"] == f"{lo}-{hi}"
                           and r["native_band_supported"]]
                stats = safe_stats([float(r["energy_pct_native_available"])
                                    for r in matched])
                summary.append({"label": label, "source_group": group,
                                "band_hz": f"{lo}-{hi}", **stats})
    write_csv(table_dir / "summary_band_energy.csv", summary)
    if freq is not None:
        plot_psd(spectra, freq, fig_dir / "01_psd_raw_median_iqr.png",
                 args.low, args.high)
    plot_energy_by_fs(rows, fig_dir / "02_energy_by_native_sr.png",
                      f"{args.low}-{args.high}")
    plot_filter_orders(fig_dir / "04_butterworth_orders.png", args.low, args.high,
                       args.filter_mode)
    # Phân bố sau khi loại <100 Hz và so sánh băng tần ứng viên có đủ dữ liệu.
    subband_profile(rows, table_dir / "summary_subband_100_2000.csv",
                    fig_dir / "05_subband_profile.png")
    plot_candidate_bands(rows, fig_dir / "06_candidate_bands.png")
    example_info = None
    if 0 in examples:
        example_info = plot_example(examples[0],
                                    fig_dir / "03_example_before_after.png",
                                    args.low, args.high, args.order,
                                    args.filter_mode)

    manifest = {
        "purpose": "DSP spectral evidence; NOT ML performance optimisation",
        "split": "train only", "raw_core_only": True,
        "label_mapping": {"0": "Asthma", "1": "Non-Asthma"},
        "resample_sr": SR, "seed": args.seed, "butterworth_order": args.order,
        "reference_band_hz": [args.low, args.high],
        "filter_mode_for_illustration": args.filter_mode,
        "filter_implementation_note": "sosfiltfilt là lọc tiến-lùi zero-phase, "
                                      "không khẳng định khớp DSP train/firmware; "
                                      "causal dùng sosfilt.",
        "literature_references": REFERENCES,
        "engineering_rationale": [
            "Pramono et al. (2019) dùng bậc 5, 150–2000 Hz cho phát hiện wheeze; "
            "đề tài dùng 100–2000 Hz: thấp hơn 50 Hz để không loại 100–150 Hz.",
            "Wheeze thường chứa thành phần vài trăm đến >1000 Hz, có thể tới "
            "2500 Hz; giới hạn 2000 Hz không bảo đảm giữ toàn bộ wheeze.",
            "Nguồn 4000 Hz chỉ hỗ trợ tới Nyquist 2000 Hz; resample 16000 Hz "
            "không phục hồi thông tin cao hơn giới hạn nguồn.",
            "Mọi đánh giá là mô tả phổ TRAIN, không chứng minh Accuracy tối ưu."],
        "evaluated_bands_hz": bands,
        "native_nyquist_policy": "out-of-band energy=missing, not zero",
        "sample_count": {"Asthma": len(asthma), "Non-Asthma": len(nonasthma)},
        "selected_raw_wavs": {
            "Asthma": [str(p.relative_to(root)) for p in asthma],
            "Non-Asthma": [str(p.relative_to(root)) for p in nonasthma],
        },
        "example_filter_effect": example_info,
        "limitations": [
            "Tỷ lệ năng lượng trong dải không chứng minh accuracy tốt hơn.",
            "Sample rate gốc khác nhau có thể gây confounding giữa hai nhãn.",
            "Dải 100–2000 Hz chưa được tối ưu hóa bằng huấn luyện nhiều băng tần.",
            "Hàm lọc minh họa cần đối chiếu với train/firmware để kiểm tra parity.",
            "WAV label Asthma không đồng nghĩa từng cửa sổ thực sự chứa wheeze.",
            "PSD chứa rất nhiều năng lượng <100 Hz; chưa rõ tỷ lệ là nhiễu hay hô hấp.",
        ],
    }
    with (out / "analysis_manifest.json").open("w", encoding="utf-8") as fp:
        json.dump(manifest, fp, indent=2, ensure_ascii=False)

    print(f"\nĐã lưu: {out}")
    print("- figures/01_psd_raw_median_iqr.png")
    print("- figures/02_energy_by_native_sr.png")
    print("- figures/03_example_before_after.png")
    print("- figures/04_butterworth_orders.png")
    print("- figures/05_subband_profile.png")
    print("- figures/06_candidate_bands.png")
    print("- tables/per_file_band_energy.csv")
    print("- tables/summary_band_energy.csv")
    print("- tables/summary_subband_100_2000.csv")
    print("- analysis_manifest.json")
    print("\nLưu ý: bằng chứng phổ học + tài liệu tham khảo, KHÔNG phải tối ưu hóa Accuracy.")
    print("Lựa chọn 100–2000 Hz gần dải 150–2000 Hz của Pramono 2019, không đồng nhất.")


if __name__ == "__main__":
    main()
