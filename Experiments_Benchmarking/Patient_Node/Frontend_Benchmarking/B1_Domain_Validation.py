"""B1_Domain_Validation.py — Phân tích Validation theo metadata miền thu.

Tác dụng:
- Ghép prediction từng file với metadata do ``B0_Dataset_Audit.py`` tạo.
- Tổng hợp metric theo nhãn, loại nguồn, sample rate và mức zero-padding.
- Đối chiếu từng trial Front-End để nhận diện sai lệch theo miền dữ liệu.

Đầu vào chỉ đọc:
- ``results/B0_dataset_audit/``;
- ``results/val_summary.csv``;
- ``artifacts/models/<trial_id>/val_predictions.csv``.

Đầu ra được ghi vào ``results/B1_domain_audit/``. Script không mở Test, không
huấn luyện và không sửa model, tensor đặc trưng hay dataset.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

from frontend_core import ARTIFACTS, RESULTS, read_json, read_rows, write_rows

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')


def as_int(value):
    return int(float(value))


def canonical(value: str) -> str:
    return str(value).replace('\\', '/')


def summarize_group(trial, group, cols, rows):
    out = []
    keys = sorted(set(tuple(r[c] for c in cols) for r in rows), key=lambda k: tuple(map(str,k)))
    for key in keys:
        subset = [r for r in rows if tuple(r[c] for c in cols) == key]
        n = len(subset)
        correct = sum(r['correct'] for r in subset)
        asthma_n = sum(r['true_label'] == 0 for r in subset)
        asthma_fn = sum(r['true_label'] == 0 and r['predicted_label'] == 1 for r in subset)
        non_asthma_n = n - asthma_n
        non_asthma_asthma = sum(r['true_label'] == 1 and r['predicted_label'] == 0 for r in subset)
        rec = {
            'trial_id': trial,
            'grouping': group,
            'source_kind': '', 'original_sr_hz': '', 'label_name': '', 'padding_band': '',
            **dict(zip(cols, key)),
            'n': n, 'correct': correct, 'errors': n - correct,
            'accuracy_or_class_recall': round(correct / n, 8),
            'asthma_n': asthma_n, 'asthma_fn': asthma_fn,
            'asthma_recall': round((asthma_n - asthma_fn) / asthma_n, 8) if asthma_n else '',
            'non_asthma_n': non_asthma_n,
            'non_asthma_pred_asthma': non_asthma_asthma,
            'small_group_n_lt_10': int(n < 10),
        }
        out.append(rec)
    return out


def by_filename(read_path: Path, name: str):
    if not read_path.is_file():
        raise FileNotFoundError(f'Missing {name}: {read_path}')
    rows = read_rows(read_path)
    result = {}
    for r in rows:
        k = canonical(r['file'])
        if k in result:
            raise ValueError(f'Duplicate {name} filename: {k}')
        result[k] = r
    return result


def inspect(args):
    meta = by_filename(
        RESULTS / 'B0_dataset_audit' / 'file_metadata.csv',
        'metadata của B0_Dataset_Audit.py',
    )
    valmeta = {k: r for k, r in meta.items() if r['split'] == 'val'}
    if len(valmeta) == 0:
        raise RuntimeError('Metadata của B0_Dataset_Audit.py không có bản ghi Validation')
    b0_manifest = read_json(RESULTS / 'B0_dataset_audit' / 'audit_manifest.json')
    summaries = read_rows(RESULTS / 'val_summary.csv')
    summaries_by_trial = {r['trial_id']: r for r in summaries if r['architecture'] == args.architecture}
    if len(summaries_by_trial) == 0:
        raise RuntimeError('No Validation trials for chosen architecture')
    trials = sorted(summaries_by_trial)
    chosen = sorted(trials if not args.variant else [t for t in trials if summaries_by_trial[t]['variant_id'] == args.variant])
    if not chosen:
        raise RuntimeError('No matching Validation trial')
    joined_by_trial = {}
    strata = []
    flat = []
    for tid in chosen:
        info = read_json(ARTIFACTS / 'models' / tid / 'training_metadata.json')
        if info['val_fingerprint'] != b0_manifest['val_fingerprint']:
            raise RuntimeError(
                f'Fingerprint Validation không khớp giữa B0_Dataset_Audit.py và training: {tid}'
            )
        if info['train_fingerprint'] != b0_manifest['train_fingerprint']:
            raise RuntimeError(
                f'Fingerprint Train không khớp giữa B0_Dataset_Audit.py và training: {tid}'
            )
        summary = summaries_by_trial[tid]
        if (summary['config_sha256'] != info['config_sha256']
                or summary['variant_id'] != info['variant_id']):
            raise RuntimeError(f'Summary / training hash mismatch: {tid}')
        preds = by_filename(ARTIFACTS / 'models' / tid / 'val_predictions.csv', tid)
        if set(preds) != set(valmeta):
            raise RuntimeError(f'Validation coverage mismatch {tid}: '
                               f'{len(set(preds)-set(valmeta))} extra; {len(set(valmeta)-set(preds))} missing')
        merged = {}
        for k, pred in preds.items():
            m = valmeta[k]
            expected_label = as_int(m['label'])
            y = as_int(pred['true_label'])
            yh = as_int(pred['predicted_label'])
            prob = float(pred['p_non_asthma'])
            if y != expected_label or y not in (0,1) or yh not in (0,1):
                raise ValueError(f'Label mismatch: {tid}, {k}')
            if not (0 <= prob <= 1) or int(prob >= .5) != yh:
                raise ValueError(f'Probability/threshold mismatch: {tid}, {k}')
            pad = float(m['estimated_zero_pad_pct'])
            row = {
                'trial_id': tid, 'file': k, 'true_label': y,
                'predicted_label': yh, 'p_non_asthma': prob,
                'correct': int(y == yh),
                'asthma_fn': int(y == 0 and yh == 1),
                'source_kind': m['source_kind'],
                'source_detail': m['source_detail'],
                'label_name': m['label_name'],
                'original_sr_hz': str(as_int(m['original_sr_hz'])),
                'estimated_zero_pad_pct': pad,
                'padding_band': ('0%' if pad < 1e-6 else
                                 '<50%' if pad < 50 else '50–80%' if pad < 80 else '>=80%'),
            }
            merged[k] = row
            flat.append(row)
        joined_by_trial[tid] = merged
        rows = list(merged.values())
        strata.extend(summarize_group(tid, 'label×source×rate',
                    ['label_name', 'source_kind', 'original_sr_hz'], rows))
        strata.extend(summarize_group(tid, 'label×rate',
                    ['label_name', 'original_sr_hz'], rows))
        strata.extend(summarize_group(tid, 'label×source',
                    ['label_name', 'source_kind'], rows))
        strata.extend(summarize_group(tid, 'label×padding',
                    ['label_name', 'padding_band'], rows))
        print(f'HỢP LỆ {tid}: ghép đủ {len(rows)} WAV Validation; không dùng Test')

    base = args.baseline_trial
    paired = []
    if base in joined_by_trial:
        b = joined_by_trial[base]
        for tid in chosen:
            if tid == base:
                continue
            c = joined_by_trial[tid]
            if as_int(summaries_by_trial[tid]['seed']) != as_int(summaries_by_trial[base]['seed']):
                print(f'BỎ QUA so sánh cặp {tid}: seed khác {base}')
                continue
            pairs = []
            for fname in sorted(b):
                bb, cc = b[fname], c[fname]
                pairs.append({
                    **{k:bb[k] for k in ['file','true_label','label_name','source_kind','original_sr_hz']},
                    'baseline_correct': bb['correct'],
                    'candidate_correct': cc['correct'],
                    'baseline_asthma_fn': bb['asthma_fn'],
                    'candidate_asthma_fn': cc['asthma_fn'],
                })
            for label, subset in [
                ('ALL',pairs),
                ('Asthma',[r for r in pairs if r['true_label'] == 0]),
                ('Non-Asthma',[r for r in pairs if r['true_label'] == 1]),
            ]:
                n = len(subset)
                paired.append({
                    'baseline_trial_id': base, 'candidate_trial_id': tid,
                    'label_group': label, 'n': n,
                    'both_correct': sum(r['baseline_correct'] and r['candidate_correct'] for r in subset),
                    'baseline_only_correct': sum(r['baseline_correct'] and not r['candidate_correct'] for r in subset),
                    'candidate_only_correct': sum(not r['baseline_correct'] and r['candidate_correct'] for r in subset),
                    'both_wrong': sum(not r['baseline_correct'] and not r['candidate_correct'] for r in subset),
                    'baseline_asthma_fn': sum(r['baseline_asthma_fn'] for r in subset),
                    'candidate_asthma_fn': sum(r['candidate_asthma_fn'] for r in subset),
                })
    else:
        print(f'CẢNH BÁO: thiếu baseline {base}; chưa tạo được so sánh theo cặp')

    output = Path(args.output_dir) if args.output_dir else RESULTS / 'B1_domain_audit'
    output.mkdir(parents=True, exist_ok=True)
    write_rows(output / 'stratified_validation.csv', strata)
    write_rows(output / 'per_file_validation_with_metadata.csv', flat)
    if paired:
        write_rows(output / 'paired_vs_F0.csv', paired)
    print('B1_Domain_Validation.py HOÀN TẤT:', output)
    print(
        'GIỚI HẠN QUAN TRỌNG: Validation không có Asthma raw 44,1 kHz; '
        'không thể ước lượng Asthma Recall chéo nguồn'
    )


def main():
    p = argparse.ArgumentParser(
        description='B1_Domain_Validation.py: phân tích Validation theo metadata miền thu; không mở Test'
    )
    p.add_argument('--architecture', default='V1')
    p.add_argument('--variant', help='Tùy chọn: chỉ audit một variant')
    p.add_argument('--baseline-trial', default='F0__V1__s42')
    p.add_argument('--output-dir')
    a = p.parse_args()
    inspect(a)


if __name__ == '__main__':
    main()
