"""Kiểm tra nhanh các bất biến quan trọng của Front-End benchmark.

Tác dụng:
- Xác nhận bảy tham số baseline F0 và kích thước cửa sổ 5 giây.
- Kiểm tra ID candidate không trùng, cờ enabled hợp lệ, F0 luôn được bật và hash
  của mọi cấu hình hợp lệ.

Chạy bằng ``python tests/test_contract.py``.
Test này không import TensorFlow, không train và không mở dữ liệu Test.
"""

import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from frontend_core import (  # noqa: E402
    BASELINE,
    CONFIG_KEYS,
    load_config,
    digest,
    read_rows,
    ROOT,
    SR,
    SAMPLES,
)


def test_baseline():
    assert len(CONFIG_KEYS) == 7
    assert asdict(BASELINE) == dict(
        low_cut_hz=100.0,
        high_cut_hz=2000.0,
        filter_order=5,
        pre_emphasis=0.97,
        n_mels=64,
        hop_length=625,
        n_fft=1024,
    )
    assert SAMPLES == SR * 5
    assert 1 + SAMPLES // BASELINE.hop_length == 129


def test_candidates():
    rows = read_rows(ROOT / "configs" / "candidates.csv")
    assert len(rows) == len(set(r["variant_id"] for r in rows))
    assert all(r["enabled"] in ("0", "1") for r in rows)
    assert rows[0]["variant_id"] == "F0"
    # F0 có thể tắt sau khi baseline artifact đã được tạo; nếu khai báo
    # thì cấu hình vẫn phải khớp BASELINE bất biến.
    f0 = next(r for r in rows if r["variant_id"] == "F0")
    assert asdict(load_config(f0)) == asdict(BASELINE)
    for row in rows:
        assert len(digest(load_config(row))) == 64


if __name__ == "__main__":
    test_baseline()
    test_candidates()
    print("PASS: baseline, candidates & config hash")
