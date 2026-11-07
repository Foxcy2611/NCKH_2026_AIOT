"""Tiện ích dùng chung cho bước D - lượng tử hóa và chuẩn bị triển khai.

Module thao tác trên checkpoint/feature đã tồn tại của Frontend. Calibration
luôn lấy từ Train; QAT dùng Train + Validation. Historical Test chỉ được đọc qua
`load_split(..., "test")`, sau khi fingerprint đã được đối chiếu với summary C.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from frontend_core import (
    ARTIFACTS, RESULTS, ROOT, dataset_root, list_split, load_config,
    load_raw_window, mel_from_wave, plans, process_wave, read_json,
    split_fingerprint,
)

os.environ.setdefault('TF_ENABLE_ONEDNN_OPTS', '0')
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')

def _namespace_from_env(variable: str, default: str) -> str:
    """Đọc tên vùng output, không cho phép đường dẫn thoát khỏi thư mục dự án."""
    value = os.environ.get(variable, default).strip()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', value):
        raise ValueError(
            f'{variable} chỉ được chứa chữ, số, dấu gạch dưới, chấm hoặc gạch ngang'
        )
    return value


# Mặc định vẫn dùng đúng vùng D hiện hành. Biến môi trường chỉ phục vụ các phép
# thử bổ sung (ví dụ kiến trúc V2) cần tái sử dụng nguyên pipeline D0-D2 nhưng
# không được làm thay đổi plan_sha256 và report của ma trận 24 checkpoint V1.
D_NAMESPACE = _namespace_from_env(
    'NCKH_D_QUANTIZATION_NAMESPACE', 'D_Quantization'
)
D_DEPLOY_NAMESPACE = _namespace_from_env(
    'NCKH_D_DEPLOYMENT_NAMESPACE', 'D_Deployment'
)
D_RESULTS = RESULTS / D_NAMESPACE
D_ARTIFACTS = ARTIFACTS / D_NAMESPACE
D_DEPLOY = ARTIFACTS / D_DEPLOY_NAMESPACE
METHOD_CONFIG = ROOT / 'configs' / 'D_quantization_methods.csv'
PLAN_PATH = D_RESULTS / 'quantization_plan.json'

METHOD_SPECS = {
    'PTQ_INT8': {'training_mode': 'PTQ', 'integer_mode': 'INT8', 'experimental': False},
    'QAT_INT8': {'training_mode': 'QAT', 'integer_mode': 'INT8', 'experimental': False},
    'PTQ_INT16x8': {'training_mode': 'PTQ', 'integer_mode': 'INT16x8', 'experimental': False},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def sha256_json(value) -> str:
    blob = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + '.pending')
    pending.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    pending.replace(path)


def load_d_plan() -> dict:
    if not PLAN_PATH.is_file():
        raise FileNotFoundError('Chưa có kế hoạch D; chạy python D0_Build_Quantization_Plan.py')
    payload = read_json(PLAN_PATH)
    stored = payload.get('plan_sha256')
    unsigned = {key: value for key, value in payload.items() if key != 'plan_sha256'}
    if not stored or sha256_json(unsigned) != stored:
        raise RuntimeError('quantization_plan.json đã thay đổi sau khi tạo')
    if int(payload.get('schema_version', 0)) < 2 or any(
        'priority_rank' not in row or 'model_role' not in row
        for row in payload.get('trials', [])
    ):
        raise RuntimeError(
            'quantization_plan.json thuộc schema cũ; chạy '
            'python D0_Build_Quantization_Plan.py --force-plan để đăng ký '
            'đủ các checkpoint của kế hoạch D hiện tại.'
        )
    return payload


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + '.pending')
    with pending.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    pending.replace(path)


def safe_identifier(value: str) -> str:
    result = re.sub(r'[^A-Za-z0-9_]', '_', str(value))
    if not result or result[0].isdigit():
        result = 'm_' + result
    return result


def load_methods(enabled_only: bool = True) -> list[dict]:
    if not METHOD_CONFIG.is_file():
        raise FileNotFoundError(METHOD_CONFIG)
    with METHOD_CONFIG.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    ids = [row.get('method_id', '') for row in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(METHOD_SPECS):
        raise ValueError(
            'D_quantization_methods.csv phải chứa đúng một dòng cho mỗi method: '
            + ', '.join(METHOD_SPECS)
        )
    for row in rows:
        method = row['method_id']
        expected = METHOD_SPECS[method]
        if row.get('enabled') not in ('0', '1'):
            raise ValueError(f'{method}: enabled phải là 0 hoặc 1')
        if row.get('training_mode') != expected['training_mode']:
            raise ValueError(f'{method}: training_mode không khớp định nghĩa')
        if row.get('integer_mode') != expected['integer_mode']:
            raise ValueError(f'{method}: integer_mode không khớp định nghĩa')
        if int(row.get('experimental', '-1')) != int(expected['experimental']):
            raise ValueError(f'{method}: cờ experimental không khớp định nghĩa')
    selected = [row for row in rows if row['enabled'] == '1'] if enabled_only else rows
    if enabled_only and not selected:
        raise ValueError('Chưa bật method nào trong configs/D_quantization_methods.csv')
    return selected


def default_quantization_trials() -> list[dict[str, object]]:
    """Trả về bốn checkpoint được bàn giao từ phân tích C hiện hành.

    Danh sách này không còn phụ thuộc registry ``D_locked_20`` của quy trình cũ.
    Có thể ghi đè phạm vi bằng ``D0_Build_Quantization_Plan.py --trials ...``.
    """
    candidates = [
        ('PRIMARY', 'combo_pre0_mel40__V1__s43'),
        ('TECHNICAL_CONTROL', 'mel_40__V1__s43'),
        ('BASELINE', 'F0__V1__s43'),
        ('C_ADDITIONAL', 'pre_0__V1__s44'),
    ]
    return [
        {'priority_rank': rank, 'model_role': role, 'trial_id': trial_id}
        for rank, (role, trial_id) in enumerate(candidates, start=1)
    ]


def default_primary_trial() -> str:
    """Tương thích ngược cho code chỉ cần checkpoint chính."""
    return str(default_quantization_trials()[0]['trial_id'])


def trial_paths(trial: str) -> dict[str, Path]:
    model_dir = ARTIFACTS / 'models' / trial
    metadata_path = model_dir / 'training_metadata.json'
    model_path = model_dir / 'Model_Asthma.keras'
    if not metadata_path.is_file() or not model_path.is_file():
        raise FileNotFoundError(f'{trial}: thiếu Model_Asthma.keras hoặc training_metadata.json')
    metadata = read_json(metadata_path)
    if metadata.get('trial_id') != trial:
        raise ValueError(f'{trial}: trial_id trong training_metadata.json không khớp')
    variant = str(metadata.get('variant_id', ''))
    feature_dir = ARTIFACTS / 'features' / variant
    required = {
        'x_train': feature_dir / 'X_train.npy',
        'y_train': feature_dir / 'Y_train.npy',
        'files_train': feature_dir / 'Files_train.npy',
        'train_metadata': feature_dir / 'train_metadata.json',
        'x_val': feature_dir / 'X_val.npy',
        'y_val': feature_dir / 'Y_val.npy',
        'files_val': feature_dir / 'Files_val.npy',
        'val_metadata': feature_dir / 'val_metadata.json',
    }
    missing = [str(path) for path in required.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f'{trial}: thiếu feature Frontend:\n- ' + '\n- '.join(missing))
    return {
        'model_dir': model_dir,
        'model': model_path,
        'metadata': metadata_path,
        'feature_dir': feature_dir,
        **required,
    }


def audit_trial(trial: str) -> dict:
    paths = trial_paths(trial)
    metadata = read_json(paths['metadata'])
    train_meta = read_json(paths['train_metadata'])
    val_meta = read_json(paths['val_metadata'])
    variant = metadata['variant_id']
    plan_rows = [row for row in plans() if row['variant_id'] == variant]
    if len(plan_rows) != 1:
        raise ValueError(f'{trial}: không tìm thấy đúng một plan row cho {variant}')
    row = plan_rows[0]
    config = load_config(row)
    if metadata.get('config_sha256') != row['config_sha256']:
        raise ValueError(f'{trial}: config hash checkpoint không khớp experiment_plan.csv')
    if train_meta.get('config_sha256') != row['config_sha256'] or val_meta.get('config_sha256') != row['config_sha256']:
        raise ValueError(f'{trial}: config hash feature không khớp checkpoint')
    if metadata.get('train_fingerprint') != train_meta.get('dataset_fingerprint'):
        raise ValueError(f'{trial}: Train fingerprint không khớp')
    if metadata.get('val_fingerprint') != val_meta.get('dataset_fingerprint'):
        raise ValueError(f'{trial}: Validation fingerprint không khớp')
    if metadata.get('test_used_for_training') is not False:
        raise ValueError(f'{trial}: metadata không xác nhận Test chưa dùng để train')
    if metadata.get('normalization_method') != 'minmax_train_only_then_float32':
        raise ValueError(f'{trial}: normalization không đúng hợp đồng Frontend')
    train_min = float(metadata['train_min'])
    train_max = float(metadata['train_max'])
    if not math.isfinite(train_min) or not math.isfinite(train_max) or train_max <= train_min:
        raise ValueError(f'{trial}: train_min/train_max không hợp lệ')
    expected_shape = [config.n_mels, 1 + 80000 // config.hop_length, 1]
    if list(metadata.get('input_shape', [])) != expected_shape:
        raise ValueError(f'{trial}: input_shape không khớp cấu hình Frontend')
    return {
        'trial_id': trial,
        'variant_id': variant,
        'architecture': metadata['architecture'],
        'seed': int(metadata['seed']),
        'config_sha256': row['config_sha256'],
        'model_path': str(paths['model'].resolve()),
        'model_sha256': sha256_file(paths['model']),
        'training_metadata_path': str(paths['metadata'].resolve()),
        'training_metadata_sha256': sha256_file(paths['metadata']),
        'feature_dir': str(paths['feature_dir'].resolve()),
        'train_feature_sha256': sha256_file(paths['x_train']),
        'train_label_sha256': sha256_file(paths['y_train']),
        'val_feature_sha256': sha256_file(paths['x_val']),
        'val_label_sha256': sha256_file(paths['y_val']),
        'train_fingerprint': metadata['train_fingerprint'],
        'val_fingerprint': metadata['val_fingerprint'],
        'train_min': train_min,
        'train_max': train_max,
        'input_shape': expected_shape,
        'parameter_count': int(metadata['parameter_count']),
        'tensorflow_training_version': metadata.get('tensorflow_version'),
        'frontend_config': {
            'low_cut_hz': config.low_cut_hz,
            'high_cut_hz': config.high_cut_hz,
            'filter_order': config.filter_order,
            'pre_emphasis': config.pre_emphasis,
            'n_mels': config.n_mels,
            'hop_length': config.hop_length,
            'n_fft': config.n_fft,
        },
    }


def verify_trial_against_plan(entry: dict) -> dict:
    current = audit_trial(entry['trial_id'])
    keys = (
        'model_sha256', 'training_metadata_sha256', 'train_feature_sha256',
        'train_label_sha256', 'val_feature_sha256', 'val_label_sha256',
        'config_sha256', 'train_fingerprint', 'val_fingerprint',
    )
    changed = [key for key in keys if current.get(key) != entry.get(key)]
    if changed:
        raise RuntimeError(f'{entry["trial_id"]}: nguồn đã thay đổi sau D0: {changed}')
    return current


_TEST_RAW_CACHE: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}


def _load_historical_test_raw(trial: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Tái tạo Test Log-Mel và xác minh với summary chuẩn do bước C tạo."""
    paths = trial_paths(trial)
    metadata = read_json(paths['metadata'])
    variant = str(metadata['variant_id'])
    plan_rows = [row for row in plans() if row['variant_id'] == variant]
    if len(plan_rows) != 1:
        raise ValueError(f'{trial}: không tìm thấy đúng một config cho Test')
    config = load_config(plan_rows[0])
    root = dataset_root(metadata.get('dataset_root'))
    summary_path = RESULTS / 'test_summary.csv'
    if not summary_path.is_file():
        raise FileNotFoundError(
            'Thiếu results/test_summary.csv; hãy đồng bộ đủ checkpoint ở bước C trước khi chạy D.'
        )
    with summary_path.open(encoding='utf-8-sig', newline='') as stream:
        rows = [row for row in csv.DictReader(stream) if row.get('trial_id') == trial]
    if len(rows) != 1:
        raise RuntimeError(
            f'{trial}: cần đúng một dòng trong results/test_summary.csv, hiện có {len(rows)}'
        )
    summary_row = rows[0]
    expected_fingerprint = summary_row.get('dataset_fingerprint', '').strip()
    expected_model_hash = summary_row.get('model_sha256', '').strip()
    current_model_hash = sha256_file(paths['model'])
    if not expected_model_hash or expected_model_hash != current_model_hash:
        raise RuntimeError(f'{trial}: model SHA256 không khớp kết quả Test của bước C.')
    current_fingerprint = split_fingerprint(root, 'test')
    if not expected_fingerprint or current_fingerprint != expected_fingerprint:
        raise RuntimeError(
            'Test fingerprint không khớp kết quả chuẩn trong bước C.'
        )

    cache_key = f'{plan_rows[0]["config_sha256"]}:{current_fingerprint}'
    if cache_key in _TEST_RAW_CACHE:
        return _TEST_RAW_CACHE[cache_key]

    records = list_split(root, 'test')
    if len(records) != 159:
        raise RuntimeError(f'Historical Test phải có 159 WAV, hiện có {len(records)}')
    features = []
    labels = []
    files = []
    for path, label in records:
        mel = mel_from_wave(process_wave(load_raw_window(path), config), config)
        if mel.dtype != np.dtype('float64'):
            raise RuntimeError(
                f'{trial}: Test Log-Mel phải là float64, hiện là {mel.dtype}'
            )
        features.append(mel)
        labels.append(int(label))
        files.append(path.relative_to(root).as_posix())
    raw = np.stack(features, axis=0)[..., np.newaxis]
    labels_array = np.asarray(labels, dtype=np.int64)
    files_array = np.asarray(files, dtype=str)
    _TEST_RAW_CACHE[cache_key] = (raw, labels_array, files_array)
    return raw, labels_array, files_array


