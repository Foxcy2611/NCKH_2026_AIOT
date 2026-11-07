"""Nhan mot frame PCM16 tu firmware Asthma_Playback_Calibration va luu capture.wav.

Dong Serial Monitor truoc khi chay vi chi mot chuong trinh duoc mo COM11.
Firmware debug dump moi capture; script nay nhan capture tiep theo roi thoat.
"""

from __future__ import annotations

import re
import time
import wave
from pathlib import Path

import serial


# =============================================================================
# CAU HINH DE DOI TRUC TIEP
# =============================================================================

SERIAL_PORT = "COM11"
SERIAL_BAUD = 460_800
WAIT_FOR_CAPTURE_SECONDS = 180.0
BINARY_READ_TIMEOUT_SECONDS = 30.0
OUTPUT_WAV = Path(__file__).resolve().parent / "capture.wav"


CAPTURE_HEADER = re.compile(
    rb"^\[CAPTURE_BEGIN\] "
    rb"version=(?P<version>\d+) "
    rb"samples=(?P<samples>\d+) "
    rb"sample_rate=(?P<sample_rate>\d+) "
    rb"channels=(?P<channels>\d+) "
    rb"sample_width=(?P<sample_width>\d+) "
    rb"encoding=(?P<encoding>\S+) "
    rb"bytes=(?P<bytes>\d+) "
    rb"fnv1a=(?P<fnv1a>[0-9A-Fa-f]{8})$"
)

CAPTURE_END = re.compile(
    rb"^\[CAPTURE_END\] "
    rb"bytes_written=(?P<bytes_written>\d+) "
    rb"fnv1a=(?P<fnv1a>[0-9A-Fa-f]{8})$"
)


def fnv1a32(data: bytes) -> int:
    value = 0x811C9DC5
    for byte in data:
        value ^= byte
        value = (value * 0x01000193) & 0xFFFFFFFF
    return value


def read_exact(port: serial.Serial, byte_count: int, timeout_seconds: float) -> bytes:
    deadline = time.monotonic() + timeout_seconds
    result = bytearray()

    while len(result) < byte_count:
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"Timeout khi nhan PCM: {len(result)}/{byte_count} byte"
            )

        chunk = port.read(byte_count - len(result))
        if chunk:
            result.extend(chunk)

    return bytes(result)


def wait_for_header(port: serial.Serial) -> re.Match[bytes]:
    deadline = time.monotonic() + WAIT_FOR_CAPTURE_SECONDS
    print("Dang cho VAD va frame [CAPTURE_BEGIN]...")
    print("Bay gio hay phat WAV qua loa sau khi firmware bao ring buffer san sang.")

    while time.monotonic() < deadline:
        line = port.readline().rstrip(b"\r\n")
        if not line:
            continue

        match = CAPTURE_HEADER.match(line)
        if match:
            print(line.decode("ascii"))
            return match

        print(line.decode("utf-8", errors="replace"))

    raise TimeoutError("Khong nhan duoc CAPTURE_BEGIN trong thoi gian cho")


def read_end_marker(port: serial.Serial) -> re.Match[bytes]:
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        line = port.readline().strip()
        if not line:
            continue
        match = CAPTURE_END.match(line)
        if match:
            print(line.decode("ascii"))
            return match
        raise RuntimeError(f"Marker sau PCM khong hop le: {line[:120]!r}")
    raise TimeoutError("Khong nhan duoc CAPTURE_END")


def save_wav(
    path: Path,
    pcm_bytes: bytes,
    sample_rate: int,
    channels: int,
    sample_width: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)


def main() -> None:
    print("=" * 72)
    print("ESP32 PCM16 CAPTURE RECEIVER")
    print("=" * 72)
    print(f"Serial : {SERIAL_PORT} @ {SERIAL_BAUD}")
    print(f"Output : {OUTPUT_WAV}")

    with serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=0.25) as port:
        # Mot so board reset khi Python mo cong. Cho bootloader/firmware on dinh,
        # nhung khong xoa RX de van thay duoc log khoi dong neu board khong reset.
        port.dtr = False
        port.rts = False
        time.sleep(1.0)

        header_match = wait_for_header(port)
        metadata = {
            key: value.decode("ascii")
            for key, value in header_match.groupdict().items()
        }

        if metadata["version"] != "1":
            raise ValueError(f"Protocol version khong ho tro: {metadata['version']}")
        if metadata["encoding"] != "pcm_s16le":
            raise ValueError(f"Encoding khong ho tro: {metadata['encoding']}")

        sample_count = int(metadata["samples"])
        sample_rate = int(metadata["sample_rate"])
        channels = int(metadata["channels"])
        sample_width = int(metadata["sample_width"])
        byte_count = int(metadata["bytes"])
        expected_checksum = int(metadata["fnv1a"], 16)

        expected_bytes = sample_count * channels * sample_width
        if byte_count != expected_bytes:
            raise ValueError(
                f"Metadata khong nhat quan: bytes={byte_count}, "
                f"samples*channels*width={expected_bytes}"
            )

        print(f"Dang nhan {byte_count} byte PCM nhi phan...")
        pcm_bytes = read_exact(port, byte_count, BINARY_READ_TIMEOUT_SECONDS)
        end_match = read_end_marker(port)

        actual_checksum = fnv1a32(pcm_bytes)
        end_bytes = int(end_match.group("bytes_written"))
        end_checksum = int(end_match.group("fnv1a"), 16)

        if end_bytes != byte_count:
            raise IOError(f"ESP32 chi gui {end_bytes}/{byte_count} byte")
        if actual_checksum != expected_checksum or end_checksum != expected_checksum:
            raise IOError(
                "Checksum FNV-1a sai: "
                f"header={expected_checksum:08X}, data={actual_checksum:08X}, "
                f"end={end_checksum:08X}"
            )

        save_wav(
            OUTPUT_WAV,
            pcm_bytes,
            sample_rate,
            channels,
            sample_width,
        )

    duration = sample_count / sample_rate
    print("=" * 72)
    print("DA LUU CAPTURE THANH CONG")
    print(f"File     : {OUTPUT_WAV}")
    print(f"Samples  : {sample_count}")
    print(f"Duration : {duration:.3f} s")
    print(f"Format   : PCM16 LE, {sample_rate} Hz, {channels} channel")
    print(f"FNV-1a  : {actual_checksum:08X}")


if __name__ == "__main__":
    main()
