"""
===============================================================================
Tên script: Argument_Oversampling.py

Tác dụng:
- Chứa năm phép tăng cường dùng riêng cho Asthma Core thuộc tập Train.
- Mọi kết quả đều được đưa về mono, 16 kHz, đúng 5 giây và giới hạn trong
  miền [-1, 1] trước khi ghi WAV.

Quy tắc V2:
- Không tăng cường Playback, Validation hoặc Test.
- Nguồn môi trường dùng để trộn phải thuộc Train.
- Tham số mặc định: gain môi trường 0.02-0.10, time stretch 0.90-1.10,
  pitch shift +/-0.5 bán âm và white noise 0.001.
===============================================================================
"""

import random

import librosa
import numpy as np


TARGET_SR = 16000
TARGET_DURATION = 5.0
TARGET_SAMPLES = int(TARGET_SR * TARGET_DURATION)


def fix_audio_length(audio):
    """Đưa tín hiệu về float32, đúng 5 giây và giới hạn miền PCM chuẩn."""
    audio = np.asarray(audio, dtype=np.float32)
    audio = librosa.util.fix_length(audio, size=TARGET_SAMPLES)
    return np.clip(audio, -1.0, 1.0).astype(np.float32)


def mix_with_noise(
    audio,
    noise_audio,
    gain=None,
    min_gain=0.02,
    max_gain=0.10,
    rng=None,
):
    """Trộn tín hiệu Asthma với một nguồn môi trường Train."""
    rng = rng or random
    if gain is None:
        gain = rng.uniform(min_gain, max_gain)
    if not min_gain <= gain <= max_gain:
        raise ValueError(f"gain phải nằm trong [{min_gain}, {max_gain}].")

    audio = fix_audio_length(audio)
    noise_audio = fix_audio_length(noise_audio)
    return np.clip(audio + noise_audio * gain, -1.0, 1.0).astype(np.float32)


def time_shift_on_silence(audio, silence_audio, insert_index=None, rng=None):
    """Lấy vùng âm chính dài 4 giây và đặt ngẫu nhiên vào nền im lặng 5 giây."""
    rng = rng or random
    audio = fix_audio_length(audio)
    silence_fixed = fix_audio_length(silence_audio)

    rms_energy = librosa.feature.rms(y=audio)[0]
    center_index = int(librosa.frames_to_samples(int(np.argmax(rms_energy))))

    core_length = int(4 * TARGET_SR)
    half_core = core_length // 2
    start_cut = max(0, center_index - half_core)
    end_cut = min(len(audio), center_index + half_core)
    core_audio = librosa.util.fix_length(
        audio[start_cut:end_cut], size=core_length
    )

    max_insert = TARGET_SAMPLES - core_length
    if insert_index is None:
        insert_index = rng.randint(0, max_insert)
    if not 0 <= insert_index <= max_insert:
        raise ValueError(f"insert_index phải nằm trong [0, {max_insert}].")

    # Dùng silence_fixed thay vì silence_audio để đầu ra luôn đúng 5 giây.
    shifted_audio = np.copy(silence_fixed)
    shifted_audio[insert_index:insert_index + core_length] += core_audio
    return np.clip(shifted_audio, -1.0, 1.0).astype(np.float32)


def add_white_noise(audio, noise_level=0.001, np_rng=None):
    """Thêm nhiễu trắng rất nhẹ trên tín hiệu float thuộc miền [-1, 1]."""
    if noise_level < 0:
        raise ValueError("noise_level không được âm.")

    audio = fix_audio_length(audio)
    np_rng = np_rng or np.random.default_rng()
    noise = np_rng.standard_normal(len(audio)).astype(np.float32)
    return np.clip(audio + noise_level * noise, -1.0, 1.0).astype(np.float32)


def time_stretch(
    audio,
    rate=None,
    min_rate=0.90,
    max_rate=1.10,
    rng=None,
):
    """Co giãn thời gian nhẹ, không làm thay đổi cao độ."""
    rng = rng or random
    if rate is None:
        rate = rng.uniform(min_rate, max_rate)
    if not min_rate <= rate <= max_rate:
        raise ValueError(f"rate phải nằm trong [{min_rate}, {max_rate}].")

    audio = fix_audio_length(audio)
    stretched = librosa.effects.time_stretch(y=audio, rate=rate)
    return fix_audio_length(stretched)


def pitch_shift(
    audio,
    n_steps=None,
    min_steps=-0.5,
    max_steps=0.5,
    rng=None,
):
    """Đổi cao độ nhẹ trong khoảng +/-0.5 bán âm."""
    rng = rng or random
    if n_steps is None:
        n_steps = rng.uniform(min_steps, max_steps)
    if not min_steps <= n_steps <= max_steps:
        raise ValueError(f"n_steps phải nằm trong [{min_steps}, {max_steps}].")

    audio = fix_audio_length(audio)
    shifted = librosa.effects.pitch_shift(
        y=audio,
        sr=TARGET_SR,
        n_steps=n_steps,
    )
    return fix_audio_length(shifted)
