"""Chạy capture.wav qua đúng preprocessing Python và model C4 V1 s44 QAT INT8.

Script nay khong sao chep lai cong thuc DSP. No import truc tiep:
- preprocess_audio_file() tu Phase2/Preprocess_Audio.py;
- cac ham normalize, quantize va TFLite tu Generate_Predictions.py.

capture.wav la cua so 5 giay da duoc firmware can theo onset, vi vay file nay
duoc preprocess tu 0-5 giay. Quy tac playback offset 1-6 giay khong ap dung cho
capture.wav.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import wave
from pathlib import Path
from types import ModuleType

import numpy as np


# =============================================================================
# CAU HINH DE DOI TRUC TIEP
# =============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parents[1]
CAPTURE_WAV = SCRIPT_DIR / "capture.wav"
DEBUG_OUTPUT_DIR = SCRIPT_DIR / "debug_capture"

PREPROCESS_SCRIPT = (
    WORKSPACE_DIR
    / "AI_Training_Model"
    / "Phase2_Preprocess_&_Traning"
    / "Preprocess_Audio.py"
)
PREDICTION_SCRIPT = (
    WORKSPACE_DIR
    / "Experiments_Benchmarking"
    / "Patient_Node"
    / "Final_V1_Validation"
    / "01_Classification_Threshold"
    / "Generate_Predictions.py"
)
MODEL_PATH = (
    WORKSPACE_DIR
    / "Experiments_Benchmarking"
    / "Patient_Node"
    / "Frontend_Benchmarking"
    / "artifacts"
    / "D_Quantization"
    / "combo_pre0_mel40_fft2048__V1__s44"
    / "methods"
    / "QAT_INT8"
    / "QAT_INT8.tflite"
)

EXPECTED_SAMPLE_RATE = 16_000
EXPECTED_SAMPLE_COUNT = 80_000
LOW_THRESHOLD = 0.50
HIGH_THRESHOLD = 0.50


def load_python_module(module_name: str, script_path: Path) -> ModuleType:
    if not script_path.is_file():
        raise FileNotFoundError(f"Khong tim thay module Python: {script_path}")

    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Khong tao duoc import spec cho: {script_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def inspect_capture(path: Path) -> tuple[np.ndarray, dict[str, int | float]]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Chua co {path}. Hay chay Capture_Wav_From_Serial.py truoc."
        )

    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        sample_count = wav_file.getnframes()
        compression = wav_file.getcomptype()
        pcm_bytes = wav_file.readframes(sample_count)

    if channels != 1:
        raise ValueError(f"capture.wav phai mono, nhung channels={channels}")
    if sample_width != 2:
        raise ValueError(f"capture.wav phai PCM16, nhung sample_width={sample_width}")
    if compression != "NONE":
        raise ValueError(f"capture.wav phai la PCM khong nen, nhung type={compression}")
    if sample_rate != EXPECTED_SAMPLE_RATE:
        raise ValueError(
            f"Sai sample rate: {sample_rate}, can {EXPECTED_SAMPLE_RATE} Hz"
        )
    if sample_count != EXPECTED_SAMPLE_COUNT:
        raise ValueError(
            f"Sai so mau: {sample_count}, can dung {EXPECTED_SAMPLE_COUNT} mau"
        )

    pcm = np.frombuffer(pcm_bytes, dtype="<i2")
    pcm_float = pcm.astype(np.float64)
    mean = float(np.mean(pcm_float))
    std = float(np.std(pcm_float))
    rms = float(np.sqrt(np.mean(np.square(pcm_float))))
    metadata: dict[str, int | float] = {
        "sample_rate": sample_rate,
        "sample_count": sample_count,
        "duration_seconds": sample_count / sample_rate,
        "pcm_min": int(np.min(pcm)),
        "pcm_max": int(np.max(pcm)),
        "pcm_mean": mean,
        "pcm_std": std,
        "pcm_rms": rms,
    }
    return pcm, metadata


def classify_probability(p_non_asthma: float) -> tuple[int, str]:
    if p_non_asthma <= LOW_THRESHOLD:
        return 0, "ASTHMA"
    if p_non_asthma >= HIGH_THRESHOLD:
        return 1, "NON-ASTHMA"
    return 2, "UNSURE"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 72)
    print("CAPTURE.WAV -> PYTHON PREPROCESS -> C4 V1 S44 QAT INT8")
    print("=" * 72)

    _, capture_info = inspect_capture(CAPTURE_WAV)
    print(
        "[WAV] "
        f"samples={capture_info['sample_count']} | "
        f"duration={capture_info['duration_seconds']:.3f}s | "
        f"min={capture_info['pcm_min']} | max={capture_info['pcm_max']} | "
        f"mean={capture_info['pcm_mean']:.3f} | "
        f"std={capture_info['pcm_std']:.3f} | rms={capture_info['pcm_rms']:.3f}"
    )

    preprocess = load_python_module("capture_preprocess_audio", PREPROCESS_SCRIPT)
    prediction = load_python_module("capture_v1_prediction", PREDICTION_SCRIPT)

    # capture.wav khong co suffix __take01/__take02, nen doc cua so 0-5 giay.
    mel_db = preprocess.preprocess_audio_file(CAPTURE_WAV).astype(np.float32)
    if mel_db.shape != (40, 129):
        raise ValueError(f"Sai Mel shape: {mel_db.shape}, can (40, 129)")
    if not np.isfinite(mel_db).all():
        raise ValueError("Mel-Spectrogram co NaN hoac Inf")

    train_min, train_max, _ = prediction.read_conversion_contract(
        prediction.CONVERSION_METADATA_PATH
    )
    interpreter, input_detail, output_detail = prediction.create_interpreter(MODEL_PATH)
    input_scale, input_zero = input_detail["quantization"]
    output_scale, output_zero = output_detail["quantization"]

    mel_with_channel = mel_db[..., np.newaxis]
    input_int8 = prediction.quantize_input(
        mel_with_channel,
        train_min,
        train_max,
        float(input_scale),
        int(input_zero),
    )
    interpreter.set_tensor(input_detail["index"], input_int8[np.newaxis, ...])
    interpreter.invoke()

    output_int8 = int(interpreter.get_tensor(output_detail["index"]).reshape(-1)[0])
    p_non_asthma = prediction.dequantize_output(
        output_int8,
        float(output_scale),
        int(output_zero),
    )
    p_asthma = 1.0 - p_non_asthma
    predicted_class, class_name = classify_probability(p_non_asthma)

    result = {
        "capture_wav": str(CAPTURE_WAV),
        "model": "combo_pre0_mel40_fft2048__V1__s44_QAT_INT8",
        "model_path": str(MODEL_PATH),
        "preprocess_script": str(PREPROCESS_SCRIPT),
        "normalization_path": str(prediction.CONVERSION_METADATA_PATH),
        **capture_info,
        "mel_shape": list(mel_db.shape),
        "mel_min_db": float(np.min(mel_db)),
        "mel_max_db": float(np.max(mel_db)),
        "mel_mean_db": float(np.mean(mel_db)),
        "train_min": float(train_min),
        "train_max": float(train_max),
        "input_scale": float(input_scale),
        "input_zero_point": int(input_zero),
        "input_int8_min": int(np.min(input_int8)),
        "input_int8_max": int(np.max(input_int8)),
        "output_scale": float(output_scale),
        "output_zero_point": int(output_zero),
        "output_int8": output_int8,
        "p_non_asthma": p_non_asthma,
        "p_asthma": p_asthma,
        "low_threshold": LOW_THRESHOLD,
        "high_threshold": HIGH_THRESHOLD,
        "predicted_class": predicted_class,
        "class_name": class_name,
    }

    DEBUG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    np.save(DEBUG_OUTPUT_DIR / "capture_mel_db.npy", mel_db)
    np.save(DEBUG_OUTPUT_DIR / "capture_input_int8.npy", input_int8)
    report_path = DEBUG_OUTPUT_DIR / "capture_inference_result.json"
    report_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        f"[MEL] shape={mel_db.shape} | min={mel_db.min():.3f} dB | "
        f"max={mel_db.max():.3f} dB | mean={mel_db.mean():.3f} dB"
    )
    print(
        f"[INT8 INPUT] scale={float(input_scale):.9f} | zero={int(input_zero)} | "
        f"min={int(input_int8.min())} | max={int(input_int8.max())}"
    )
    print(
        f"[INT8 OUTPUT] raw={output_int8} | scale={float(output_scale):.9f} | "
        f"zero={int(output_zero)}"
    )
    print(
        f"[RESULT] p_non_asthma={p_non_asthma:.9f} | "
        f"p_asthma={p_asthma:.9f} | class={predicted_class} ({class_name})"
    )
    print(f"[REPORT] {report_path}")


if __name__ == "__main__":
    main()
