"""
===============================================================================
Tên script: Record_Playback.py

Tác dụng:
- Đọc danh sách nguồn cố định từ Playback_Source_List.csv.
- Phát từng WAV qua loa máy tính và đồng thời thu lại bằng INMP441.
- Mỗi source có đúng hai take; hai take giữ nguyên split của source gốc.
- Tự bỏ qua output đã tồn tại để có thể dừng rồi chạy tiếp.
- Ghi lịch sử các take thành công vào Playback_capture_log.csv.

Chạy:
python Record_Playback.py

Lưu ý:
- Nạp firmware của project ESP32_Read_INMP441 trước khi chạy.
- Đóng Serial Monitor để script chiếm COM11.
- Chỉnh âm lượng Windows/loa bằng tay và giữ điều kiện thu ổn định.
===============================================================================
"""

import csv
import hashlib
import math
import sys
import threading
import time
import wave
import winsound
from array import array
from datetime import datetime
from pathlib import Path

try:
    import serial
except ImportError as error:
    raise SystemExit("Thiếu pyserial. Cài bằng: pip install pyserial") from error


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ======================== CẤU HÌNH CẦN ĐỔI ================================

SERIAL_PORT = "COM11"

# Chọn nhóm muốn thu:
# ALL, Asthma, Bronchial, COPD, Healthy hoặc Pneumonia.
CAPTURE_GROUP = "ALL"

# Khoảng im lặng được giữ lại trước và sau file phát.
LEAD_IN_SECONDS = 0.6
TAIL_OUT_SECONDS = 0.6

# Không cho output ngắn hơn 5 giây dù source ngắn hơn.
MIN_CAPTURE_SECONDS = 5.0

# False: xác nhận/nghe lại từng take. True: tự chạy toàn bộ hàng đợi.
CONTINUOUS_MODE = True

# Thời gian nghỉ tự động giữa hai take trong chế độ liên tục.
# Có thể để 0.0 nếu loa và micro đã được đặt cố định.
DELAY_BETWEEN_TAKES_SECONDS = 1.0

# Ba giá trị metadata: script không tự chỉnh âm lượng hoặc đo khoảng cách.
PLAYBACK_VOLUME_PERCENT = 60
SPEAKER_DISTANCE_CM = 6.0
PLAYBACK_DEVICE_NOTE = "Loa mặc định của Windows"

# ========================================================================

SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH_BYTES = 2
BAUD_RATE = 460800
SERIAL_WARMUP_SECONDS = 2.0
READ_TIMEOUT_SECONDS = 2.0

# Chỉ dùng để chặn file hỏng rõ ràng trong chế độ liên tục.
# Đây không phải ngưỡng Final của Model V2.
AUTO_MIN_RECORDED_RMS = 20.0
AUTO_MAX_RECORDED_CLIPPED_RATIO = 0.01
AUTO_CLIP_LEVEL = 32000

PROJECT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = PROJECT_DIR.parents[1]
DATASET_ROOT = WORKSPACE_DIR / "AI_Training_Model" / "Dataset_TuThu_v_Kaggle"
TUTHU_DIR = DATASET_ROOT / "TuThu"
SOURCE_LIST_CSV = WORKSPACE_DIR / "AI_Training_Model" / "Phase1_Split_Data" / "Output" / "01_Random_Playback" / "Playback_Source_List.csv"
OUTPUT_ROOT = TUTHU_DIR / "Playback_Raw"
CAPTURE_LOG_CSV = TUTHU_DIR / "TKe" / "Playback_capture_log.csv"

ALLOWED_GROUPS = {
    "ALL",
    "Asthma",
    "Bronchial",
    "COPD",
    "Healthy",
    "Pneumonia",
}

