"""Phân tích tín hiệu Front-End trên WAV thuộc tập Train.

Tác dụng:
- Lấy cân bằng 12 Asthma raw và 12 Non-Asthma raw.
- Bổ sung 1 Asthma + 2 Non-Asthma playback và 3 environment để audit miền thu.
- Playback ưu tiên source có raw tương ứng trong 12 mẫu; environment ưu tiên loại khác nhau.
- Phân tích waveform, PSD, STFT, spectral flux và đáp ứng của các khối DSP.
- Minh họa ảnh hưởng của Mel bins, hop length, FFT và dạng đặc trưng.

Đầu vào: WAV Train và các tùy chọn ``--dataset-root``, ``--raw-per-class``,
``--environment-count``, hai quota playback theo nhãn và ``--seed``.
Đầu ra: toàn bộ artifact của mục A nằm trong
``results/A_scientific_frontend_evidence/``; hình nằm tại thư mục con
``figures/`` để không trộn với kết quả benchmark của mục B.
Giới hạn: không train, không inference và không đọc Validation/Test để chọn cấu hình.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
from pathlib import Path

import librosa
import librosa.display
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import butter, freqz, welch

from frontend_core import (
    BASELINE,
    RESULTS,
    SR,
    SAMPLES,
    dataset_root,
    list_split,
    load_raw_window,
    mel_from_wave,
    process_wave,
    write_json,
    write_rows,
    PROTOCOL,
)

A_RESULTS = RESULTS / 'A_scientific_frontend_evidence'
A_FIGURES = A_RESULTS / 'figures'


def save(fig, name):
    A_FIGURES.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(A_FIGURES / name, dpi=170, bbox_inches='tight')
    plt.close(fig)


def is_playback(path: Path) -> bool:
    return path.stem.casefold().endswith(('__take01', '__take02'))


def is_asthma_raw_core(path: Path) -> bool:
    stem = path.stem.casefold()
    return not is_playback(path) and not stem.startswith(('augv2__', 'env__'))


def is_environment(path: Path) -> bool:
    return path.stem.casefold().startswith('env__')


def is_non_asthma_raw_core(path: Path) -> bool:
    stem = path.stem.casefold()
    return not is_playback(path) and not stem.startswith(('augv2__', 'env__'))


def non_asthma_group(path: Path) -> str:
    stem = path.stem.casefold()
    if is_playback(path):
        return 'playback'
    if stem.startswith('env__'):
        parts = stem.split('__')
        environment = parts[1] if len(parts) > 1 else 'unknown'
        return f'environment:{environment}'
    if 'bronchial' in stem:
        return 'raw:bronchial'
    if 'copd' in stem:
        return 'raw:copd'
    if 'healthy' in stem:
        return 'raw:healthy'
    if 'pneumonia' in stem:
        return 'raw:pneumonia'
    return 'raw:other'


def sample_family(sample_group: str) -> str:
    if sample_group.startswith('raw:'):
        return 'raw'
    if sample_group.startswith('playback:'):
        return 'playback'
    if sample_group.startswith('environment:'):
        return 'environment'
    return 'other'


def choose_random(paths, count, rng):
    if count <= 0 or not paths:
        return []
    indexes = sorted(
        rng.choice(len(paths), size=min(count, len(paths)), replace=False)
    )
    return [paths[index] for index in indexes]


def choose_diverse(
    paths,
    count,
    rng,
    preferred_order,
    randomize_group_order=False,
):
    groups = {}
    for path in paths:
        groups.setdefault(non_asthma_group(path), []).append(path)

    shuffled_groups = {}
    for group_name, group_paths in groups.items():
        order = rng.permutation(len(group_paths))
        shuffled_groups[group_name] = [group_paths[index] for index in order]

    group_order = [name for name in preferred_order if name in shuffled_groups]
    group_order.extend(sorted(set(shuffled_groups) - set(group_order)))
    if randomize_group_order:
        rng.shuffle(group_order)

    selected = []
    round_index = 0
    while len(selected) < count:
        added_this_round = False
        for group_name in group_order:
            group_paths = shuffled_groups[group_name]
            if round_index < len(group_paths):
                selected.append((group_paths[round_index], group_name))
                added_this_round = True
                if len(selected) >= count:
                    break
        if not added_this_round:
            break
        round_index += 1
    return selected


def choose_distinct_playback_sources(paths, count, rng):
    """Chọn tối đa một take cho mỗi source playback trước khi lặp source."""
    source_groups = {}
    for path in paths:
        stem = path.stem.casefold()
        source_id = stem.removesuffix('__take01').removesuffix('__take02')
        source_groups.setdefault(source_id, []).append(path)

    source_ids = list(source_groups)
    rng.shuffle(source_ids)
    selected = []
    for source_id in source_ids:
        candidates = source_groups[source_id]
        selected.append(candidates[int(rng.integers(0, len(candidates)))])
        if len(selected) >= count:
            return selected

    # Chỉ xảy ra khi yêu cầu nhiều hơn số source độc lập hiện có.
    remaining = [path for path in paths if path not in selected]
    selected.extend(choose_random(remaining, count - len(selected), rng))
    return selected


def playback_raw_key(path: Path) -> str:
    """Trả về stem raw được mã hóa trong tên ``PREFIX__RAW__takeXX``."""
    parts = path.stem.casefold().split('__')
    if is_playback(path) and len(parts) >= 3:
        return parts[-2]
    return path.stem.casefold()


def choose_paired_playback_sources(playback_paths, raw_paths, count, rng):
    """Ưu tiên playback có raw tương ứng và chỉ lấy một take trên mỗi source."""
    raw_by_key = {path.stem.casefold(): path for path in raw_paths}
    playback_by_key = {}
    for path in playback_paths:
        playback_by_key.setdefault(playback_raw_key(path), []).append(path)

    paired_keys = [key for key in playback_by_key if key in raw_by_key]
    rng.shuffle(paired_keys)
    selected_playback = []
    paired_raw = []
    for key in paired_keys[:count]:
        takes = playback_by_key[key]
        selected_playback.append(takes[int(rng.integers(0, len(takes)))])
        paired_raw.append(raw_by_key[key])

    if len(selected_playback) < count:
        remaining = [
            path
            for path in playback_paths
            if playback_raw_key(path)
            not in {playback_raw_key(item) for item in selected_playback}
        ]
        selected_playback.extend(
            choose_distinct_playback_sources(
                remaining,
                count - len(selected_playback),
                rng,
            )
        )
    return selected_playback, paired_raw


def with_required_raw_random(raw_paths, required_paths, count, rng):
    """Giữ raw ghép cặp bắt buộc rồi bốc ngẫu nhiên phần quota còn lại."""
    required = list(dict.fromkeys(required_paths))
    if len(required) > count:
        raise ValueError('Playback pairing requires more raw files than raw quota')
    remaining = [path for path in raw_paths if path not in required]
    return required + choose_random(remaining, count - len(required), rng)


def with_required_raw_diverse(
    raw_paths,
    required_paths,
    count,
    rng,
    preferred_order,
):
    """Giữ raw ghép cặp rồi phân tầng phần Non-Asthma raw còn lại."""
    required = list(dict.fromkeys(required_paths))
    if len(required) > count:
        raise ValueError('Playback pairing requires more raw files than raw quota')
    selected = [
        (path, non_asthma_group(path))
        for path in required
    ]

    remaining_groups = {}
    for path in raw_paths:
        if path not in required:
            remaining_groups.setdefault(non_asthma_group(path), []).append(path)
    for group_paths in remaining_groups.values():
        rng.shuffle(group_paths)

    group_order = [name for name in preferred_order if name in remaining_groups]
    group_order.extend(sorted(set(remaining_groups) - set(group_order)))
    group_counts = Counter(group_name for _, group_name in selected)

    while len(selected) < count:
        available = [
            name for name in group_order if remaining_groups.get(name)
        ]
        if not available:
            break
        minimum_count = min(group_counts.get(name, 0) for name in available)
        next_group = next(
            name
            for name in available
            if group_counts.get(name, 0) == minimum_count
        )
        selected.append((remaining_groups[next_group].pop(), next_group))
        group_counts[next_group] += 1
    return selected


def select_analysis_files(
    root,
    raw_per_class,
    environment_count,
    asthma_playback_count,
    non_asthma_playback_count,
    seed,
):
    rng = np.random.default_rng(seed)
    per_class = {0: [], 1: []}
    for path, label in list_split(root, 'train'):
        per_class[label].append(path)

    asthma_raw = [path for path in per_class[0] if is_asthma_raw_core(path)]
    asthma_playback = [path for path in per_class[0] if is_playback(path)]
    non_asthma_raw = [
        path for path in per_class[1] if is_non_asthma_raw_core(path)
    ]
    non_asthma_playback = [path for path in per_class[1] if is_playback(path)]
    environment = [path for path in per_class[1] if is_environment(path)]

    selected_asthma_playback, paired_asthma_raw = (
        choose_paired_playback_sources(
            asthma_playback,
            asthma_raw,
            asthma_playback_count,
            rng,
        )
    )
    selected_non_asthma_playback, paired_non_asthma_raw = (
        choose_paired_playback_sources(
            non_asthma_playback,
            non_asthma_raw,
            non_asthma_playback_count,
            rng,
        )
    )

    selected_asthma_raw = with_required_raw_random(
        asthma_raw,
        paired_asthma_raw,
        raw_per_class,
        rng,
    )
    selected_non_asthma_raw = with_required_raw_diverse(
        non_asthma_raw,
        paired_non_asthma_raw,
        raw_per_class,
        rng,
        [
            'raw:bronchial',
            'raw:copd',
            'raw:healthy',
            'raw:pneumonia',
            'raw:other',
        ],
    )
    selected_environment = choose_diverse(
        environment,
        environment_count,
        rng,
        [
            'environment:clap',
            'environment:fan',
            'environment:knock',
            'environment:podcast',
            'environment:room_noise',
            'environment:speech',
        ],
        randomize_group_order=True,
    )

    if len(selected_asthma_raw) < raw_per_class:
        raise ValueError('Not enough Asthma raw core files for requested sample budget')
    if len(selected_asthma_playback) < asthma_playback_count:
        raise ValueError('Not enough independent Asthma playback files')
    if len(selected_non_asthma_raw) < raw_per_class:
        raise ValueError('Not enough Non-Asthma raw core files')
    if len(selected_non_asthma_playback) < non_asthma_playback_count:
        raise ValueError('Not enough independent Non-Asthma playback files')
    if len(selected_environment) < environment_count:
        raise ValueError('Not enough Non-Asthma environment files')

    chosen = [
        (path, 0, 'raw:asthma')
        for path in selected_asthma_raw
    ]
    chosen.extend(
        (path, 0, 'playback:asthma')
        for path in selected_asthma_playback
    )
    chosen.extend(
        (path, 1, group_name)
        for path, group_name in selected_non_asthma_raw
    )
    chosen.extend(
        (path, 1, 'playback:non_asthma')
        for path in selected_non_asthma_playback
    )
    chosen.extend(
        (path, 1, group_name)
        for path, group_name in selected_environment
    )
    return chosen


def analyze(
    root,
    raw_per_class,
    environment_count,
    asthma_playback_count,
    non_asthma_playback_count,
    seed,
):
    chosen = select_analysis_files(
        root,
        raw_per_class,
        environment_count,
        asthma_playback_count,
        non_asthma_playback_count,
        seed,
    )
    rawpsd = {0: [], 1: []}
    raw_only_psd = {0: [], 1: []}
    source_psd = {'raw': [], 'playback': [], 'environment': []}
    psd_rows = []
    energy_rows = []
    sample_audio = {}
    selected_group_counts = {}
    for path, label, sample_group in chosen:
        audio = load_raw_window(path)
        # Raw waveform before bandpass: normalize only for inter-file spectral proportions.
        scale = max(float(np.max(np.abs(audio))), 1e-10)
        xn = audio / scale
        f, density = welch(
            xn,
            fs=SR,
            nperseg=2048,
            noverlap=1024,
            window='hann',
            scaling='density',
        )
        rawpsd[label].append(density)
        family = sample_family(sample_group)
        if family == 'raw':
            raw_only_psd[label].append(density)
        if family in source_psd:
            source_psd[family].append(density)

        relative_file = str(path.relative_to(root))
        psd_rows.extend(
            {
                'file': relative_file,
                'label': label,
                'sample_group': sample_group,
                'freq_hz': float(freq_hz),
                'psd_linear': float(psd_value),
            }
            for freq_hz, psd_value in zip(f, density)
        )
        total = np.trapezoid(density, f)
        row = {
            'file': relative_file,
            'label': label,
            'sample_group': sample_group,
        }
        for lo, hi in ((0, 100), (100, 2000), (2000, 4000), (4000, 8000)):
            region = (f >= lo) & (f <= hi)
            row[f'energy_{lo}_{hi}_pct'] = (
                float(100 * np.trapezoid(density[region], f[region]) / total)
                if total > 0
                else 0.
            )
        energy_rows.append(row)
        sample_audio.setdefault(label, (path, xn))
        group_count_key = f'label_{label}:{sample_group}'
        selected_group_counts[group_count_key] = (
            selected_group_counts.get(group_count_key, 0) + 1
        )
    write_rows(A_RESULTS / 'signal_summary.csv', energy_rows)
    write_rows(A_RESULTS / 'psd_by_file.csv', psd_rows)

    fig, ax = plt.subplots(figsize=(11, 4.5))
    for label, name in [(0, 'Asthma label'), (1, 'Non-Asthma label')]:
        stacked = np.array(rawpsd[label])
        median = np.median(stacked, axis=0)
        low, high = np.quantile(stacked, [.25, .75], axis=0)
        ax.plot(
            f,
            10 * np.log10(median + 1e-15),
            label=f'{name} n={len(stacked)}',
        )
        ax.fill_between(
            f,
            10 * np.log10(low + 1e-15),
            10 * np.log10(high + 1e-15),
            alpha=.15,
        )
    ax.axvspan(100, 2000, alpha=.1, color='grey', label='V1 100–2000 Hz')
    ax.set(
        xlim=(0, 4000),
        xlabel='Frequency (Hz)',
        ylabel='Welch PSD (dB relative)',
        title='Raw TRAIN WAV spectrum — BEFORE bandpass',
    )
    ax.legend()
    ax.grid(alpha=.2)
    save(fig, '01_raw_train_psd.png')

    # Phép so sánh chính của notebook: chỉ 12 raw Asthma vs 12 raw Non-Asthma.
    fig, ax = plt.subplots(figsize=(11, 4.5))
    for label, name in [(0, 'Asthma RAW'), (1, 'Non-Asthma RAW')]:
        stacked = np.asarray(raw_only_psd[label])
        if stacked.size == 0:
            continue
        median = np.median(stacked, axis=0)
        low, high = np.quantile(stacked, [.25, .75], axis=0)
        ax.plot(
            f,
            10 * np.log10(median + 1e-15),
            label=f'{name} n={len(stacked)}',
        )
        ax.fill_between(
            f,
            10 * np.log10(low + 1e-15),
            10 * np.log10(high + 1e-15),
            alpha=.15,
        )
    ax.axvspan(100, 2000, alpha=.1, color='grey', label='V1 100–2000 Hz')
    ax.set(
        xlim=(0, 4000),
        xlabel='Frequency (Hz)',
        ylabel='Welch PSD (dB relative)',
        title='RAW vs RAW — median spectrum + IQR (per file)',
    )
    ax.legend()
    ax.grid(alpha=.2)
    save(fig, '01a_psd_raw_vs_raw.png')

    # Audit miền thu phụ; không dùng thay cho phép so sánh raw-vs-raw phía trên.
    fig, ax = plt.subplots(figsize=(11, 4.5))
    source_names = {
        'raw': 'Raw core',
        'playback': 'Playback',
        'environment': 'Environment',
    }
    for family, name in source_names.items():
        stacked = np.asarray(source_psd[family])
        if stacked.size == 0:
            continue
        median = np.median(stacked, axis=0)
        low, high = np.quantile(stacked, [.25, .75], axis=0)
        ax.plot(
            f,
            10 * np.log10(median + 1e-15),
            label=f'{name} n={len(stacked)}',
        )
        ax.fill_between(
            f,
            10 * np.log10(low + 1e-15),
            10 * np.log10(high + 1e-15),
            alpha=.10,
        )
    ax.axvspan(100, 2000, alpha=.08, color='grey', label='F0 100–2000 Hz')
    ax.set(
        xlim=(0, 4000),
        xlabel='Frequency (Hz)',
        ylabel='Welch PSD (dB relative)',
        title='Supplementary domain audit — raw / playback / environment',
    )
    ax.legend()
    ax.grid(alpha=.2)
    save(fig, '01b_psd_by_source.png')

    path, xn = sample_audio[0]
    fig, axes = plt.subplots(2, 1, figsize=(12, 7))
    axes[0].plot(np.arange(SAMPLES) / SR, xn, lw=.45)
    axes[0].set(
        xlabel='Time (s)',
        ylabel='Amplitude',
        title=f'Example Asthma-labeled raw WAV: {path.name}',
    )
    D = librosa.stft(xn, n_fft=1024, hop_length=256, center=True)
    Ddb = librosa.amplitude_to_db(np.abs(D), ref=np.max, top_db=80)
    im = librosa.display.specshow(
        Ddb,
        sr=SR,
        hop_length=256,
        x_axis='time',
        y_axis='linear',
        ax=axes[1],
        cmap='magma',
    )
    axes[1].set(ylim=(0, 4000), title='Raw STFT (before frequency truncation)')
    axes[1].axhline(100, color='cyan', lw=.8, ls='--')
    axes[1].axhline(2000, color='cyan', lw=.8, ls='--')
    fig.colorbar(im, ax=axes[1])
    save(fig, '02_raw_waveform_stft.png')

    # Spectral-flux onset proxy; peaks are acoustic transients, NOT clinical wheeze labels.
    magnitude = np.abs(D)
    flux = np.maximum(np.diff(magnitude, axis=1), 0).mean(axis=0)
    tflux = np.arange(1, magnitude.shape[1]) * 256 / SR
    fig, ax = plt.subplots(figsize=(11, 3.4))
    ax.plot(tflux, flux, lw=1)
    ax.set(
        xlabel='Time (s)',
        ylabel='Positive spectral flux (a.u.)',
        title='Spectral-flux onset proxy on raw example WAV; NOT ground-truth wheeze onset',
    )
    ax.grid(alpha=.3)
    save(fig, '02b_spectral_flux_onset_proxy.png')

    fig, ax = plt.subplots(figsize=(10, 4.5))
    for order in (3, 5, 7):
        b, a = butter(
            order,
            [100 / (SR / 2), 2000 / (SR / 2)],
            btype='band',
            output='ba',
        )
        freqs, H = freqz(b, a, worN=8192, fs=SR)
        ax.plot(
            freqs,
            20 * np.log10(np.maximum(np.abs(H), 1e-9)),
            label=f'order {order}',
        )
    ax.axvline(100, color='grey', ls='--')
    ax.axvline(2000, color='grey', ls='--')
    ax.set(
        xlim=(0, 4000),
        ylim=(-100, 5),
        xlabel='Frequency (Hz)',
        ylabel='Magnitude (dB)',
        title='Butterworth 100–2000 Hz response (actual coefficients)',
    )
    ax.legend()
    ax.grid(alpha=.3)
    save(fig, '03_butterworth_orders.png')

    fig, ax = plt.subplots(figsize=(10, 4.5))
    freqs = np.linspace(0, SR / 2, 3000)
    for c in (0., .95, .97):
        h = np.abs(1 - c * np.exp(-1j * 2 * np.pi * freqs / SR))
        ax.plot(
            freqs,
            20 * np.log10(np.maximum(h, 1e-10)),
            label=f'coef {c}',
        )
    ax.set(
        xlim=(0, 4000),
        xlabel='Frequency (Hz)',
        ylabel='Magnitude (dB)',
        title='Pre-emphasis theoretical frequency response',
    )
    ax.grid(alpha=.3)
    ax.legend()
    save(fig, '04_pre_emphasis_response.png')

    fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharex=True)
    for ax, n in zip(axes, (40, 64, 80)):
        fb = librosa.filters.mel(
            sr=SR,
            n_fft=1024,
            n_mels=n,
            fmin=100,
            fmax=2000,
            htk=False,
            norm='slaney',
        )
        hz = librosa.fft_frequencies(sr=SR, n_fft=1024)
        ax.plot(hz, fb.T, lw=.5)
        ax.set(xlim=(0, 2500), xlabel='Hz', title=f'{n} Mel bins')
    axes[0].set_ylabel('Filter weight')
    fig.suptitle('Slaney Mel filterbanks — fixed FFT=1024')
    save(fig, '05_mel_filterbanks.png')

    # Same WAV and DSP for Mel parameter comparisons; no supervised training.
    wave = process_wave(load_raw_window(path), BASELINE)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for ax, n in zip(axes, (40, 64, 80)):
        mel = mel_from_wave(wave, replace(BASELINE, n_mels=n))
        im = ax.imshow(
            mel,
            origin='lower',
            aspect='auto',
            extent=(0, 5, 0, n),
            vmin=-80,
            vmax=0,
            cmap='magma',
        )
        ax.set(xlabel='Time (s)', title=f'N_MELS={n}, {mel.shape[1]} frames')
    axes[0].set_ylabel('Mel bin index')
    fig.colorbar(im, ax=axes.tolist(), fraction=.025)
    save(fig, '06_mel_bins.png')

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for ax, hop in zip(axes, (400, 625, 800)):
        c = replace(BASELINE, hop_length=hop)
        mel = mel_from_wave(wave, c)
        ax.imshow(
            mel,
            origin='lower',
            aspect='auto',
            extent=(0, 5, 0, c.n_mels),
            vmin=-80,
            vmax=0,
            cmap='magma',
        )
        ax.set(xlabel='Time (s)', title=f'HOP={hop}: {mel.shape[1]} frames')
    axes[0].set_ylabel('Mel bin index')
    save(fig, '07_mel_hop.png')

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, nfft in zip(axes, (1024, 2048)):
        c = replace(BASELINE, n_fft=nfft)
        mel = mel_from_wave(wave, c)
        ax.imshow(
            mel,
            origin='lower',
            aspect='auto',
            extent=(0, 5, 0, c.n_mels),
            vmin=-80,
            vmax=0,
            cmap='magma',
        )
        ax.set(
            xlabel='Time (s)',
            title=f'FFT={nfft}: window={nfft / SR * 1000:.0f} ms',
        )
    axes[0].set_ylabel('Mel bin index')
    save(fig, '08_mel_fft.png')

    # Compare feature geometry only. Not an accuracy comparison.
    logmel = mel_from_wave(wave, BASELINE)
    mfcc = librosa.feature.mfcc(S=logmel, n_mfcc=13, dct_type=2, norm='ortho')
    delta = librosa.feature.delta(mfcc, order=1, width=9)
    delta2 = librosa.feature.delta(mfcc, order=2, width=9)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for ax, arr, title in zip(
        axes.flat,
        (logmel, mfcc, delta, delta2),
        ('Log-Mel 64 bins', 'MFCC 13', 'MFCC delta', 'MFCC delta-delta'),
    ):
        ax.imshow(
            arr,
            aspect='auto',
            origin='lower',
            extent=(0, 5, 0, arr.shape[0]),
            cmap='magma',
        )
        ax.set(xlabel='Time (s)', ylabel='Mel bin / cepstral coeff', title=title)
    fig.suptitle('Same TRAIN WAV: feature representations (visual comparison only)')
    save(fig, '09_logmel_vs_mfcc_deltas.png')

    grid = []
    for n in (40, 64, 80):
        for hop in (400, 625, 800):
            frames = 1 + SAMPLES // hop
            grid.append(
                {
                    'n_mels': n,
                    'hop_length': hop,
                    'frames': frames,
                    'elements': n * frames,
                    'input_int8_bytes': n * frames,
                    'input_float32_bytes': 4 * n * frames,
                }
            )
    write_rows(A_RESULTS / 'mel_input_cost.csv', grid)
    selected_raw_keys = {
        path.stem.casefold(): str(path.relative_to(root))
        for path, _, sample_group in chosen
        if sample_family(sample_group) == 'raw'
    }
    write_json(
        A_RESULTS / 'analysis_manifest.json',
        {
            'protocol': PROTOCOL,
            'dataset': str(root),
            'train_only': True,
            'sampling_policy': {
                'raw_per_class': raw_per_class,
                'asthma_raw_core': raw_per_class,
                'non_asthma_raw_core': raw_per_class,
                'asthma_playback': asthma_playback_count,
                'non_asthma_playback': non_asthma_playback_count,
                'non_asthma_environment': environment_count,
                'asthma_augmentation': 0,
                'primary_comparison': '12 Asthma raw vs 12 Non-Asthma raw',
                'supplementary_domain_audit': (
                    '1 Asthma + 2 Non-Asthma playback and 3 environment by default'
                ),
                'non_asthma_raw': 'stratified round-robin by disease group',
                'environment': 'stratified round-robin by environment type',
                'playback': (
                    'one take per source; prefer a source whose raw file is '
                    'included in the raw quota'
                ),
            },
            'selected_files': [
                {
                    'file': str(path.relative_to(root)),
                    'label': label,
                    'sample_group': sample_group,
                    'paired_raw_file': (
                        selected_raw_keys.get(playback_raw_key(path))
                        if sample_family(sample_group) == 'playback'
                        else None
                    ),
                }
                for path, label, sample_group in chosen
            ],
            'selected_group_counts': selected_group_counts,
            'total_counts_by_label': {str(k): len(v) for k, v in rawpsd.items()},
            'raw_counts_by_label': {
                str(k): len(v) for k, v in raw_only_psd.items()
            },
            'seed': seed,
            'note': 'Plots use real train WAVs; not diagnostic or proof of optimal classification.',
        },
    )
    print(
        'DONE: results/A_scientific_frontend_evidence/figures/*.png, '
        'signal_summary.csv, psd_by_file.csv, mel_input_cost.csv, '
        'analysis_manifest.json'
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dataset-root')
    p.add_argument('--raw-per-class', type=int, default=12)
    p.add_argument('--environment-count', type=int, default=3)
    p.add_argument('--asthma-playback-count', type=int, default=1)
    p.add_argument('--non-asthma-playback-count', type=int, default=2)
    p.add_argument('--seed', type=int, default=42)
    a = p.parse_args()
    if a.raw_per_class < 1:
        p.error('--raw-per-class must be >= 1')
    if a.environment_count < 0:
        p.error('--environment-count must be >= 0')
    if a.asthma_playback_count < 0:
        p.error('--asthma-playback-count must be >= 0')
    if a.non_asthma_playback_count < 0:
        p.error('--non-asthma-playback-count must be >= 0')
    if a.asthma_playback_count > a.raw_per_class:
        p.error('--asthma-playback-count cannot exceed --raw-per-class')
    if a.non_asthma_playback_count > a.raw_per_class:
        p.error('--non-asthma-playback-count cannot exceed --raw-per-class')
    analyze(
        dataset_root(a.dataset_root),
        a.raw_per_class,
        a.environment_count,
        a.asthma_playback_count,
        a.non_asthma_playback_count,
        a.seed,
    )


if __name__ == '__main__':
    main()
