"""
===============================================================================
Tên script: Chon_Mau_Test_Phat_Loa.py

Tác dụng:
- Đọc đúng các WAV thuộc tập test của Asthma và Non_Asthma.
- Chỉ giữ các mẫu mà mô hình TFLite Python đã dự đoán đúng.
- Ưu tiên mẫu tương đối to và khác bệnh nhân khi có thể.
- Non_Asthma ưu tiên 3 Healthy, 3 COPD, 2 Pneumonia, 2 Bronchial.
- Nếu một nhóm không đủ mẫu vừa to vừa được Python đoán đúng, lấy nhóm khác bù
  để vẫn đủ 10 mẫu và ghi cảnh báo rõ ràng.
- Sao chép nguyên WAV vào hai thư mục Asthma và Non_Asthma ngay trong P5.

Lưu ý:
- Script không tăng âm, không chuẩn hóa và không sửa dữ liệu gốc.
- Có thể thay SO_MAU_MOI_NHAN nếu muốn lấy nhiều hoặc ít mẫu hơn.
===============================================================================
"""

import csv
import re
import shutil
import sys
import wave
from pathlib import Path

import numpy as np


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


SO_MAU_ASTHMA = 10
SO_MAU_NON_ASTHMA_TONG = 10
SO_MAU_NON_ASTHMA = {
    "Healthy": 3,
    "COPD": 3,
    "Pneumonia": 2,
    "Bronchial": 2,
}
RMS_TOI_THIEU_DBFS = -22.0

P5_DIR = Path(__file__).resolve().parent
AI_TRAINING_DIR = P5_DIR.parent
DATASET_CHIA_DIR = AI_TRAINING_DIR / "Dataset_Chia"
FILES_TEST_PATH = (
    AI_TRAINING_DIR
    / "P2_Preprocess_&_Traning_Model"
    / "Output_Preprocess"
    / "Files_test.npy"
)
REFERENCE_CSV_PATH = (
    AI_TRAINING_DIR
    / "P4_Kiem_Tra_CPP"
    / "Output_Test_113"
    / "Python_Reference_Test_113.csv"
)

OUTPUT_DIRS = {
    "Asthma": P5_DIR / "Asthma",
    "Non_Asthma": P5_DIR / "Non_Asthma",
}
REPORT_PATH = P5_DIR / "Danh_Sach_Mau_Phat_Loa.csv"


def doc_ket_qua_python():
    ket_qua = {}
    with REFERENCE_CSV_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            ket_qua[int(row["index"])] = row
    return ket_qua


def doc_wav_mono(path):
    with wave.open(str(path), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        frames = wav_file.getnframes()
        raw_audio = wav_file.readframes(frames)

    if sample_width == 1:
        audio = np.frombuffer(raw_audio, dtype=np.uint8).astype(np.float64)
        audio = (audio - 128.0) / 128.0
    elif sample_width == 2:
        audio = np.frombuffer(raw_audio, dtype="<i2").astype(np.float64)
        audio /= 32768.0
    elif sample_width == 4:
        audio = np.frombuffer(raw_audio, dtype="<i4").astype(np.float64)
        audio /= 2147483648.0
    else:
        raise ValueError(f"Không hỗ trợ WAV {sample_width * 8}-bit: {path}")

    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)

    return audio, sample_rate


def do_am_luong(path):
    audio, sample_rate = doc_wav_mono(path)
    if audio.size == 0:
        return -120.0, -120.0, sample_rate, 0.0

    rms = float(np.sqrt(np.mean(audio * audio)))
    peak = float(np.max(np.abs(audio)))
    rms_dbfs = 20.0 * np.log10(max(rms, 1e-12))
    peak_dbfs = 20.0 * np.log10(max(peak, 1e-12))
    duration = audio.size / sample_rate
    return rms_dbfs, peak_dbfs, sample_rate, duration


def lay_ma_benh_nhan(file_name):
    match = re.match(r"(P\d+)", file_name, flags=re.IGNORECASE)
    return match.group(1).upper() if match else file_name


def phan_nhom_non_asthma(file_name):
    name = file_name.lower()
    if "healthy" in name:
        return "Healthy"
    if "copd" in name:
        return "COPD"
    if "pneumonia" in name:
        return "Pneumonia"
    if "bronchial" in name:
        return "Bronchial"
    return "Khac"


def chon_mau_khac_benh_nhan(samples, so_luong):
    samples = sorted(
        samples,
        key=lambda item: (item["rms_dbfs"], item["peak_dbfs"]),
        reverse=True,
    )
    selected = []
    selected_indexes = set()
    used_patients = set()

    # Lượt đầu ưu tiên mỗi bệnh nhân một mẫu.
    for sample in samples:
        if sample["patient"] in used_patients:
            continue
        selected.append(sample)
        selected_indexes.add(sample["index"])
        used_patients.add(sample["patient"])
        if len(selected) >= so_luong:
            return selected

    # Nếu chưa đủ thì lấy tiếp các mẫu to còn lại.
    for sample in samples:
        if sample["index"] in selected_indexes:
            continue
        selected.append(sample)
        if len(selected) >= so_luong:
            break

    return selected


