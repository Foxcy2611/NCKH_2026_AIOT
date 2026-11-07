"""D3 - xuất TFLite đã chọn thành C++ header và deployment manifest.

Script không sửa firmware. INT16x8 bị chặn khỏi nhánh firmware INT8 nếu người
dùng chưa xác nhận rõ bằng ``--allow-int16x8``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from d_quantization_core import (
    D_ARTIFACTS, D_DEPLOY, METHOD_SPECS, atomic_json, inspect_tflite,
    load_d_plan, safe_identifier, sha256_file, utc_now,
    verify_trial_against_plan,
)
from frontend_core import read_json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')


def header_text(data: bytes, array_name: str, metadata: dict) -> str:
    safe = safe_identifier(array_name)
    guard = safe.upper() + '_H'
    lines = []
    for start in range(0, len(data), 12):
        chunk = data[start:start + 12]
        lines.append('    ' + ', '.join(f'0x{byte:02x}' for byte in chunk))
    body = ',\n'.join(lines)
    input_info = metadata['io']['input']
    output_info = metadata['io']['output']
    return f'''#ifndef {guard}
#define {guard}

#include <stddef.h>
#include <stdint.h>

// Sinh tự động bởi D3_Export_Deployment.py.
// Trial : {metadata['trial_id']}
// Method: {metadata['method_id']}
// SHA256: {metadata['tflite_sha256']}
// Input : {input_info['dtype']}, scale={input_info['scale']}, zero={input_info['zero_point']}
// Output: {output_info['dtype']}, scale={output_info['scale']}, zero={output_info['zero_point']}

alignas(4) const unsigned char {safe}[] = {{
{body}
}};

const size_t {safe}_len = {len(data)}u;

#endif  // {guard}
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial-id', required=True)
    parser.add_argument('--method', required=True, choices=tuple(METHOD_SPECS))
    parser.add_argument('--array-name', default='asthma_model')
    parser.add_argument('--output-dir', help='Mặc định artifacts/D_Deployment/<trial>/<method>')
    parser.add_argument(
        '--allow-int16x8', action='store_true',
        help='Xác nhận firmware đích đã hỗ trợ input/output INT16',
    )
    args = parser.parse_args()

    plan = load_d_plan()
    method_ids = {row['method_id'] for row in plan['methods']}
    if args.method not in method_ids:
        parser.error(f'{args.method} chưa được đăng ký trong kế hoạch D0')
    trial_entries = [row for row in plan['trials'] if row['trial_id'] == args.trial_id]
    if len(trial_entries) != 1:
        parser.error(f'{args.trial_id} chưa được đăng ký trong kế hoạch D0')
    current = verify_trial_against_plan(trial_entries[0])
    spec = METHOD_SPECS[args.method]
    if spec['integer_mode'] == 'INT16x8' and not args.allow_int16x8:
        parser.error('INT16x8 không tương thích trực tiếp firmware INT8; thêm --allow-int16x8 sau khi đã sửa firmware')

    source_dir = D_ARTIFACTS / args.trial_id / 'methods' / args.method
    model_path = source_dir / f'{args.method}.tflite'
    conversion_path = source_dir / 'conversion_metadata.json'
    validation_path = D_ARTIFACTS / args.trial_id / 'evaluation' / args.method / 'val_metrics.json'
    for path in (model_path, conversion_path, validation_path):
        if not path.is_file():
            raise FileNotFoundError(f'Thiếu artifact bắt buộc: {path}')
    conversion = read_json(conversion_path)
    validation = read_json(validation_path)
    if conversion.get('plan_sha256') != plan['plan_sha256']:
        raise RuntimeError('Conversion artifact thuộc kế hoạch E khác')
    if validation.get('plan_sha256') != plan['plan_sha256']:
        raise RuntimeError('Validation artifact thuộc kế hoạch E khác')
    model_hash = sha256_file(model_path)
    if conversion.get('tflite_sha256') != model_hash:
        raise RuntimeError('TFLite đã thay đổi sau D1')
    io = inspect_tflite(model_path)

    output_dir = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir else D_DEPLOY / args.trial_id / args.method
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    data = model_path.read_bytes()
    header_metadata = {
        'trial_id': args.trial_id,
        'method_id': args.method,
        'tflite_sha256': model_hash,
        'io': io,
    }
    header_path = output_dir / 'Asthma_Model.h'
    pending = header_path.with_suffix('.h.pending')
    pending.write_text(header_text(data, args.array_name, header_metadata), encoding='utf-8')
    pending.replace(header_path)

    manifest = {
        'schema_version': 1,
        'status': 'DEPLOYMENT_ARTIFACT_EXPORTED',
        'generated_utc': utc_now(),
        'trial_id': args.trial_id,
        'variant_id': current['variant_id'],
        'method_id': args.method,
        **spec,
        'array_name': safe_identifier(args.array_name),
        'array_alignment_bytes': 4,
        'source_tflite': str(model_path.resolve()),
        'source_tflite_sha256': model_hash,
        'source_tflite_size_bytes': len(data),
        'header_path': str(header_path.resolve()),
        'header_sha256': sha256_file(header_path),
        'io': io,
        'normalization': conversion['normalization'],
        'frontend_config': current['frontend_config'],
        'input_shape': current['input_shape'],
        'validation_summary': validation['summary_row'],
        'plan_sha256': plan['plan_sha256'],
        'firmware_notes': [
            'Quantize normalized float input using input scale and zero_point from this manifest.',
            'Dequantize output to p_non_asthma. The TFLite model does not embed a decision threshold.',
            'Threshold 0.5 is only the binary evaluation baseline; production Patient Node uses the frozen LOW=0.47 and HIGH=0.77 policy from Final_V1_Validation.',
            'INT16x8 requires int16_t input/output handling and is not a drop-in INT8 replacement.',
            'Header export does not prove TFLite Micro operator support or tensor-arena capacity.',
        ],
    }
    atomic_json(output_dir / 'deployment_manifest.json', manifest)
    print(f'HEADER  : {header_path}')
    print(f'MANIFEST: {output_dir / "deployment_manifest.json"}')
    print(f'IO      : {io["input"]["dtype"]} -> {io["output"]["dtype"]}')
    print('Firmware chưa bị chỉnh sửa; cần benchmark TFLite Micro riêng.')


if __name__ == '__main__':
    main()
