"""B0_Dataset_Audit.py — Kiểm kê metadata WAV và nguy cơ zero-padding của V1.

Tác dụng:
- Đọc header của toàn bộ WAV thuộc Train + Validation bằng ``soundfile.info``.
- Thống kê sample rate gốc, thời lượng, nhóm nguồn và phần âm thanh còn dùng được
  sau quy tắc crop của V1.
- Ước lượng lượng zero-padding cần thêm để đủ cửa sổ 5 giây và chỉ ra các nhóm
  có nguy cơ tương quan nhãn với sample rate/nguồn/padding.

Script chỉ đọc metadata, không giải mã waveform, không sửa dataset và không truy
cập tập Test. Kết quả được ghi vào ``results/B0_dataset_audit/`` dưới dạng các
CSV cùng ``audit_manifest.json``.

``Notebook/02_Dataset_Audit/B0_SampleRate_Source_Audit.ipynb`` đọc các artifact do
``B0_Dataset_Audit.py`` tạo để trực quan hóa và diễn giải audit dataset; sau đó
notebook tiếp tục đọc kết quả Validation do chuỗi 01→04 và B1_Domain_Validation.py
tạo ra. Notebook không
thay thế script preprocess/train/evaluate, không tự tạo số liệu còn thiếu và
không dùng Test để chọn cấu hình.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

import soundfile as sf

from frontend_core import DURATION, PROTOCOL, RESULTS, dataset_root, list_split, split_fingerprint

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

LABELS = {0: 'Asthma', 1: 'Non-Asthma'}
SPLITS = ('train', 'val')
FILE_COLUMNS = [
    'file', 'split', 'label', 'label_name', 'source_kind', 'source_detail',
    'original_sr_hz', 'original_nyquist_hz', 'original_channels', 'original_frames',
    'original_duration_s', 'original_format', 'original_subtype',
    'v1_offset_s', 'v1_window_s', 'usable_duration_s', 'estimated_zero_pad_s',
    'estimated_zero_pad_pct', 'requires_padding', 'usable_lt_1s',
    'usable_lt_3s', 'padding_ge_50pct', 'padding_ge_80pct',
]


def classify_source(path: Path, label: int) -> tuple[str, str]:
    """Phân nhóm theo tên file giống mục A; ``raw`` nghĩa là *không augmentation*.

    Tên nhóm này không khẳng định WAV gốc chưa được xử lý hoặc độc lập về nguồn.
    """
    stem = path.stem.casefold()
    if stem.endswith(('__take01', '__take02')):
        return 'playback', 'take'
    if stem.startswith('env__'):
        parts = stem.split('__')
        return 'environment', parts[1] if len(parts) > 1 else 'unknown'
    if stem.startswith('augv2__'):
        return 'augmentation', 'augv2'
    if label == 0:
        return 'raw', 'asthma'
    return 'raw', next(
        (name for name in ('bronchial', 'copd', 'healthy', 'pneumonia') if name in stem),
        'other',
    )


def csv_write(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def inspect_files(root: Path) -> tuple[list[dict], list[dict]]:
    rows, errors = [], []
    for split in SPLITS:
        for path, label in list_split(root, split):
            filename = path.relative_to(root).as_posix()
            try:
                info = sf.info(str(path))  # WAV header only; no decoding/resampling
                sr = int(info.samplerate)
                frames = int(info.frames)
                channels = int(info.channels)
                if sr <= 0 or frames < 0 or channels <= 0:
                    raise ValueError(f'Invalid WAV header: sr={sr}, frames={frames}, ch={channels}')
                seconds = frames / sr
                source_kind, source_detail = classify_source(path, label)
                offset = 1.0 if source_kind == 'playback' else 0.0
                # V1 load_raw_window uses offset and duration *before* zero-padding.
                usable = min(DURATION, max(0.0, seconds - offset))
                missing = max(0.0, DURATION - usable)
                missing_pct = missing / DURATION * 100
                rows.append({
                    'file': filename, 'split': split, 'label': label,
                    'label_name': LABELS[label], 'source_kind': source_kind,
                    'source_detail': source_detail, 'original_sr_hz': sr,
                    'original_nyquist_hz': sr / 2, 'original_channels': channels,
                    'original_frames': frames, 'original_duration_s': round(seconds, 8),
                    'original_format': str(info.format), 'original_subtype': str(info.subtype),
                    'v1_offset_s': offset, 'v1_window_s': DURATION,
                    'usable_duration_s': round(usable, 8),
                    'estimated_zero_pad_s': round(missing, 8),
                    'estimated_zero_pad_pct': round(missing_pct, 6),
                    'requires_padding': int(missing > 1e-5),
                    'usable_lt_1s': int(usable < 1),
                    'usable_lt_3s': int(usable < 3),
                    'padding_ge_50pct': int(missing_pct >= 50),
                    'padding_ge_80pct': int(missing_pct >= 80),
                })
            except Exception as e:
                errors.append({'split': split, 'file': filename,
                               'error': f'{type(e).__name__}: {e}'})
    return rows, errors


def summarize(rows: list[dict], keys: tuple[str, ...], extended: bool = False):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[k] for k in keys)].append(row)
    output = []
    for tup, group in sorted(groups.items(), key=lambda item: tuple(str(v) for v in item[0])):
        r = dict(zip(keys, tup))
        r.update({
            'n': len(group),
            'requires_padding_n': sum(a['requires_padding'] for a in group),
            'usable_lt_1s_n': sum(a['usable_lt_1s'] for a in group),
            'usable_lt_3s_n': sum(a['usable_lt_3s'] for a in group),
            'padding_ge_50pct_n': sum(a['padding_ge_50pct'] for a in group),
            'padding_ge_80pct_n': sum(a['padding_ge_80pct'] for a in group),
        })
        if extended:
            r.update({
                'median_original_duration_s': round(median(a['original_duration_s'] for a in group), 5),
                'median_usable_duration_s': round(median(a['usable_duration_s'] for a in group), 5),
                'median_zero_pad_pct': round(median(a['estimated_zero_pad_pct'] for a in group), 5),
                'padding_required_pct': round(100 * r['requires_padding_n'] / len(group), 4),
                'padding_ge_50pct_pct': round(100 * r['padding_ge_50pct_n'] / len(group), 4),
            })
        output.append(r)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description='B0_Dataset_Audit.py: kiểm kê header WAV Train/Validation và padding V1; không mở Test'
    )
    parser.add_argument('--dataset-root', help='Thư mục gốc Dataset_Chia_V2; bỏ trống để tự tìm')
    parser.add_argument('--output-dir', help='Mặc định: results/B0_dataset_audit tại root benchmark')
    args = parser.parse_args()
    root = dataset_root(args.dataset_root)
    out = Path(args.output_dir).expanduser().resolve() if args.output_dir else RESULTS / 'B0_dataset_audit'
    data, errors = inspect_files(root)
    if not data:
        raise RuntimeError('B0_Dataset_Audit.py không tìm thấy metadata WAV Train/Validation có thể đọc')

    csv_write(out / 'file_metadata.csv', data, FILE_COLUMNS)
    csv_write(out / 'metadata_errors.csv', errors, ['split', 'file', 'error'])

    base = ['n', 'requires_padding_n', 'usable_lt_1s_n', 'usable_lt_3s_n',
            'padding_ge_50pct_n', 'padding_ge_80pct_n']
    extra = ['median_original_duration_s', 'median_usable_duration_s',
             'median_zero_pad_pct', 'padding_required_pct', 'padding_ge_50pct_pct']
    rate_keys = ('split', 'label', 'label_name', 'source_kind', 'original_sr_hz')
    csv_write(out / 'sample_rate_distribution.csv', summarize(data, rate_keys), list(rate_keys) + base)

    raw_keys = ('split', 'label', 'label_name', 'original_sr_hz')
    raw = [r for r in data if r['source_kind'] == 'raw']
    csv_write(out / 'raw_source_rate_crosstab.csv', summarize(raw, raw_keys), list(raw_keys) + base)

    duration_keys = ('split', 'label', 'label_name', 'source_kind')
    csv_write(out / 'duration_padding_summary.csv', summarize(data, duration_keys, True),
              list(duration_keys) + base + extra)
    risk_keys = ('split', 'label', 'label_name', 'source_kind', 'original_sr_hz')
    csv_write(out / 'padding_risk_summary.csv', summarize(data, risk_keys, True),
              list(risk_keys) + base + extra)

    manifest = {
        'audit': 'B0_DATASET_METADATA_AND_V1_PADDING', 'protocol': PROTOCOL,
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'dataset_root': str(root), 'splits': list(SPLITS),
        'read_only': True, 'waveforms_decoded': False, 'test_accessed': False,
        'original_sr_from_header': True,
        'window_s': DURATION, 'playback_offset_s': 1.0,
        'valid_file_count': len(data), 'metadata_error_count': len(errors),
        'counts_by_split_label': {
            f'{split}:{label_name}': n
            for (split, label_name), n in sorted(Counter((a['split'], a['label_name']) for a in data).items())
        },
        'train_fingerprint': split_fingerprint(root, 'train'),
        'val_fingerprint': split_fingerprint(root, 'val'),
        'source_kind_inferred_from_filename': True,
        'limitations': [
            'Thời lượng từ header chỉ ước lượng padding do V1 thêm, không đo khoảng im lặng sẵn có.',
            'Phân nhóm theo tên file không chứng minh nguồn hoặc bệnh nhân độc lập.',
            'Resample lên 16 kHz không khôi phục được băng thông đã thiếu ở nguồn.',
            'Nếu có lỗi đọc file, phân bố thống kê theo nhóm có thể chưa đầy đủ.',
            'Script không train, không kiểm tra Test và không sửa dataset.',
        ],
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / 'audit_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(f'B0_Dataset_Audit.py HOÀN TẤT — {len(data)} header WAV Train/Validation; {len(errors)} lỗi')
    print(f'Đầu ra: {out}')
    print('Mở Notebook/02_Dataset_Audit/B0_SampleRate_Source_Audit.ipynb để diễn giải kết quả.')


if __name__ == '__main__':
    main()