def tao_danh_sach_ung_vien():
    files_test = np.load(FILES_TEST_PATH, allow_pickle=True)
    ket_qua_python = doc_ket_qua_python()
    ung_vien = {"Asthma": [], "Non_Asthma": []}

    for index, relative_value in enumerate(files_test):
        relative_text = str(relative_value).replace("\\", "/")
        label = relative_text.split("/", 1)[0]
        if label not in ung_vien:
            continue

        reference = ket_qua_python.get(index)
        if reference is None or reference["correct"] != "1":
            continue

        source_path = DATASET_CHIA_DIR / Path(relative_text)
        if not source_path.exists():
            print(f"Bỏ qua vì không tìm thấy: {source_path}")
            continue

        rms_dbfs, peak_dbfs, sample_rate, duration = do_am_luong(source_path)
        if rms_dbfs < RMS_TOI_THIEU_DBFS:
            continue

        ung_vien[label].append(
            {
                "index": index,
                "label": label,
                "source": source_path,
                "rms_dbfs": rms_dbfs,
                "peak_dbfs": peak_dbfs,
                "sample_rate": sample_rate,
                "duration": duration,
                "patient": lay_ma_benh_nhan(source_path.name),
                "subgroup": (
                    "Asthma"
                    if label == "Asthma"
                    else phan_nhom_non_asthma(source_path.name)
                ),
                "python_probability_non_asthma": reference[
                    "python_probability_non_asthma"
                ],
            }
        )

    ung_vien["Asthma"] = chon_mau_khac_benh_nhan(
        ung_vien["Asthma"],
        SO_MAU_ASTHMA,
    )

    non_asthma_goc = ung_vien["Non_Asthma"]
    non_asthma_da_chon = []
    for subgroup, so_luong in SO_MAU_NON_ASTHMA.items():
        samples = [
            sample
            for sample in ung_vien["Non_Asthma"]
            if sample["subgroup"] == subgroup
        ]
        selected = chon_mau_khac_benh_nhan(samples, so_luong)
        if len(selected) < so_luong:
            print(
                f"Cảnh báo: nhóm {subgroup} chỉ chọn được "
                f"{len(selected)}/{so_luong} mẫu đạt yêu cầu"
            )
        non_asthma_da_chon.extend(selected)

    # Bộ test chỉ có một Bronchial vừa đủ to vừa được Python đoán đúng.
    # Ưu tiên Healthy để bù số lượng vì đây là đối chứng gần với demo người thật.
    if len(non_asthma_da_chon) < SO_MAU_NON_ASTHMA_TONG:
        selected_indexes = {sample["index"] for sample in non_asthma_da_chon}
        for fallback_group in ("Healthy", "Pneumonia", "COPD", "Bronchial"):
            extras = [
                sample
                for sample in non_asthma_goc
                if sample["subgroup"] == fallback_group
                and sample["index"] not in selected_indexes
            ]
            extras.sort(
                key=lambda item: (item["rms_dbfs"], item["peak_dbfs"]),
                reverse=True,
            )
            for sample in extras:
                non_asthma_da_chon.append(sample)
                selected_indexes.add(sample["index"])
                print(
                    f"Bù 1 mẫu {fallback_group}: {sample['source'].name}"
                )
                if len(non_asthma_da_chon) >= SO_MAU_NON_ASTHMA_TONG:
                    break
            if len(non_asthma_da_chon) >= SO_MAU_NON_ASTHMA_TONG:
                break

    ung_vien["Non_Asthma"] = non_asthma_da_chon

    return ung_vien


def xoa_wav_cu():
    for output_dir in OUTPUT_DIRS.values():
        output_dir.mkdir(parents=True, exist_ok=True)
        for old_wav in output_dir.glob("*.wav"):
            old_wav.unlink()


def sao_chep_va_ghi_bao_cao(ung_vien):
    xoa_wav_cu()
    rows = []

    for label, samples in ung_vien.items():
        print(f"\n{label}: chọn {len(samples)} mẫu")
        for sample in samples:
            destination = OUTPUT_DIRS[label] / sample["source"].name
            shutil.copy2(sample["source"], destination)
            print(
                f"- {destination.name}: RMS {sample['rms_dbfs']:.1f} dBFS, "
                f"peak {sample['peak_dbfs']:.1f} dBFS"
            )
            rows.append(
                {
                    "index_test": sample["index"],
                    "label": label,
                    "subgroup": sample["subgroup"],
                    "patient": sample["patient"],
                    "file_name": destination.name,
                    "rms_dbfs": f"{sample['rms_dbfs']:.3f}",
                    "peak_dbfs": f"{sample['peak_dbfs']:.3f}",
                    "sample_rate": sample["sample_rate"],
                    "duration_seconds": f"{sample['duration']:.3f}",
                    "python_probability_non_asthma": sample[
                        "python_probability_non_asthma"
                    ],
                    "source_path": str(sample["source"]),
                }
            )

    fieldnames = [
        "index_test",
        "label",
        "subgroup",
        "patient",
        "file_name",
        "rms_dbfs",
        "peak_dbfs",
        "sample_rate",
        "duration_seconds",
        "python_probability_non_asthma",
        "source_path",
    ]
    with REPORT_PATH.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    for required_path in (FILES_TEST_PATH, REFERENCE_CSV_PATH, DATASET_CHIA_DIR):
        if not required_path.exists():
            raise FileNotFoundError(f"Không tìm thấy: {required_path}")

    ung_vien = tao_danh_sach_ung_vien()
    sao_chep_va_ghi_bao_cao(ung_vien)
    print(f"\nĐã ghi báo cáo: {REPORT_PATH}")


if __name__ == "__main__":
    main()
