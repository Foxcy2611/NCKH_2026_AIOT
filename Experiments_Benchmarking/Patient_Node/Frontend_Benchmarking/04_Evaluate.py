"""Đánh giá checkpoint theo từng file và tổng hợp metric phân loại.

Tác dụng:
- Nạp model, tensor và metadata có cùng config/dataset fingerprint.
- Xuất p(Non-Asthma), nhãn dự đoán của từng file và confusion matrix.
- In và lưu Confusion Matrix + Classification Report vào <split>_classification_report.txt.
- Tính Accuracy, Balanced Accuracy, Macro F1 và recall của từng lớp.

Mặc định: đánh giá Validation bằng ``--split val``.
Test: chỉ mở sau bước lock; chỉ candidate đã chọn và F0 control được phép chạy.
Đầu ra: predictions/confusion trong thư mục model và summary trong ``results/``.
Giữ nguyên liên kết: ``results/experiment_plan.csv``, ``results/val_summary.csv``,
  ``artifacts/features/<variant>/`` và ``artifacts/models/<trial_id>/``.
Giới hạn: không train và không được dùng Test để thay đổi lựa chọn đã khóa.
"""
import argparse
import hashlib
import os
import sys
from pathlib import Path

# Match Training_Model.py / 03_Train.py on CPU inference.
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')

import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    confusion_matrix,
    log_loss,
    classification_report,
)

from frontend_core import (
    ARTIFACTS,
    RESULTS,
    enabled_plans,
    plans,
    read_json,
    trial_id,
    write_json,
    write_rows,
    read_rows,
    split_fingerprint,
)

SUMMARY_FIELDS = [
    'trial_id',
    'variant_id',
    'architecture',
    'seed',
    'config_sha256',
    'accuracy',
    'balanced_accuracy',
    'macro_f1',
    'asthma_recall',
    'non_asthma_recall',
    'asthma_fn',
    'non_asthma_fp',
    'asthma_count',
    'non_asthma_count',
    'log_loss',
    'parameter_count',
    'train_seconds',
    'model_sha256',
    'dataset_fingerprint',
]


def file_sha256(path):
    """Trả về SHA-256 của đúng tệp checkpoint đã dùng để suy luận."""
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def summarize(true, prob):
    pred = (prob >= .5).astype(int)
    mat = confusion_matrix(true, pred, labels=[0, 1])
    a0, a1 = mat[0]
    n0, n1 = mat[1]
    metrics = {
        'accuracy': float(accuracy_score(true, pred)),
        'balanced_accuracy': float(balanced_accuracy_score(true, pred)),
        'macro_f1': float(
            f1_score(
                true,
                pred,
                average='macro',
                labels=[0, 1],
                zero_division=0,
            )
        ),
        'asthma_recall': float(a0 / (a0 + a1)) if a0 + a1 else None,
        'non_asthma_recall': float(n1 / (n0 + n1)) if n0 + n1 else None,
        'asthma_fn': int(a1),
        'non_asthma_fp': int(n0),
        'asthma_count': int(a0 + a1),
        'non_asthma_count': int(n0 + n1),
        'log_loss': float(log_loss(true, prob, labels=[0, 1])),
    }
    return metrics, pred, mat


