"""Calib playback 3 Asthma + 3 Non-Asthma, moi file lap lai 3 lan.

Moi trial duoc gan cung mot dong du lieu:
- file va true_class;
- p_non cua WAV goc tren Python;
- p_non cua WAV thu lai tren Python;
- p_non do chinh ESP32 tinh;
- PCM RMS va peak cua capture.

Script tu phat WAV bang loa mac dinh cua Windows, nhan PCM16 tu ESP32 qua
Serial, luu tung capture va append CSV ngay sau moi trial thanh cong.
"""

from __future__ import annotations

import csv
import importlib.util
import re
import sys
import threading
import time
import wave
from pathlib import Path
from types import ModuleType

import numpy as np
import serial

try:
    from . import Capture_Wav_From_Serial as capture_protocol
except ImportError:
    import Capture_Wav_From_Serial as capture_protocol


# =============================================================================
# CAU HINH DE DOI TRUC TIEP
# =============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parents[1]

SERIAL_PORT = "COM11"
SERIAL_BAUD = 460_800
TRIALS_PER_FILE = 3
READY_TIMEOUT_SECONDS = 180.0
RESULT_TIMEOUT_SECONDS = 60.0
PLAYBACK_START_DELAY_SECONDS = 0.25

EXPERIMENT_DIR = (
    WORKSPACE_DIR
    / "Experiments_Benchmarking"
    / "Patient_Node"
    / "Final_V1_Validation"
    / "01_Classification_Threshold"
)
PLAYBACK_DIR = EXPERIMENT_DIR / "Playback_Calibration"
MANIFEST_PATH = PLAYBACK_DIR / "playback_calibration_manifest.csv"

PREPROCESS_SCRIPT = (
    WORKSPACE_DIR
    / "AI_Training_Model"
    / "Phase2_Preprocess_&_Traning"
    / "Preprocess_Audio.py"
)
PREDICTION_SCRIPT = EXPERIMENT_DIR / "Generate_Predictions.py"
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

OUTPUT_DIR = SCRIPT_DIR / "calibration_results"
CAPTURE_DIR = OUTPUT_DIR / "captures"
RESULT_CSV = OUTPUT_DIR / "playback_calibration_results.csv"

READY_MARKER = b"[VAD] Bo dem da du 1 giay, bat dau lang nghe."
ESP_RESULT_RE = re.compile(
    rb"^\[AI\] raw=(?P<raw>-?\d+) \| "
    rb"p_non_asthma=(?P<p_non>\d+(?:\.\d+)?) \|"
)

CSV_COLUMNS = [
    "file",
    "true_class",
    "trial",
    "p_non_original_python",
    "p_non_capture_python",
    "p_non_esp32",
    "pcm_rms",
    "pcm_peak",
    "capture_file",
]


