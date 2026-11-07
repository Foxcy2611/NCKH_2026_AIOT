"""Lập kế hoạch cửa sổ theo session và trích xuất metric Quality Gate.

Quy trình gồm ba bước ``plan``, ``calibrate`` và ``test``. Tập Test chỉ được
đọc sau khi cấu hình đã được đóng băng. Script không sao chép, chuẩn hóa hoặc
thay đổi WAV; dữ liệu đầu vào phải là PCM16 mono 16 kHz giống firmware.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import wave
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from quality_utils import (SAMPLE_RATE, WINDOW_SAMPLES, QualityThresholds,
                           classify_audio, extract_metrics, file_sha256, load_frozen,
                            write_test_provenance, test_provenance_path)

# Tránh lỗi UnicodeEncodeError khi PowerShell đang dùng code page cp1252.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8', errors='replace')

HERE = Path(__file__).resolve().parent


def find_repo_root(start: Path) -> Path:
    """Tìm repository root dựa trên các thư mục đặc trưng của dự án."""
    resolved = start.resolve()
    for candidate in (resolved, *resolved.parents):
        if (
            (candidate / 'AI_Training_Model').is_dir()
            and (candidate / 'Experiments_Benchmarking').is_dir()
            and (candidate / 'Final_Project_NCKH').is_dir()
        ):
            return candidate
    raise FileNotFoundError(
        'Không tìm thấy repository root khi dò từ: ' + str(resolved)
    )


DEFAULT_REPO_ROOT = find_repo_root(HERE)
MANIFEST = HERE / 'results' / 'quality_window_manifest.csv'
CALIBRATION = HERE / 'results' / 'calibration_metrics.csv'
TEST = HERE / 'results' / 'test_metrics.csv'
FINAL = HERE / 'results' / 'final_quality_gate.json'
COLUMNS = ['qc_split', 'original_split', 'session_id', 'subtype', 'source_kind',
           'file_path', 'file_name', 'window_index', 'crop_start_s',
           'window_seconds', 'sample_rate', 'source_group']



# Nguồn authoritative theo Environment_Data_Collection_Guide_V2.md bản cuối.
# Đây là danh sách session thực tế, KHÔNG dùng số thứ tự 01..05 tự suy luận.
OFFICIAL_ENV_SPLIT_RELATIVE = Path(
    'AI_Training_Model/Phase1_Split_Data/Output/03_Cut_Environment/environment_session_split.csv'
)
EXPECTED_MAIN_BY_SUBTYPE = {
    'podcast': ['podcast_old_01', *(f'podcast_session_{i:02d}' for i in range(2, 7))],
    'fan': ['fan_session_01', 'fan_session_02', 'fan_session_03',
            'fan_session_04', 'fan_session_06'],
    'clap': [f'clap_session_{i:02d}' for i in range(1, 7)],
    'knock': [f'knock_session_{i:02d}' for i in range(1, 6)],
    'room_noise': [f'room_noise_session_{i:02d}' for i in range(1, 7)],
    'speech': [f'speech_session_{i:02d}' for i in range(1, 6)],
}
EXPECTED_SPLIT_COUNTS = {
    'podcast': (5, 1, 0),
    'fan': (4, 1, 0),
    'clap': (5, 1, 0),
    'knock': (4, 0, 1),
    'room_noise': (5, 0, 1),
    'speech': (4, 0, 1),
}
EXPECTED_LEGACY = {'keyfan_old_01': 'fan_keyboard', 'silence_old_01': 'silence'}


def _normalize_split(value: str) -> str:
    val = str(value).strip().casefold()
    aliases = {'validation': 'val', 'valid': 'val', 'training': 'train',
               'testing': 'test'}
    return aliases.get(val, val)


def _load_official_split(repo: Path) -> dict[str, str]:
    """Không đoán split từ Env_session.csv, ID filename hoặc random seed.

    CSV 03_Cut_Environment là authority cho 33 Environment chính.
    Dừng rõ ràng nếu không thể diễn giải schema của CSV đang có.
    """
    path = repo / OFFICIAL_ENV_SPLIT_RELATIVE
    if not path.is_file():
        raise FileNotFoundError(
            f'Không tìm thấy bảng chia session V2 chính thức: {path}. '
            'Cần chạy lại 03_Cut_Environment hoặc cung cấp CSV này; '
            'KHÔNG tự chia 20% unassigned làm Test.'
        )
    with path.open('r', encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        norm = {c.strip().casefold(): c for c in header}
        sid_col = next((norm[k] for k in ('session_id','source_session_id','session') if k in norm), None)
        split_col = next((norm[k] for k in ('split','dataset_split','assigned_split','split_name','set') if k in norm), None)
        if not sid_col or not split_col:
            raise ValueError(
                f'Schema chưa được hỗ trợ tại {path}: {header}. '
                'Cần cột session_id và split (Train/Val/Test), không được tự đoán.'
            )
        mapping = {}
        for row in reader:
            sid = str(row.get(sid_col) or '').strip()
            split = _normalize_split(row.get(split_col) or '')
            if not sid:
                continue
            if split not in ('train', 'val', 'test'):
                # CSV có thể có thêm dòng chú giải hoặc asset ngoài tập chính.
                if sid in {x for ids in EXPECTED_MAIN_BY_SUBTYPE.values() for x in ids}:
                    raise ValueError(f'Split V2 không hợp lệ: {sid}={split!r} trong {path}')
                continue
            if sid in mapping and mapping[sid] != split:
                raise ValueError(f'Session có hai split trái nhau trong CSV: {sid}')
            mapping[sid] = split
    expected = {sid for values in EXPECTED_MAIN_BY_SUBTYPE.values() for sid in values}
    missing = expected - set(mapping)
    if missing:
        raise ValueError(
            'Bảng split chính thức thiếu session thuộc inventory V2: '
            + ', '.join(sorted(missing))
        )
    for subtype, ids in EXPECTED_MAIN_BY_SUBTYPE.items():
        actual_counts = tuple(sum(mapping[sid] == split for sid in ids)
                              for split in ('train', 'val', 'test'))
        if actual_counts != EXPECTED_SPLIT_COUNTS[subtype]:
            raise ValueError(
                f'Chia tập {subtype} sai tài liệu V2: {actual_counts} != '
                f'{EXPECTED_SPLIT_COUNTS[subtype]}. Kiểm tra {path}'
            )
    return {sid: mapping[sid] for sid in expected}


def path_key(p: Path) -> str:
    return str(p.resolve()).casefold()


def _read_env(repo: Path) -> list[dict]:
    root = repo / 'AI_Training_Model' / 'Dataset_TuThu_v_Kaggle' / 'TuThu'
    csv_path = root / 'TKe' / 'Env_session.csv'
    wav_root = root / 'Record_Env'
    if not csv_path.exists():
        raise FileNotFoundError(f'Không tìm thấy Env_session.csv: {csv_path}')
    if not wav_root.exists():
        raise FileNotFoundError(f'Không tìm thấy Record_Env: {wav_root}')
    official_split = _load_official_split(repo)
    expected_main = set(official_split)
    expected_all = expected_main | set(EXPECTED_LEGACY)
    wav_index = defaultdict(list)
    for path in wav_root.rglob('*.wav'):
        wav_index[path.name.casefold()].append(path)
    with csv_path.open('r', encoding='utf-8-sig', newline='') as fh:
        source_rows = list(csv.DictReader(fh))
    out, seen_sessions = [], set()
    for row in source_rows:
        file_name = str(row.get('file_name') or '').strip()
        session = str(row.get('session_id') or '').strip()
        if not file_name or not session:
            raise ValueError('Env_session.csv phải có file_name và session_id')
        if session in seen_sessions:
            raise ValueError('session_id bị trùng trong Env_session.csv: ' + session)
        seen_sessions.add(session)
        if session not in expected_all:
            raise ValueError(
                f'Session không có trong inventory tài liệu V2: {session}. '
                'Cập nhật MD + script có kiểm soát trước khi plan lại.'
            )
        paths = wav_index.get(Path(file_name).name.casefold(), [])
        if len(paths) != 1:
            raise ValueError(
                f'Cần đúng một WAV master cho {file_name}, nhưng tìm thấy {len(paths)}'
            )
        capture_type = str(row.get('capture_type') or 'environment').strip().casefold()
        recorded_split = _normalize_split(row.get('split') or 'unassigned')
        if recorded_split not in ('train', 'val', 'test', 'unassigned', 'not_applicable', ''):
            raise ValueError(f'Env_session.csv split không hợp lệ: {session}={recorded_split}')
        subtype = str(row.get('subtype') or '').strip().casefold()
        if session in expected_main:
            subtype_expected = next(k for k, ids in EXPECTED_MAIN_BY_SUBTYPE.items() if session in ids)
            if subtype != subtype_expected:
                raise ValueError(f'Subtype sai inventory: {session} có {subtype!r}, cần {subtype_expected!r}')
            split = official_split[session]
            if recorded_split in ('train','val','test') and recorded_split != split:
                raise ValueError(
                    f'Metadata và official split mâu thuẫn tại {session}: '
                    f'Env_session={recorded_split}, official={split}'
                )
            if capture_type == 'quality_check_asset':
                raise ValueError(f'Environment chính không phải quality asset: {session}')
            source_kind = 'environment_master'
        else:
            if subtype != EXPECTED_LEGACY[session]:
                raise ValueError(f'Legacy subtype sai: {session}={subtype!r}')
            if session == 'silence_old_01':
                if recorded_split not in ('not_applicable','unassigned',''):
                    raise ValueError('silence_old_01 chỉ là quality asset, không được gán Test classifier')
                if capture_type != 'quality_check_asset':
                    raise ValueError('silence_old_01 phải có capture_type=quality_check_asset')
                split = 'not_applicable'
                source_kind = 'quality_check_asset'
            else:
                if recorded_split not in ('train','unassigned',''):
                    raise ValueError('keyfan_old_01 phải được giữ ở Train / Calibration')
                split = 'train'
                source_kind = 'environment_master'
        out.append(dict(session_id=session, subtype=subtype, original_split=split,
                        path=paths[0], source_kind=source_kind,
                        crop_offset=0.0, source_group=session))
    if seen_sessions != expected_all:
        raise ValueError(
            'Inventory Env_session.csv không khớp tài liệu V2. Thiếu: '
            + str(sorted(expected_all - seen_sessions))
            + '; thừa: ' + str(sorted(seen_sessions - expected_all))
        )
    return out


def _add_playback_sources(repo: Path) -> list[dict]:
    """Tùy chọn: chỉ lấy WAV playback PCM16 thực sự thu qua INMP441.

    Giữ nguyên split của dataset. ``source_group`` gom take01/take02 thuộc cùng
    nguồn. Không đưa WAV Kaggle 4 kHz vào phép hiệu chỉnh Quality Gate.
    """
    root = repo / 'AI_Training_Model' / 'Dataset_Chia_V2'
    if not root.exists():
        raise FileNotFoundError(root)
    out = []
    for label in ('Asthma', 'Non_Asthma_Disease'):
        for split in ('train', 'val', 'test'):
            folder = root / label / split
            for path in sorted(folder.rglob('*.wav')) if folder.exists() else []:
                if not re.search(r'__take0[12]\.wav$', path.name, re.IGNORECASE):
                    continue
                group = re.sub(r'__take0[12]\.wav$', '', path.name, flags=re.IGNORECASE)
                out.append(dict(session_id=f'PB_{label}_{group}', subtype=f'playback_{label.lower()}',
                                original_split=split, path=path, source_kind='playback',
                                crop_offset=1.0, source_group=f'PB_{label}_{group}'))
    return out


def _qc_assignments(sources: list[dict]) -> dict[str, str]:
    """Duy trì split lịch sử; KHÔNG tự bốc 20% Test từ nguồn unassigned."""
    decisions = {}
    for src in sources:
        sid = src['source_group']
        split = _normalize_split(src['original_split'])
        if split in ('train', 'val', 'not_applicable'):
            assigned = 'calibration'
        elif split == 'test':
            assigned = 'test'
        else:
            raise ValueError(
                f'Nguồn {sid} chưa có split chính thức ({split!r}). '
                'Không được tự gán ngẫu nhiên để nghiệm thu Quality Gate.'
            )
        if sid in decisions and decisions[sid] != assigned:
            raise ValueError(f'Playback/session bị leakage Calibration–Test: {sid}')
        decisions[sid] = assigned
    return decisions


def _inspect_wav_header(path: Path) -> tuple[int, int]:
    with wave.open(str(path), 'rb') as wf:
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != SAMPLE_RATE or wf.getcomptype() != 'NONE':
            raise ValueError(f'Only PCM16 mono 16000Hz permitted: {path}')
        return wf.getnframes(), wf.getframerate()


def _window_starts(nframes: int, offset: float, count: int, kind: str) -> list[int]:
    first = int(round(offset * SAMPLE_RATE))
    max_start = nframes - WINDOW_SAMPLES
    if first > max_start:
        raise ValueError(f'Audio shorter than 5s from offset {offset}')
    if kind == 'playback':
        return [first]
    # Chọn cửa sổ không chồng nhau theo quy tắc xác định từ bản ghi master.
    allowable = max_start - first
    starts = [first + int(round(allowable * f)) for f in (.18, .76)] if count == 2 else [first + allowable // 2]
    if count == 2 and starts[1] - starts[0] < WINDOW_SAMPLES:
        starts = [first, max_start] if max_start-first >= WINDOW_SAMPLES else [first]
    if len(set(starts)) < len(starts):
        starts = sorted(set(starts))
    return starts


def plan(repo: Path, manifest: Path, windows_per_session: int, include_playback: bool) -> None:
    if manifest.exists():
        raise FileExistsError(
            f'Manifest đã tồn tại: {manifest}. '
            'Hãy lưu trữ lần chạy hiện tại trước khi lập kế hoạch lại.'
        )
    sources = _read_env(repo)
    if include_playback:
        sources.extend(_add_playback_sources(repo))
    decisions = _qc_assignments(sources)
    print('Đã xác minh 33 Environment V2 bằng environment_session_split.csv; 2 legacy giữ Calibration.')
    rows = []
    for source in sources:
        nframes, _ = _inspect_wav_header(source['path'])
        try:
            starts = _window_starts(nframes, source['crop_offset'], windows_per_session, source['source_kind'])
        except ValueError as exc:
            raise ValueError(f'{source["path"]}: {exc}') from exc
        for i, sample_start in enumerate(starts, 1):
            rows.append(dict(qc_split=decisions[source['source_group']],
                             original_split=source['original_split'],
                             session_id=source['session_id'], subtype=source['subtype'],
                             source_kind=source['source_kind'], file_path=str(source['path'].resolve()),
                             file_name=source['path'].name, window_index=i,
                             crop_start_s=f'{sample_start / SAMPLE_RATE:.6f}',
                             window_seconds=5, sample_rate=SAMPLE_RATE,
                             source_group=source['source_group']))
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with manifest.open('w', newline='', encoding='utf-8-sig') as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS); writer.writeheader(); writer.writerows(rows)
    print('Manifest:', manifest)
    print('Số cửa sổ:', len(rows), '| Số session:', len(set(x['source_group'] for x in rows)))
    print('Session theo split:', {split: len({x['source_group'] for x in rows if x['qc_split'] == split}) for split in ('calibration', 'test')})
    print('Cửa sổ theo split:', dict(Counter(x['qc_split'] for x in rows)))
    if not any(row['qc_split'] == 'test' for row in rows):
        print(
            'CẢNH BÁO: chưa có session Test độc lập; '
            'hãy thu hoặc phân bổ session riêng trước khi đóng băng cấu hình.'
        )


def _read_pcm_window(path: Path, offset_s: float) -> np.ndarray:
    with wave.open(str(path), 'rb') as wf:
        if (wf.getnchannels(), wf.getsampwidth(), wf.getframerate(), wf.getcomptype()) != (1, 2, SAMPLE_RATE, 'NONE'):
            raise ValueError('WAV không đạt chuẩn PCM16 mono 16 kHz: ' + str(path))
        start = int(round(float(offset_s) * SAMPLE_RATE))
        if start + WINDOW_SAMPLES > wf.getnframes():
            raise ValueError('Cửa sổ vượt quá độ dài WAV: ' + str(path))
        wf.setpos(start)
        raw = wf.readframes(WINDOW_SAMPLES)
    x = np.frombuffer(raw, dtype='<i2').copy()
    if len(x) != WINDOW_SAMPLES:
        raise ValueError('Không đọc đủ số mẫu PCM yêu cầu: ' + str(path))
    return x


def extract(stage: str, manifest: Path, calibration: Path, test: Path, frozen: Path) -> None:
    if not manifest.exists():
        raise FileNotFoundError('Cần chạy bước plan trước: ' + str(manifest))
    selected_split = 'calibration' if stage == 'calibrate' else 'test'
    if stage == 'test':
        params, cfg = load_frozen(frozen, file_sha256(manifest))
        if not calibration.exists() or cfg['calibration_metrics_sha256'] != file_sha256(calibration):
            raise ValueError('CSV Calibration đã thay đổi sau khi đóng băng cấu hình')
    else:
        # Chỉ dùng cấu hình baseline để trích metric; notebook sẽ chọn ngưỡng cuối.
        params = QualityThresholds()
    with manifest.open('r', newline='', encoding='utf-8-sig') as fh:
        windows = [r for r in csv.DictReader(fh) if r['qc_split'] == selected_split]
    if not windows:
        raise ValueError(
            f'Không có cửa sổ thuộc split {selected_split}; '
            'hãy kiểm tra manifest và cách chia session.'
        )
    rows = []
    for row in windows:
        audio = _read_pcm_window(Path(row['file_path']), float(row['crop_start_s']))
        result, metrics = classify_audio(audio, params)
        # Ngưỡng MAV=20 là baseline firmware. Lưu MAV của từng block dưới dạng
        # JSON gọn để notebook có thể sweep mà không phải đọc lại WAV.
        x_abs = np.abs(audio.astype(np.int32))
        mavs = [int(x_abs[i:i+256].astype(np.uint64).sum() // len(x_abs[i:i+256]))
                for i in range(0, len(audio), 256)]
        out = {**row, **metrics, 'baseline_state': result,
               'block_mav_json': json.dumps(mavs, separators=(',', ':'))}
        if stage == 'test':
            # Tính lại bằng ngưỡng active block và clipping đã đóng băng.
            final_metrics = extract_metrics(audio,
                block_size=params.block_size, clip_level=params.clip_level,
                active_block_threshold=params.active_block_threshold)
            out.update(final_metrics)
            from quality_utils import decide
            out['final_state'] = decide(final_metrics, params)
        rows.append(out)
    target = calibration if stage == 'calibrate' else test
    if target.exists() or (stage == 'test' and test_provenance_path(target).exists()):
        raise FileExistsError(
            'Output/provenance đã tồn tại. Hãy lưu trữ thí nghiệm cũ trước: ' + str(target)
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('w', newline='', encoding='utf-8-sig') as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)
    if stage == 'test':
        sidecar = write_test_provenance(target, frozen, manifest, calibration)
        print('Provenance:', sidecar)
    print(f'{stage}: {len(rows)} cửa sổ -> {target}')
    print('Theo subtype:', dict(Counter(x['subtype'] for x in rows)))
    if stage == 'test':
        print('Kết quả Test Quality Gate:', dict(Counter(x['final_state'] for x in rows)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['plan', 'calibrate', 'test'])
    parser.add_argument('--repo-root', type=Path, default=DEFAULT_REPO_ROOT)
    parser.add_argument('--manifest', type=Path, default=MANIFEST)
    parser.add_argument('--windows-per-session', type=int, choices=[1, 2], default=2)
    parser.add_argument('--with-playback', action='store_true',
                        help='Thêm WAV PCM16 __take và giữ nguyên split của nguồn gốc')
    args = parser.parse_args()
    if args.stage == 'plan':
        plan(args.repo_root, args.manifest, args.windows_per_session, args.with_playback)
    else:
        extract(args.stage, args.manifest, CALIBRATION, TEST, FINAL)


if __name__ == '__main__':
    main()
