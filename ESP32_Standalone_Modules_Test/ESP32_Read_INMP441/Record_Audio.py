"""
===============================================================================
Tên script: Record_Audio.py

Tác dụng:
- Hỗ trợ chế độ Environment cũ: tự sinh session_id theo Env_session.csv.
- Hỗ trợ chế độ custom: đặt tên WAV trực tiếp để thu session nghiên cứu VAD.
- Thu PCM16 mono 16 kHz từ ESP32-S3 qua Serial trong thời lượng được chọn.
- Mặc định thu 300 giây (5 phút), có thể đổi bằng --seconds.
- Chế độ Environment lưu WAV vào Dataset_TuThu_v_Kaggle/TuThu/Record_Env.
- Chế độ VAD lưu WAV vào Final_V1_Validation/03_VAD_Trigger/extra_validation.
- Thêm session mới vào TuThu/TKe/Env_session.csv với split=unassigned.
- Thu xong không tự mở biểu đồ; dùng Test_Audio.py khi cần phân tích.

Chạy nhanh: sửa CAPTURE_MODE và các biến cấu hình ở đầu file, sau đó nhấn
Ctrl+Alt+N hoặc chạy: python Record_Audio.py

Có thể dùng tham số dòng lệnh để ghi đè cấu hình khi cần.

Lưu ý:
- ESP32 phải được nạp firmware trong project ESP32_Read_INMP441.
- Không mở Serial Monitor đồng thời với script này.
- Script không ghi đè file hoặc session_id đã tồn tại.
===============================================================================
"""

import argparse
import csv
import re
import sys
import time
import wave
from pathlib import Path

try:
    import serial
except ImportError as error:
    raise SystemExit("Thiếu pyserial. Cài bằng: pip install pyserial") from error


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ======================== CẤU HÌNH CẦN ĐỔI ================================

# Chỉ cần đổi state này rồi nhấn Ctrl+Alt+N:
# - "VAD_RESEARCH": tên tùy chọn, 5 phút, lưu vào 03_VAD_Trigger, không sửa CSV.
# - "DATASET_ENV": tự sinh session_id theo ENV_NAME và cập nhật Env_session.csv.
CAPTURE_MODE = "VAD_RESEARCH"

# Cấu hình khi CAPTURE_MODE = "VAD_RESEARCH".
VAD_FILE_NAME = "vad_silence_session_01.wav"
VAD_RECORD_SECONDS = 300.0

# Cấu hình khi CAPTURE_MODE = "DATASET_ENV".
# ENV_NAME: podcast, speech, fan, fan_keyboard, clap, knock, room_noise, silence.
ENV_NAME = "fan"
DATASET_RECORD_SECONDS = 60.0

SERIAL_PORT = "COM11"

# ========================================================================

SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH_BYTES = 2
BAUD_RATE = 460800
SESSION_NOTE = "Thu mới bằng INMP441 cho Environment V2"
WARMUP_SECONDS = 2.0
READ_TIMEOUT_SECONDS = 2.0

PROJECT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = PROJECT_DIR.parents[1]
TUTHU_ROOT = (
    WORKSPACE_DIR
    / "AI_Training_Model"
    / "Dataset_TuThu_v_Kaggle"
    / "TuThu"
)
RECORD_ENV_ROOT = TUTHU_ROOT / "Record_Env"
SESSION_CSV = TUTHU_ROOT / "TKe" / "Env_session.csv"
VAD_TRIGGER_DIR = (
    WORKSPACE_DIR
    / "Experiments_Benchmarking"
    / "Patient_Node"
    / "Final_V1_Validation"
    / "03_VAD_Trigger"
)
CUSTOM_VAD_OUTPUT_DIR = VAD_TRIGGER_DIR / "extra_validation"

ENV_FOLDER_BY_SUBTYPE = {
    "podcast": "Podcast",
    "speech": "Speech",
    "fan": "Fan",
    "fan_keyboard": "Fan",
    "keyboard": "Keyboard",
    "room_noise": "Room_Noise",
    "clap": "Clap",
    "knock": "Knock",
    "silence": "Silence",
}

