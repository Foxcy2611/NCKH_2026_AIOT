"""Kiểm tra danh sách candidate và tạo kế hoạch thí nghiệm có truy vết.

Tác dụng:
- Đọc ``configs/candidates.csv`` và kiểm tra ID, cờ enabled.
- ``F0`` là tùy chọn trong lịch train. Nếu có dòng ``F0`` thì cấu hình
  của nó vẫn phải khớp baseline bất biến, nhưng có thể đặt ``enabled=0``.
- Tính ``config_sha256`` cho từng cấu hình Front-End.
- Khóa quan hệ giữa candidate, protocol và cấu hình trước khi preprocess/train.

Đầu vào: ``configs/candidates.csv`` hoặc đường dẫn truyền qua ``--candidates``.
Đầu ra: ``results/experiment_plan.csv`` và ``results/plan_manifest.json``.
Giới hạn: không preprocess, không train và không đọc nhãn Test.
"""
import argparse
from dataclasses import asdict

from frontend_core import (
    BASELINE,
    CONFIG_KEYS,
    PROTOCOL,
    RESULTS,
    ROOT,
    digest,
    load_config,
    read_rows,
    safe_id,
    write_rows,
    write_json,
)


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        '--candidates',
        default=str(ROOT / 'configs' / 'candidates.csv'),
    )
    a = p.parse_args()

    rows = read_rows(__import__('pathlib').Path(a.candidates))
    if not rows:
        raise ValueError('Candidate file empty')

    ids = set()
    plans = []
    for r in rows:
        cid = safe_id(r['variant_id'])
        if cid in ids:
            raise ValueError(f'Duplicate ID: {cid}')
        ids.add(cid)
        c = load_config(r)
        if cid == 'F0' and asdict(c) != asdict(BASELINE):
            raise ValueError('F0 must exactly match baseline')
        if r.get('enabled', '0') not in ('0', '1'):
            raise ValueError('enabled must be 0/1')
        plans.append(
            {
                **r,
                'config_sha256': digest(c),
                'protocol': PROTOCOL,
            }
        )

    enabled_count = sum(r['enabled'] == '1' for r in plans)
    if enabled_count == 0:
        raise ValueError('At least one candidate must have enabled=1')

    f0_row = next((r for r in plans if r['variant_id'] == 'F0'), None)

    out = RESULTS / 'experiment_plan.csv'
    write_rows(out, plans)
    write_json(
        RESULTS / 'plan_manifest.json',
        {
            'protocol': PROTOCOL,
            'candidate_count': len(plans),
            'enabled_count': enabled_count,
            'f0_present': f0_row is not None,
            'f0_enabled': bool(f0_row and f0_row['enabled'] == '1'),
            'note': (
                'Test labels are not inspected when building plan. '
                'F0 is optional in the training schedule.'
            ),
        },
    )
    print('PLAN', out, 'enabled:', enabled_count)
    if f0_row is None:
        print('NOTE: F0 is absent; the plan schedules enabled candidates only.')
    elif f0_row['enabled'] != '1':
        print('NOTE: F0 is disabled; its existing artifacts may still be used as control later.')


if __name__ == '__main__':
    main()
