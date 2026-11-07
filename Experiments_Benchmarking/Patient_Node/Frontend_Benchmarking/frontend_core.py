"""Thư viện dùng chung và hợp đồng Front-End của toàn bộ thí nghiệm.

Tác dụng:
- Khai báo baseline F0, protocol, sample rate, thời lượng và quy ước nhãn.
- Tìm dataset, liệt kê split, crop WAV và tạo fingerprint truy vết.
- Thực hiện normalize, Butterworth, pre-emphasis và Log-Mel thống nhất.
- Cung cấp helper đọc/ghi CSV, JSON, plan và định danh trial.

Đây là module được các script 00–05 import, không phải bước chạy độc lập.
Module không import firmware/deployment và không tự train hoặc evaluate model.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / 'artifacts'
RESULTS = ROOT / 'results'
FIGURES = ROOT / 'figures'
# V3 khóa ngữ nghĩa dtype theo đúng Phase 2 gốc:
# Log-Mel thô được giữ nguyên float64 sau scipy.signal.lfilter/librosa và chỉ
# chuyển sang float32 sau khi min-max trong bước train/evaluate.
# Đổi protocol để artifact float32 cũ không thể bị tái sử dụng nhầm.
PROTOCOL = 'NCKH_FRONTEND_V3_PHASE2_EXACT_2026_10'
SR, DURATION, SAMPLES = 16000, 5.0, 80000
LABEL_DIRS = [('Asthma', 0), ('Non_Asthma_Disease', 1)]


@dataclass(frozen=True)
class Frontend:
    low_cut_hz: float = 100.0
    high_cut_hz: float = 2000.0
    filter_order: int = 5
    pre_emphasis: float = 0.97
    n_mels: int = 64
    hop_length: int = 625
    n_fft: int = 1024


BASELINE = Frontend()
CONFIG_KEYS = tuple(asdict(BASELINE))


def validate(c: Frontend) -> None:
    if not (0 < c.low_cut_hz < c.high_cut_hz < SR / 2):
        raise ValueError(f'Invalid low/high cut: {c}')
    if c.filter_order not in (0, 3, 5, 7):
        raise ValueError('The reference study supports order 0/3/5/7; extend explicitly if needed')
    if not (0 <= c.pre_emphasis < 1):
        raise ValueError('Invalid pre-emphasis')
    if c.n_mels < 8 or c.n_mels > 256 or c.hop_length < 1 or c.n_fft < 256:
        raise ValueError('Invalid Mel resolution')
    if c.n_fft % 2 or c.n_fft > SAMPLES:
        raise ValueError('n_fft must be even and <= audio length')
    if c.hop_length > c.n_fft:
        raise ValueError('hop > n_fft leaves temporal gaps; define separate protocol if intended')


def digest(c: Frontend) -> str:
    validate(c)
    blob = {
        'protocol': PROTOCOL,
        'frontend': asdict(c),
        'sr': SR,
        'duration': DURATION,
        'window': 'hann',
        'mel_norm': 'slaney',
        'fft_center': True,
        'filter_impl': 'butter_ba_lfilter',
        'playback_offset_seconds': 1.0,
    }
    return hashlib.sha256(json.dumps(blob, sort_keys=True).encode()).hexdigest()


def safe_id(s: str) -> str:
    if not re.fullmatch(r'[a-zA-Z0-9][\w.-]*', str(s)):
        raise ValueError(f'Unsafe identifier: {s}')
    return str(s)


def dataset_root(override=None) -> Path:
    if override:
        p = Path(override).expanduser().resolve()
    else:
        search = [ROOT, *ROOT.parents, Path.cwd(), *Path.cwd().parents]
        p = next(
            (
                q / 'AI_Training_Model' / 'Dataset_Chia_V2'
                for q in search
                if (q / 'AI_Training_Model' / 'Dataset_Chia_V2').is_dir()
            ),
            None,
        )
        if p is None:
            raise FileNotFoundError('Dataset_Chia_V2 not found. Pass --dataset-root PATH')
    if not p.is_dir():
        raise FileNotFoundError(f'Invalid dataset root: {p}')
    return p


def list_split(root: Path, split: str) -> list[tuple[Path, int]]:
    if split not in ('train', 'val', 'test'):
        raise ValueError(f'Invalid split: {split}')
    output = []
    for folder, label in LABEL_DIRS:
        d = root / folder / split
        if not d.is_dir():
            raise FileNotFoundError(f'Missing split folder: {d}')
        wavs = sorted(d.glob('*.wav'))
        if not wavs:
            raise FileNotFoundError(f'No WAV files in {d}')
        output.extend((p, label) for p in wavs)
    return output


def split_fingerprint(root: Path, split: str) -> str:
    """Record changes to source audio files without reading the Test audio itself."""
    rows = []
    for path, label in list_split(root, split):
        st = path.stat()
        rows.append((path.relative_to(root).as_posix(), label, st.st_size, st.st_mtime_ns))
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False).encode('utf-8')).hexdigest()


def load_raw_window(path: Path) -> np.ndarray:
    import librosa

    offset = 1.0 if path.stem.casefold().endswith(('__take01', '__take02')) else 0.0
    x, _ = librosa.load(
        str(path),
        sr=SR,
        mono=True,
        offset=offset,
        duration=DURATION,
        dtype=np.float32,
        res_type='soxr_hq',
    )
    return librosa.util.fix_length(x, size=SAMPLES, axis=-1, mode='constant')


def process_wave(x: np.ndarray, c: Frontend) -> np.ndarray:
    """Baseline-compatible: librosa normalize -> butter output='ba' -> lfilter -> preemphasis."""
    import librosa
    from scipy.signal import butter, lfilter

    validate(c)
    x = librosa.util.normalize(x, norm=np.inf, axis=0, threshold=None, fill=None)
    if c.filter_order:
        b, a = butter(
            c.filter_order,
            [c.low_cut_hz / (SR / 2), c.high_cut_hz / (SR / 2)],
            btype='band',
            analog=False,
            output='ba',
        )
        x = lfilter(b, a, x, axis=-1, zi=None)
    x = np.append(x[0], x[1:] - c.pre_emphasis * x[:-1])
    if not np.isfinite(x).all():
        raise FloatingPointError('Nonfinite output from IIR/preemphasis; try safer order separately')
    return x


def mel_from_wave(x: np.ndarray, c: Frontend) -> np.ndarray:
    import librosa

    mel = librosa.feature.melspectrogram(
        y=x,
        sr=SR,
        n_fft=c.n_fft,
        hop_length=c.hop_length,
        win_length=c.n_fft,
        n_mels=c.n_mels,
        fmin=c.low_cut_hz,
        fmax=c.high_cut_hz,
        center=True,
        htk=False,
        norm='slaney',
        window='hann',
        pad_mode='constant',
        power=2.0,
        dtype=np.float32,
    )
    db = librosa.power_to_db(mel, ref=np.max, amin=1e-10, top_db=80.0)
    expected = (c.n_mels, 1 + SAMPLES // c.hop_length)
    if db.shape != expected or not np.isfinite(db).all():
        raise ValueError(f'Mel expected {expected}, got {db.shape}')
    # KHÔNG ép float32 tại đây. Preprocess_Audio.py của Phase 2 cũng trả
    # thẳng mel_db; do lfilter nhận hệ số float64 nên artifact X_*_mel.npy
    # gốc là float64. Training_Model.py chỉ cast sau phép min-max.
    return db


def phase2_preprocess_dir() -> Path:
    """Tìm artifact preprocess V1 gốc dùng làm oracle cho F0."""
    for ancestor in [ROOT, *ROOT.parents]:
        candidate = (
            ancestor
            / 'AI_Training_Model'
            / 'Phase2_Preprocess_&_Traning'
            / 'Output_Preprocess'
        )
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(
        'Không tìm thấy Phase2_Preprocess_&_Traning/Output_Preprocess '
        'để kiểm chứng baseline F0.'
    )


def load_config(row: dict) -> Frontend:
    values = {
        k: (
            int(row[k])
            if k in ('filter_order', 'n_mels', 'hop_length', 'n_fft')
            else float(row[k])
        )
        for k in CONFIG_KEYS
    }
    c = Frontend(**values)
    validate(c)
    return c


def read_rows(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def write_rows(path: Path, rows: list[dict], fields=None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows and fields is None:
        raise ValueError('Cannot infer CSV schema from no rows')
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]), extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf8')


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf8'))


def plans() -> list[dict]:
    p = RESULTS / 'experiment_plan.csv'
    rows = read_rows(p)
    for row in rows:
        if digest(load_config(row)) != row['config_sha256']:
            raise ValueError(f'Plan config changed after creation: {row["variant_id"]}')
    return rows


def enabled_plans(variant=None) -> list[dict]:
    rows = [r for r in plans() if str(r['enabled']) in ('1','true','True')]
    if variant:
        rows = [r for r in rows if r['variant_id'] == variant]
    if not rows:
        raise ValueError('No enabled candidate. Check configs/candidates.csv / plan')
    return rows


def trial_id(variant: str, architecture: str, seed: int) -> str:
    return f'{safe_id(variant)}__{safe_id(architecture)}__s{seed}'


def default_builder_path() -> Path:
    p = ROOT
    for ancestor in [ROOT, *ROOT.parents]:
        builder = (
            ancestor
            / 'AI_Training_Model'
            / 'Phase2_Preprocess_&_Traning'
            / 'Model_Architectures'
            / 'V1_SepConv2D_Flatten.py'
        )
        if builder.is_file():
            return builder
    # Different training phases may organize architecture modules differently.
    for ancestor in [ROOT, *ROOT.parents]:
        ai = ancestor / 'AI_Training_Model'
        if ai.is_dir():
            matches = list(ai.glob('**/V1_SepConv2D_Flatten.py'))
            if matches:
                return sorted(matches)[0]
    raise FileNotFoundError('Cannot locate V1_SepConv2D_Flatten.py; pass --builder-path')