ALLOWED_SUBTYPES = tuple(ENV_FOLDER_BY_SUBTYPE)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Thu PCM16 mono 16 kHz từ INMP441. Chạy không đối số sẽ dùng "
            "CAPTURE_MODE và các biến cấu hình ở đầu file."
        )
    )
    parser.add_argument(
        "--mode",
        choices=("VAD_RESEARCH", "DATASET_ENV"),
        default=CAPTURE_MODE,
        help="Ghi đè CAPTURE_MODE cho lần chạy hiện tại.",
    )
    parser.add_argument(
        "--name",
        help=(
            "Ghi đè VAD_FILE_NAME, ví dụ vad_silence_session_02.wav. "
            "Chỉ dùng trong mode VAD_RESEARCH."
        ),
    )
    parser.add_argument(
        "--seconds",
        type=float,
        help="Ghi đè thời lượng mặc định của mode được chọn.",
    )
    parser.add_argument("--port", default=SERIAL_PORT, help="Cổng Serial của ESP32-S3.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help=(
            "Thư mục cho WAV custom. Mặc định là "
            "Final_V1_Validation/03_VAD_Trigger/extra_validation."
        ),
    )
    return parser.parse_args()


def normalize_custom_wav_name(value):
    """Chuẩn hóa tên WAV custom và chặn đường dẫn lồng/ghi nhầm vị trí."""
    name = str(value or "").strip()
    if not name:
        raise ValueError("Tên WAV custom đang trống.")

    path = Path(name)
    if path.name != name or path.is_absolute():
        raise ValueError("--name chỉ nhận tên file, không nhận đường dẫn.")
    if path.suffix and path.suffix.casefold() != ".wav":
        raise ValueError("Tên custom chỉ được dùng phần mở rộng .wav.")

    stem = path.stem if path.suffix else path.name
    if not re.fullmatch(r"[A-Za-z0-9_-]+", stem):
        raise ValueError(
            "Tên WAV chỉ được chứa chữ không dấu, số, dấu gạch dưới và gạch ngang."
        )
    return stem + ".wav"


def read_existing_sessions():
    if not SESSION_CSV.exists():
        raise FileNotFoundError(f"Không tìm thấy bảng session: {SESSION_CSV}")

    with SESSION_CSV.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def create_next_session_id(env_name, existing_rows):
    """Tự tăng hậu tố dựa trên mọi session cùng subtype, kể cả master cũ."""
    numbers = []

    for row in existing_rows:
        if row.get("subtype") != env_name:
            continue

        match = re.search(r"_(\d+)$", row.get("session_id", ""))
        if match:
            numbers.append(int(match.group(1)))

    next_number = max(numbers, default=0) + 1
    return f"{env_name}_session_{next_number:02d}"


