"""D0 - kiểm toán checkpoint và khóa kế hoạch lượng tử hóa Frontend.

Script không import TensorFlow và không lượng tử hóa. Nếu không truyền phạm vi,
bốn checkpoint bàn giao từ bước C được sử dụng. ``--all-c-checkpoints`` khóa
đúng ma trận 8 cấu hình × 3 seed đã có trong cả hai summary của bước C.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from d_quantization_core import (
    D_RESULTS, METHOD_CONFIG, METHOD_SPECS, PLAN_PATH, ROOT,
    atomic_json, audit_trial, default_quantization_trials, load_methods,
    sha256_file, sha256_json, utc_now, write_csv,
)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')


C_VARIANTS = (
    'F0',
    'pre_0',
    'mel_40',
    'fft_2048',
    'combo_pre0_mel40',
    'combo_pre0_fft2048',
    'combo_mel40_fft2048',
    'combo_pre0_mel40_fft2048',
)
C_SEEDS = (42, 43, 44)


def read_summary(split: str) -> dict[str, dict[str, str]]:
    """Đọc summary chuẩn của C và chặn trial_id trùng."""
    path = ROOT / 'results' / f'{split}_summary.csv'
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    indexed: dict[str, dict[str, str]] = {}
    for row in rows:
        trial_id = row.get('trial_id', '')
        if not trial_id:
            continue
        if trial_id in indexed:
            raise ValueError(f'{path}: trial_id bị trùng: {trial_id}')
        indexed[trial_id] = row
    return indexed


def all_c_checkpoint_trials() -> list[str]:
    """Xác minh và trả về đúng 24 checkpoint C theo thứ tự cấu hình rồi seed."""
    expected = [
        f'{variant}__V1__s{seed}'
        for variant in C_VARIANTS
        for seed in C_SEEDS
    ]
    summaries = {split: read_summary(split) for split in ('val', 'test')}
    problems: list[str] = []
    for trial_id in expected:
        val = summaries['val'].get(trial_id)
        test = summaries['test'].get(trial_id)
        if val is None or test is None:
            missing = [name for name, row in (('val', val), ('test', test)) if row is None]
            problems.append(f'{trial_id}: thiếu summary {"/".join(missing)}')
            continue
        for field in ('variant_id', 'architecture', 'seed', 'config_sha256', 'model_sha256'):
            if not val.get(field) or not test.get(field):
                problems.append(f'{trial_id}: thiếu {field} trong Val/Test summary')
            elif val[field] != test[field]:
                problems.append(f'{trial_id}: {field} khác nhau giữa Val và Test')
    if problems:
        raise RuntimeError(
            'Không thể khóa plan 24 checkpoint C:\n- ' + '\n- '.join(problems)
        )
    return expected


def registered_c_hashes() -> dict[str, str]:
    """Đọc SHA checkpoint từ summary Test chuẩn của bước C."""
    path = ROOT / 'results' / 'test_summary.csv'
    if not path.is_file():
        return {}
    with path.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    return {
        row['trial_id']: row['model_sha256']
        for row in rows
        if row.get('trial_id') and row.get('model_sha256')
    }


def write_plan_csv(payload: dict) -> None:
    """Xuất ma trận checkpoint × method để kiểm tra trước khi chạy D1."""
    rows = []
    for trial in payload['trials']:
        for method in payload['methods']:
            rows.append({
                'priority_rank': trial['priority_rank'],
                'model_role': trial['model_role'],
                'trial_id': trial['trial_id'],
                'variant_id': trial['variant_id'],
                'architecture': trial['architecture'],
                'seed': trial['seed'],
                'method_id': method['method_id'],
                'training_mode': method['training_mode'],
                'integer_mode': method['integer_mode'],
                'input_shape': 'x'.join(str(value) for value in trial['input_shape']),
                'parameter_count': trial['parameter_count'],
                'source_model_sha256': trial['model_sha256'],
                'status': 'PLANNED',
            })
    write_csv(
        D_RESULTS / 'quantization_plan.csv',
        rows,
        [
            'priority_rank', 'model_role', 'trial_id', 'variant_id',
            'architecture', 'seed', 'method_id', 'training_mode',
            'integer_mode', 'input_shape', 'parameter_count',
            'source_model_sha256', 'status',
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument(
        '--trials', nargs='+',
        help=(
            'Một hoặc nhiều trial_id theo thứ tự ưu tiên; mặc định dùng '
            'primary, technical control, baseline và pre_0 seed 44'
        ),
    )
    scope.add_argument(
        '--all-c-checkpoints', action='store_true',
        help='Dùng đúng 24 checkpoint: 8 cấu hình C × seed 42/43/44',
    )
    parser.add_argument('--representative-per-class', type=int, default=50)
    parser.add_argument('--representative-seed', type=int, default=42)
    parser.add_argument('--qat-epochs', type=int, default=15)
    parser.add_argument('--qat-batch-size', type=int, default=32)
    parser.add_argument('--qat-learning-rate', type=float, default=1e-5)
    parser.add_argument('--qat-patience', type=int, default=5)
    parser.add_argument(
        '--force-plan', action='store_true',
        help='Ghi kế hoạch mới nếu quantization_plan.json hiện tại khác',
    )
    args = parser.parse_args()
    if args.representative_per_class < 1 or args.representative_seed < 0:
        parser.error('Representative count/seed không hợp lệ')
    if args.qat_epochs < 1 or args.qat_batch_size < 1 or args.qat_learning_rate <= 0:
        parser.error('Ngân sách QAT không hợp lệ')
    if args.qat_patience < 1:
        parser.error('qat-patience phải >= 1')

    default_scope = default_quantization_trials() if not args.trials else []
    if args.trials:
        try:
            default_scope = default_quantization_trials()
        except FileNotFoundError:
            # Vẫn cho phép phạm vi explicit khi registry D không còn tại máy.
            default_scope = []
    default_roles = {
        str(row['trial_id']): str(row['model_role']) for row in default_scope
    }
    if args.all_c_checkpoints:
        trials = all_c_checkpoint_trials()
    else:
        trials = args.trials or [str(row['trial_id']) for row in default_scope]
    if len(trials) != len(set(trials)):
        parser.error('--trials chứa trial_id trùng')
    methods = load_methods(enabled_only=True)
    c_hashes = registered_c_hashes()
    audited = []
    for priority_rank, trial in enumerate(trials, start=1):
        entry = audit_trial(trial)
        if trial in c_hashes and c_hashes[trial] != entry['model_sha256']:
            raise RuntimeError(f'{trial}: checkpoint khác hash đã đánh giá trong bước C')
        entry['registered_in_c'] = trial in c_hashes
        entry['priority_rank'] = priority_rank
        entry['model_role'] = default_roles.get(
            trial,
            'C_FULL_MATRIX' if args.all_c_checkpoints else 'EXPLICIT',
        )
        audited.append(entry)

    payload = {
        'schema_version': 2,
        'stage': 'D_QUANTIZATION_PLAN',
        'generated_utc': utc_now(),
        # Full-C cần đọc registry Test đã tồn tại để chứng minh đúng 24 checkpoint;
        # D0 không đọc WAV/prediction và không dùng metric để xếp hạng lại model.
        'test_accessed': bool(args.all_c_checkpoints),
        'test_access_scope': (
            'historical summary identity/config/model SHA only'
            if args.all_c_checkpoints else 'none'
        ),
        'selection_rule': 'Quantization calibration uses Train only; QAT uses Train and Validation only',
        'threshold_p_non_asthma': 0.5,
        'method_config_path': str(METHOD_CONFIG.resolve()),
        'method_config_sha256': sha256_file(METHOD_CONFIG),
        'methods': [
            {
                'method_id': row['method_id'],
                **METHOD_SPECS[row['method_id']],
                'description': row.get('description', ''),
            }
            for row in methods
        ],
        'settings': {
            'representative_per_class': args.representative_per_class,
            'representative_seed': args.representative_seed,
            'qat_epochs': args.qat_epochs,
            'qat_batch_size': args.qat_batch_size,
            'qat_learning_rate': args.qat_learning_rate,
            'qat_patience': args.qat_patience,
        },
        'trials': audited,
        'notes': [
            'PTQ representative samples are balanced and selected only from Train.',
            'QAT never reads Test and uses the frozen FP32 checkpoint as initialization.',
            'QAT is provided only for full INT8; INT16x8 remains a PTQ comparison branch.',
            'INT16x8 is not a drop-in replacement for firmware that assumes INT8 input/output.',
            'Full-C scope reads historical Val/Test summary identity and SHA only; it does not rank checkpoints by Test metrics.',
        ],
    }
    payload['plan_sha256'] = sha256_json(payload)
    if PLAN_PATH.is_file() and not args.force_plan:
        current = json.loads(PLAN_PATH.read_text(encoding='utf-8'))
        current_compare = {k: v for k, v in current.items() if k not in ('generated_utc', 'plan_sha256')}
        new_compare = {k: v for k, v in payload.items() if k not in ('generated_utc', 'plan_sha256')}
        if current_compare == new_compare:
            D_RESULTS.mkdir(parents=True, exist_ok=True)
            write_plan_csv(current)
            print(f'KẾ HOẠCH D ĐÃ TỒN TẠI VÀ KHỚP: {PLAN_PATH}')
            return

        # Cho phép tái sử dụng output từng mang nhãn E sau khi đổi tên workflow
        # thành D, miễn phạm vi checkpoint/method và mọi SHA nguồn vẫn giống hệt.
        def operational_signature(plan: dict) -> dict:
            return {
                'settings': plan.get('settings'),
                'methods': [
                    (row.get('method_id'), row.get('training_mode'), row.get('integer_mode'))
                    for row in plan.get('methods', [])
                ],
                'trials': [
                    (
                        row.get('trial_id'), row.get('model_sha256'),
                        row.get('config_sha256'), row.get('train_feature_sha256'),
                        row.get('val_feature_sha256'),
                    )
                    for row in plan.get('trials', [])
                ],
            }

        if operational_signature(current) == operational_signature(payload):
            D_RESULTS.mkdir(parents=True, exist_ok=True)
            write_plan_csv(current)
            print(
                'KẾ HOẠCH LƯỢNG TỬ CŨ ĐÃ ĐƯỢC TÁI SỬ DỤNG SAU KHI ĐỔI E → D; '
                'SHA artifact không thay đổi.'
            )
            print(f'Plan: {PLAN_PATH}')
            return
        raise FileExistsError(
            f'{PLAN_PATH} đã tồn tại với nội dung khác; kiểm tra rồi dùng --force-plan nếu chủ động đổi kế hoạch.'
        )
    D_RESULTS.mkdir(parents=True, exist_ok=True)
    atomic_json(PLAN_PATH, payload)
    write_plan_csv(payload)
    print(f'ĐÃ KHÓA KẾ HOẠCH D: {PLAN_PATH}')
    print('Trials :', ', '.join(trials))
    print('Methods:', ', '.join(row['method_id'] for row in methods))
    print(f'Matrix : {len(trials)} checkpoint × {len(methods)} method = {len(trials) * len(methods)} model lượng tử')
    print(f'CSV    : {D_RESULTS / "quantization_plan.csv"}')
    if args.all_c_checkpoints:
        print('Historical Test: chỉ đọc registry identity/SHA của C; không đọc WAV/prediction, không xếp hạng lại model.')
    else:
        print('Test chưa được truy cập.')


if __name__ == '__main__':
    main()
