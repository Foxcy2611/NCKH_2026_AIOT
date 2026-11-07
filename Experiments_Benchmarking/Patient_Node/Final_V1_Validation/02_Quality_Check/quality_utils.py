"""Logic tương đương ``Final_Project_NCKH/Patient_Node/src/Quality_Check.cpp``.

Đầu vào là PCM16 thu ở 16 kHz trước mọi bước chuẩn hóa/DSP. Firmware tính MAV
nguyên theo block (có phép chia lấy phần nguyên), dùng so sánh chặt ``>`` và
ưu tiên trạng thái INACTIVE, sau đó TOO_LOUD rồi TOO_WEAK.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16000
WINDOW_SECONDS = 5
WINDOW_SAMPLES = SAMPLE_RATE * WINDOW_SECONDS


@dataclass(frozen=True)
class QualityThresholds:
    min_rms: float = 20.0
    min_active_ratio: float = 0.01
    max_clipped_ratio: float = 0.01
    clip_level: int = 32000
    active_block_threshold: int = 20
    block_size: int = 256

    def validate(self) -> None:
        if not (0 <= self.min_rms <= 32768):
            raise ValueError('min_rms phải nằm trong [0, 32768]')
        if not (0 <= self.min_active_ratio <= 1):
            raise ValueError('min_active_ratio phải nằm trong [0, 1]')
        if not (0 <= self.max_clipped_ratio <= 1):
            raise ValueError('max_clipped_ratio phải nằm trong [0, 1]')
        if not (1 <= self.clip_level <= 32768):
            raise ValueError('clip_level phải nằm trong [1, 32768]')
        if not (0 <= self.active_block_threshold <= 32768):
            raise ValueError('active_block_threshold phải nằm trong [0, 32768]')
        if not (1 <= self.block_size <= WINDOW_SAMPLES):
            raise ValueError('block_size nằm ngoài phạm vi hợp lệ')


def extract_metrics(samples: np.ndarray, *, block_size: int = 256, clip_level: int = 32000,
                    active_block_threshold: int = 20) -> dict:
    """Khớp C++: tổng trị tuyệt đối uint64, chia nguyên, abs(-32768)=32768.

    RMS được tính trên toàn bộ mẫu int16, không chuẩn hóa biên độ.
    """
    x = np.asarray(samples)
    if x.dtype != np.int16 or x.ndim != 1 or x.size != WINDOW_SAMPLES:
        raise ValueError(
            f'Cần đúng 80000 mẫu int16 mono, nhận dtype={x.dtype}, shape={x.shape}'
        )
    if not 1 <= block_size <= WINDOW_SAMPLES:
        raise ValueError('block_size không hợp lệ')
    absolute = np.abs(x.astype(np.int32))
    # Firmware dùng điều kiện >, không phải >=.
    clipped_count = int(np.count_nonzero(absolute > clip_level))
    peak = int(absolute.max())
    square_sum = np.sum(x.astype(np.float64)**2, dtype=np.float64)
    block_mav = np.array([
        int(np.sum(absolute[start:start+block_size], dtype=np.uint64) //
            len(absolute[start:start+block_size]))
        for start in range(0, len(absolute), block_size)
    ], dtype=np.int32)
    active_blocks = int(np.count_nonzero(block_mav > active_block_threshold))
    total_blocks = int(len(block_mav))
    return {
        'rms': float(math.sqrt(float(square_sum) / len(x))),
        'peak': peak,
        'clipped_samples': clipped_count,
        'clipped_ratio': clipped_count / len(x),
        'active_blocks': active_blocks,
        'total_blocks': total_blocks,
        'active_ratio': active_blocks / total_blocks,
        'dc_offset': float(np.mean(x.astype(np.float64))),
        'rms_dbfs': float(20 * np.log10(max(math.sqrt(float(square_sum) / len(x)), 1e-12) / 32768)),
    }


def decide(metrics: dict, params: QualityThresholds) -> str:
    params.validate()
    # Giữ đúng thứ tự ưu tiên và cơ chế dừng sớm của firmware.
    if float(metrics['active_ratio']) < params.min_active_ratio:
        return 'AUDIO_INACTIVE'
    if float(metrics['clipped_ratio']) > params.max_clipped_ratio:
        return 'AUDIO_TOO_LOUD'
    if float(metrics['rms']) < params.min_rms:
        return 'AUDIO_TOO_WEAK'
    return 'AUDIO_OK'


def classify_audio(samples: np.ndarray, params: QualityThresholds) -> tuple[str, dict]:
    m = extract_metrics(samples, block_size=params.block_size,
                        clip_level=params.clip_level,
                        active_block_threshold=params.active_block_threshold)
    return decide(m, params), m


def file_sha256(path: Path) -> str:
    hash_obj = hashlib.sha256()
    with Path(path).open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024*1024), b''):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def freeze_config(path: Path, params: QualityThresholds, manifest_sha: str,
                  calibration_sha: str, selection_note: str, calibration_summary: dict) -> Path:
    params.validate()
    if not selection_note.strip():
        raise ValueError('Phải ghi lý do chọn ngưỡng dựa trên Calibration')
    if path.exists():
        raise FileExistsError('Cấu hình đóng băng đã tồn tại: ' + str(path))
    payload = {
        'status': 'FROZEN',
        'experiment': 'Patient_Node_Final_V1_Quality_Gate',
        'selection_split': 'calibration',
        'test_used_for_selection': False,
        'audio_contract': 'PCM16 LE mono, 16000Hz, 80000 samples, PRE-normalization',
        'metrics_contract': 'Exact Quality_Check.cpp block integer-MAV, strict comparisons, priority',
        'thresholds': asdict(params),
        'manifest_sha256': manifest_sha,
        'calibration_metrics_sha256': calibration_sha,
        'calibration_summary': calibration_summary,
        'selection_note': selection_note.strip(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return path


def load_frozen(path: Path, expected_manifest_sha: str | None = None) -> tuple[QualityThresholds, dict]:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if payload.get('status') != 'FROZEN' or payload.get('selection_split') != 'calibration':
        raise ValueError('Quality Gate chưa được đóng băng')
    if payload.get('test_used_for_selection') is not False:
        raise ValueError('Vi phạm nguyên tắc: không được dùng Test để chọn ngưỡng')
    if expected_manifest_sha and payload.get('manifest_sha256') != expected_manifest_sha:
        raise ValueError('Manifest đã đổi sau khi đóng băng; không được mở Test')
    params = QualityThresholds(**payload['thresholds'])
    params.validate()
    return params, payload


def test_provenance_path(test_csv: Path) -> Path:
    return Path(test_csv).with_name(Path(test_csv).stem + '_provenance.json')


def expected_test_provenance(test_csv: Path, frozen_json: Path,
                             manifest_csv: Path, calibration_csv: Path) -> dict:
    """Hashes used to prevent reusing held-out Test from another frozen run."""
    params, contract = load_frozen(frozen_json, file_sha256(manifest_csv))
    cal_sha = file_sha256(calibration_csv)
    if contract.get('calibration_metrics_sha256') != cal_sha:
        raise ValueError('Calibration không còn khớp cấu hình FROZEN')
    # Also bind to the actual PCM16 source WAVs; manifest paths alone do not
    # detect if a recording was replaced after the historical Test extraction.
    with Path(test_csv).open('r', encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(fh)
        if 'file_path' not in (reader.fieldnames or []):
            raise ValueError('Test CSV thiếu cột file_path để xác minh nguồn WAV')
        wav_paths = sorted({str(Path(row['file_path']).resolve())
                            for row in reader})
    return {
        'status': 'FROZEN_TEST_RESULT',
        'experiment': 'Patient_Node_Final_V1_Quality_Gate',
        'test_metrics_sha256': file_sha256(test_csv),
        'frozen_config_sha256': file_sha256(frozen_json),
        'manifest_sha256': file_sha256(manifest_csv),
        'calibration_metrics_sha256': cal_sha,
        'test_source_wav_sha256': {p: file_sha256(Path(p)) for p in wav_paths},
    }


def write_test_provenance(test_csv: Path, frozen_json: Path,
                          manifest_csv: Path, calibration_csv: Path) -> Path:
    """Create a provenance sidecar only for newly generated held-out results."""
    target = test_provenance_path(test_csv)
    data = expected_test_provenance(test_csv, frozen_json, manifest_csv, calibration_csv)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8') as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write('\n')
    return target


def verify_test_provenance(test_csv: Path, frozen_json: Path,
                           manifest_csv: Path, calibration_csv: Path) -> dict:
    """Reject stale Test CSVs, including old results without a sidecar."""
    target = test_provenance_path(test_csv)
    if not target.is_file():
        raise FileNotFoundError(
            'Test cache thiếu provenance: ' + str(target) +
            '. Lưu trữ results cũ rồi chạy lại stage test; KHÔNG tự gắn tag.'
        )
    actual = json.loads(target.read_text(encoding='utf-8'))
    if actual.get('test_metrics_sha256') != file_sha256(test_csv):
        raise ValueError('Test CSV đã thay đổi so với provenance FROZEN')
    expected = expected_test_provenance(test_csv, frozen_json, manifest_csv, calibration_csv)
    if actual != expected:
        raise ValueError('Test cache/provenance sai SHA hoặc không thuộc bản FROZEN hiện tại')
    return actual
