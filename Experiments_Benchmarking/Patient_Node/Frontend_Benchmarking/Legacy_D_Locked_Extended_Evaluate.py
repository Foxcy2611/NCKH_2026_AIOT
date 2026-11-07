"""NCKH D — so sánh model chính đã khóa và kiểm toán Test thăm dò trên 20 trial.

Đặt file này cạnh ``frontend_core.py``, ``01_Build_Plan.py`` và thư mục
``artifacts/models/`` trong ``Frontend_Benchmarking``. Script KHÔNG sửa các
script 01/02/03/04, artifact model, ``test_summary.csv`` cũ hoặc
``locked_selection.json``.

Quy trình:
  python D_Locked_Extended_Evaluate.py --freeze
  # Đọc results/D_locked_20/D_freeze.json TRƯỚC khi tiếp tục.
  python D_Locked_Extended_Evaluate.py --run

CẢNH BÁO: tập Test lịch sử gồm 159 WAV đã được xem trong lần đánh giá trước.
Phải coi TOÀN BỘ kết quả D là đánh giá lại/thăm dò, KHÔNG phải kết quả trên một
tập holdout cuối cùng hoàn toàn mới và độc lập.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Đồng bộ với quy ước đánh giá của Phase 2.
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')

import numpy as np

from frontend_core import (
    ROOT, ARTIFACTS, RESULTS, PROTOCOL, dataset_root, list_split,
    split_fingerprint, load_raw_window, process_wave, mel_from_wave,
    read_json, read_rows, plans, load_config, digest, trial_id,
)

SCRIPT_VERSION = 'D_FROZEN_20_PHASE2_ALIGNED_V1'
RECIPE = 'V1_phase2_exact_float64_raw_float32_after_normalize_v2'
D_DIR = RESULTS / 'D_locked_20'
FREEZE_NAME = 'D_freeze.json'
PRIMARY = 'combo_pre0_mel40__V1__s43'
BASELINE = 'F0__V1__s43'
TECHNICAL = 'mel_40__V1__s43'
B1_VARIANTS = (
    'F0', 'fft_2048', 'hop_800', 'mel_40', 'mel_80',
    'order_3', 'order_7', 'pre_0', 'pre_095',
)
B3_VARIANTS = ('F0', 'pre_0', 'mel_40', 'fft_2048')
COMBO = 'combo_pre0_mel40'


def registered_trials():
    """Đăng ký trước rõ ràng 9 B1 + 8 B3 bổ sung + 3 C = 20 trial."""
    rows = [(trial_id(v, 'V1', 42), 'B1_s42') for v in B1_VARIANTS]
    rows += [(trial_id(v, 'V1', seed), 'B3_extra')
             for v in B3_VARIANTS for seed in (43, 44)]
    rows += [(trial_id(COMBO, 'V1', seed), 'C_combo')
             for seed in (42, 43, 44)]
    assert len(rows) == len({t for t, _ in rows}) == 20
    assert {PRIMARY, BASELINE, TECHNICAL}.issubset({t for t, _ in rows})
    return rows


def sha256_file(p: Path):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def json_bytes(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf8')


def atomic_json(path, value):
    temp = path.with_suffix(path.suffix + '.pending')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    temp.replace(path)


def csv_write(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def validate_checkpoint_files(dataset, silent=False):
    """Không liệt kê, nạp hoặc kiểm tra tập Test trong hàm này."""
    plan_path = RESULTS / 'experiment_plan.csv'
    summary_path = RESULTS / 'val_summary.csv'
    if not plan_path.is_file() or not summary_path.is_file():
        raise FileNotFoundError('Missing results/experiment_plan.csv or results/val_summary.csv')
    # Đọc TOÀN BỘ variant trong kế hoạch, không chỉ các dòng đang enabled.
    plan = {r['variant_id']: r for r in plans()}
    summaries = {r['trial_id']: r for r in read_rows(summary_path)}
    train_fp, val_fp = split_fingerprint(dataset, 'train'), split_fingerprint(dataset, 'val')
    refs = []
    validation_registry = None
    expected_root = dataset.resolve()
    for tid, stage in registered_trials():
        var = tid.split('__')[0]
        seed = int(tid.rsplit('__s', 1)[1])
        if var not in plan:
            raise ValueError(f'Variant {var} absent in experiment_plan.csv; rebuild plan (01).')
        row = plan[var]
        cfg = load_config(row)
        if digest(cfg) != row['config_sha256']:
            raise ValueError(f'Configuration hash changed for {var}')
        if tid not in summaries:
            raise ValueError(f'Missing Validation summary for trial {tid}')
        vm = summaries[tid]
        if vm['config_sha256'] != row['config_sha256']:
            raise ValueError(f'Validation summary hash does not match plan: {tid}')
        if vm['variant_id'] != var or int(vm['seed']) != seed or vm['architecture'] != 'V1':
            raise ValueError(f'Validation metadata mismatch: {tid}')
        modeldir = ARTIFACTS / 'models' / tid
        ckpt = modeldir / 'Model_Asthma.keras'
        meta = modeldir / 'training_metadata.json'
        val_preds = modeldir / 'val_predictions.csv'
        for p in (ckpt, meta, val_preds):
            if not p.is_file():
                raise FileNotFoundError(f'{tid}: missing {p}')
        info = read_json(meta)
        if info.get('training_recipe_id') != RECIPE:
            raise ValueError(f'{tid}: recipe mismatch: {info.get("training_recipe_id")} != {RECIPE}')
        if str(info.get('raw_train_dtype')) != 'float64' or str(info.get('raw_val_dtype')) != 'float64':
            raise ValueError(f'{tid}: expected raw Train/Val features float64, got '
                             f'{info.get("raw_train_dtype")}/{info.get("raw_val_dtype")}')
        if info.get('train_fingerprint') != train_fp or info.get('val_fingerprint') != val_fp:
            raise ValueError(f'{tid}: Train/Val fingerprint differs from training metadata')
        if Path(info['dataset_root']).resolve() != expected_root:
            raise ValueError(f'{tid}: dataset_root differs; use original location or audit explicitly')
        if info.get('config_sha256') != row['config_sha256']:
            raise ValueError(f'{tid}: checkpoint metadata config hash mismatch')
        if info.get('seed') != seed or info.get('architecture') != 'V1' or info.get('variant_id') != var:
            raise ValueError(f'{tid}: checkpoint seed/architecture mismatch')
        if not math.isfinite(float(info['train_min'])) or not math.isfinite(float(info['train_max'])):
            raise ValueError(f'{tid}: invalid normalization extrema')
        if float(info['train_min']) >= float(info['train_max']):
            raise ValueError(f'{tid}: invalid Train min/max')
        shape = list(info['input_shape'])
        if shape != [cfg.n_mels, 1 + 80000 // cfg.hop_length, 1]:
            raise ValueError(f'{tid}: checkpoint shape {shape} != expected Mel size')
        # Mọi file dự đoán Validation phải cùng tham chiếu đúng 154 WAV cố định.
        with val_preds.open(encoding='utf-8-sig', newline='') as f:
            pred_rows = list(csv.DictReader(f))
        if len(pred_rows) != 154:
            raise ValueError(f'{tid}: validation predictions count {len(pred_rows)} != 154')
        ids = [r['file'].replace('\\', '/') for r in pred_rows]
        if len(set(ids)) != len(ids):
            raise ValueError(f'{tid}: duplicate filenames in Val predictions')
        current = {r['file'].replace('\\', '/'): int(r['true_label']) for r in pred_rows}
        correct = 0
        for pr in pred_rows:
            label = int(pr['true_label'])
            predicted = int(pr['predicted_label'])
            probability = float(pr['p_non_asthma'])
            if label not in (0, 1) or predicted != int(probability >= .5) or not 0 <= probability <= 1:
                raise ValueError(f'{tid}: inconsistent validation prediction record')
            correct += int(label == predicted)
        if abs(correct / len(pred_rows) - float(vm['accuracy'])) > 1e-8:
            raise ValueError(f'{tid}: val_summary accuracy does not match saved predictions')
        if validation_registry is None:
            validation_registry = current
        elif current != validation_registry:
            raise ValueError(f'{tid}: Validation WAV names/labels differ from other seeds')
        refs.append({
            'trial_id': tid, 'stage': stage, 'variant_id': var, 'seed': seed,
            'config_sha256': row['config_sha256'], 'architecture': 'V1',
            'model_sha256': sha256_file(ckpt),
            'metadata_sha256': sha256_file(meta),
            'val_predictions_sha256': sha256_file(val_preds),
            'train_min': float(info['train_min']), 'train_max': float(info['train_max']),
            'parameter_count': int(info['parameter_count']),
            'input_shape': shape,
            'val_accuracy': float(vm['accuracy']),
            'val_macro_f1': float(vm['macro_f1']),
            'val_asthma_fn': int(float(vm['asthma_fn'])),
        })
    # Khi freeze không kiểm tra Test; chỉ đối chiếu fingerprint Train/Validation.
    if not silent:
        print(f'PREFLIGHT OK — {len(refs)} checkpoints; Train/Val fingerprints agree; Test untouched.')
    return refs, {'train': train_fp, 'val': val_fp}


def freeze(args):
    root = dataset_root(args.dataset_root)
    if D_DIR.exists():
        raise FileExistsError(f'{D_DIR} already exists: no overwrite / re-freeze')
    refs, fingerprints = validate_checkpoint_files(root)
    # Kiểm tra nhanh dtype bằng một WAV Train; không truy cập tín hiệu Test tại đây.
    first_train_wav = list_split(root, 'train')[0][0]
    config = load_config(next(r for r in plans() if r['variant_id'] == 'F0'))
    preview = mel_from_wave(process_wave(load_raw_window(first_train_wav), config), config)
    if preview.dtype != np.dtype('float64'):
        raise RuntimeError(f'Frontend returns raw {preview.dtype}; expected float64. '
                           'Your installed frontend_core.py is an old float32 version. '
                           'DO NOT freeze/use Test until corrected.')
    core = Path(sys.modules['frontend_core'].__file__).resolve()
    project_plan = RESULTS / 'experiment_plan.csv'
    payload = {
        'script_version': SCRIPT_VERSION,
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'FROZEN_BEFORE_D_TEST',
        'primary_trial': PRIMARY, 'baseline_trial': BASELINE,
        'technical_control_trial': TECHNICAL,
        'primary_decision_rule': 'C1 s43 selected on Validation as middle-performing C1 seed; no Test-based promotion',
        'extended_scope': '20 registered checkpoints evaluated descriptively, never primary-selection source',
        'historical_test_previously_inspected': True,
        'test_independence': 'NOT PRISTINE; historical 159-WAV Test has been explored previously',
        'threshold_p_non_asthma': 0.5,
        'label_rule': '0=Asthma; 1=Non-Asthma; p(Non-Asthma)>=0.5 -> 1',
        'training_recipe_required': RECIPE,
        'raw_logmel_dtype_preflight_on_train': str(preview.dtype),
        'dataset_root': str(root.resolve()),
        'train_val_fingerprints': fingerprints,
        'protocol': PROTOCOL,
        'script_sha256': sha256_file(Path(__file__).resolve()),
        'frontend_core_sha256': sha256_file(core),
        'plan_sha256': sha256_file(project_plan),
        'trials': refs,
        'limitations': [
            'Test has been examined in a previous benchmark; not a truly independent final holdout.',
            'All 20 trials share one set of Test WAVs; do not treat predictions as independent samples.',
            'Patient/source-group separation and sample-rate confounding require separate audit.',
            'Clinical diagnostic validation is NOT claimed.',
        ],
    }
    payload['freeze_sha256'] = hashlib.sha256(json_bytes(payload)).hexdigest()
    D_DIR.mkdir(parents=True, exist_ok=False)
    atomic_json(D_DIR / FREEZE_NAME, payload)
    print(f'FROZEN: {D_DIR / FREEZE_NAME}')
    print('READ THE FREEZE DOCUMENT. Test has not been loaded or examined by this command.')
    print('When ready, run: python D_Locked_Extended_Evaluate.py --run')


def verify_frozen(frozen):
    root = dataset_root(frozen['dataset_root'])
    payload = {k: v for k, v in frozen.items() if k != 'freeze_sha256'}
    if hashlib.sha256(json_bytes(payload)).hexdigest() != frozen['freeze_sha256']:
        raise RuntimeError('Freeze JSON was modified after locking')
    if frozen.get('status') != 'FROZEN_BEFORE_D_TEST' or frozen['script_version'] != SCRIPT_VERSION:
        raise RuntimeError('Wrong/stale freeze version')
    if frozen['script_sha256'] != sha256_file(Path(__file__).resolve()):
        raise RuntimeError('D script changed after --freeze; do not run without audit')
    core = Path(sys.modules['frontend_core'].__file__).resolve()
    if frozen['frontend_core_sha256'] != sha256_file(core):
        raise RuntimeError('frontend_core.py changed after --freeze')
    if frozen['plan_sha256'] != sha256_file(RESULTS / 'experiment_plan.csv'):
        raise RuntimeError('Plan changed after --freeze')
    refs, fps = validate_checkpoint_files(root, silent=True)
    if fps != frozen['train_val_fingerprints']:
        raise RuntimeError('Train/Val dataset changed after freeze')
    if refs != frozen['trials']:
        raise RuntimeError('Checkpoint / Validation artifact changed after freeze')
    return root, refs


def summarize_metrics(y, prob):
    from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, log_loss, confusion_matrix
    pred = (prob >= 0.5).astype(np.int64)
    cm = confusion_matrix(y, pred, labels=[0, 1]).astype(int)
    n0 = int(cm[0].sum())
    n1 = int(cm[1].sum())
    return dict(
        accuracy=float(accuracy_score(y, pred)),
        balanced_accuracy=float(balanced_accuracy_score(y, pred)),
        macro_f1=float(f1_score(y, pred, average='macro', labels=[0, 1], zero_division=0)),
        asthma_recall=float(cm[0, 0]/n0) if n0 else float('nan'),
        non_asthma_recall=float(cm[1, 1]/n1) if n1 else float('nan'),
        asthma_fn=int(cm[0, 1]), non_asthma_fp=int(cm[1, 0]),
        asthma_count=n0, non_asthma_count=n1,
        log_loss=float(log_loss(y, prob, labels=[0, 1])),
        cm=cm.tolist(),
    ), pred


def source_group(path, label):
    stem = path.stem.casefold()
    if stem.endswith(('__take01', '__take02')):
        return 'playback'
    if stem.startswith('env__'):
        return 'environment'
    if stem.startswith('augv2__'):
        return 'augmentation'
    # Suy ra từ quy tắc đặt tên, không phải thông tin nguồn/bệnh nhân thực tế.
    return 'raw'


def get_test_meta(path, root, y):
    import soundfile as sf
    info = sf.info(str(path))
    offset = 1.0 if path.stem.casefold().endswith(('__take01', '__take02')) else 0.0
    usable = min(5.0, max(0.0, float(info.duration) - offset))
    return {
        'file': path.relative_to(root).as_posix(), 'true_label': y,
        'original_sr_hz': int(info.samplerate), 'original_duration_s': float(info.duration),
        'estimated_padding_pct': (5.0-usable) * 20.0,
        'source_kind_inferred': source_group(path, y),
    }


def paired_results(all_predictions, primary, baseline):
    """Mỗi trial thay thế có một bản ghi, ghép cặp trên chính xác cùng WAV Test."""
    p = all_predictions[primary]
    pb = all_predictions[baseline]
    if set(p) != set(pb):
        raise RuntimeError('Unmatched Test filenames between primary and baseline')
    rows = []
    for tid, other in all_predictions.items():
        if tid == primary:
            continue
        if set(p) != set(other):
            raise RuntimeError(f'Unmatched Test filenames in trial {tid}')
        improvement, worsening, same_both_wrong = 0, 0, 0
        for fname, a in p.items():
            b = other[fname]
            if a['true_label'] != b['true_label']:
                raise RuntimeError(f'Label mismatch across Test candidates: {fname}')
            p_ok = a['predicted_label'] == a['true_label']
            b_ok = b['predicted_label'] == b['true_label']
            # So sánh độ đúng của model chính và model thay thế theo từng chiều.
            if not p_ok and b_ok:
                improvement += 1  # Model thay thế đúng, model chính sai.
            if p_ok and not b_ok:
                worsening += 1  # Model thay thế sai, model chính đúng.
            if not p_ok and not b_ok:
                same_both_wrong += 1
        rows.append({'alternative_trial_id': tid, 'primary_trial_id': primary,
                     'alternative_correct_primary_wrong': improvement,
                     'primary_correct_alternative_wrong': worsening,
                     'both_wrong': same_both_wrong,
                     'net_alternative_more_correct': improvement-worsening})
    return rows


def run(args):
    if not D_DIR.is_dir() or not (D_DIR / FREEZE_NAME).is_file():
        raise FileNotFoundError('Run --freeze first (read the frozen primary decision).')
    if any(p.exists() for p in [D_DIR/'D_run_manifest.json', D_DIR/'D_test_summary.csv', D_DIR/'D_test_predictions.csv']):
        raise FileExistsError('D Test already evaluated. Never run twice in the same D folder.')
    frozen = read_json(D_DIR / FREEZE_NAME)
    root, refs = verify_frozen(frozen)
    print('Freeze verified. Beginning ONE registered Test evaluation (not a pristine holdout).')

    # Chỉ truy cập Test từ vị trí này trở xuống, sau khi freeze được xác minh thành công.
    records = list_split(root, 'test')
    file_names = [p.relative_to(root).as_posix() for p, _ in records]
    y = np.asarray([lab for _, lab in records], dtype=np.int64)
    if len(file_names) != len(set(file_names)) or len(records) != 159:
        raise RuntimeError(f'Expected exactly 159 unique Test WAVs, got {len(records)}')
    test_fp = split_fingerprint(root, 'test')
    metarows = [get_test_meta(path, root, lab) for path, lab in records]

    # frontend_core hiện tại bắt buộc phải sinh Mel thô dạng float64.
    # Các bản lưu trữ cũ sinh float32; phải dừng thay vì âm thầm so sánh hai
    # pipeline tiền xử lý không tương thích.
    import tensorflow as tf
    import librosa, scipy
    by_var = defaultdict(list)
    for ref in refs:
        by_var[ref['variant_id']].append(ref)
    plan = {r['variant_id']: r for r in plans()}
    stage = D_DIR / '_IN_PROGRESS_DO_NOT_REPORT'
    if stage.exists():
        raise FileExistsError(f'Incomplete prior D run exists at {stage}; manual review needed')
    stage.mkdir(parents=True)
    try:
        results, predrows, all_predictions = [], [], {}
        dtype_checked = False
        for i, (var, group_refs) in enumerate(by_var.items(), 1):
            cfg = load_config(plan[var])
            print(f'[{i}/{len(by_var)}] Extracting Test Log-Mel: {var}', flush=True)
            X = []
            for path, _label in records:
                mel = mel_from_wave(process_wave(load_raw_window(path), cfg), cfg)
                if not dtype_checked:
                    if mel.dtype != np.dtype('float64'):
                        raise RuntimeError(
                            'CRITICAL: current frontend_core returns Log-Mel '
                            f'{mel.dtype}, expected float64 (Phase2-aligned). '
                            'Install your actual aligned frontend_core.py; DO NOT run Test with old code.'
                        )
                    dtype_checked = True
                if mel.shape != (cfg.n_mels, 1+80000//cfg.hop_length) or not np.isfinite(mel).all():
                    raise RuntimeError(f'{var}: invalid Log-Mel feature shape/dtype')
                X.append(mel)
            X = np.stack(X)[..., np.newaxis]  # Mel thô float64, giống Phase 2.
            for ref in group_refs:
                tid = ref['trial_id']
                d = ARTIFACTS / 'models' / tid
                info = read_json(d / 'training_metadata.json')
                normalized = ((X - ref['train_min'])/(ref['train_max']-ref['train_min'])).astype(np.float32)
                if tuple(normalized.shape[1:]) != tuple(ref['input_shape']):
                    raise RuntimeError(f'{tid}: model input shape incompatible')
                # Mỗi seed dùng min/max Train của CHÍNH NÓ, tuyệt đối không dùng min/max Test.
                tf.keras.backend.clear_session()  # Tránh tích lũy graph qua 20 checkpoint.
                model = tf.keras.models.load_model(d / 'Model_Asthma.keras', compile=False)
                p_non = np.asarray(model.predict(normalized, batch_size=32, verbose=0)).reshape(-1)
                if len(p_non) != len(y) or not np.isfinite(p_non).all() or (p_non<0).any() or (p_non>1).any():
                    raise RuntimeError(f'{tid}: invalid sigmoid predictions')
                metrics, pred = summarize_metrics(y, p_non)
                score = {k:v for k,v in metrics.items() if k!='cm'}
                score.update({k: ref[k] for k in ('trial_id','stage','variant_id','seed','parameter_count','model_sha256','val_accuracy')})
                score['test_minus_val_pp'] = (metrics['accuracy'] - ref['val_accuracy'])*100
                score['is_primary'] = int(tid==PRIMARY)
                score['is_baseline'] = int(tid==BASELINE)
                results.append(score)
                all_predictions[tid] = {}
                for fname, yy, prob, yy_hat in zip(file_names, y, p_non, pred):
                    row = {'trial_id':tid, 'file':fname, 'true_label':int(yy),
                           'p_non_asthma':float(prob), 'predicted_label':int(yy_hat)}
                    predrows.append(row)
                    all_predictions[tid][fname] = row
                del model
                print(f'  {tid}: Accuracy={metrics["accuracy"]:.4%}, Asthma FN={metrics["asthma_fn"]}')
            del X
        primary_accuracy = next(r['accuracy'] for r in results if r['trial_id'] == PRIMARY)
        for r in results:
            r['test_exceeds_frozen_primary'] = int(
                r['trial_id'] != PRIMARY and r['accuracy'] > primary_accuracy
            )
        summary_fields = [
            'trial_id','stage','variant_id','seed','is_primary','is_baseline',
            'accuracy','balanced_accuracy','macro_f1','asthma_recall',
            'non_asthma_recall','asthma_fn','non_asthma_fp','asthma_count',
            'non_asthma_count','log_loss','parameter_count','val_accuracy',
            'test_minus_val_pp','test_exceeds_frozen_primary','model_sha256'
        ]
        csv_write(stage/'D_test_summary.csv', results, summary_fields)
        csv_write(stage/'D_test_predictions.csv', predrows,
                  ['trial_id','file','true_label','p_non_asthma','predicted_label'])
        csv_write(stage/'D_test_metadata.csv', metarows,
                  ['file','true_label','original_sr_hz','original_duration_s',
                   'estimated_padding_pct','source_kind_inferred'])
        pair = paired_results(all_predictions, PRIMARY, BASELINE)
        csv_write(stage/'D_paired_vs_primary.csv', pair, list(pair[0]))
        runinfo = {
            'status': 'D_TEST_COMPLETE', 'created_utc': datetime.now(timezone.utc).isoformat(),
            'freeze_sha256': frozen['freeze_sha256'], 'registered_trial_count': len(refs),
            'test_wav_count': len(records), 'test_fingerprint': test_fp,
            'primary_trial': PRIMARY, 'baseline_trial': BASELINE,
            'historical_test_previously_inspected': True,
            'not_pristine_independent_holdout': True,
            'tensorflow_version':tf.__version__, 'librosa_version':librosa.__version__,
            'scipy_version':scipy.__version__, 'numpy_version':np.__version__,
            'logmel_raw_dtype':'float64','normalized_input_dtype':'float32',
            'threshold':0.5,
            'result_sha256': {n: sha256_file(stage/n) for n in [
                'D_test_summary.csv','D_test_predictions.csv','D_test_metadata.csv',
                'D_paired_vs_primary.csv']},
        }
        atomic_json(stage/'D_run_manifest.json', runinfo)
        # Công bố toàn bộ kết quả mà không ghi đè artifact B/C lịch sử.
        for f in stage.iterdir():
            target = D_DIR / f.name
            if target.exists():
                raise FileExistsError(target)
            f.replace(target)
        stage.rmdir()
        print(f'D COMPLETE — read only {D_DIR}; old 04_Evaluate output UNCHANGED.')
    except Exception:
        print(f'D FAILED. Staging dir retained for inspection: {stage}', file=sys.stderr)
        raise


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    exclusive = ap.add_mutually_exclusive_group(required=True)
    exclusive.add_argument(
        '--freeze', action='store_true',
        help='Kiểm toán và khóa 20 checkpoint, KHÔNG truy cập Test',
    )
    exclusive.add_argument(
        '--run', action='store_true',
        help='Đánh giá 20 checkpoint đã khóa trên Test ĐÚNG MỘT LẦN',
    )
    ap.add_argument(
        '--dataset-root',
        help='Thư mục Dataset_Chia_V2 gốc; bỏ qua để frontend_core tự tìm',
    )
    args = ap.parse_args()
    if args.freeze:
        freeze(args)
    else:
        run(args)


if __name__ == '__main__':
    main()
