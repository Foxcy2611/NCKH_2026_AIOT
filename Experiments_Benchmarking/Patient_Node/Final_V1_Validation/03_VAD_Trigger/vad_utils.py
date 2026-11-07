"""Mô phỏng VAD energy-based của I2S_Mic.cpp (không chạy model/voting).

PCM16 raw 16 kHz, chunk 256, MAV nguyên: floor(sum(abs(x))/len(chunk)).
VAD so sánh CHẶT MAV > threshold; reset chuỗi ngay khi không vượt.
Monitor reset: warmup 100 chunks, ring được đổ đầy >=16000 mẫu.
Playback pre-armed: warmup đã xong trước khi phát; 1 giây đầu WAV làm ring.
Sau trigger: hồi phục onset từ chunk active đầu, capture 80000 mẫu kể từ onset,
không VAD khi đang capture, reset ring sau capture (không warmup lại).
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import numpy as np

SAMPLE_RATE = 16_000
CHUNK_SAMPLES = 256
TOTAL_SAMPLES = 80_000
PRE_ROLL_SAMPLES = 16_000
WARMUP_CHUNKS = 100


@dataclass(frozen=True)
class VadConfig:
    threshold: int = 75
    consecutive: int = 4
    chunk_samples: int = CHUNK_SAMPLES
    sample_rate: int = SAMPLE_RATE
    pre_roll_samples: int = PRE_ROLL_SAMPLES
    capture_samples: int = TOTAL_SAMPLES
    warmup_chunks: int = WARMUP_CHUNKS

    def validate(self):
        if not (0 <= self.threshold <= 32768):
            raise ValueError('threshold nằm ngoài khoảng hợp lệ')
        if not (1 <= self.consecutive <= 30):
            raise ValueError('consecutive phải từ 1 đến 30')
        if self.chunk_samples != 256 or self.sample_rate != 16000:
            raise ValueError('Để so sánh firmware, chunk=256 và sample_rate=16000 là cố định')
        if self.pre_roll_samples != 16000 or self.capture_samples != 80000 or self.warmup_chunks != 100:
            raise ValueError('Giữ nguyên pre-roll=16000, capture=80000, warmup=100 khi nghiệm thu')
        if self.consecutive * self.chunk_samples > self.pre_roll_samples:
            raise ValueError('Ring không đủ chứa onset candidate')


def pcm16_chunk_mav(samples: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Trả về MAV uint32 cho từng chunk và số mẫu từng chunk (last chunk có thể ngắn)."""
    x = np.asarray(samples)
    if x.ndim != 1 or x.dtype != np.int16:
        raise ValueError(f'PCM16 mono 1D cần int16, nhận {x.dtype}/{x.shape}')
    full, rest = divmod(len(x), CHUNK_SAMPLES)
    if full:
        abs_values = np.abs(x[:full * CHUNK_SAMPLES].astype(np.int32))
        sums = abs_values.reshape(-1, CHUNK_SAMPLES).sum(axis=1, dtype=np.uint64)
        mav = sums // CHUNK_SAMPLES
    else:
        mav = np.empty((0,), dtype=np.uint64)
    lengths = np.full(full, CHUNK_SAMPLES, dtype=np.int32)
    if rest:
        tail_sum = np.abs(x[full * CHUNK_SAMPLES:].astype(np.int32)).sum(dtype=np.uint64)
        mav = np.append(mav, tail_sum // rest)
        lengths = np.append(lengths, rest)
    return mav.astype(np.uint32), lengths


def simulate(mav: np.ndarray, lengths: np.ndarray, config: VadConfig,
             *, playback_prearmed: bool = False, max_triggers: int | None = None) -> list[dict]:
    """Mô phỏng tuần tự LISTEN -> CAPTURE -> RESET -> LISTEN.

    playback_prearmed=True: warmup đã diễn ra *trước* WAV, nhưng ring vẫn cần
    lấp 1s từ đầu file; phù hợp clip phát sau khi UI LISTENING. Không được gọi
    đây là bản mô phỏng power-on của ESP32.

    max_triggers=None: mô phỏng liên tục đến cuối file để thống kê activation rate.
    max_triggers=3: kiểm tra chu kỳ ba trigger (KHÔNG mô phỏng AI/Quality vote).
    """
    config.validate()
    mav = np.asarray(mav)
    lengths = np.asarray(lengths)
    if mav.ndim != 1 or lengths.ndim != 1 or len(mav) != len(lengths):
        raise ValueError('mav/lengths phải cùng số chunk')
    if np.any(lengths <= 0) or np.any(lengths > config.chunk_samples):
        raise ValueError('Chunk length ngoài (0,256]')
    if max_triggers is not None and max_triggers < 1:
        raise ValueError('max_triggers phải >= 1 hoặc None')

    starts = np.concatenate(([0], np.cumsum(lengths, dtype=np.int64)))
    total = int(starts[-1]); fs = config.sample_rate
    state = 'LISTEN'
    warmup_remaining = 0 if playback_prearmed else config.warmup_chunks
    ring_valid = 0
    active_count = 0
    candidate_start = -1
    candidate_samples = 0
    capture_target = -1
    saved = None
    events: list[dict] = []

    for i in range(len(mav)):
        s, e, n = int(starts[i]), int(starts[i+1]), int(lengths[i])
        if state == 'CAPTURE':
            # Firmware tiếp tục nhận nguyên chunk; có thể phần cuối chunk vượt 80000.
            if e >= capture_target:
                assert saved is not None
                saved['capture_complete'] = True
                saved['capture_end_s'] = round(capture_target / fs, 6)
                saved['complete_within_file'] = True
                events.append(saved)
                saved = None
                state = 'LISTEN'
                ring_valid = 0
                active_count = 0
                candidate_start = -1
                candidate_samples = 0
                # Phần dư trong chunk cuối capture bị bỏ, đúng I2S_MonitorCaptureStep.
                if max_triggers is not None and len(events) >= max_triggers:
                    break
            continue

        if warmup_remaining:
            warmup_remaining -= 1
            continue

        ring_valid = min(config.pre_roll_samples, ring_valid + n)
        if ring_valid < config.pre_roll_samples:
            continue

        if int(mav[i]) > config.threshold:
            if active_count == 0:
                candidate_start = s
                candidate_samples = 0
            if active_count < config.consecutive:
                active_count += 1
                candidate_samples += n
        else:
            active_count = 0
            candidate_start = -1
            candidate_samples = 0

        if active_count >= config.consecutive:
            # Candidate onset = chunk active đầu tiên, không phải âm học onset thật.
            saved = {
                'candidate_onset_s': round(candidate_start / fs, 6),
                'confirmed_s': round(e / fs, 6),
                'confirmation_delay_ms': round((e-candidate_start)*1000/fs, 3),
                'recovered_samples': int(candidate_samples),
                'recovered_ms': round(candidate_samples*1000/fs, 3),
                'confirm_mav': int(mav[i]),
                'capture_complete': False,
                'complete_within_file': False,
                'capture_end_s': None,
            }
            capture_target = candidate_start + config.capture_samples
            active_count = 0
            state = 'CAPTURE'
            # Bình thường capture_target > e: onset mới bắt đầu vài chunk trước.
            # Trường hợp đặc biệt capture_samples rất ngắn không xảy ra bởi hợp đồng.
    if saved is not None:
        # WAV hết trước khi firmware có thể thu đầy cửa sổ; không phải lỗi phần cứng.
        events.append(saved)
    return events


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def freeze(path: Path, cfg: VadConfig, manifest: Path, calibration_csv: Path,
           calibration_npz: Path, reason: str) -> None:
    cfg.validate()
    if path.exists():
        raise FileExistsError(f'Đã freeze: {path}')
    if not reason.strip():
        raise ValueError('Phải ghi lý do lựa chọn trên Calibration')
    data = {
        'status': 'FROZEN', 'experiment': '03_VAD_Trigger',
        'selection_split': 'calibration', 'test_used_for_selection': False,
        'config': asdict(cfg),
        'source_manifest_sha256': sha256(manifest),
        'calibration_metrics_sha256': sha256(calibration_csv),
        'calibration_mav_sha256': sha256(calibration_npz),
        'note': reason.strip(),
        'limitations': 'Energy-based event activation, not respiratory-content recognition. 3-vote logic is owned by State_Machine.',
    }
    path.parent.mkdir(exist_ok=True,parents=True)
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')


def load_frozen(path: Path, manifest: Path, cal_csv: Path, cal_npz: Path) -> tuple[VadConfig, dict]:
    data=json.loads(path.read_text(encoding='utf-8'))
    if data.get('status') != 'FROZEN' or data.get('test_used_for_selection') is not False:
        raise ValueError('Chưa freeze hợp lệ')
    for key,p in [('source_manifest_sha256',manifest),('calibration_metrics_sha256',cal_csv),
                  ('calibration_mav_sha256',cal_npz)]:
        if not p.exists() or sha256(p) != data.get(key):
            raise ValueError('Dữ liệu đã đổi sau Freeze: '+str(p))
    cfg=VadConfig(**data['config'])
    cfg.validate()
    return cfg,data
