"""
===============================================================================
Tên script: 2_Chia_va_Tang_Cuong_Asthma.py

Tác dụng:
- Gom 288 file Asthma gốc theo mã bệnh nhân và chia cả nhóm bệnh nhân thành
  train/val/test.
- Chỉ tăng cường các file Asthma thuộc train bằng năm phép biến đổi âm thanh.
- Sinh số Asthma train gần bằng số Non-Asthma train thực tế và lưu thông tin
  file cha/phương pháp để truy vết.

Điểm tinh chỉnh so với model ban đầu:
- Chia bệnh nhân trước rồi mới tăng cường, nên file gốc và các bản họ hàng
  tăng cường không thể lọt sang val/test.
- Val/test chỉ giữ file gốc; không nhân bản dữ liệu để làm đẹp điểm đánh giá.
===============================================================================
"""

import re
import csv
import os
import random
import shutil
import hashlib
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

from Argument_Oversampling import (
    mix_with_noise, time_shift_on_silence, add_white_noise,
    time_stretch, pitch_shift
)


SEED = 42
SR = 16000
SAMPLES = SR * 5

# Đường dẫn mặc định khi chạy từ thư mục gốc NCKH_2026_AIOT.
RAW = Path(os.path.join("AI_Training_Model", "Dataset", "3_asthma"))
NOISE = Path(os.path.join("AI_Training_Model", "Dataset", "2_TuThu"))
OUT = Path(os.path.join("AI_Training_Model", "Dataset_Chia", "Asthma"))

# ==<>== Đường dẫn CSV của Non_Asthma, dùng để tính target ĐỘNG,
# thay vì hard-code TARGET_TRAIN = 836 như bản cũ.
# BẮT BUỘC chạy 2_Chia_Non_Asthma.py trước script này.
NON_ASTHMA_OUT = Path(os.path.join(
    "AI_Training_Model", "Dataset_Chia", "Non_Asthma"
))


def get_patient(file):
    match = re.match(r"P\d+", file.name)
    if not match:
        raise ValueError(f"Tên file không đúng định dạng P<số>: {file.name}")
    return match.group()


# ==<>== THÊM: hash-dedup cho Asthma gốc, đồng bộ với 2_Chia_Non_Asthma.py
def remove_duplicates(files):
    unique = []
    duplicates = []
    seen = {}

    for file in files:
        file_hash = hashlib.sha256(file.read_bytes()).hexdigest()
        if file_hash in seen:
            duplicates.append([file.name, seen[file_hash].name])
        else:
            seen[file_hash] = file
            unique.append(file)

    return unique, duplicates


def split_data():
    if (OUT / "train").exists():
        return

    raw_files = sorted(RAW.glob("*.wav"))
    raw_files, duplicates = remove_duplicates(raw_files)

    groups = {}
    for file in raw_files:
        groups.setdefault(get_patient(file), []).append(file)

    patients = list(groups)
    random.seed(SEED)
    random.shuffle(patients)

    # Chia theo tỉ lệ 80/10/10 trên SỐ BỆNH NHÂN, không hard-code số cố định,
    # để linh hoạt khi tổng số bệnh nhân thay đổi (thêm dữ liệu sau này)
    n_total = len(patients)
    n_train = round(n_total * 0.8)
    n_val = (n_total - n_train) // 2

    parts = {
        "train": patients[:n_train],
        "val": patients[n_train:n_train + n_val],
        "test": patients[n_train + n_val:]
    }

    rows = []
    for part, patient_list in parts.items():
        folder = OUT / part
        folder.mkdir(parents=True)

        for patient in patient_list:
            for file in groups[patient]:
                shutil.copy2(file, folder / file.name)
                rows.append([file.name, patient, part])

    with open(OUT / "chia_du_lieu.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["file_name", "patient_id", "split"])
        writer.writerows(rows)

    with open(OUT / "file_trung.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["file_bo_qua", "trung_voi_file"])
        writer.writerows(duplicates)

    print(f"Bỏ qua file trùng: {len(duplicates)} file")
    print(f"Tổng bệnh nhân: {n_total} -> Train {len(parts['train'])} / Val {len(parts['val'])} / Test {len(parts['test'])}")


# ==<>== Đọc target ĐỘNG từ số Non_Asthma train thực tế, thay vì hard-code
def get_dynamic_target():
    non_asthma_train = NON_ASTHMA_OUT / "train"
    if not non_asthma_train.exists():
        raise RuntimeError(
            "Chưa tìm thấy Dataset_Chia/Non_Asthma/train. "
            "Hãy chạy 2_Chia_Non_Asthma.py trước khi augment Asthma."
        )
    count = len(list(non_asthma_train.glob("*.wav")))
    print(f"[TARGET ĐỘNG] Số Non_Asthma Học thực tế: {count}")
    return count


def augment_train():
    target_train = get_dynamic_target()

    train = OUT / "train"
    originals = sorted(f for f in train.glob("*.wav")
                       if not f.name.startswith("Aug_"))
    aug_files = list(train.glob("Aug_*.wav"))
    start = len(aug_files)
    needed = target_train - len(originals) - start

    if needed <= 0:
        print(f"Đã đủ hoặc thừa so với target ({len(originals) + start} >= {target_train}), không augment thêm.")
        return

    mix_noises = list(NOISE.glob("postcard_*.wav")) + list(NOISE.glob("quat_phim_*.wav"))
    silences = list(NOISE.glob("im_lang_*.wav"))
    methods = ["mix", "shift", "white", "stretch", "pitch"]
    csv_path = OUT / "tang_cuong.csv"
    is_new_file = not csv_path.exists()

    with open(csv_path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if is_new_file:
            # ==<>== THÊM cột seed + tham số biến đổi để đúng yêu cầu tài liệu
            writer.writerow(["file_moi", "file_goc", "patient_id", "phuong_phap", "seed", "tham_so"])

        for i in range(start, start + needed):
            seed_i = SEED + i
            random.seed(seed_i)
            np.random.seed(seed_i)

            source = originals[i % len(originals)]
            method = methods[i % len(methods)]
            audio, _ = librosa.load(source, sr=SR)
            audio = librosa.util.fix_length(audio, size=SAMPLES)

            param_note = ""
            if method == "mix":
                noise_path = random.choice(mix_noises)
                noise, _ = librosa.load(noise_path, sr=SR)
                result = mix_with_noise(audio, noise)
                param_note = f"noise_file={noise_path.name}"
            elif method == "shift":
                silence_path = random.choice(silences)
                silence, _ = librosa.load(silence_path, sr=SR)
                silence = librosa.util.fix_length(silence, size=SAMPLES)
                result = time_shift_on_silence(audio, silence)
                param_note = f"silence_file={silence_path.name}"
            elif method == "white":
                result = add_white_noise(audio)
                param_note = "noise_level=0.001"
            elif method == "stretch":
                result = time_stretch(audio)
                param_note = "rate_range=0.8-1.2"
            else:
                result = pitch_shift(audio)
                param_note = "n_steps_range=-0.5..0.5"

            result = librosa.util.fix_length(result, size=SAMPLES)
            result = np.clip(result, -1.0, 1.0)

            new_name = f"Aug_{i:04d}_{method}_{source.stem}.wav"
            sf.write(train / new_name, result, SR)
            writer.writerow([new_name, source.name, get_patient(source), method, seed_i, param_note])


def main():
    split_data()
    augment_train()

    for part in ["train", "val", "test"]:
        total = len(list((OUT / part).glob("*.wav")))
        print(f"{part}: {total} file")


if __name__ == "__main__":
    main()
