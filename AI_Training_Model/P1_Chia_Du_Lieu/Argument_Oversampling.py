"""
===============================================================================
Tên script: Argument_Oversampling.py

Tác dụng:
- Cung cấp các hàm tăng cường Asthma: trộn nhiễu môi trường, dịch vị trí âm
  thanh, thêm nhiễu trắng, co giãn thời gian và đổi cao độ.
- Chuẩn hóa kết quả về 16 kHz và 5 giây để script chia Asthma sử dụng.

Điểm tinh chỉnh so với model ban đầu:
- Các hàm này chỉ được gọi cho file cha thuộc Asthma train và chỉ dùng nguồn
  nhiễu thuộc train; không áp dụng cho val/test.
- File này chỉ chứa phép biến đổi; quy tắc chia và số lượng nằm trong
  2_Chia_va_Tang_Cuong_Asthma.py.
===============================================================================
"""

import os
import glob
import random
import librosa
import numpy as np

Target_Sr = 16000
Target_Duration = 5.0

Target_Samples = int(Target_Sr * Target_Duration)

Dir_Asthma_Raw = "Dataset/3_asthma"
Dir_Non_Asthma_Raw = "Dataset/4_Raw_Non_Asthma"
Dir_Tu_Thu = "Dataset/2_TuThu"

def mix_with_noise(audio, noise_audio, min_gain=0.02, max_gain=0.1):
    coef = random.uniform(min_gain, max_gain)    
    noise_audio = librosa.util.fix_length(noise_audio, size=Target_Samples)
    mixed_audio = audio + (noise_audio * coef)

    return mixed_audio

def time_shift_on_silence(audio, silence_audio):
    silence_fixed = librosa.util.fix_length(silence_audio, size=Target_Samples)
    
    rms_energy = librosa.feature.rms(y=audio)[0]

    max_energy_frame = np.argmax(rms_energy)

    center_idx = librosa.frames_to_samples(max_energy_frame)

    core_length = int(4 * Target_Sr) 
    haft_core = core_length // 2 

    start_cut = max(0, center_idx - haft_core)
    end_cut   = min(len(audio), center_idx + haft_core) 

    core_audio = audio[start_cut:end_cut]

    core_audio = librosa.util.fix_length(core_audio, size=core_length)

    insert_idx = random.randint(0, Target_Samples - core_length)

    shifted_audio = np.copy(silence_audio)
    shifted_audio[insert_idx : insert_idx + core_length] += core_audio 

    return shifted_audio   

def add_white_noise(audio, noise_level=0.001):
    noise = np.random.randn(len(audio))
    agumented_audio = audio + noise_level * noise
    
    return agumented_audio

def time_stretch(audio):
    rate = random.uniform(0.8, 1.2)
    stretched = librosa.effects.time_stretch(y=audio, rate=rate)
    stretched_fix = librosa.util.fix_length(stretched, size=Target_Samples)

    return stretched_fix

def pitch_shift(audio):
    n_steps = random.uniform(-0.5, 0.5)
    shifted = librosa.effects.pitch_shift(y=audio, sr=Target_Sr, n_steps=n_steps)

    shifted_fix = librosa.util.fix_length(shifted, size=Target_Samples)

    return shifted_fix