def evaluate(row, tid, split, force, tf):
    modeldir = ARTIFACTS / 'models' / tid
    model_path = modeldir / 'Model_Asthma.keras'
    training_metadata_path = modeldir / 'training_metadata.json'
    missing_model_files = [
        str(path)
        for path in (model_path, training_metadata_path)
        if not path.is_file()
    ]
    if missing_model_files:
        raise FileNotFoundError(
            f'04_Evaluate.py thiếu artifact model của trial {tid}:\n- '
            + '\n- '.join(missing_model_files)
            + '\nHãy chạy 03_Train.py cho trial này trước.'
        )
    info = read_json(training_metadata_path)
    print(f'EVALUATE: {tid} | training_recipe={info.get("training_recipe_id", "OLD_OR_UNKNOWN")}')
    if info.get('training_recipe_id') is None:
        print('WARNING: trial has no V1-aligned recipe ID. Consider retraining 03_Train.py.')
    if info['config_sha256'] != row['config_sha256']:
        raise ValueError('Training metadata config hash differs from plan')
    feat = ARTIFACTS / 'features' / row['variant_id']
    feature_paths = {
        'metadata': feat / f'{split}_metadata.json',
        'X': feat / f'X_{split}.npy',
        'Y': feat / f'Y_{split}.npy',
        'Files': feat / f'Files_{split}.npy',
    }
    missing_feature_files = [str(path) for path in feature_paths.values() if not path.is_file()]
    if missing_feature_files:
        raise FileNotFoundError(
            f'04_Evaluate.py thiếu feature {split} của variant {row["variant_id"]}:\n- '
            + '\n- '.join(missing_feature_files)
            + '\nHãy chạy 02_Preprocess.py cho split/variant này trước.'
        )
    fmeta = read_json(feature_paths['metadata'])
    if (
        fmeta['config_sha256'] != row['config_sha256']
        or fmeta['dataset_root'] != info['dataset_root']
        or fmeta.get('dataset_fingerprint')
        != split_fingerprint(Path(info['dataset_root']), split)
    ):
        raise ValueError('Feature data provenance mismatch')

    out = modeldir / f'{split}_predictions.csv'
    summary_path = RESULTS / f'{split}_summary.csv'
    if out.exists() and not force:
        if split == 'val':
            print(
                f'BỎ QUA {tid}: đã có {out}. '
                'Dùng --force nếu muốn tính lại Validation.'
            )
            return
        raise FileExistsError(
            f'Kết quả Test đã tồn tại: {out}. Không tự động đọc/chạy lại Test.'
        )
    if split == 'test' and force:
        raise PermissionError('No --force for Final Test')

    X_raw = np.load(feature_paths['X'])
    y = np.load(feature_paths['Y']).astype('int64')
    fnames = np.load(feature_paths['Files'], allow_pickle=False)
    if len(X_raw) != len(y) or len(y) != len(fnames):
        raise ValueError('Feature/label/filename length mismatch')
    if tuple(X_raw.shape[1:]) != tuple(info['input_shape']):
        raise ValueError('Model/feature shape mismatch')
    if split == 'val' and fmeta['dataset_fingerprint'] != info.get('val_fingerprint'):
        raise ValueError('Validation fingerprint changed since train')

    if not np.isfinite(X_raw).all():
        raise ValueError(f'{split} features contain NaN/Inf')
    X = ((X_raw - info['train_min']) /
         (info['train_max'] - info['train_min'])).astype(np.float32)
    # Same as V1: load compiled checkpoint and report Keras evaluate loss/accuracy.
    model = tf.keras.models.load_model(model_path)
    keras_metrics = model.evaluate(
        X, y.astype(np.float32), batch_size=32, verbose=0, return_dict=True
    )
    keras_loss = float(keras_metrics['loss'])
    keras_accuracy = float(keras_metrics.get('accuracy', float('nan')))
    prob = np.asarray(model.predict(X, batch_size=32, verbose=0)).reshape(-1)
    if len(prob) != len(y):
        raise ValueError('Output length mismatch')
    if not np.isfinite(prob).all() or (prob < 0).any() or (prob > 1).any():
        raise ValueError('Expected sigmoid p(Non-Asthma) in [0,1]')

    metrics, pred, mat = summarize(y, prob)
    class_report = classification_report(
        y, pred,
        labels=[0, 1],
        target_names=['Asthma', 'Non-Asthma'],
        digits=4,
        zero_division=0,
    )
    report_text = '\n'.join([
        f'Trial: {tid}',
        f'Split: {split} | architecture: {info["architecture"]} | seed: {info["seed"]}',
        f'Training recipe: {info.get("training_recipe_id", "OLD_OR_UNKNOWN")}',
        f'Keras {split} Loss: {keras_loss:.6f}',
        f'Keras {split} Accuracy: {keras_accuracy:.6f}',
        'Labels: 0=Asthma, 1=Non-Asthma; sigmoid output is p(Non-Asthma).',
        'Confusion Matrix (rows: actual, columns: predicted; order [Asthma, Non-Asthma]):',
        np.array2string(mat),
        f'Asthma missed (FN, actual Asthma -> predicted Non-Asthma): {int(mat[0, 1])}',
        '',
        'Classification Report:',
        class_report,
        '',
        'Summary metrics:',
        *[f'  {key}: {value}' for key, value in metrics.items()],
        f'  parameter_count: {info["parameter_count"]}',
        f'  train_seconds: {info["train_seconds"]}',
        '',
        f'NOTE: {split} metrics only. Not a clinical diagnostic validation.',
    ])
    report_path = modeldir / f'{split}_classification_report.txt'
    report_path.write_text(report_text + '\n', encoding='utf-8')
    print('\n' + '=' * 60)
    print('EVALUATION REPORT:', tid)
    print('=' * 60)
    print(report_text)
    print(f'SAVED REPORT: {report_path}')
    write_rows(
        out,
        [
            {
                'file': name,
                'true_label': int(actual),
                'p_non_asthma': float(p),
                'predicted_label': int(z),
            }
            for name, actual, p, z in zip(fnames, y, prob, pred)
        ],
        fields=['file', 'true_label', 'p_non_asthma', 'predicted_label'],
    )
    rec = {
        'trial_id': tid,
        'variant_id': row['variant_id'],
        'architecture': info['architecture'],
        'seed': info['seed'],
        'config_sha256': row['config_sha256'],
        **metrics,
        'parameter_count': info['parameter_count'],
        'train_seconds': info['train_seconds'],
        # Hai dấu vân tay này gắn metric với đúng checkpoint và đúng tập dữ liệu.
        # Tuyệt đối không bổ sung chúng về sau nếu chưa inference lại.
        'model_sha256': file_sha256(model_path),
        'dataset_fingerprint': fmeta['dataset_fingerprint'],
    }
    existing = read_rows(summary_path) if summary_path.is_file() else []
    existing = [r for r in existing if r['trial_id'] != tid]
    existing.append(rec)
    write_rows(summary_path, existing, fields=SUMMARY_FIELDS)
    write_json(
        modeldir / f'{split}_confusion.json',
        {
            'labels': [0, 1],
            'matrix': mat.tolist(),
            'note': 'matrix rows: actual Asthma, Non-Asthma; columns: predicted same order',
        },
    )
    print('EVALUATED', split, tid, rec)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--architecture', default='V1')
    p.add_argument('--seed', type=int, default=42)
    p.add_argument(
        '--variant',
        help=(
            'Evaluate one named variant from experiment_plan.csv. '
            'An explicit variant may currently have enabled=0.'
        ),
    )
    p.add_argument(
        '--trial-id',
        help=(
            'Evaluate one exact trained trial, including a trial whose variant '
            'currently has enabled=0.'
        ),
    )
    p.add_argument('--split', choices=['val', 'test'], default='val')
    p.add_argument('--force', action='store_true')
    a = p.parse_args()

    if a.split == 'test':
        if a.force:
            p.error('Refusing --force on Test')
        if not a.trial_id:
            p.error(
                'Test yêu cầu --trial-id rõ ràng. Để đồng bộ ma trận C, dùng '
                'Notebook/04_Fontend_Selection/C_Sync_24_Checkpoints.py.'
            )
        metadata_path = ARTIFACTS / 'models' / a.trial_id / 'training_metadata.json'
        if not metadata_path.is_file():
            p.error(f'Không tìm thấy training metadata: {metadata_path}')
        trial_metadata = read_json(metadata_path)
        variant = trial_metadata.get('variant_id')
        matching_rows = [row for row in plans() if row['variant_id'] == variant]
        if len(matching_rows) != 1:
            p.error(f'Không tìm thấy đúng một plan row cho variant {variant}')
        if a.variant and a.variant != variant:
            p.error(f'--variant={a.variant} không khớp trial {a.trial_id}')
        requests = [(matching_rows[0], a.trial_id)]
    else:
        if a.trial_id:
            metadata_path = (
                ARTIFACTS / 'models' / a.trial_id / 'training_metadata.json'
            )
            if not metadata_path.is_file():
                p.error(
                    f'Không tìm thấy training metadata của trial: {metadata_path}'
                )
            trial_metadata = read_json(metadata_path)
            variant = trial_metadata.get('variant_id')
            if not variant:
                p.error(
                    f'training_metadata.json của {a.trial_id} thiếu variant_id'
                )
            if a.variant and a.variant != variant:
                p.error(
                    f'--variant={a.variant} không khớp variant={variant} '
                    f'trong trial {a.trial_id}'
                )
            matching_rows = [
                row for row in plans() if row['variant_id'] == variant
            ]
            if len(matching_rows) != 1:
                p.error(
                    f'Không tìm thấy đúng một plan row cho variant {variant}'
                )
            requests = [(matching_rows[0], a.trial_id)]
        elif a.variant:
            # Explicit selection is allowed for an already-trained candidate
            # even when it is disabled in the current training schedule.
            matching_rows = [
                row for row in plans() if row['variant_id'] == a.variant
            ]
            if len(matching_rows) != 1:
                p.error(
                    f'Không tìm thấy đúng một variant={a.variant} '
                    'trong experiment_plan.csv'
                )
            requests = [
                (
                    matching_rows[0],
                    trial_id(a.variant, a.architecture, a.seed),
                )
            ]
        else:
            # No explicit target: preserve the scheduled behavior and only
            # evaluate candidates currently enabled in the plan.
            requests = [
                (row, trial_id(row['variant_id'], a.architecture, a.seed))
                for row in enabled_plans()
            ]

    pending_requests = []
    for row, tid in requests:
        prediction_path = ARTIFACTS / 'models' / tid / f'{a.split}_predictions.csv'
        if prediction_path.is_file() and not a.force:
            if a.split == 'test':
                p.error(
                    f'Kết quả Test đã tồn tại: {prediction_path}. '
                    'Không được dùng --force cho Final Test.'
                )
            print(
                f'BỎ QUA {tid}: Validation đã có tại {prediction_path}. '
                'Dùng --force nếu muốn tính lại.'
            )
            continue
        pending_requests.append((row, tid))

    if not pending_requests:
        print('04_Evaluate.py: không có trial nào cần chạy lại.')
        return

    try:
        import tensorflow as tf
    except ImportError as exc:
        raise SystemExit('TensorFlow required for model inference') from exc

    for row, tid in pending_requests:
        evaluate(row, tid, a.split, a.force, tf)


if __name__ == '__main__':
    main()
