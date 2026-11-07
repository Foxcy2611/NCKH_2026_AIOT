"""D1 - tạo các model TFLite PTQ/QAT đã đăng ký trong kế hoạch D0.

Calibration chỉ dùng Train. QAT dùng Train + Validation và khởi tạo từ đúng
checkpoint FP32 của trial. Script không đọc Test và chưa xuất header firmware.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import numpy as np

from d_quantization_core import (
    D_ARTIFACTS, D_RESULTS, METHOD_SPECS, PLAN_PATH, atomic_json,
    convert_integer_model, inspect_tflite, load_d_plan, load_split,
    representative_indices, save_binary, sha256_file, sha256_json,
    train_qat_model, trial_paths, utc_now, verify_trial_against_plan,
    write_csv,
)
from frontend_core import read_json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')


def method_dir(trial: str, method: str) -> Path:
    return D_ARTIFACTS / trial / 'methods' / method


def completed_and_current(trial: str, method: str, plan_hash: str) -> bool:
    directory = method_dir(trial, method)
    model_path = directory / f'{method}.tflite'
    metadata_path = directory / 'conversion_metadata.json'
    if not model_path.is_file() or not metadata_path.is_file():
        return False
    metadata = read_json(metadata_path)
    return (
        metadata.get('plan_sha256') == plan_hash
        and metadata.get('tflite_sha256') == sha256_file(model_path)
        and metadata.get('status') == 'CONVERSION_COMPLETE'
    )


def write_conversion_summary(plan: dict) -> None:
    """Tổng hợp trạng thái và đường dẫn TFLite của toàn bộ job trong plan."""
    rows = []
    for entry in plan['trials']:
        for method in plan['methods']:
            method_id = method['method_id']
            directory = method_dir(entry['trial_id'], method_id)
            model_path = directory / f'{method_id}.tflite'
            metadata_path = directory / 'conversion_metadata.json'
            status = 'MISSING'
            metadata = {}
            if metadata_path.is_file():
                metadata = read_json(metadata_path)
                status = (
                    'COMPLETE'
                    if model_path.is_file()
                    and metadata.get('status') == 'CONVERSION_COMPLETE'
                    and metadata.get('plan_sha256') == plan['plan_sha256']
                    and metadata.get('tflite_sha256') == sha256_file(model_path)
                    else 'STALE_OR_INVALID'
                )
            io = metadata.get('io', {})
            rows.append({
                'priority_rank': entry['priority_rank'],
                'model_role': entry['model_role'],
                'trial_id': entry['trial_id'],
                'variant_id': entry['variant_id'],
                'method_id': method_id,
                'training_mode': method['training_mode'],
                'integer_mode': method['integer_mode'],
                'status': status,
                'tflite_path': str(model_path.resolve()) if model_path.is_file() else '',
                'tflite_size_bytes': metadata.get('tflite_size_bytes', ''),
                'input_dtype': io.get('input', {}).get('dtype', ''),
                'output_dtype': io.get('output', {}).get('dtype', ''),
                'tflite_sha256': metadata.get('tflite_sha256', ''),
                'source_model_sha256': entry['model_sha256'],
            })
    write_csv(
        D_RESULTS / 'conversion_summary.csv',
        rows,
        [
            'priority_rank', 'model_role', 'trial_id', 'variant_id',
            'method_id', 'training_mode', 'integer_mode', 'status',
            'tflite_path', 'tflite_size_bytes', 'input_dtype',
            'output_dtype', 'tflite_sha256', 'source_model_sha256',
        ],
    )


def save_conversion(
    trial_entry: dict,
    method: str,
    data: bytes,
    rep_indices: np.ndarray,
    labels: np.ndarray,
    plan: dict,
    tf,
    qat_info: dict | None = None,
) -> None:
    directory = method_dir(trial_entry['trial_id'], method)
    model_path = directory / f'{method}.tflite'
    metadata_path = directory / 'conversion_metadata.json'
    save_binary(model_path, data)
    io = inspect_tflite(model_path)
    spec = METHOD_SPECS[method]
    expected_dtype = 'int8' if spec['integer_mode'] == 'INT8' else 'int16'
    if io['input']['dtype'] != expected_dtype or io['output']['dtype'] != expected_dtype:
        raise RuntimeError(
            f'{method}: converter không tạo full {expected_dtype} input/output: {io}'
        )
    selected_labels = labels[rep_indices]
    metadata = {
        'schema_version': 1,
        'status': 'CONVERSION_COMPLETE',
        'generated_utc': utc_now(),
        'trial_id': trial_entry['trial_id'],
        'variant_id': trial_entry['variant_id'],
        'method_id': method,
        **spec,
        'plan_path': str(PLAN_PATH.resolve()),
        'plan_sha256': plan['plan_sha256'],
        'source_model_sha256': trial_entry['model_sha256'],
        'source_training_metadata_sha256': trial_entry['training_metadata_sha256'],
        'tflite_path': str(model_path.resolve()),
        'tflite_sha256': sha256_file(model_path),
        'tflite_size_bytes': model_path.stat().st_size,
        'representative_count': int(len(rep_indices)),
        'representative_class_counts': {
            '0': int(np.sum(selected_labels == 0)),
            '1': int(np.sum(selected_labels == 1)),
        },
        'representative_indices_sha256': hashlib.sha256(rep_indices.tobytes()).hexdigest(),
        'representative_source': 'normalized Train features only',
        'normalization': {
            'method': 'minmax_train_only_then_float32',
            'train_min': trial_entry['train_min'],
            'train_max': trial_entry['train_max'],
        },
        'input_shape': trial_entry['input_shape'],
        'io': io,
        'tensorflow_version': tf.__version__,
        'numpy_version': np.__version__,
        'test_accessed': False,
        'qat': qat_info,
    }
    atomic_json(metadata_path, metadata)
    print(f'  HOÀN TẤT {method}: {model_path.name} ({model_path.stat().st_size:,} bytes)')


def convert_trial(entry: dict, methods: list[str], plan: dict, force: bool) -> None:
    import tensorflow as tf

    current = verify_trial_against_plan(entry)
    trial = entry['trial_id']
    pending = [
        method for method in methods
        if force or not completed_and_current(trial, method, plan['plan_sha256'])
    ]
    skipped = [method for method in methods if method not in pending]
    for method in skipped:
        print(f'  BỎ QUA {trial}/{method}: artifact đã đầy đủ và đúng plan')
    if not pending:
        return

    tf.keras.backend.clear_session()
    tf.keras.utils.set_random_seed(int(current['seed']))
    np.random.seed(int(current['seed']))
    paths = trial_paths(trial)
    model = tf.keras.models.load_model(paths['model'], compile=False)
    if list(model.input_shape[1:]) != current['input_shape']:
        raise ValueError(f'{trial}: Keras input shape không khớp metadata')
    x_train, y_train, _ = load_split(trial, 'train')
    indices = representative_indices(
        y_train,
        int(plan['settings']['representative_per_class']),
        int(plan['settings']['representative_seed']),
    )
    print(f'\n{trial}: Train={len(y_train)}, representative={len(indices)}, pending={pending}')

    for method in [name for name in pending if METHOD_SPECS[name]['training_mode'] == 'PTQ']:
        data = convert_integer_model(
            model, x_train, indices, METHOD_SPECS[method]['integer_mode']
        )
        save_conversion(current, method, data, indices, y_train, plan, tf)

    qat_methods = [name for name in pending if METHOD_SPECS[name]['training_mode'] == 'QAT']
    if qat_methods:
        x_val, y_val, _ = load_split(trial, 'val')
        qat_dir = D_ARTIFACTS / trial / 'qat'
        existing_qat_outputs = list(qat_dir.glob('*')) if qat_dir.is_dir() else []
        if existing_qat_outputs and not force:
            raise FileExistsError(
                f'{qat_dir} đã có QAT artifact nhưng còn method QAT chưa hoàn tất. '
                'Bật toàn bộ method QAT cần khảo sát trong cùng lần chạy hoặc dùng --force sau khi kiểm tra.'
            )
        qat_model, history, saved_model, bridge_diff, class_weights = train_qat_model(
            model, x_train, y_train, x_val, y_val, qat_dir, plan['settings']
        )
        losses = history.history.get('val_loss', [])
        qat_info = {
            'fake_quant_semantics': 'INT8-aware selective QAT',
            'epochs_completed': len(losses),
            'best_epoch': int(np.argmin(losses) + 1) if losses else None,
            'best_val_loss': float(np.min(losses)) if losses else None,
            'bridge_max_abs_diff': bridge_diff,
            'class_weights': class_weights,
            'saved_qat_model': str(saved_model.resolve()) if saved_model else None,
        }
        atomic_json(qat_dir / 'QAT_Metadata.json', {
            **qat_info,
            'trial_id': trial,
            'plan_sha256': plan['plan_sha256'],
            'source_model_sha256': current['model_sha256'],
            'generated_utc': utc_now(),
            'test_accessed': False,
        })
        for method in qat_methods:
            data = convert_integer_model(
                qat_model, x_train, indices, METHOD_SPECS[method]['integer_mode']
            )
            save_conversion(current, method, data, indices, y_train, plan, tf, qat_info)

    del model, x_train
    tf.keras.backend.clear_session()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial-id', help='Chỉ chạy một trial đã đăng ký trong D0')
    parser.add_argument('--method', choices=tuple(METHOD_SPECS), help='Chỉ chạy một method đã đăng ký')
    parser.add_argument(
        '--force', action='store_true',
        help='Chủ động tạo lại artifact method/QAT hiện có; không dùng nếu chưa kiểm tra output cũ',
    )
    args = parser.parse_args()
    try:
        import tensorflow as tf
    except ImportError as exc:
        raise SystemExit('Thiếu TensorFlow trong môi trường lượng tử hóa') from exc

    plan = load_d_plan()
    registered_methods = [row['method_id'] for row in plan['methods']]
    if args.method and args.method not in registered_methods:
        parser.error(f'{args.method} chưa được đăng ký trong quantization_plan.json')
    selected_methods = [args.method] if args.method else registered_methods
    selected_trials = [
        row for row in plan['trials']
        if args.trial_id is None or row['trial_id'] == args.trial_id
    ]
    if not selected_trials:
        parser.error(f'Không tìm thấy trial đã đăng ký: {args.trial_id}')
    print(f'TensorFlow: {tf.__version__}')
    print('Methods   :', ', '.join(selected_methods))
    for entry in selected_trials:
        convert_trial(entry, selected_methods, plan, args.force)
    write_conversion_summary(plan)
    print(f'CSV       : {D_RESULTS / "conversion_summary.csv"}')
    print('\nD1 HOÀN TẤT - chưa truy cập Test, chưa sửa firmware.')


if __name__ == '__main__':
    main()