def append_session_csv(file_name, session_id, subtype, duration, note):
    with SESSION_CSV.open("a", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow([
            file_name,
            session_id,
            subtype,
            "environment",
            f"{duration:.3f}",
            SAMPLE_RATE,
            "unassigned",
            note,
        ])


def collect_audio(port, baud_rate, target_bytes, duration_seconds):
    audio_data = bytearray()

    print(f"Đang kết nối {port} ở {baud_rate} baud...")
    with serial.Serial(
        port=port,
        baudrate=baud_rate,
        timeout=READ_TIMEOUT_SECONDS,
        write_timeout=READ_TIMEOUT_SECONDS,
    ) as device:
        print(f"Ổn định micro trong {WARMUP_SECONDS:.0f} giây...")
        time.sleep(WARMUP_SECONDS)
        device.reset_input_buffer()
        device.write(b"R")
        device.flush()

        print(
            f"BẮT ĐẦU THU {duration_seconds:g} GIÂY "
            f"({target_bytes:,} byte PCM16)..."
        )
        started_at = time.monotonic()
        last_progress_second = -1

        try:
            while len(audio_data) < target_bytes:
                remaining = target_bytes - len(audio_data)
                chunk = device.read(min(8192, remaining))

                if not chunk:
                    raise TimeoutError(
                        "Không nhận được PCM trong 2 giây. "
                        "Kiểm tra cổng COM, dây INMP441 và đóng Serial Monitor."
                    )

                audio_data.extend(chunk)

                recorded_seconds = (
                    len(audio_data) / (SAMPLE_RATE * SAMPLE_WIDTH_BYTES)
                )
                whole_second = int(recorded_seconds)
                if whole_second != last_progress_second:
                    last_progress_second = whole_second
                    print(
                        f"\rĐã thu: {recorded_seconds:6.1f}/{duration_seconds:g} giây",
                        end="",
                        flush=True,
                    )
        finally:
            # Dừng ESP kể cả khi PC timeout hoặc người dùng ngắt script.
            device.write(b"S")
            device.flush()

        elapsed = time.monotonic() - started_at
        print(f"\nĐã nhận đủ dữ liệu trong {elapsed:.2f} giây.")

    return bytes(audio_data)


def write_wav(output_path, audio_data):
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(SAMPLE_WIDTH_BYTES)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(audio_data)


def main():
    args = parse_args()
    custom_mode = args.mode == "VAD_RESEARCH"
    record_seconds = args.seconds
    if record_seconds is None:
        record_seconds = (
            VAD_RECORD_SECONDS if custom_mode else DATASET_RECORD_SECONDS
        )

    if not custom_mode and ENV_NAME not in ALLOWED_SUBTYPES:
        raise ValueError(
            f"ENV_NAME='{ENV_NAME}' không hợp lệ. "
            f"Chọn một trong: {', '.join(ALLOWED_SUBTYPES)}"
        )
    if not custom_mode and (args.name or args.output_dir):
        raise ValueError("--name và --output-dir chỉ dùng với mode VAD_RESEARCH.")

    if record_seconds <= 0:
        raise ValueError("Thời lượng thu phải lớn hơn 0 giây.")

    if custom_mode:
        file_name = normalize_custom_wav_name(args.name or VAD_FILE_NAME)
        output_dir = (
            args.output_dir.expanduser().resolve()
            if args.output_dir
            else CUSTOM_VAD_OUTPUT_DIR
        )
        session_id = Path(file_name).stem
        output_path = output_dir / file_name
        session_label = "CUSTOM VAD (không tự ghi Env_session.csv)"
        existing_rows = None
    else:
        output_dir = RECORD_ENV_ROOT / ENV_FOLDER_BY_SUBTYPE[ENV_NAME]
        SESSION_CSV.parent.mkdir(parents=True, exist_ok=True)
        existing_rows = read_existing_sessions()
        session_id = create_next_session_id(ENV_NAME, existing_rows)
        output_path = output_dir / f"{session_id}.wav"
        session_label = ENV_NAME

        if any(row["session_id"] == session_id for row in existing_rows):
            raise ValueError(f"session_id đã tồn tại trong CSV: {session_id}")

    output_dir.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise FileExistsError(f"Không ghi đè WAV đã tồn tại: {output_path}")

    print("\n========== CẤU HÌNH SESSION ==========")
    print(f"Chế độ      : {session_label}")
    print(f"Session ID  : {session_id}")
    print(f"Thời lượng  : {record_seconds:g} giây")
    print(f"Cổng Serial : {args.port}")
    print(f"Output      : {output_path}")
    print("======================================")

    target_samples = round(record_seconds * SAMPLE_RATE)
    target_bytes = target_samples * SAMPLE_WIDTH_BYTES
    audio_data = collect_audio(
        args.port,
        BAUD_RATE,
        target_bytes,
        record_seconds,
    )

    if len(audio_data) != target_bytes or len(audio_data) % 2 != 0:
        raise RuntimeError(
            f"PCM không đủ hoặc lệch byte: nhận {len(audio_data)}, "
            f"cần {target_bytes}."
        )

    write_wav(output_path, audio_data)
    actual_duration = target_samples / SAMPLE_RATE
    if not custom_mode:
        append_session_csv(
            output_path.name,
            session_id,
            ENV_NAME,
            actual_duration,
            SESSION_NOTE,
        )

    print("\n========== THU SESSION THÀNH CÔNG ==========")
    print(f"Session ID : {session_id}")
    print(f"Chế độ     : {session_label}")
    print(f"WAV        : {output_path}")
    print(f"Thời lượng : {actual_duration:.3f} giây")
    print(f"Định dạng  : mono PCM16, {SAMPLE_RATE} Hz")
    if custom_mode:
        print("CSV        : Không cập nhật; hãy duyệt WAV trước khi đăng ký session.")
    else:
        print(f"CSV        : {SESSION_CSV}")
    print("============================================")


if __name__ == "__main__":
    main()
