"""Tiền xử lý WAV thành tensor Log-Mel cho từng Front-End candidate.

Tác dụng:
- Đọc plan đã tạo bởi ``01_Build_Plan.py``.
- Áp dụng crop, normalize, Butterworth, pre-emphasis và Log-Mel.
- Lưu riêng X, Y, tên file và metadata cho từng split/candidate.

Mặc định: chỉ xử lý Train và Validation; có thể giới hạn bằng ``--variant``.
Test: chỉ xử lý khi gọi rõ ``--include-test``, sau khi đã xác định checkpoint
cần hậu kiểm; không dùng Test để điều chỉnh ngược candidate.
Đầu ra: ``artifacts/features/<variant>/``. Script này không train model.
"""
import argparse
from pathlib import Path

import numpy as np

from frontend_core import (
    ARTIFACTS,
    dataset_root,
    enabled_plans,
    list_split,
    load_raw_window,
    load_config,
    mel_from_wave,
    phase2_preprocess_dir,
    process_wave,
    split_fingerprint,
    read_json,
    write_json,
)


def assert_f0_matches_phase2(split, X, Y, files):
    """Khóa F0 theo đúng tensor/nhãn/thứ tự file của Phase 2 V1."""
    reference_dir = phase2_preprocess_dir()
    paths = {
        'X': reference_dir / f'X_{split}_mel.npy',
        'Y': reference_dir / f'Y_{split}_mel.npy',
        'Files': reference_dir / f'Files_{split}.npy',
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            'Thiếu artifact Phase 2 để kiểm chứng F0:\n- '
            + '\n- '.join(missing)
        )

    ref_X = np.load(paths['X'])
    ref_Y = np.load(paths['Y'])
    ref_files = np.load(paths['Files'], allow_pickle=False)

    # Phase 2 ghi separator theo hệ điều hành; Frontend ghi POSIX để portable.
    normalized_files = np.char.replace(files.astype(str), '\\', '/')
    normalized_ref_files = np.char.replace(ref_files.astype(str), '\\', '/')

    errors = []
    if X.dtype != ref_X.dtype:
        errors.append(f'dtype X: Frontend={X.dtype}, Phase2={ref_X.dtype}')
    if X.shape != ref_X.shape:
        errors.append(f'shape X: Frontend={X.shape}, Phase2={ref_X.shape}')
    elif not np.array_equal(X, ref_X):
        errors.append(
            'giá trị X không trùng tuyệt đối; '
            f'max_abs_error={float(np.max(np.abs(X - ref_X))):.12g}'
        )
    if not np.array_equal(Y, ref_Y):
        errors.append('Y/nhãn hoặc thứ tự mẫu không trùng')
    if not np.array_equal(normalized_files, normalized_ref_files):
        errors.append('Files/thứ tự WAV không trùng')

    if errors:
        raise RuntimeError(
            f'F0/{split} chưa đồng bộ Phase 2, dừng trước khi train:\n- '
            + '\n- '.join(errors)
        )
    print(f'PHASE2 PARITY PASS: F0/{split} | dtype={X.dtype} | shape={X.shape}')


def run_split(droot, row, split, force):
    c = load_config(row)
    var = row['variant_id']
    target = ARTIFACTS / 'features' / var
    target.mkdir(parents=True, exist_ok=True)
    meta = target / f'{split}_metadata.json'
    xp = target / f'X_{split}.npy'
    yp = target / f'Y_{split}.npy'
    fp = target / f'Files_{split}.npy'
    fingerprint = split_fingerprint(droot, split)

    if meta.is_file() and xp.is_file() and yp.is_file() and fp.is_file() and not force:
        obj = read_json(meta)
        if (
            obj.get('config_sha256') == row['config_sha256']
            and obj.get('dataset_root') == str(droot)
            and obj.get('dataset_fingerprint') == fingerprint
        ):
            print('SKIP', var, split)
            return
        raise RuntimeError(f'Stale artifact {var}/{split}: --force after review')

    records = list_split(droot, split)
    tensors = []
    labels = []
    names = []
    for path, label in records:
        audio = load_raw_window(path)
        mel = mel_from_wave(process_wave(audio, c), c)
        tensors.append(mel)
        labels.append(label)
        names.append(path.relative_to(droot).as_posix())

    # Giữ dtype thô đúng Phase 2 (float64 sau IIR/Log-Mel). Việc cast
    # float32 thuộc bước min-max trong 03_Train.py/04_Evaluate.py.
    X = np.stack(tensors)[..., None]
    Y = np.array(labels, dtype=np.int64)
    files = np.array(names)
    if not np.isfinite(X).all():
        raise FloatingPointError(f'NaN/Inf in {var}/{split}')

    phase2_parity = False
    if var == 'F0':
        assert_f0_matches_phase2(split, X, Y, files)
        phase2_parity = True

    np.save(xp, X)
    np.save(yp, Y)
    np.save(fp, files)
    write_json(
        meta,
        {
            'variant_id': var,
            'split': split,
            'shape': list(X.shape),
            'raw_feature_dtype': str(X.dtype),
            'phase2_f0_parity': phase2_parity,
            'config_sha256': row['config_sha256'],
            'dataset_root': str(droot),
            'dataset_fingerprint': fingerprint,
            'labels': '0 Asthma, 1 Non-Asthma',
            'sample_names': names,
            'test_used_for_selection': False,
        },
    )
    print('DONE', var, split, X.shape)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dataset-root')
    p.add_argument('--variant')
    p.add_argument('--include-test', action='store_true')
    p.add_argument('--force', action='store_true')
    a = p.parse_args()

    root = dataset_root(a.dataset_root)
    rows = enabled_plans(a.variant)
    for row in rows:
        for split in (('test',) if a.include_test else ('train', 'val')):
            run_split(root, row, split, a.force)


if __name__ == '__main__':
    main()
