"""B1_Preflight.py — Kiểm tra an toàn trước preprocess và huấn luyện.

Tác dụng:
- Đọc động tất cả cấu hình có ``enabled=1`` trong ``configs/candidates.csv``.
- Không bắt buộc ``F0`` có mặt trong lịch train; mỗi candidate được bật
  vẫn phải chỉ thay đổi đúng một tham số so với baseline F0 bất biến.
- Đối chiếu candidate với ``results/experiment_plan.csv`` bằng config hash.
- Kiểm tra audit B0_Dataset_Audit, fingerprint Train/Validation và đường dẫn kiến trúc V1.
- Cảnh báo giới hạn phân bố nguồn/sample rate trước khi chạy ``02_Preprocess.py``.

Thứ tự chạy: ``python 01_Build_Plan.py`` rồi ``python B1_Preflight.py`` tại
thư mục gốc ``Frontend_Benchmarking/``. Script không import TensorFlow, không
huấn luyện, không sửa dataset và không truy cập âm thanh Test.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict
from pathlib import Path

from frontend_core import (
    BASELINE, RESULTS, ROOT, dataset_root, digest, load_config,
    read_rows, split_fingerprint,
)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def run(dataset_override: str | None, builder_override: str | None) -> None:
    candidates = ROOT / 'configs' / 'candidates.csv'
    plan_file = RESULTS / 'experiment_plan.csv'
    b0_folder = RESULTS / 'B0_dataset_audit'
    config_rows = read_rows(candidates)
    if not config_rows:
        raise ValueError('configs/candidates.csv đang rỗng')
    ids = [r['variant_id'] for r in config_rows]
    if len(ids) != len(set(ids)):
        raise ValueError('Có variant_id trùng trong configs/candidates.csv')
    invalid_flags = [r['variant_id'] for r in config_rows if r.get('enabled') not in ('0', '1')]
    if invalid_flags:
        raise ValueError(f'Cột enabled phải là 0 hoặc 1 cho các candidate: {invalid_flags}')

    enabled = [r for r in config_rows if r['enabled'] == '1']
    enabled_map = {r['variant_id']: r for r in enabled}
    if not enabled:
        raise ValueError('Không có candidate nào được bật trong configs/candidates.csv')

    baseline_dict = asdict(BASELINE)
    for variant, row in enabled_map.items():
        config = load_config(row)
        actual = asdict(config)
        changed = {
            key: (baseline_dict[key], actual[key])
            for key in baseline_dict
            if actual[key] != baseline_dict[key]
        }
        if variant == 'F0':
            if changed:
                raise ValueError(f'F0 phải khớp hoàn toàn baseline; tham số đã đổi={changed}')
            change_note = 'baseline'
        else:
            if len(changed) != 1:
                raise ValueError(
                    f'{variant}: B1_Preflight.py yêu cầu chỉ đổi đúng một tham số so với F0; '
                    f'tham số đã đổi={changed}'
                )
            key, (old, new) = next(iter(changed.items()))
            change_note = f'{key}: {old} -> {new}'
        print(
            f'HỢP LỆ candidate {variant:<16} | {change_note:<32} '
            f'| sha256={digest(config)[:16]}'
        )

    if not plan_file.is_file():
        raise FileNotFoundError('Cần chạy python 01_Build_Plan.py trước B1_Preflight.py')
    plan_rows = read_rows(plan_file)
    by_id = {r['variant_id']: r for r in plan_rows}
    if set(by_id) != {r['variant_id'] for r in config_rows}:
        raise RuntimeError('experiment_plan.csv không khớp candidates.csv; hãy chạy lại 01_Build_Plan.py')
    plan_enabled = {variant for variant, row in by_id.items() if row.get('enabled') == '1'}
    if plan_enabled != set(enabled_map):
        raise RuntimeError(
            'experiment_plan.csv có cờ enabled cũ; hãy chạy lại python 01_Build_Plan.py. '
            f'plan={sorted(plan_enabled)}, config={sorted(enabled_map)}'
        )
    for variant in enabled_map:
        row = by_id[variant]
        if row.get('enabled') != '1' or row['config_sha256'] != digest(load_config(enabled_map[variant])):
            raise RuntimeError(f'Plan đã cũ hoặc candidate bị tắt: {variant}')
    print(f'KẾ HOẠCH HỢP LỆ: {len(enabled_map)} candidate được bật và hash khớp candidates.csv')

    root = dataset_root(dataset_override)
    manifest_path = b0_folder / 'audit_manifest.json'
    meta_path = b0_folder / 'file_metadata.csv'
    if not manifest_path.is_file() or not meta_path.is_file():
        raise FileNotFoundError(
            'Cần chạy python B0_Dataset_Audit.py trên dataset này trước; '
            'đang thiếu manifest/metadata trong results/B0_dataset_audit'
        )
    manifest = json.loads(manifest_path.read_text(encoding='utf8'))
    if int(manifest.get('metadata_error_count', -1)) != 0:
        raise RuntimeError('B0_Dataset_Audit.py báo lỗi metadata; cần kiểm tra trước khi train')
    for split in ('train', 'val'):
        if split not in manifest.get('splits', []):
            raise RuntimeError(f'B0_Dataset_Audit.py chưa kiểm tra split {split}')
        actual = split_fingerprint(root, split)
        if actual != manifest.get(f'{split}_fingerprint'):
            raise RuntimeError(
                f'File trong split {split} đã thay đổi sau B0_Dataset_Audit.py; '
                'hãy chạy lại B0_Dataset_Audit.py trước B1_Preflight.py'
            )
        print(f'FINGERPRINT HỢP LỆ {split}: {actual[:16]}')
    if str(root) != manifest.get('dataset_root'):
        raise RuntimeError('Dataset root khác với B0_Dataset_Audit.py; phải dùng cùng một dataset')
    with meta_path.open(encoding='utf-8-sig', newline='') as f:
        meta = list(csv.DictReader(f))
    val = [r for r in meta if r['split'] == 'val']
    if not val or {r['label_name'] for r in val} != {'Asthma', 'Non-Asthma'}:
        raise RuntimeError('Metadata từ B0_Dataset_Audit.py thiếu nhãn trong Validation')
    print(
        f'B0_Dataset_Audit.py HỢP LỆ: {len(meta)} bản ghi metadata '
        'Train/Validation; không có lỗi đọc'
    )

    if builder_override:
        builder = Path(builder_override).expanduser().resolve()
    else:
        from frontend_core import default_builder_path
        builder = default_builder_path()
    if not builder.is_file() or builder.name != 'V1_SepConv2D_Flatten.py':
        raise FileNotFoundError(f'Pass the original V1 builder using --builder-path: {builder}')
    code = builder.read_text(encoding='utf-8-sig')
    if 'build_and_compile_model' not in code:
        raise RuntimeError('Original V1 builder has no expected build_and_compile_model function')
    print(f'KIẾN TRÚC V1 HỢP LỆ: {builder}')

    # Sai lệch nguồn do B0_Dataset_Audit.py phát hiện chỉ là cảnh báo; không tự ý loại Validation.
    asthma_raw = [r for r in val if r['source_kind'] == 'raw' and r['label_name'] == 'Asthma']
    sr_counts = {}
    for r in asthma_raw:
        sr_counts[r['original_sr_hz']] = sr_counts.get(r['original_sr_hz'], 0) + 1
    print(f'CẢNH BÁO MIỀN NGUỒN: số Asthma raw Validation theo sample rate gốc: {sr_counts}')
    if sr_counts.get('44100', 0) == 0:
        print('KHÔNG ƯỚC LƯỢNG ĐƯỢC: Asthma Recall raw 44,1 kHz trên Validation hiện tại.')
    print('B1_Preflight.py HOÀN TẤT — có thể preprocess/train; chưa truy cập Test.')


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--dataset-root')
    p.add_argument(
        '--builder-path',
        help='Đường dẫn chính xác tới Model_Architectures/V1_SepConv2D_Flatten.py gốc',
    )
    a = p.parse_args()
    run(a.dataset_root, a.builder_path)


if __name__ == '__main__':
    main()
