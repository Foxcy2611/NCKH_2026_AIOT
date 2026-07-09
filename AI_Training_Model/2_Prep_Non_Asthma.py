"""
=========================================================
2. Chuẩn bị tập dữ liệu Non-Asthma 
=========================================================
"""

import os
import glob
import librosa
from soundfile import write

# ==== Tham số ===
Target_SR = 16000
Target_Duration = 5.0
# 80.000 mẫu
Target_Samples = int(Target_SR * Target_Duration)

# === Đường dẫn ===
Dir_Tu_Thu = "Dataset/2_TuThu"
Dir_Raw_Non_Asthma = "Dataset/4_Raw_Non_Asthma"

Dir_Out_Non_Asthma = "Dataset/1_Non_Asthma"

# === Tạo folder nếu chưa tồn tại ===
os.makedirs(Dir_Out_Non_Asthma, exist_ok=True)

# === Hàm xử lý âm thanh ===
def Process_and_Save_Audio(file_path, output_dir, prefix=""):
    try:
        # 1. Đọc và ép tần số các mẫu Folder_4 về 16 kHz
        audio_data, _ = librosa.load(file_path, sr=Target_SR)
        # 2. Cắt file dài hơn 5s hoặc thêm khoảng lặng (0) vào đủ độ dài
        audio_fixed = librosa.util.fix_length(audio_data, size=Target_Samples)

        # 3. Tạo lại tên file và lưu
        base_name = os.path.basename(file_path)
        new_name = f"{prefix}{base_name}"
        output_path = os.path.join(output_dir, new_name)

        # 4. Ghi file ra ổ cứng
        write(output_path, audio_fixed, Target_SR)
        return True
    
    except Exception as e:
        print(f"Lỗi khi xử lý file {file_path}: {e}")
        return False
    
def main():
    print("Chuẩn bị chuẩn hóa dữ liệu NON-ASTHMA ...")    

    succes_cnt = 0

    # 1. Quét Folder 4
    print(f"\nĐang quét thư mục: {Dir_Raw_Non_Asthma}")
    # Lấy 1 list chứa đường dẫn các file
    raw_files = glob.glob(os.path.join(Dir_Raw_Non_Asthma, "*.wav"))

    for file_path in raw_files:
        if Process_and_Save_Audio(file_path, Dir_Out_Non_Asthma, prefix="Kaggle_"):
            succes_cnt += 1
    
    # 2. Lấy các file Folder 2 
    print(f"\nĐang quét thư mục: {Dir_Tu_Thu}")
    tuthu_files = glob.glob(os.path.join(Dir_Tu_Thu, "*.wav"))

    for file_path in tuthu_files:
        if Process_and_Save_Audio(file_path, Dir_Out_Non_Asthma, prefix="Noise_"):
            succes_cnt += 1
    
    # 2. Tổng kết
    print("\n==========================================")
    print("ĐÃ HOÀN THÀNH!")
    print(f"Tổng số file đã xử lý và lưu vào 1_Non_Asthma: {succes_cnt} / {len(raw_files) + len(tuthu_files)}")
    print("==========================================")

if __name__ == "__main__":
    main()            
