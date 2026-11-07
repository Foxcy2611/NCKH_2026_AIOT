"""Sinh bộ kiểm thử RAW PCM16 cho Deploy_Model/2_Test_Model_LiveMic.

Quy tắc:
- Tái sử dụng đúng WAV trong manifest static của target được chọn.
- Đưa WAV về mono PCM16/16 kHz và đóng gói đúng 80.000 mẫu vào C++ header.
- Playback ``__take01/__take02`` lấy cửa sổ 1,0-6,0 giây; file khác lấy 0-5 giây.
- Không peak-normalize khi chuẩn hóa định dạng WAV thành PCM16.
- Đọc lại chính PCM16 vừa tạo, chạy frontend Python và TFLite để sinh oracle.
- Kiểm tra Asthma_Model.h trong Deploy_Model/2 trùng model target trước khi xuất.

Mặc định dùng ``C4_QAT_INT8``. Script không sửa WAV nguồn.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
import tempfile
import wave
from array import array
from pathlib import Path

import numpy as np
import soxr

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault(
    "NUMBA_CACHE_DIR",
    str(Path(tempfile.gettempdir()) / "nckh_numba_cache"),
)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


# =============================================================================
# CẤU HÌNH
# =============================================================================

SAMPLE_RATE = 16_000
DURATION_SECONDS = 5.0
SAMPLE_COUNT = int(SAMPLE_RATE * DURATION_SECONDS)
PLAYBACK_OFFSET_SECONDS = 1.0
PLAYBACK_TAKE_SUFFIXES = ("__take01", "__take02")

SCRIPT_DIR = Path(__file__).resolve().parent
AI_DIR = SCRIPT_DIR.parent
WORKSPACE_DIR = AI_DIR.parent

DATASET_DIR = AI_DIR / "Dataset_Chia_V2"
FRONTEND_DIR = (
    WORKSPACE_DIR
    / "Experiments_Benchmarking"
    / "Patient_Node"
    / "Frontend_Benchmarking"
)
FRONTEND_CORE_PATH = FRONTEND_DIR / "frontend_core.py"
D_QUANTIZATION_DIR = FRONTEND_DIR / "artifacts" / "D_Quantization"
D_DEPLOYMENT_DIR = FRONTEND_DIR / "artifacts" / "D_Deployment"
STATIC_OUTPUT_DIR = SCRIPT_DIR / "Output_Static_Test_Tensors"

TARGETS = {
    "C4_QAT_INT8": {
        "trial_id": "combo_pre0_mel40_fft2048__V1__s44",
        "method_id": "QAT_INT8",
    },
    "F0_PTQ_INT8": {
        "trial_id": "F0__V1__s43",
        "method_id": "PTQ_INT8",
    },
    "C3_QAT_INT8": {
        "trial_id": "combo_mel40_fft2048__V1__s44",
        "method_id": "QAT_INT8",
    },
}

OUTPUT_DIR = SCRIPT_DIR / "Output_LiveMic_PCM16_Test"
OUTPUT_MANIFEST_PATH = OUTPUT_DIR / "LiveMic_PCM16_Test_Manifest.csv"

DEPLOY_HEADER_PATH = (
    WORKSPACE_DIR
    / "Deploy_Model"
    / "2_Test_Model_LiveMic"
    / "include"
    / "Raw_PCM16_Test"
    / "Raw_PCM16_Test_Samples.h"
)
DEPLOY_MODEL_HEADER_PATH = (
    WORKSPACE_DIR
    / "Deploy_Model"
    / "2_Test_Model_LiveMic"
    / "include"
    / "Model_AI"
    / "Asthma_Model.h"
)

OUTPUT_COLUMNS = [
    "test_index",
    "class_label",
    "class_name",
    "source_file",
    "source_relative_path",
    "source_sha256",
    "pcm16_sha256",
    "array_name",
    "source_sample_rate",
    "source_channels",
    "source_sample_width_bytes",
    "output_sample_rate",
    "format_conversion",
    "original_frame_count",
    "original_duration_seconds",
    "crop_start_seconds",
    "crop_start_sample",
    "samples_read",
    "samples_zero_padded",
    "output_sample_count",
    "peak_pcm16",
    "rms_pcm16",
    "expected_output_int8",
    "expected_probability_non_asthma",
    "expected_predicted_label",
    "reference_trial_id",
    "reference_method_id",
    "reference_model_sha256",
    "frontend_config_sha256",
]


def portable_path(path: Path) -> str:
    path = path.resolve()
    try:
        return path.relative_to(WORKSPACE_DIR).as_posix()
    except ValueError:
        return path.as_posix()


def is_playback(path: Path) -> bool:
    return path.stem.casefold().endswith(PLAYBACK_TAKE_SUFFIXES)


def safe_identifier(text: str) -> str:
    identifier = re.sub(r"[^A-Za-z0-9_]", "_", text).lower()
    if not identifier or identifier[0].isdigit():
        identifier = f"raw_{identifier}"
    return identifier


def cpp_string(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def parse_int(row: dict[str, str], key: str) -> int:
    value = row.get(key, "").strip()
    if not value:
        raise ValueError(f"Manifest thiếu {key}: {row}")
    return int(value)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(module_name: str, module_path: Path):
    if not module_path.is_file():
        raise FileNotFoundError(f"Không tìm thấy module: {module_path}")
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Không thể import module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def resolve_target(target_key: str) -> dict[str, object]:
    spec = TARGETS[target_key]
    trial_id = spec["trial_id"]
    method_id = spec["method_id"]
    method_dir = D_QUANTIZATION_DIR / trial_id / "methods" / method_id
    deployment_dir = D_DEPLOYMENT_DIR / trial_id / method_id
    target = {
        "key": target_key,
        "trial_id": trial_id,
        "method_id": method_id,
        "selection_manifest_path": (
            STATIC_OUTPUT_DIR / trial_id / method_id / "Static_Test_Tensors_Manifest.csv"
        ),
        "model_path": method_dir / f"{method_id}.tflite",
        "conversion_metadata_path": method_dir / "conversion_metadata.json",
        "deployment_manifest_path": deployment_dir / "deployment_manifest.json",
        "deployment_header_path": deployment_dir / "Asthma_Model.h",
    }
    missing = [
        str(path)
        for name, path in target.items()
        if name.endswith("_path") and not Path(path).is_file()
    ]
    if missing:
        raise FileNotFoundError(
            f"Thiếu artifact cho target {target_key}:\n- " + "\n- ".join(missing)
        )
    return target


def load_static_selection(manifest_path: Path) -> list[dict[str, str]]:
    if not manifest_path.is_file():
        raise FileNotFoundError(
            "Không tìm thấy manifest bộ tensor tĩnh:\n"
            f"  {manifest_path}\n"
            "Hãy chạy Generate_Static_Test_Tensors.py --target tương ứng trước."
        )

    with manifest_path.open("r", newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError("Static_Test_Tensors_Manifest.csv không có mẫu nào")

    rows.sort(key=lambda row: parse_int(row, "test_index"))
    expected_indices = list(range(1, len(rows) + 1))
    actual_indices = [parse_int(row, "test_index") for row in rows]
    if actual_indices != expected_indices:
        raise ValueError(
            f"test_index không liên tục: expected={expected_indices}, actual={actual_indices}"
        )

    relative_paths = [row["source_relative_path"].strip() for row in rows]
    if len(relative_paths) != len(set(relative_paths)):
        raise ValueError("Manifest chứa WAV trùng lặp")

    return rows


def float_audio_to_pcm16(audio: np.ndarray) -> array:
    """Đổi float [-1, 1] của audio decoder về PCM16, không peak-normalize."""
    audio = np.asarray(audio, dtype=np.float32).reshape(-1)
    scaled = np.rint(audio * 32768.0)
    pcm = np.clip(scaled, -32768, 32767).astype("<i2")
    samples = array("h")
    samples.frombytes(pcm.tobytes())
    if sys.byteorder != "little":
        samples.byteswap()
    return samples


def read_pcm16_window(path: Path) -> dict[str, object]:
    """
    Tạo cửa sổ PCM16/16 kHz giống định dạng INMP441.

    WAV đã là mono PCM16/16 kHz được đọc nguyên sample. WAV có sample rate hoặc
    channel khác chỉ được decode/resample/remix bằng soxr_hq; không chạy bất kỳ
    bước DSP/model preprocessing nào.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy WAV: {path}")

    crop_start_seconds = PLAYBACK_OFFSET_SECONDS if is_playback(path) else 0.0
    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
        compression = wav_file.getcomptype()
        source_crop_start_frame = int(round(crop_start_seconds * sample_rate))
        source_frames_to_read = int(math.ceil(DURATION_SECONDS * sample_rate))

        if compression != "NONE":
            raise ValueError(f"{path.name}: WAV nén {compression}, yêu cầu PCM không nén")
        if sample_width != 2:
            raise ValueError(
                f"{path.name}: sample width={sample_width * 8} bit, yêu cầu PCM16"
            )

        wav_file.setpos(min(source_crop_start_frame, frame_count))
        source_bytes = wav_file.readframes(source_frames_to_read)

        direct_pcm16 = (
            channels == 1
            and sample_width == 2
            and sample_rate == SAMPLE_RATE
        )

    if direct_pcm16:
        samples = array("h")
        samples.frombytes(source_bytes)
        if sys.byteorder != "little":
            samples.byteswap()
        format_conversion = "direct_pcm16"
    else:
        # Decode PCM16, trộn channel bằng trung bình và resample trực tiếp bằng
        # libsoxr HQ. Không import/call Preprocess_Audio.py hoặc librosa.
        source_pcm = np.frombuffer(source_bytes, dtype="<i2")
        complete_values = (source_pcm.size // channels) * channels
        source_pcm = source_pcm[:complete_values]
        if channels > 1:
            source_pcm = source_pcm.reshape(-1, channels).astype(np.float32)
            float_audio = source_pcm.mean(axis=1) / 32768.0
        else:
            float_audio = source_pcm.astype(np.float32) / 32768.0

        if sample_rate != SAMPLE_RATE and float_audio.size > 0:
            float_audio = soxr.resample(
                float_audio,
                sample_rate,
                SAMPLE_RATE,
                quality="HQ",
            )
        samples = float_audio_to_pcm16(float_audio)
        format_conversion = "soxr_hq_to_mono_pcm16"

    samples_read = len(samples)
    if samples_read > SAMPLE_COUNT:
        del samples[SAMPLE_COUNT:]
        samples_read = SAMPLE_COUNT

    zero_padding = SAMPLE_COUNT - samples_read
    if zero_padding > 0:
        samples.extend([0] * zero_padding)

    if len(samples) != SAMPLE_COUNT:
        raise RuntimeError(
            f"{path.name}: output có {len(samples)} mẫu, yêu cầu {SAMPLE_COUNT}"
        )

    peak = max((abs(int(value)) for value in samples), default=0)
    sum_square = sum(int(value) * int(value) for value in samples)
    rms = math.sqrt(sum_square / SAMPLE_COUNT) if SAMPLE_COUNT else 0.0

    return {
        "samples": samples,
        "source_sample_rate": sample_rate,
        "source_channels": channels,
        "source_sample_width": sample_width,
        "output_sample_rate": SAMPLE_RATE,
        "format_conversion": format_conversion,
        "frame_count": frame_count,
        "duration_seconds": frame_count / sample_rate,
        "crop_start_seconds": crop_start_seconds,
        "crop_start_sample": source_crop_start_frame,
        "samples_read": samples_read,
        "zero_padding": zero_padding,
        "peak": peak,
        "rms": rms,
    }


def format_int16_array(values: array, values_per_line: int = 16) -> str:
    lines = []
    for start in range(0, len(values), values_per_line):
        chunk = values[start : start + values_per_line]
        lines.append("    " + ", ".join(f"{int(value):6d}" for value in chunk))
    return ",\n".join(lines)


def prepare_reference(target: dict[str, object]) -> dict[str, object]:
    """Nạp frontend, normalization và TFLite oracle của đúng target deploy."""
    import tensorflow as tf

    model_path = Path(target["model_path"])
    model_sha256 = sha256_file(model_path)
    conversion = json.loads(
        Path(target["conversion_metadata_path"]).read_text(encoding="utf-8")
    )
    deployment = json.loads(
        Path(target["deployment_manifest_path"]).read_text(encoding="utf-8")
    )

    if conversion.get("tflite_sha256") != model_sha256:
        raise RuntimeError("SHA-256 TFLite không khớp conversion_metadata.json")
    if deployment.get("source_tflite_sha256") != model_sha256:
        raise RuntimeError("SHA-256 TFLite không khớp deployment_manifest.json")
    if deployment.get("trial_id") != target["trial_id"]:
        raise RuntimeError("trial_id trong deployment manifest không khớp target")
    if deployment.get("method_id") != target["method_id"]:
        raise RuntimeError("method_id trong deployment manifest không khớp target")

    canonical_header = Path(target["deployment_header_path"])
    if DEPLOY_MODEL_HEADER_PATH.read_bytes() != canonical_header.read_bytes():
        raise RuntimeError(
            "Asthma_Model.h trong Deploy_Model/2 không trùng target đã chọn:\n"
            f"  deploy : {DEPLOY_MODEL_HEADER_PATH}\n"
            f"  target : {canonical_header}"
        )

    frontend = load_module("frontend_core_live_pcm16", FRONTEND_CORE_PATH)
    frontend_values = deployment.get("frontend_config", {})
    missing = [key for key in frontend.CONFIG_KEYS if key not in frontend_values]
    if missing:
        raise ValueError("Deployment manifest thiếu frontend_config: " + ", ".join(missing))
    frontend_config = frontend.Frontend(
        **{key: frontend_values[key] for key in frontend.CONFIG_KEYS}
    )
    frontend.validate(frontend_config)

    normalization = deployment.get("normalization", {})
    train_min = float(normalization["train_min"])
    train_max = float(normalization["train_max"])
    if train_max <= train_min:
        raise ValueError("Normalization train_min/train_max không hợp lệ")

    interpreter = tf.lite.Interpreter(model_path=str(model_path))
    interpreter.allocate_tensors()
    input_detail = interpreter.get_input_details()[0]
    output_detail = interpreter.get_output_details()[0]
    if input_detail["dtype"] != np.int8 or output_detail["dtype"] != np.int8:
        raise TypeError("Bài test Deploy_Model/2 yêu cầu model INT8 input/output")

    expected_shape = (
        1,
        frontend_config.n_mels,
        1 + frontend.SAMPLES // frontend_config.hop_length,
        1,
    )
    actual_shape = tuple(int(value) for value in input_detail["shape"])
    if actual_shape != expected_shape:
        raise ValueError(f"Input TFLite {actual_shape} không khớp frontend {expected_shape}")

    return {
        "frontend": frontend,
        "frontend_config": frontend_config,
        "frontend_config_sha256": frontend.digest(frontend_config),
        "train_min": train_min,
        "train_max": train_max,
        "interpreter": interpreter,
        "input_detail": input_detail,
        "output_detail": output_detail,
        "model_sha256": model_sha256,
    }


def infer_exact_pcm16(samples: array, reference: dict[str, object]) -> dict[str, object]:
    """Chạy Python oracle từ đúng byte PCM16 sẽ được biên dịch vào ESP32."""
    frontend = reference["frontend"]
    config = reference["frontend_config"]
    pcm = np.frombuffer(samples.tobytes(), dtype="<i2")
    audio = pcm.astype(np.float32) / 32768.0
    filtered = frontend.process_wave(audio, config)
    mel_db = frontend.mel_from_wave(filtered, config)
    normalized = (
        (mel_db.astype(np.float32) - reference["train_min"])
        / (reference["train_max"] - reference["train_min"])
    ).astype(np.float32)
    float_input = normalized[np.newaxis, ..., np.newaxis]

    input_detail = reference["input_detail"]
    input_scale, input_zero = input_detail["quantization"]
    if input_scale <= 0:
        raise ValueError(f"Input quantization scale không hợp lệ: {input_scale}")
    limits = np.iinfo(input_detail["dtype"])
    quantized = np.clip(
        np.round(float_input / float(input_scale) + int(input_zero)),
        limits.min,
        limits.max,
    ).astype(input_detail["dtype"])

    interpreter = reference["interpreter"]
    interpreter.set_tensor(input_detail["index"], quantized)
    interpreter.invoke()
    output_detail = reference["output_detail"]
    output_int8 = int(interpreter.get_tensor(output_detail["index"]).reshape(-1)[0])
    output_scale, output_zero = output_detail["quantization"]
    probability = float(
        np.clip((output_int8 - int(output_zero)) * float(output_scale), 0.0, 1.0)
    )
    return {
        "expected_output_int8": output_int8,
        "expected_probability": probability,
        "expected_prediction": int(probability >= 0.5),
    }


def build_records(
    selection: list[dict[str, str]],
    target: dict[str, object],
    reference: dict[str, object],
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []

    for row in selection:
        index = parse_int(row, "test_index")
        label = parse_int(row, "class_label")
        relative_path = Path(row["source_relative_path"])
        source_path = DATASET_DIR / relative_path
        audio = read_pcm16_window(source_path)
        prediction = infer_exact_pcm16(audio["samples"], reference)

        class_token = "asthma" if label == 0 else "non_asthma"
        array_name = safe_identifier(f"raw_pcm16_{class_token}_{index:02d}")
        source_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()

        records.append(
            {
                "index": index,
                "label": label,
                "class_name": row["class_name"].strip(),
                "source_file": row["source_file"].strip(),
                "source_relative_path": relative_path.as_posix(),
                "source_path": source_path,
                "source_sha256": source_sha256,
                "pcm16_sha256": hashlib.sha256(audio["samples"].tobytes()).hexdigest(),
                "array_name": array_name,
                **prediction,
                "reference_trial_id": target["trial_id"],
                "reference_method_id": target["method_id"],
                "reference_model_sha256": reference["model_sha256"],
                "frontend_config_sha256": reference["frontend_config_sha256"],
                **audio,
            }
        )

    return records


def write_header(
    records: list[dict[str, object]],
    target: dict[str, object],
    reference: dict[str, object],
) -> None:
    lines = [
        "#ifndef RAW_PCM16_TEST_SAMPLES_H",
        "#define RAW_PCM16_TEST_SAMPLES_H",
        "",
        "#include <stddef.h>",
        "#include <stdint.h>",
        "",
        "// Tu dong sinh boi Generate_LiveMic_PCM16_Test_Header.py.",
        "// Day la RAW PCM16; CHUA qua preprocess/Mel/normalize Python.",
        "// Label: 0=Asthma, 1=Non-Asthma.",
        "",
        f"constexpr uint32_t kRawPcmSampleRate = {SAMPLE_RATE};",
        f"constexpr size_t kRawPcmSamplesPerTest = {SAMPLE_COUNT};",
        f"constexpr size_t kRawPcmTestCount = {len(records)};",
        f'constexpr const char* kRawPcmReferenceTrial = "{target["trial_id"]}";',
        f'constexpr const char* kRawPcmReferenceMethod = "{target["method_id"]}";',
        f'constexpr const char* kRawPcmReferenceModelSha256 = "{reference["model_sha256"]}";',
        "",
    ]

    for record in records:
        lines.extend(
            [
                f'// [{record["index"]}] {record["class_name"]}: '
                f'{record["source_relative_path"]}',
                f'static const int16_t {record["array_name"]}'
                "[kRawPcmSamplesPerTest] = {",
                format_int16_array(record["samples"]),
                "};",
                "",
            ]
        )

    lines.extend(
        [
            "struct RawPcm16TestSample {",
            "    const char* source_name;",
            "    const char* source_relative_path;",
            "    uint8_t expected_label;",
            "    int8_t expected_output_int8;",
            "    float expected_probability_non_asthma;",
            "    uint8_t expected_prediction;",
            "    const int16_t* pcm16;",
            "};",
            "",
            "static const RawPcm16TestSample kRawPcm16Tests[] = {",
        ]
    )

    for record in records:
        lines.append(
            "    {"
            f'"{cpp_string(str(record["source_file"]))}", '
            f'"{cpp_string(str(record["source_relative_path"]))}", '
            f'{record["label"]}, '
            f'{record["expected_output_int8"]}, '
            f'{record["expected_probability"]:.9f}f, '
            f'{record["expected_prediction"]}, '
            f'{record["array_name"]}'
            "},"
        )

    lines.extend(
        [
            "};",
            "",
            "#endif  // RAW_PCM16_TEST_SAMPLES_H",
            "",
        ]
    )

    DEPLOY_HEADER_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEPLOY_HEADER_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_manifest(records: list[dict[str, object]]) -> None:
    rows = []
    for record in records:
        rows.append(
            {
                "test_index": record["index"],
                "class_label": record["label"],
                "class_name": record["class_name"],
                "source_file": record["source_file"],
                "source_relative_path": record["source_relative_path"],
                "source_sha256": record["source_sha256"],
                "pcm16_sha256": record["pcm16_sha256"],
                "array_name": record["array_name"],
                "source_sample_rate": record["source_sample_rate"],
                "source_channels": record["source_channels"],
                "source_sample_width_bytes": record["source_sample_width"],
                "output_sample_rate": record["output_sample_rate"],
                "format_conversion": record["format_conversion"],
                "original_frame_count": record["frame_count"],
                "original_duration_seconds": f'{record["duration_seconds"]:.6f}',
                "crop_start_seconds": f'{record["crop_start_seconds"]:.3f}',
                "crop_start_sample": record["crop_start_sample"],
                "samples_read": record["samples_read"],
                "samples_zero_padded": record["zero_padding"],
                "output_sample_count": SAMPLE_COUNT,
                "peak_pcm16": record["peak"],
                "rms_pcm16": f'{record["rms"]:.6f}',
                "expected_output_int8": record["expected_output_int8"],
                "expected_probability_non_asthma": (
                    f'{record["expected_probability"]:.9f}'
                ),
                "expected_predicted_label": record["expected_prediction"],
                "reference_trial_id": record["reference_trial_id"],
                "reference_method_id": record["reference_method_id"],
                "reference_model_sha256": record["reference_model_sha256"],
                "frontend_config_sha256": record["frontend_config_sha256"],
            }
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_MANIFEST_PATH.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sinh RAW PCM16 header và Python oracle từ chính PCM16 cho Deploy_Model/2."
        )
    )
    parser.add_argument(
        "--target",
        choices=tuple(TARGETS),
        default="C4_QAT_INT8",
        help="Model tham chiếu (mặc định: C4_QAT_INT8).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target = resolve_target(args.target)
    selection = load_static_selection(Path(target["selection_manifest_path"]))
    reference = prepare_reference(target)
    records = build_records(selection, target, reference)
    write_header(records, target, reference)
    write_manifest(records)

    asthma_count = sum(int(record["label"] == 0) for record in records)
    non_asthma_count = sum(int(record["label"] == 1) for record in records)

    print("=" * 72)
    print("LIVE MIC RAW PCM16 TEST ARTIFACT")
    print("=" * 72)
    print(f"Target       : {args.target}")
    print(f"Trial/method : {target['trial_id']} / {target['method_id']}")
    print(f"Model SHA-256: {reference['model_sha256']}")
    print(f"Frontend     : {reference['frontend_config']}")
    for record in records:
        print(
            f'[{record["index"]:02d}/{len(records):02d}] '
            f'{record["class_name"]:<11} | '
            f'crop={record["crop_start_seconds"]:.1f}s | '
            f'pad={record["zero_padding"]:5d} | '
            f'peak={record["peak"]:5d} | '
            f'rms={record["rms"]:8.2f} | '
            f'{record["source_file"]}'
        )

    print("-" * 72)
    print(f"Số mẫu       : {len(records)} ({asthma_count} Asthma + {non_asthma_count} Non-Asthma)")
    print(f"PCM mỗi mẫu  : {SAMPLE_COUNT} mẫu, mono PCM16, {SAMPLE_RATE} Hz")
    print(f"Header deploy: {portable_path(DEPLOY_HEADER_PATH)}")
    print(f"Manifest     : {portable_path(OUTPUT_MANIFEST_PATH)}")
    print("Python oracle: CÓ - tính lại từ đúng PCM16 ghi vào header")
    print("=" * 72)


if __name__ == "__main__":
    main()
