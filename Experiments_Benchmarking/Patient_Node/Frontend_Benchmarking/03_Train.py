"""Huấn luyện model cho từng Front-End candidate đã được bật trong plan.

Tác dụng:
- Đọc tensor Train/Validation do ``02_Preprocess.py`` tạo.
- Normalize theo min/max của Train và giữ nguyên scaler cho Validation.
- Nạp hàm ``build_and_compile_model(input_shape)`` từ architecture builder.
- Train, lưu checkpoint tốt nhất, history và metadata truy vết.

Đầu vào chính: ``--architecture``, ``--builder-path``, ``--variant`` và seed/budget.
Đầu ra: ``artifacts/models/<variant>__<architecture>__s<seed>/``.
Giữ nguyên liên kết: ``results/experiment_plan.csv`` và ``configs/candidates.csv``
  (đọc qua ``frontend_core.enabled_plans``), ``artifacts/features/<variant>/``,
  ``history.csv`` và ``training_metadata.json``; KHÔNG đọc Test.
Cảnh báo: đây là script duy nhất trong chuỗi chính thực hiện huấn luyện model.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
from datetime import datetime, timezone
import sys
import time
from pathlib import Path

# Match Training_Model.py (V1): disable oneDNN before TensorFlow import.
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from frontend_core import (
    ARTIFACTS,
    RESULTS,
    default_builder_path,
    enabled_plans,
    plans,
    split_fingerprint,
    read_json,
    trial_id,
    write_json,
)


# Versioned recipe ID: older checkpoints must not be silently reused.
TRAINING_RECIPE_ID = 'V1_phase2_exact_float64_raw_float32_after_normalize_v2'


def builder_from(path: Path):
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    spec = importlib.util.spec_from_file_location(
        f'benchmark_builder_{hashlib.md5(str(path).encode()).hexdigest()}',
        path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fun = getattr(module, 'build_and_compile_model', None)
    if not callable(fun):
        raise AttributeError(f'{path} must implement build_and_compile_model(input_shape)')
    return fun, hashlib.sha256(path.read_bytes()).hexdigest()


def train_one(row, args, tf, builder, builderhash):
    variant = row['variant_id']
    tid = trial_id(variant, args.architecture, args.seed)
    feats = ARTIFACTS / 'features' / variant
    required_features = [
        feats / f'{kind}_{split}.npy'
        for split in ('train', 'val')
        for kind in ('X', 'Y', 'Files')
    ] + [feats / f'{split}_metadata.json' for split in ('train', 'val')]
    missing_features = [str(path) for path in required_features if not path.is_file()]
    if missing_features:
        raise FileNotFoundError(
            f'03_Train.py thiếu artifact của variant {variant}:\n- '
            + '\n- '.join(missing_features)
            + '\nHãy chạy lại 02_Preprocess.py cho variant này.'
        )

    metadatas = {}
    for split in ('train','val'):
        m = read_json(feats / f'{split}_metadata.json')
        if m['config_sha256'] != row['config_sha256']:
            raise ValueError('Stale feature hash for ' + variant)
        from pathlib import Path as _Path

        if m.get('dataset_fingerprint') != split_fingerprint(
            _Path(m['dataset_root']), split
        ):
            raise ValueError('Source WAV dataset changed since preprocessing: ' + split)
        metadatas[split] = m
    if metadatas['train']['dataset_root'] != metadatas['val']['dataset_root']:
        raise ValueError('Train/Val from different datasets')
    if variant == 'F0' and not all(
        metadatas[split].get('phase2_f0_parity') is True
        for split in ('train', 'val')
    ):
        raise ValueError(
            'F0 chưa qua kiểm tra parity với artifact Phase 2. '
            'Chạy lại 02_Preprocess.py --variant F0 --force.'
        )

    # Original V1 normalization semantics:
    # load preserving dtype, compute min/max on Train, then cast normalized X to float32.
    X_raw = np.load(feats / 'X_train.npy')
    y_raw = np.load(feats / 'Y_train.npy')
    V_raw = np.load(feats / 'X_val.npy')
    vy_raw = np.load(feats / 'Y_val.npy')
    if len(X_raw) != len(y_raw) or len(V_raw) != len(vy_raw):
        raise ValueError('Feature/label lengths mismatch in Train or Validation')
    if not np.isfinite(X_raw).all() or not np.isfinite(V_raw).all():
        raise ValueError('Train/Val feature contains NaN or Inf')
    if not set(np.unique(y_raw)).issubset({0, 1}) or not set(np.unique(vy_raw)).issubset({0, 1}):
        raise ValueError('Unexpected class labels')
    if set(np.unique(y_raw)) != {0, 1}:
        raise ValueError('Train needs both classes')
    amin = float(np.min(X_raw))
    amax = float(np.max(X_raw))
    if amax <= amin:
        raise ValueError('Train feature scaling range invalid')
    X = ((X_raw - amin) / (amax - amin)).astype(np.float32)
    V = ((V_raw - amin) / (amax - amin)).astype(np.float32)
    y = y_raw.astype(np.float32)
    vy = vy_raw.astype(np.float32)

    trial = ARTIFACTS / 'models' / tid
    ckpt = trial / 'Model_Asthma.keras'
    metadata = trial / 'training_metadata.json'
    history_path = trial / 'history.csv'
    model_outputs = (ckpt, metadata, history_path)
    if trial.is_dir() and any(trial.iterdir()):
        if not args.force and all(path.is_file() for path in model_outputs):
            prev = read_json(metadata)
            if (
                prev.get('training_recipe_id') == TRAINING_RECIPE_ID
                and prev.get('op_determinism_enabled') == args.enable_op_determinism
                and prev['config_sha256'] == row['config_sha256']
                and prev['builder_sha256'] == builderhash
                and prev['seed'] == args.seed
                and prev['epochs_requested'] == args.epochs
                and prev['batch_size'] == args.batch_size
            ):
                print(f'BỎ QUA {tid}: checkpoint theo recipe mới đã đầy đủ')
                return
        if not args.force:
            raise RuntimeError(
                f'{tid} đã có output (có thể dùng training recipe cũ). '
                'Sao lưu dữ liệu trước, rồi chạy lại với --force; '
                'script sẽ TỰ LƯU toàn bộ thư mục trial cũ sang artifacts/models/_archive/.'
            )
        # Do not destroy checkpoints, predictions, confusion or CSVs from a prior run.
        archive_dir = ARTIFACTS / 'models' / '_archive'
        archive_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        archived = archive_dir / f'{tid}__{stamp}'
        trial.rename(archived)
        print(f'BACKUP OLD TRIAL: {archived}')
        print('NOTE: Existing results/val_summary.csv entry will be replaced only after 04_Evaluate.py runs.')
    trial.mkdir(parents=True, exist_ok=True)

    # clear_session is necessary for independent successive candidate trials.
    # It does not change the builder architecture; seed is reset per model.
    tf.keras.backend.clear_session()
    tf.keras.utils.set_random_seed(args.seed)
    determinism_enabled = False
    if args.enable_op_determinism:
        # Explicit opt-in only: V1 original does NOT call this.
        tf.config.experimental.enable_op_determinism()
        determinism_enabled = True
    model = builder(X.shape[1:])
    if tuple(model.input_shape[1:]) != tuple(X.shape[1:]):
        raise ValueError(f'Architecture input mismatch: {model.input_shape} != {X.shape}')
    from sklearn.utils.class_weight import compute_class_weight

    labels = np.unique(y).astype(int)
    weights = compute_class_weight(class_weight='balanced', classes=labels, y=y.astype(int))
    weight_map = {int(k): float(v) for k, v in zip(labels, weights)}
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=10,
            mode='min',
            restore_best_weights=True,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=.5,
            patience=5,
            min_lr=1e-6,
            mode='min',
            verbose=1,
        ),
        tf.keras.callbacks.ModelCheckpoint(
            str(ckpt),
            monitor='val_loss',
            mode='min',
            save_best_only=True,
            verbose=1,
        ),
        tf.keras.callbacks.CSVLogger(str(history_path), separator=',', append=False),
        tf.keras.callbacks.TensorBoard(log_dir=str(trial / 'logs'), histogram_freq=1),
        tf.keras.callbacks.TerminateOnNaN(),
    ]
    print('\n' + '=' * 60)
    print('START TRAIN:', tid)
    print(f'Train={len(y)} | Validation={len(vy)} | Input={tuple(X.shape[1:])}')
    print(f'Params={model.count_params()} | Seed={args.seed} | Epochs<={args.epochs} | Batch={args.batch_size}')
    print(f'Raw feature dtypes: train={X_raw.dtype}, val={V_raw.dtype}; normalized=float32')
    print(f'TRAIN_MIN={amin}, TRAIN_MAX={amax}')
    print(f'TF_ENABLE_ONEDNN_OPTS={os.environ["TF_ENABLE_ONEDNN_OPTS"]} | op_determinism={determinism_enabled}')
    print(f'Class weights: {weight_map}')
    print(f'Training recipe: {TRAINING_RECIPE_ID}')
    model.summary()
    print('=' * 60)
    start = time.perf_counter()
    history = model.fit(
        X,
        y,
        validation_data=(V, vy),
        epochs=args.epochs,
        batch_size=args.batch_size,
        callbacks=callbacks,
        class_weight=weight_map,
        shuffle=True,
        verbose=1,
    )
    best = int(np.argmin(history.history['val_loss']))
    write_json(
        metadata,
        {
            'training_recipe_id': TRAINING_RECIPE_ID,
            'training_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'normalization_method': 'minmax_train_only_then_float32',
            'preprocess_protocol': row['protocol'],
            'phase2_f0_parity': bool(
                variant == 'F0'
                and metadatas['train'].get('phase2_f0_parity')
                and metadatas['val'].get('phase2_f0_parity')
            ),
            'raw_train_dtype': str(X_raw.dtype),
            'raw_val_dtype': str(V_raw.dtype),
            'tf_enable_onednn_opts': os.environ['TF_ENABLE_ONEDNN_OPTS'],
            'op_determinism_enabled': determinism_enabled,
            'keras_clear_session_before_build': True,
            'trial_id': tid,
            'variant_id': variant,
            'architecture': args.architecture,
            'builder_path': str(args.builder_path),
            'builder_sha256': builderhash,
            'config_sha256': row['config_sha256'],
            'seed': args.seed,
            'train_min': amin,
            'train_max': amax,
            'parameter_count': int(model.count_params()),
            'input_shape': list(X.shape[1:]),
            'epochs_requested': args.epochs,
            'epochs_completed': len(history.history['val_loss']),
            'best_epoch': best + 1,
            'best_val_loss': float(history.history['val_loss'][best]),
            'batch_size': args.batch_size,
            'train_seconds': time.perf_counter() - start,
            'class_weights': weight_map,
            'dataset_root': metadatas['train']['dataset_root'],
            'train_fingerprint': metadatas['train']['dataset_fingerprint'],
            'val_fingerprint': metadatas['val']['dataset_fingerprint'],
            'tensorflow_version': tf.__version__,
            'status': 'VALIDATION_CHECKPOINT',
            'test_used_for_training': False,
        },
    )
    print('TRAINED', tid, 'best epoch', best + 1)
    print(f'History: {history_path}')
    print(f'Checkpoint: {ckpt}')
    print('NOTE: 03_Train.py chi luu model va history; khong tao Confusion Matrix trong buoc train.')
    print('NOTE: Sau khi train, chay Validation Evaluate de in va luu Classification Report:')
    print(
        f'python 04_Evaluate.py --architecture {args.architecture} '
        f'--variant {variant} --seed {args.seed} --split val'
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--architecture', default='V1')
    p.add_argument('--builder-path')
    p.add_argument('--variant')
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--epochs', type=int, default=100)
    p.add_argument('--batch-size', type=int, default=32)
    p.add_argument('--force', action='store_true',
                   help='Archive prior trial artifacts then retrain; never silently overwrite.')
    p.add_argument('--enable-op-determinism', action='store_true',
                   help='Opt in (V1 original did not enable operation determinism).')
    args = p.parse_args()

    if args.epochs < 1 or args.batch_size < 1:
        p.error('Invalid training budget')
    if args.architecture != 'V1' and not args.builder_path:
        p.error('Architecture != V1 requires explicit --builder-path to prevent mislabeling a V1 model')
    args.builder_path = (
        Path(args.builder_path).expanduser().resolve()
        if args.builder_path
        else default_builder_path().resolve()
    )
    try:
        import tensorflow as tf
    except ImportError as exc:
        raise SystemExit(
            'TensorFlow not installed: use the exact V1 train environment'
        ) from exc

    builder, builderhash = builder_from(args.builder_path)

    if args.variant:
        # Khi người dùng chỉ rõ một variant, cho phép huấn luyện đúng variant đó
        # dù nó đang enabled=0 trong lịch chạy hàng loạt. Cách này hữu ích khi bổ
        # sung seed cho một thí nghiệm đã hoàn tất mà không cần sửa candidates.csv
        # rồi dựng lại toàn bộ experiment plan. Config SHA vẫn được plans() kiểm tra.
        selected = [
            row for row in plans()
            if row['variant_id'] == args.variant
        ]
        if len(selected) != 1:
            p.error(
                f'Cần đúng một variant={args.variant} trong experiment_plan.csv; '
                f'hiện tìm thấy {len(selected)}'
            )
    else:
        selected = enabled_plans()

    for row in selected:
        train_one(row, args, tf, builder, builderhash)


if __name__ == '__main__':
    main()
