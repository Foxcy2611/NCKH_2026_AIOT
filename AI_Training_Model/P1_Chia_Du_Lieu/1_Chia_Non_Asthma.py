"""
===============================================================================
Tên script: 1_Chia_Non_Asthma.py

Tác dụng:
- Đọc dữ liệu Non-Asthma gốc từ Kaggle và các file môi trường tự thu.
- Loại các bản sao trùng hoàn toàn bằng mã băm, rồi chia dữ liệu Kaggle theo
  nhóm bệnh + bệnh nhân thành train/val/test.
- Đưa toàn bộ phiên môi trường hiện có vào train để không làm rò rỉ các đoạn
  cùng phiên thu sang val/test.

Điểm tinh chỉnh so với model ban đầu:
- Chia file gốc theo bệnh nhân trước khi huấn luyện, không chia ngẫu nhiên từng
  file sau khi đã trộn dữ liệu.
- Giữ cố định SEED và lưu danh sách file trùng để có thể tái tạo kết quả.
===============================================================================
"""

import re
import csv
import os
import random
import shutil
import hashlib
from pathlib import Path


SEED = 42

RAW = Path(os.path.join("AI_Training_Model", "Dataset", "4_Raw_Non_Asthma"))
NOISE = Path(os.path.join("AI_Training_Model", "Dataset", "2_TuThu"))
OUT = Path(os.path.join("AI_Training_Model", "Dataset_Chia", "Non_Asthma"))

DISEASES = ["Bronchial", "COPD", "Healthy", "Pneumonia"]


def get_disease(file):
    for disease in DISEASES:
        if disease in file.name:
            return disease
    raise ValueError(f"Không nhận ra nhóm bệnh: {file.name}")


def get_group(file):
    patient = re.match(r"P\d+", file.name).group()
    return f"{get_disease(file)}_{patient}"


def remove_duplicates(files):
    """Giữ file đầu tiên, bỏ qua các bản sao giống hệt nội dung."""
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


def main():
    if OUT.exists():
        print(f"Đã tồn tại: {OUT}")
        print("Không chia lại để tránh trộn với kết quả cũ.")
        return

    files = sorted(RAW.glob("*.wav"))
    files, duplicates = remove_duplicates(files)

    # Gom file theo: nhóm bệnh + bệnh nhân
    groups = {}
    for file in files:
        groups.setdefault(get_group(file), []).append(file)

    random.seed(SEED)
    parts = {"train": [], "val": [], "test": []}

    # Chia riêng trong từng nhóm bệnh để tập nào cũng có đủ loại bệnh
    for disease in DISEASES:
        group_names = sorted(g for g in groups if g.startswith(disease + "_"))
        random.shuffle(group_names)

        n_train = round(len(group_names) * 0.8)
        n_val = (len(group_names) - n_train) // 2

        parts["train"] += group_names[:n_train]
        parts["val"] += group_names[n_train:n_train + n_val]
        parts["test"] += group_names[n_train + n_val:]

    rows = []

    # Chép các mẫu Kaggle vào đúng tập
    for part, group_names in parts.items():
        folder = OUT / part
        folder.mkdir(parents=True)

        for group_name in group_names:
            for file in groups[group_name]:
                shutil.copy2(file, folder / file.name)
                rows.append([
                    file.name, group_name, get_disease(file), part, "Kaggle"
                ])

    # 180 mẫu tự thu hiện tại chỉ đưa vào train
    for file in sorted(NOISE.glob("*.wav")):
        new_name = f"Noise_{file.name}"
        shutil.copy2(file, OUT / "train" / new_name)
        rows.append([new_name, "TuThu_HienTai", "Environment", "train", "TuThu"])

    with open(OUT / "chia_du_lieu.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["file_name", "group_id", "loai", "split", "nguon"])
        writer.writerows(rows)

    with open(OUT / "file_trung.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["file_bo_qua", "trung_voi_file"])
        writer.writerows(duplicates)

    print(f"Kaggle gốc: 820 file")
    print(f"Bỏ qua file trùng: {len(duplicates)} file")

    for part in ["train", "val", "test"]:
        total = len(list((OUT / part).glob("*.wav")))
        print(f"{part}: {total} file")


if __name__ == "__main__":
    main()