LOG_FIELDS = (
    "captured_at",
    "source_id",
    "label",
    "subtype",
    "group_id",
    "split",
    "take_id",
    "source_relative_path",
    "output_relative_path",
    "source_duration_seconds",
    "capture_duration_seconds",
    "sample_rate",
    "serial_port",
    "lead_in_seconds",
    "tail_out_seconds",
    "playback_volume_percent",
    "speaker_distance_cm",
    "playback_device_note",
    "recorded_peak_pcm",
    "recorded_rms_pcm",
    "recorded_clipped_ratio",
    "status",
)


def read_source_list():
    if not SOURCE_LIST_CSV.is_file():
        raise FileNotFoundError(f"Không tìm thấy danh sách playback: {SOURCE_LIST_CSV}")

    with SOURCE_LIST_CSV.open("r", newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))

    required = {
        "source_id",
        "label",
        "subtype",
        "group_id",
        "split",
        "source_relative_path",
        "source_duration_seconds",
        "source_sha256",
        "take_01_file",
        "take_02_file",
    }
    missing = required.difference(rows[0].keys() if rows else ())
    if missing:
        raise ValueError(f"Playback_Source_List.csv thiếu cột: {sorted(missing)}")
    return rows


def output_path_for(row, take_number):
    file_name = row[f"take_{take_number:02d}_file"]
    if row["label"] == "Asthma":
        folder = OUTPUT_ROOT / "Asthma"
    else:
        folder = OUTPUT_ROOT / "Non_Asthma"
    return folder / file_name


