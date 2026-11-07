"""Unit tests for 5 s PCM16 Quality Gate and cached Test provenance.

These Python tests do not establish hardware parity by themselves.
"""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from quality_utils import (
    QualityThresholds, classify_audio, extract_metrics, file_sha256,
    freeze_config, verify_test_provenance, write_test_provenance,
)


class QualityGateParityTests(unittest.TestCase):
    def test_zero_buffer_is_inactive(self):
        state, m = classify_audio(np.zeros(80000, np.int16), QualityThresholds())
        self.assertEqual(state, 'AUDIO_INACTIVE')
        self.assertEqual((m['active_blocks'], m['total_blocks']), (0, 313))

    def test_strong_nonclipped_is_ok(self):
        state, _ = classify_audio(np.full(80000, 100, np.int16), QualityThresholds())
        self.assertEqual(state, 'AUDIO_OK')

    def test_firmware_strict_clipping(self):
        state, m = classify_audio(np.full(80000, 32000, np.int16), QualityThresholds())
        self.assertEqual((state, m['clipped_samples']), ('AUDIO_OK', 0))
        state, m = classify_audio(np.full(80000, 32767, np.int16), QualityThresholds())
        self.assertEqual((state, m['clipped_ratio']), ('AUDIO_TOO_LOUD', 1.0))

    def test_negative_full_scale_and_priority(self):
        state, m = classify_audio(np.full(80000, -32768, np.int16), QualityThresholds())
        self.assertEqual((m['peak'], state), (32768, 'AUDIO_TOO_LOUD'))

    def test_integer_mav_threshold(self):
        x = np.zeros(80000, dtype=np.int16)
        x[:256] = 20
        state, m = classify_audio(x, QualityThresholds())
        self.assertEqual((m['active_blocks'], state), (0, 'AUDIO_INACTIVE'))

    def test_too_weak_with_active_blocks(self):
        x = np.zeros(80000, np.int16)
        x[:2048] = 30
        state, metrics = classify_audio(x, QualityThresholds())
        self.assertGreaterEqual(metrics['active_ratio'], .01)
        self.assertLess(metrics['rms'], 20)
        self.assertEqual(state, 'AUDIO_TOO_WEAK')

    def test_clipped_ratio_equal_boundary(self):
        x = np.full(80000, 100, np.int16)
        x[:800] = 32767  # exactly 1%, should still be AUDIO_OK
        state, metrics = classify_audio(x, QualityThresholds())
        self.assertEqual(metrics['clipped_ratio'], 0.01)
        self.assertEqual(state, 'AUDIO_OK')
        x[800] = 32767  # strictly > 1%
        state, _ = classify_audio(x, QualityThresholds())
        self.assertEqual(state, 'AUDIO_TOO_LOUD')

    def test_inactive_precedes_too_loud(self):
        x = np.full(80000, 32767, np.int16)
        state, _ = classify_audio(x, QualityThresholds(active_block_threshold=32768))
        self.assertEqual(state, 'AUDIO_INACTIVE')

    def test_partial_last_block_is_counted(self):
        x = np.zeros(80000, np.int16)
        x[-128:] = 100  # final block contains 128 samples
        metrics = extract_metrics(x)
        self.assertEqual(metrics['total_blocks'], 313)
        self.assertEqual(metrics['active_blocks'], 1)

    def test_invalid_float_input_rejected(self):
        with self.assertRaises(ValueError):
            extract_metrics(np.zeros(80000, np.float32))

    def test_test_cache_is_tied_to_frozen_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, calibration, test, frozen = [root / n for n in
                ('manifest.csv', 'cal.csv', 'test.csv', 'frozen.json')]
            manifest.write_text('sample\n1\n')
            calibration.write_text('metric\n1\n')
            test_wav = root/'synthetic.wav'
            test_wav.write_bytes(b'pcm16-sample-fixture')
            test.write_text(f'file_path,result\n{test_wav},pass\n')
            freeze_config(frozen, QualityThresholds(), file_sha256(manifest),
                          file_sha256(calibration), 'Baseline selected on calibration', {})
            with self.assertRaises(FileNotFoundError):
                verify_test_provenance(test, frozen, manifest, calibration)
            write_test_provenance(test, frozen, manifest, calibration)
            self.assertEqual(verify_test_provenance(test, frozen, manifest, calibration)['status'],
                             'FROZEN_TEST_RESULT')
            test_wav.write_bytes(b'replaced-pcm16')
            with self.assertRaises(ValueError):
                verify_test_provenance(test, frozen, manifest, calibration)
            test_wav.write_bytes(b'pcm16-sample-fixture')
            test.write_text(f'file_path,result\n{test_wav},changed\n')
            with self.assertRaises(ValueError):
                verify_test_provenance(test, frozen, manifest, calibration)


if __name__ == '__main__':
    unittest.main()
