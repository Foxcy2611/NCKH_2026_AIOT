#!/usr/bin/env python3
"""Host tests: g++ + Python 3, no ESP32 or broker needed. Run from any directory."""
from pathlib import Path
import json, subprocess, tempfile
root = Path(__file__).resolve().parents[2]
def run(*args):
    return subprocess.check_output(args, cwd=root, text=True)
with tempfile.TemporaryDirectory() as tmp:
    common = ['g++', '-std=c++11', '-Wall', '-Wextra', '-Werror', '-Itest/native', '-Iinclude']
    subprocess.check_call(common + ['test/native/test_record.cpp', '-o', tmp+'/record'], cwd=root)
    print(run(tmp+'/record').strip())
    for mode in [0, 2]:
        subprocess.check_call(common + [f'-DGATEWAY_SENSOR_MODE={mode}', 'test/native/test_json.cpp', 'src/gateway_json.cpp', '-o', tmp+'/json'], cwd=root)
        lines = run(tmp+'/json').splitlines()
        def invalid(value): raise AssertionError('Non-standard JSON number: '+value)
        rows = [json.loads(line, parse_constant=invalid) for line in lines]
        telemetry, event, partial = rows
        assert telemetry['gate']['timestamp'] == 4294967297
        assert telemetry['gate']['time_basis'] == 'uptime_ms'
        assert telemetry['patient_event'] is None and telemetry['source'] is None
        assert telemetry['has_patient_event'] is False
        assert telemetry['gate']['temperature'] is None and telemetry['gate']['eco2'] is None
        assert telemetry['gate']['wifi_rssi_dbm'] is None
        assert event['has_patient_event'] is True
        assert event['source']['sequence'] == 4294967295
        assert event['source']['received_uptime_ms'] == 18446744073709551615
        assert event['patient_event']['heart_rate'] == 72 and event['patient_event']['spo2'] == 98
        assert event['gate']['tvoc'] == 0 and event['gate']['eco2'] == 500
        assert event['patient_event']['model_score'] == .875
        assert partial['gate']['temperature'] is None and partial['gate']['pressure'] is None
        assert partial['patient_event']['heart_rate'] is None and partial['patient_event']['spo2'] is None
        assert partial['patient_event']['time_basis'] == 'unsynced'
        assert all(r['synthetic'] == (mode == 2) for r in rows)
        assert telemetry['transport'] == 'none'
        assert event['transport'] == partial['transport'] == 'wifi'
        assert telemetry['record_id'] != event['record_id']
        assert event['record_id'] == partial['record_id']
        print(f'PASS: JSON mode={mode}, telemetry/event/status/alert, null/nonfinite, metadata, 64-bit, stable retry, buffer limits')

    subprocess.check_call(['g++', '-std=c++11', '-Wall', '-Wextra', '-Werror', '-DGATEWAY_NETWORK_CONFIGURED=1', '-Itest/native/wifi_mock', '-Iinclude', 'test/native/test_wifi.cpp', 'src/network/gateway_wifi.cpp', '-o', tmp+'/wifi'], cwd=root)
    print(run(tmp+'/wifi').strip())