def load_python_module(module_name: str, script_path: Path) -> ModuleType:
    if not script_path.is_file():
        raise FileNotFoundError(f"Khong tim thay module: {script_path}")

    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Khong import duoc: {script_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class PythonV1Runner:
    """Tai pipeline/model mot lan va dung lai cho toan bo 24 inference."""

    def __init__(self) -> None:
        self.preprocess = load_python_module(
            "calibration_preprocess_audio", PREPROCESS_SCRIPT
        )
        self.prediction = load_python_module(
            "calibration_v1_prediction", PREDICTION_SCRIPT
        )
        self.train_min, self.train_max, _ = self.prediction.read_conversion_contract(
            self.prediction.CONVERSION_METADATA_PATH
        )
        (
            self.interpreter,
            self.input_detail,
            self.output_detail,
        ) = self.prediction.create_interpreter(MODEL_PATH)

    def infer(self, wav_path: Path) -> float:
        mel_db = self.preprocess.preprocess_audio_file(wav_path).astype(np.float32)
        if mel_db.shape != (40, 129):
            raise ValueError(f"Sai Mel shape cua {wav_path}: {mel_db.shape}")
        if not np.isfinite(mel_db).all():
            raise ValueError(f"Mel co NaN/Inf: {wav_path}")

        input_scale, input_zero = self.input_detail["quantization"]
        output_scale, output_zero = self.output_detail["quantization"]
        input_int8 = self.prediction.quantize_input(
            mel_db[..., np.newaxis],
            self.train_min,
            self.train_max,
            float(input_scale),
            int(input_zero),
        )
        self.interpreter.set_tensor(
            self.input_detail["index"], input_int8[np.newaxis, ...]
        )
        self.interpreter.invoke()

        output_int8 = int(
            self.interpreter.get_tensor(self.output_detail["index"]).reshape(-1)[0]
        )
        return self.prediction.dequantize_output(
            output_int8,
            float(output_scale),
            int(output_zero),
        )


def load_calibration_items() -> list[dict[str, str | Path]]:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Khong tim thay manifest: {MANIFEST_PATH}")

    items: list[dict[str, str | Path]] = []
    with MANIFEST_PATH.open("r", newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            copied_relative = Path(row["copied_file"])
            wav_path = EXPERIMENT_DIR / copied_relative
            if not wav_path.is_file():
                raise FileNotFoundError(f"Thieu WAV calibration: {wav_path}")
            items.append(
                {
                    "file": copied_relative.as_posix(),
                    "true_class": row["class_name"],
                    "wav_path": wav_path,
                }
            )

    class_counts: dict[str, int] = {}
    for item in items:
        class_name = str(item["true_class"])
        class_counts[class_name] = class_counts.get(class_name, 0) + 1
    if class_counts != {"Asthma": 3, "Non_Asthma": 3}:
        raise ValueError(
            "Manifest phai co dung 3 Asthma + 3 Non_Asthma, "
            f"nhung dang co {class_counts}"
        )
    return items


def load_completed_trials() -> set[tuple[str, int]]:
    if not RESULT_CSV.is_file():
        return set()

    completed: set[tuple[str, int]] = set()
    with RESULT_CSV.open("r", newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            completed.add((row["file"], int(row["trial"])))
    return completed


def append_result(row: dict[str, str | int | float]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_header = not RESULT_CSV.is_file() or RESULT_CSV.stat().st_size == 0
    with RESULT_CSV.open("a", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def print_serial_line(line: bytes) -> None:
    print(line.decode("utf-8", errors="replace"))


def wait_for_ready(port: serial.Serial) -> None:
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        line = port.readline().rstrip(b"\r\n")
        if not line:
            continue
        print_serial_line(line)
        if line == READY_MARKER:
            return
    raise TimeoutError("Khong thay firmware bao VAD ready")


def wait_for_capture_header(port: serial.Serial) -> re.Match[bytes]:
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        line = port.readline().rstrip(b"\r\n")
        if not line:
            continue
        match = capture_protocol.CAPTURE_HEADER.match(line)
        if match:
            print_serial_line(line)
            return match
        print_serial_line(line)
    raise TimeoutError("Khong nhan duoc CAPTURE_BEGIN")


def receive_capture(port: serial.Serial, output_path: Path) -> np.ndarray:
    header = wait_for_capture_header(port)
    metadata = {
        key: value.decode("ascii") for key, value in header.groupdict().items()
    }
    sample_count = int(metadata["samples"])
    sample_rate = int(metadata["sample_rate"])
    channels = int(metadata["channels"])
    sample_width = int(metadata["sample_width"])
    byte_count = int(metadata["bytes"])
    expected_checksum = int(metadata["fnv1a"], 16)

    if metadata["version"] != "1" or metadata["encoding"] != "pcm_s16le":
        raise ValueError(f"Protocol capture khong ho tro: {metadata}")
    if sample_count != 80_000 or sample_rate != 16_000:
        raise ValueError(
            f"Capture khong dung 80000 mau/16 kHz: {sample_count}/{sample_rate}"
        )
    if channels != 1 or sample_width != 2:
        raise ValueError(f"Capture khong phai mono PCM16: {channels}/{sample_width}")
    if byte_count != sample_count * channels * sample_width:
        raise ValueError("Metadata byte count khong nhat quan")

    pcm_bytes = capture_protocol.read_exact(
        port, byte_count, capture_protocol.BINARY_READ_TIMEOUT_SECONDS
    )
    end_marker = capture_protocol.read_end_marker(port)
    actual_checksum = capture_protocol.fnv1a32(pcm_bytes)
    end_bytes = int(end_marker.group("bytes_written"))
    end_checksum = int(end_marker.group("fnv1a"), 16)
    if end_bytes != byte_count:
        raise IOError(f"ESP32 gui thieu: {end_bytes}/{byte_count} byte")
    if actual_checksum != expected_checksum or end_checksum != expected_checksum:
        raise IOError("Checksum capture khong khop")

    capture_protocol.save_wav(
        output_path, pcm_bytes, sample_rate, channels, sample_width
    )
    return np.frombuffer(pcm_bytes, dtype="<i2").copy()


def wait_for_esp_result(port: serial.Serial) -> float:
    deadline = time.monotonic() + RESULT_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        line = port.readline().rstrip(b"\r\n")
        if not line:
            continue
        print_serial_line(line)
        match = ESP_RESULT_RE.match(line)
        if match:
            return float(match.group("p_non"))
    raise TimeoutError("Khong nhan duoc p_non_asthma tu ESP32")


def play_wav_blocking(wav_path: Path) -> None:
    if sys.platform != "win32":
        raise RuntimeError("Auto playback hien chi ho tro Windows/winsound")
    import winsound

    winsound.PlaySound(
        str(wav_path),
        winsound.SND_FILENAME | winsound.SND_NODEFAULT,
    )


def run_one_trial(
    port: serial.Serial,
    runner: PythonV1Runner,
    item: dict[str, str | Path],
    trial: int,
    p_non_original: float,
) -> None:
    source_path = Path(item["wav_path"])
    true_class = str(item["true_class"])
    file_key = str(item["file"])
    capture_path = (
        CAPTURE_DIR
        / true_class
        / f"{source_path.stem}__trial{trial:02d}__capture.wav"
    )

    print("\n" + "=" * 72)
    print(f"{true_class} | {source_path.name} | trial {trial}/{TRIALS_PER_FILE}")
    print("Cho firmware tao du ring buffer...")
    wait_for_ready(port)
    time.sleep(PLAYBACK_START_DELAY_SECONDS)

    playback_errors: list[BaseException] = []

    def playback_worker() -> None:
        try:
            play_wav_blocking(source_path)
        except BaseException as exc:  # Chuyen loi tu thread ve main.
            playback_errors.append(exc)

    playback_thread = threading.Thread(target=playback_worker, daemon=True)
    print(f"[PLAYBACK] {source_path}")
    playback_thread.start()

    pcm = receive_capture(port, capture_path)
    p_non_esp32 = wait_for_esp_result(port)
    playback_thread.join(timeout=10.0)
    if playback_errors:
        raise RuntimeError(f"Khong phat duoc WAV: {playback_errors[0]}")

    p_non_capture = runner.infer(capture_path)
    pcm_float = pcm.astype(np.float64)
    pcm_rms = float(np.sqrt(np.mean(np.square(pcm_float))))
    pcm_peak = int(np.max(np.abs(pcm.astype(np.int32))))

    row: dict[str, str | int | float] = {
        "file": file_key,
        "true_class": true_class,
        "trial": trial,
        "p_non_original_python": f"{p_non_original:.9f}",
        "p_non_capture_python": f"{p_non_capture:.9f}",
        "p_non_esp32": f"{p_non_esp32:.9f}",
        "pcm_rms": f"{pcm_rms:.6f}",
        "pcm_peak": pcm_peak,
        "capture_file": capture_path.relative_to(SCRIPT_DIR).as_posix(),
    }
    append_result(row)
    print(
        "[SAVED] "
        f"original={p_non_original:.9f} | capture_py={p_non_capture:.9f} | "
        f"esp32={p_non_esp32:.9f} | RMS={pcm_rms:.3f} | peak={pcm_peak}"
    )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    items = load_calibration_items()
    completed = load_completed_trials()

    print("=" * 72)
    print("PLAYBACK CALIBRATION: 3 ASTHMA + 3 NON-ASTHMA x 3 TRIAL")
    print("=" * 72)
    print(f"Serial : {SERIAL_PORT} @ {SERIAL_BAUD}")
    print(f"CSV    : {RESULT_CSV}")
    print("Yeu cau: dong PlatformIO Serial Monitor va giu nguyen am luong/vi tri loa.")
    print("Firmware phai la ban debug dump MOI capture.")
    input("Nhan Enter de tai model va bat dau... ")

    print("Dang tai preprocessing va V1 PTQ INT8 (chi tai mot lan)...")
    runner = PythonV1Runner()
    original_probabilities: dict[str, float] = {}
    for item in items:
        file_key = str(item["file"])
        original_probabilities[file_key] = runner.infer(Path(item["wav_path"]))
        print(
            f"[ORIGINAL] {file_key}: "
            f"p_non={original_probabilities[file_key]:.9f}"
        )

    pending = [
        (item, trial)
        for item in items
        for trial in range(1, TRIALS_PER_FILE + 1)
        if (str(item["file"]), trial) not in completed
    ]
    if not pending:
        print("Da du 18 trial trong CSV, khong con gi de chay.")
        return

    print(f"Con {len(pending)}/18 trial. Dang mo Serial...")
    with serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=0.25) as port:
        port.dtr = False
        port.rts = False
        time.sleep(1.0)

        for item, trial in pending:
            file_key = str(item["file"])
            run_one_trial(
                port,
                runner,
                item,
                trial,
                original_probabilities[file_key],
            )

    print("\n" + "=" * 72)
    print("DA HOAN THANH 18 TRIAL")
    print(f"Ket qua: {RESULT_CSV}")
    print(f"Capture : {CAPTURE_DIR}")


if __name__ == "__main__":
    main()