def load_split(trial: str, split: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if split not in ('train', 'val', 'test'):
        raise ValueError('Bước D chỉ hỗ trợ Train/Validation/Test')
    paths = trial_paths(trial)
    metadata = read_json(paths['metadata'])
    if split == 'test':
        raw, labels, files = _load_historical_test_raw(trial)
    else:
        raw = np.load(paths[f'x_{split}'])
        labels = np.load(paths[f'y_{split}']).astype(np.int64)
        files = np.load(paths[f'files_{split}'], allow_pickle=False)
    if len(raw) != len(labels) or len(files) != len(labels):
        raise ValueError(f'{trial}/{split}: X, Y, Files không cùng số mẫu')
    if str(raw.dtype) != 'float64':
        raise ValueError(f'{trial}/{split}: Log-Mel thô phải là float64, hiện là {raw.dtype}')
    if not np.isfinite(raw).all() or set(np.unique(labels)) != {0, 1}:
        raise ValueError(f'{trial}/{split}: feature/label không hợp lệ')
    lo, hi = float(metadata['train_min']), float(metadata['train_max'])
    normalized = ((raw - lo) / (hi - lo)).astype(np.float32)
    if not np.isfinite(normalized).all():
        raise ValueError(f'{trial}/{split}: normalized feature có NaN/Inf')
    return normalized, labels, files.astype(str)


def representative_indices(labels: np.ndarray, per_class: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    chosen: list[int] = []
    for label in (0, 1):
        candidates = np.flatnonzero(labels == label)
        if not len(candidates):
            raise ValueError(f'Train không có label {label}')
        amount = min(int(per_class), len(candidates))
        chosen.extend(rng.choice(candidates, size=amount, replace=False).tolist())
    result = np.asarray(chosen, dtype=np.int64)
    rng.shuffle(result)
    return result


def representative_generator(features: np.ndarray, indices: np.ndarray):
    def generate():
        for index in indices:
            yield [features[index:index + 1].astype(np.float32, copy=False)]
    return generate


def save_binary(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + '.pending')
    pending.write_bytes(data)
    pending.replace(path)


def convert_integer_model(model, features, indices, integer_mode: str) -> bytes:
    import tensorflow as tf

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_generator(features, indices)
    if integer_mode == 'INT8':
        converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
        converter.inference_input_type = tf.int8
        converter.inference_output_type = tf.int8
    elif integer_mode == 'INT16x8':
        converter.target_spec.supported_ops = [
            tf.lite.OpsSet.EXPERIMENTAL_TFLITE_BUILTINS_ACTIVATIONS_INT16_WEIGHTS_INT8
        ]
        converter.inference_input_type = tf.int16
        converter.inference_output_type = tf.int16
    else:
        raise ValueError(f'Không hỗ trợ integer_mode={integer_mode}')
    return converter.convert()


def _sanitize_layer_config(config: dict) -> dict:
    result = copy.deepcopy(config)
    for key in ('batch_shape', 'optional', 'quantization_config'):
        result.pop(key, None)
    dtype = result.get('dtype')
    if isinstance(dtype, dict):
        name = dtype.get('config', {}).get('name')
        if name:
            result['dtype'] = name
    return result


def build_qat_compatible_model(source_model, qat_keras):
    if source_model.__class__.__name__ != 'Sequential':
        raise NotImplementedError('QAT bridge hiện chỉ hỗ trợ Sequential model')
    input_shape = tuple(source_model.input_shape[1:])
    legacy = qat_keras.Sequential(name=f'{source_model.name}_qat_compatible')
    legacy.add(qat_keras.layers.InputLayer(input_shape=input_shape, dtype='float32'))
    for layer in source_model.layers:
        if layer.__class__.__name__ == 'InputLayer':
            continue
        try:
            rebuilt = qat_keras.layers.deserialize({
                'class_name': layer.__class__.__name__,
                'config': _sanitize_layer_config(layer.get_config()),
            })
        except Exception as exc:
            raise NotImplementedError(
                f'Không rebuild được layer QAT: {layer.name} ({layer.__class__.__name__})'
            ) from exc
        legacy.add(rebuilt)
    legacy(np.zeros((1, *input_shape), dtype=np.float32), training=False)
    source_weights, target_weights = source_model.get_weights(), legacy.get_weights()
    if len(source_weights) != len(target_weights):
        raise ValueError('QAT bridge: số weight tensor không khớp')
    for source, target in zip(source_weights, target_weights):
        if source.shape != target.shape:
            raise ValueError('QAT bridge: shape weight không khớp')
    legacy.set_weights(source_weights)
    return legacy


def build_selective_qat_model(base_model, tfmot, qat_keras):
    quantizable = {'Conv2D', 'DepthwiseConv2D', 'SeparableConv2D', 'Dense'}

    def annotate(layer):
        if layer.__class__.__name__ in quantizable:
            return tfmot.quantization.keras.quantize_annotate_layer(layer)
        return layer

    annotated = qat_keras.models.clone_model(base_model, clone_function=annotate)
    annotated.set_weights(base_model.get_weights())
    return tfmot.quantization.keras.quantize_apply(annotated)


def train_qat_model(
    source_model,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    output_dir: Path,
    settings: dict,
):
    try:
        import tensorflow_model_optimization as tfmot
        from tensorflow_model_optimization.python.core.keras.compat import keras as qat_keras
        from sklearn.utils.class_weight import compute_class_weight
    except ImportError as exc:
        raise ImportError(
            'QAT cần tensorflow-model-optimization và tf_keras trong đúng môi trường TensorFlow.'
        ) from exc

    legacy = build_qat_compatible_model(source_model, qat_keras)
    sample = x_val[: min(32, len(x_val))]
    source_prob = np.asarray(source_model.predict(sample, verbose=0)).reshape(-1)
    legacy_prob = np.asarray(legacy.predict(sample, verbose=0)).reshape(-1)
    max_diff = float(np.max(np.abs(source_prob - legacy_prob)))
    if max_diff > 1e-5 or np.any((source_prob >= .5) != (legacy_prob >= .5)):
        raise ValueError(f'QAT bridge làm đổi baseline trước fine-tune; max_diff={max_diff}')

    qat_model = build_selective_qat_model(legacy, tfmot, qat_keras)
    qat_model.compile(
        optimizer=qat_keras.optimizers.Adam(learning_rate=float(settings['qat_learning_rate'])),
        loss='binary_crossentropy',
        metrics=['accuracy'],
    )
    classes = np.unique(y_train.astype(int))
    weights = compute_class_weight('balanced', classes=classes, y=y_train.astype(int))
    class_weight = {int(key): float(value) for key, value in zip(classes, weights)}
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / 'QAT_Training_Log.csv'
    callbacks = [
        qat_keras.callbacks.EarlyStopping(
            monitor='val_loss', mode='min', patience=int(settings['qat_patience']),
            restore_best_weights=True, verbose=1,
        ),
        qat_keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss', mode='min', factor=.5, patience=2,
            min_lr=1e-6, verbose=1,
        ),
        qat_keras.callbacks.CSVLogger(str(log_path), append=False),
        qat_keras.callbacks.TerminateOnNaN(),
    ]
    history = qat_model.fit(
        x_train, y_train.astype(np.float32),
        validation_data=(x_val, y_val.astype(np.float32)),
        epochs=int(settings['qat_epochs']),
        batch_size=int(settings['qat_batch_size']),
        callbacks=callbacks,
        class_weight=class_weight,
        shuffle=True,
        verbose=1,
    )
    model_path = output_dir / 'QAT_Model.keras'
    try:
        qat_model.save(str(model_path))
    except Exception as exc:
        # TFLite vẫn được xuất trong cùng tiến trình; lỗi save được ghi lại để
        # không tạo cảm giác artifact QAT có thể load lại khi thực tế không thể.
        model_path = None
        (output_dir / 'QAT_Save_Warning.txt').write_text(str(exc), encoding='utf-8')
    return qat_model, history, model_path, max_diff, class_weight


def tensor_detail(detail: dict) -> dict:
    scale, zero = detail.get('quantization', (0.0, 0))
    return {
        'name': str(detail.get('name', '')),
        'shape': [int(value) for value in detail['shape']],
        'dtype': np.dtype(detail['dtype']).name,
        'scale': float(scale),
        'zero_point': int(zero),
    }


def inspect_tflite(path: Path) -> dict:
    import tensorflow as tf

    interpreter = tf.lite.Interpreter(model_path=str(path))
    interpreter.allocate_tensors()
    inputs, outputs = interpreter.get_input_details(), interpreter.get_output_details()
    if len(inputs) != 1 or len(outputs) != 1:
        raise ValueError('Pipeline hiện chỉ hỗ trợ model một input, một output')
    return {'input': tensor_detail(inputs[0]), 'output': tensor_detail(outputs[0])}


def quantize_array(value: np.ndarray, dtype, scale: float, zero: int) -> np.ndarray:
    if scale <= 0:
        raise ValueError('Quantization scale phải > 0')
    limits = np.iinfo(dtype)
    result = np.rint(value / scale + zero)
    return np.clip(result, limits.min, limits.max).astype(dtype)


def run_tflite(path: Path, features: np.ndarray) -> tuple[np.ndarray, dict]:
    import tensorflow as tf

    interpreter = tf.lite.Interpreter(model_path=str(path))
    interpreter.allocate_tensors()
    input_detail = interpreter.get_input_details()[0]
    output_detail = interpreter.get_output_details()[0]
    probabilities = []
    for sample in features:
        batch = sample[np.newaxis, ...]
        input_dtype = input_detail['dtype']
        if input_dtype == np.float32:
            model_input = batch.astype(np.float32)
        elif input_dtype in (np.int8, np.int16):
            scale, zero = input_detail['quantization']
            model_input = quantize_array(batch, input_dtype, float(scale), int(zero))
        else:
            raise TypeError(f'Không hỗ trợ TFLite input dtype={input_dtype}')
        interpreter.set_tensor(input_detail['index'], model_input)
        interpreter.invoke()
        output = interpreter.get_tensor(output_detail['index'])
        output_dtype = output_detail['dtype']
        if output_dtype == np.float32:
            probability = float(output.reshape(-1)[0])
        elif output_dtype in (np.int8, np.int16):
            scale, zero = output_detail['quantization']
            probability = float((output.astype(np.float32) - zero).reshape(-1)[0] * scale)
        else:
            raise TypeError(f'Không hỗ trợ TFLite output dtype={output_dtype}')
        probabilities.append(probability)
    result = np.asarray(probabilities, dtype=np.float32)
    if not np.isfinite(result).all():
        raise ValueError('TFLite prediction có NaN/Inf')
    return result, {'input': tensor_detail(input_detail), 'output': tensor_detail(output_detail)}


def binary_metrics(labels: np.ndarray, probabilities: np.ndarray) -> tuple[dict, np.ndarray]:
    from sklearn.metrics import (
        accuracy_score, balanced_accuracy_score, confusion_matrix,
        f1_score, precision_score, recall_score,
    )

    predicted = (probabilities >= .5).astype(np.int64)
    cm = confusion_matrix(labels, predicted, labels=[0, 1]).astype(int)
    metrics = {
        'accuracy': float(accuracy_score(labels, predicted)),
        'balanced_accuracy': float(balanced_accuracy_score(labels, predicted)),
        'macro_f1': float(f1_score(labels, predicted, average='macro', zero_division=0)),
        'asthma_precision': float(precision_score(labels, predicted, pos_label=0, zero_division=0)),
        'asthma_recall': float(recall_score(labels, predicted, pos_label=0, zero_division=0)),
        'asthma_f1': float(f1_score(labels, predicted, pos_label=0, zero_division=0)),
        'non_asthma_precision': float(precision_score(labels, predicted, pos_label=1, zero_division=0)),
        'non_asthma_recall': float(recall_score(labels, predicted, pos_label=1, zero_division=0)),
        'non_asthma_f1': float(f1_score(labels, predicted, pos_label=1, zero_division=0)),
        'asthma_fn': int(cm[0, 1]),
        'non_asthma_fp': int(cm[1, 0]),
        'confusion_matrix': cm.tolist(),
    }
    return metrics, predicted