def validate_source(row):
    source_path = DATASET_ROOT / Path(row["source_relative_path"])
    if not source_path.is_file():
        raise FileNotFoundError(f"Thiếu source: {source_path}")

    actual_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if actual_hash != row["source_sha256"]:
        raise ValueError(f"Source đã thay đổi nội dung: {source_path}")

    with wave.open(str(source_path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        frame_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
        compression = wav_file.getcomptype()

    if channels != 1 or sample_width != 2 or compression != "NONE":
        raise ValueError(
            f"Source không phải mono PCM16 không nén: {source_path.name}"
        )

    duration = frame_count / frame_rate
    listed_duration = float(row["source_duration_seconds"])
    if abs(duration - listed_duration) > 0.01:
        raise ValueError(f"Thời lượng source không khớp CSV: {source_path.name}")

    return source_path, duration


def write_pcm16_wav(output_path, audio_data):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(SAMPLE_WIDTH_BYTES)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(audio_data)


def append_capture_log(row):
    CAPTURE_LOG_CSV.parent.mkdir(parents=True, exist_ok=True)
    existing_rows = []
    if CAPTURE_LOG_CSV.exists():
        with CAPTURE_LOG_CSV.open("r", newline="", encoding="utf-8-sig") as file:
            existing_rows = list(csv.DictReader(file))

    # source_id + take_id là khóa duy nhất. Thu lại sẽ thay log cũ, không nhân đôi.
    existing_rows = [
        old
        for old in existing_rows
        if not (
            old.get("source_id") == row["source_id"]
            and old.get("take_id") == row["take_id"]
        )
    ]
    existing_rows.append(row)

    temp_path = CAPTURE_LOG_CSV.with_suffix(".csv.tmp")
    with temp_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=LOG_FIELDS)
        writer.writeheader()
        writer.writerows(existing_rows)
    temp_path.replace(CAPTURE_LOG_CSV)


def stop_playback():
    try:
        winsound.PlaySound(None, winsound.SND_PURGE)
    except RuntimeError:
        pass


def capture_take(device, source_path, capture_seconds):
    target_samples = round(capture_seconds * SAMPLE_RATE)
    target_bytes = target_samples * SAMPLE_WIDTH_BYTES
    audio_data = bytearray()
    playback_error = []

    def start_playback():
        try:
            winsound.PlaySound(
                str(source_path),
                winsound.SND_FILENAME | winsound.SND_ASYNC,
            )
        except RuntimeError as error:
            playback_error.append(error)

    device.reset_input_buffer()
    device.write(b"R")
    device.flush()

    playback_timer = threading.Timer(LEAD_IN_SECONDS, start_playback)
    playback_timer.start()
    print(
        f"BẮT ĐẦU THU {capture_seconds:.2f} GIÂY; "
        f"source sẽ phát sau {LEAD_IN_SECONDS:.1f} giây..."
    )

    last_progress_second = -1
    try:
        while len(audio_data) < target_bytes:
            remaining = target_bytes - len(audio_data)
            chunk = device.read(min(8192, remaining))
            if not chunk:
                raise TimeoutError(
                    "Không nhận được PCM trong 2 giây. Kiểm tra COM và đóng Serial Monitor."
                )

            audio_data.extend(chunk)
            recorded_seconds = len(audio_data) / (
                SAMPLE_RATE * SAMPLE_WIDTH_BYTES
            )
            whole_second = int(recorded_seconds)
            if whole_second != last_progress_second:
                last_progress_second = whole_second
                print(
                    f"\rĐã thu: {recorded_seconds:5.1f}/{capture_seconds:.1f} giây",
                    end="",
                    flush=True,
                )
    finally:
        playback_timer.cancel()
        stop_playback()
        try:
            device.write(b"S")
            device.flush()
        except serial.SerialException:
            pass

    print()
    if playback_error:
        raise RuntimeError(f"Không phát được WAV: {playback_error[0]}")
    if len(audio_data) != target_bytes or len(audio_data) % 2:
        raise RuntimeError(
            f"PCM không đủ hoặc lệch byte: nhận {len(audio_data)}, cần {target_bytes}."
        )
    return bytes(audio_data), target_samples / SAMPLE_RATE


def calculate_recorded_metrics(audio_data):
    samples = array("h")
    samples.frombytes(audio_data)
    if sys.byteorder != "little":
        samples.byteswap()
    if not samples:
        return {
            "peak": 0,
            "rms": 0.0,
            "clipped_ratio": 0.0,
            "auto_ok": False,
        }

    peak = max(abs(sample) for sample in samples)
    square_sum = sum(sample * sample for sample in samples)
    rms = math.sqrt(square_sum / len(samples))
    clipped_count = sum(abs(sample) > AUTO_CLIP_LEVEL for sample in samples)
    clipped_ratio = clipped_count / len(samples)
    auto_ok = (
        rms >= AUTO_MIN_RECORDED_RMS
        and clipped_ratio <= AUTO_MAX_RECORDED_CLIPPED_RATIO
    )
    return {
        "peak": peak,
        "rms": rms,
        "clipped_ratio": clipped_ratio,
        "auto_ok": auto_ok,
    }


def preview_source(source_path):
    print(f"Đang phát thử: {source_path.name}")
    winsound.PlaySound(str(source_path), winsound.SND_FILENAME)


def ask_action():
    if CONTINUOUS_MODE:
        return ""
    return input(
        "Enter=thu | P=nghe thử | S=bỏ qua take này | Q=dừng: "
    ).strip().lower()


def review_pending_capture(pending_path):
    """Chỉ đổi pending thành output chính thức khi người thu xác nhận đạt."""
    if CONTINUOUS_MODE:
        return "accept"

    while True:
        action = input(
            "Kiểm tra take: Enter=chấp nhận | P=nghe lại | "
            "R=thu lại | S=bỏ qua | Q=dừng: "
        ).strip().lower()
        if action == "p":
            preview_source(pending_path)
            continue
        if action in ("", "a"):
            return "accept"
        if action == "r":
            return "retry"
        if action == "s":
            return "skip"
        if action == "q":
            return "quit"
        print("Lệnh không hợp lệ. Chọn Enter, P, R, S hoặc Q.")


def build_pending_queue(rows):
    pending = []
    for row in rows:
        if CAPTURE_GROUP != "ALL" and row["subtype"] != CAPTURE_GROUP:
            continue
        for take_number in (1, 2):
            output_path = output_path_for(row, take_number)
            if not output_path.exists():
                pending.append((row, take_number, output_path))
    return pending


def run_capture_queue(device, pending):
    skipped = 0
    captured_now = 0

    for queue_index, (row, take_number, output_path) in enumerate(pending, start=1):
        source_path, source_duration = validate_source(row)
        capture_seconds = max(
            MIN_CAPTURE_SECONDS,
            LEAD_IN_SECONDS + source_duration + TAIL_OUT_SECONDS,
        )

        print("\n--------------------------------------------------")
        print(f"Tiến độ      : {queue_index}/{len(pending)} take còn thiếu")
        print(f"Source ID    : {row['source_id']}")
        print(f"Nhãn / bệnh  : {row['label']} / {row['subtype']}")
        print(f"Nhóm bệnh nhân: {row['group_id']}")
        print(f"Split        : {row['split']}")
        print(f"Source       : {source_path.name}")
        print(f"Take         : {take_number}/2")
        print(f"Thu dự kiến  : {capture_seconds:.2f} giây")
        print(f"Output       : {output_path}")

        while True:
            action = ask_action()
            if action == "p":
                preview_source(source_path)
                continue
            if action == "s":
                skipped += 1
                break
            if action == "q":
                print("Đã dừng an toàn. Lần sau chạy lại sẽ tiếp tục take còn thiếu.")
                return captured_now, skipped, True
            if action != "":
                print("Lệnh không hợp lệ. Chọn Enter, P, S hoặc Q.")
                continue

            while True:
                audio_data, actual_duration = capture_take(
                    device,
                    source_path,
                    capture_seconds,
                )
                recorded_metrics = calculate_recorded_metrics(audio_data)
                pending_path = output_path.with_name(
                    f"{output_path.stem}__pending.wav"
                )
                write_pcm16_wav(pending_path, audio_data)

                print(
                    "Kiểm tra nhanh | "
                    f"Peak={recorded_metrics['peak']} | "
                    f"RMS={recorded_metrics['rms']:.2f} | "
                    f"Clipping={recorded_metrics['clipped_ratio'] * 100:.4f}%"
                )

                if CONTINUOUS_MODE and not recorded_metrics["auto_ok"]:
                    print(
                        "[DỪNG AUTO] Take không đạt kiểm tra sơ bộ. "
                        f"File tạm được giữ để xem lại: {pending_path}"
                    )
                    return captured_now, skipped, True

                review = review_pending_capture(pending_path)
                if review == "retry":
                    pending_path.unlink(missing_ok=True)
                    print("Đã bỏ take lỗi. Chuẩn bị thu lại đúng source/take này.")
                    continue
                if review == "skip":
                    pending_path.unlink(missing_ok=True)
                    skipped += 1
                    break
                if review == "quit":
                    pending_path.unlink(missing_ok=True)
                    print("Đã dừng an toàn; take chưa được chấp nhận không được lưu.")
                    return captured_now, skipped, True

                pending_path.replace(output_path)
                append_capture_log({
                    "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "source_id": row["source_id"],
                    "label": row["label"],
                    "subtype": row["subtype"],
                    "group_id": row["group_id"],
                    "split": row["split"],
                    "take_id": f"take{take_number:02d}",
                    "source_relative_path": row["source_relative_path"],
                    "output_relative_path": output_path.relative_to(TUTHU_DIR).as_posix(),
                    "source_duration_seconds": f"{source_duration:.3f}",
                    "capture_duration_seconds": f"{actual_duration:.3f}",
                    "sample_rate": SAMPLE_RATE,
                    "serial_port": SERIAL_PORT,
                    "lead_in_seconds": LEAD_IN_SECONDS,
                    "tail_out_seconds": TAIL_OUT_SECONDS,
                    "playback_volume_percent": PLAYBACK_VOLUME_PERCENT,
                    "speaker_distance_cm": SPEAKER_DISTANCE_CM,
                    "playback_device_note": PLAYBACK_DEVICE_NOTE,
                    "recorded_peak_pcm": recorded_metrics["peak"],
                    "recorded_rms_pcm": f"{recorded_metrics['rms']:.3f}",
                    "recorded_clipped_ratio": (
                        f"{recorded_metrics['clipped_ratio']:.6f}"
                    ),
                    "status": (
                        "captured_auto_accepted"
                        if CONTINUOUS_MODE
                        else "captured_and_accepted"
                    ),
                })
                captured_now += 1
                print(f"ĐÃ CHẤP NHẬN: {output_path}")

                if CONTINUOUS_MODE and DELAY_BETWEEN_TAKES_SECONDS > 0:
                    print(
                        f"Chờ {DELAY_BETWEEN_TAKES_SECONDS:g} giây trước take tiếp theo..."
                    )
                    time.sleep(DELAY_BETWEEN_TAKES_SECONDS)
                break
            break

    return captured_now, skipped, False


def main():
    if CAPTURE_GROUP not in ALLOWED_GROUPS:
        raise ValueError(
            f"CAPTURE_GROUP='{CAPTURE_GROUP}' không hợp lệ. "
            f"Chọn: {', '.join(sorted(ALLOWED_GROUPS))}"
        )
    if LEAD_IN_SECONDS < 0 or TAIL_OUT_SECONDS < 0:
        raise ValueError("LEAD_IN_SECONDS và TAIL_OUT_SECONDS không được âm.")
    if DELAY_BETWEEN_TAKES_SECONDS < 0:
        raise ValueError("DELAY_BETWEEN_TAKES_SECONDS không được âm.")
    if not 0 <= PLAYBACK_VOLUME_PERCENT <= 100:
        raise ValueError("PLAYBACK_VOLUME_PERCENT phải nằm trong khoảng 0–100.")
    if SPEAKER_DISTANCE_CM <= 0:
        raise ValueError("SPEAKER_DISTANCE_CM phải lớn hơn 0.")

    rows = read_source_list()
    pending = build_pending_queue(rows)
    total_expected = sum(
        2
        for row in rows
        if CAPTURE_GROUP == "ALL" or row["subtype"] == CAPTURE_GROUP
    )
    completed = total_expected - len(pending)

    print("\n================ PLAYBACK DATASET ================")
    print(f"Nhóm đang thu : {CAPTURE_GROUP}")
    print(f"Đã có         : {completed}/{total_expected} take")
    print(f"Còn thiếu     : {len(pending)} take")
    print(f"Âm lượng ghi  : {PLAYBACK_VOLUME_PERCENT}% (hãy đặt thủ công)")
    print(f"Khoảng cách   : {SPEAKER_DISTANCE_CM:g} cm")
    print(f"Thiết bị phát : {PLAYBACK_DEVICE_NOTE}")
    print(f"Output        : {OUTPUT_ROOT}")
    print("==================================================")

    if not pending:
        print("Nhóm đã đủ toàn bộ take, không cần thu thêm.")
        return

    print(
        "Chế độ        : "
        f"{'LIÊN TỤC TỰ ĐỘNG' if CONTINUOUS_MODE else 'THỦ CÔNG CÓ KIỂM TRA'}"
    )
    print(f"Đang kết nối {SERIAL_PORT} ở {BAUD_RATE} baud...")
    with serial.Serial(
        port=SERIAL_PORT,
        baudrate=BAUD_RATE,
        timeout=READ_TIMEOUT_SECONDS,
        write_timeout=READ_TIMEOUT_SECONDS,
    ) as device:
        print(f"Ổn định micro một lần trong {SERIAL_WARMUP_SECONDS:.0f} giây...")
        time.sleep(SERIAL_WARMUP_SECONDS)
        captured_now, skipped, stopped_early = run_capture_queue(device, pending)

    print("\n================ HOÀN TẤT LƯỢT CHẠY ================")
    print(f"Thu mới : {captured_now} take")
    print(f"Bỏ qua  : {skipped} take")
    print(f"Dừng sớm: {'Có' if stopped_early else 'Không'}")
    print(f"Log     : {CAPTURE_LOG_CSV}")
    print("=====================================================")


if __name__ == "__main__":
    main()
