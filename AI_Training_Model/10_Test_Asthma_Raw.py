"""
=========================================================
10. LẤY NGUYÊN LIỆU THÔ CỦA ASTHMA & NON-ASTHMA (BATCH MODE)
- Chuyển đổi hàng loạt 8 file .wav sang .h (int16_t array)
- 4 file Asthma và 4 file Non-Asthma (bao gồm COPD)
=========================================================
"""

import os
import librosa
import numpy as np

# --- 1. CẤU HÌNH ĐƯỜNG DẪN ---
Base_Dir = os.path.dirname(os.path.abspath(__file__))
Dataset_Asthma_Dir = os.path.join(Base_Dir, "Dataset", "0_Asthma")
Dataset_Non_Asthma_Dir = os.path.join(Base_Dir, "Dataset", "1_Non_Asthma")


Output_Dir_P1 = os.path.join(Base_Dir, "10_Input_Asthma_Raw", "Raw_Include_Phase_1")
Output_Dir_P2 = os.path.join(Base_Dir, "10_Input_Asthma_Raw", "Raw_Include_Phase_2")
Output_Dir_P3 = os.path.join(Base_Dir, "10_Input_Asthma_Raw", "Raw_Include_Phase_3")

if not os.path.exists(Output_Dir_P3):
    os.makedirs(Output_Dir_P3)
    print(f"[*] Đã tạo thư mục mới: {Output_Dir_P3}")

Target_Sr = 16000
Total_Samples = 80000 # 5 giây

# --- 2. DANH SÁCH FILE CẦN XỬ LÝ ---
# Định dạng: (Thư mục nguồn, Tên file wav, Tên file .h xuất ra, Tên mảng C++)
# Đây là tập dữ liệu vs Asthma level=0.005
# => Kết luận là lỏ
Audio_Files_1 = [
    # ---- 4 MẪU ASTHMA ----
    (Dataset_Asthma_Dir, "Orig_P14WheezingIU_66.wav", "Raw_Asthma_Audio_1.h", "raw_asthma_audio_1"),
    (Dataset_Asthma_Dir, "Orig_P42WheezingIE_209.wav",     "Raw_Asthma_Audio_2.h", "raw_asthma_audio_2"),
    (Dataset_Asthma_Dir, "Aug_WNoise_gen_0364.wav",     "Raw_Asthma_Audio_3.h", "raw_asthma_audio_3"),
    (Dataset_Asthma_Dir, "Aug_Sil_gen_0573.wav",     "Raw_Asthma_Audio_4.h", "raw_asthma_audio_4"),

    # ---- 4 MẪU NON-ASTHMA ----
    (Dataset_Non_Asthma_Dir, "Kaggle_P2COPDPr_15.wav", "Raw_Non_Asthma_Audio_1.h", "raw_non_asthma_audio_1"), # COPD 1 
    (Dataset_Non_Asthma_Dir, "Kaggle_P1COPDMc_6.wav",    "Raw_Non_Asthma_Audio_2.h", "raw_non_asthma_audio_2"), # COPD 2
    (Dataset_Non_Asthma_Dir, "Kaggle_P3BronchialTc_13.wav",  "Raw_Non_Asthma_Audio_3.h", "raw_non_asthma_audio_3"), # Bronchial
    (Dataset_Non_Asthma_Dir, "Noise_im_lang_000.wav",  "Raw_Non_Asthma_Audio_4.h", "raw_non_asthma_audio_4"), # Im lặng môi trường
]

# Đây là tập dữ liệu vs Asthma khi đã tinh giảm 1 số hệ số dùng để mix taapjj 
Audio_Files_2 = [
    # ---- 4 MẪU ASTHMA ----
    (Dataset_Asthma_Dir, "Aug_Fan_Key_gen_0033.wav", "Raw_Asthma_Audio_1.h", "raw_asthma_audio_1"),
    (Dataset_Asthma_Dir, "Orig_P18WheezingIE_89.wav",     "Raw_Asthma_Audio_2.h", "raw_asthma_audio_2"),
    (Dataset_Asthma_Dir, "Aug_WNoise_gen_0121.wav",     "Raw_Asthma_Audio_3.h", "raw_asthma_audio_3"),
    (Dataset_Asthma_Dir, "Aug_Sil_gen_0242.wav",     "Raw_Asthma_Audio_4.h", "raw_asthma_audio_4"),

    # ---- 4 MẪU NON-ASTHMA ----
    (Dataset_Non_Asthma_Dir, "Kaggle_P5COPDMc_40.wav", "Raw_Non_Asthma_Audio_1.h", "raw_non_asthma_audio_1"), # COPD
    (Dataset_Non_Asthma_Dir, "Noise_postcard_024.wav",    "Raw_Non_Asthma_Audio_2.h", "raw_non_asthma_audio_2"), # Tiếng podcast
    (Dataset_Non_Asthma_Dir, "Kaggle_P28Pneumonia56Y.wav",  "Raw_Non_Asthma_Audio_3.h", "raw_non_asthma_audio_3"), # Pneumonia
    (Dataset_Non_Asthma_Dir, "Noise_im_lang_013.wav",  "Raw_Non_Asthma_Audio_4.h", "raw_non_asthma_audio_4"), # Im lặng môi trường
]

Audio_Files_3 = [
    # ---- 7 MẪU ASTHMA ----
    (Dataset_Asthma_Dir, "Aug_Fan_Key_gen_0247.wav",   "Raw_Asthma_Audio_1.h", "raw_asthma_audio_1"), # Quạt + Phím + Asthma
    (Dataset_Asthma_Dir, "Aug_Pitch_gen_0611.wav",     "Raw_Asthma_Audio_2.h", "raw_asthma_audio_2"), # Tiếng đọc Podcast + Asthma
    (Dataset_Asthma_Dir, "Aug_Pod_gen_0609.wav",       "Raw_Asthma_Audio_3.h", "raw_asthma_audio_3"), # White Noise + Asthma
    (Dataset_Asthma_Dir, "Aug_Sil_gen_0017.wav",       "Raw_Asthma_Audio_4.h", "raw_asthma_audio_4"), # Pitch: Đổi cao độ nhịp thở gốc
    (Dataset_Asthma_Dir, "Aug_Stretch_gen_0647.wav",   "Raw_Asthma_Audio_5.h", "raw_asthma_audio_5"), # Kéo giãn hoặc nén time
    (Dataset_Asthma_Dir, "Aug_WNoise_gen_0149.wav",    "Raw_Asthma_Audio_6.h", "raw_asthma_audio_6"), # Dịch khung time 
    (Dataset_Asthma_Dir, "Orig_P42WheezingIU_210.wav", "Raw_Asthma_Audio_7.h", "raw_asthma_audio_7"), # Real từ Kaggle

    # ---- 7 MẪU NON-ASTHMA ----
    (Dataset_Non_Asthma_Dir, "Kaggle_P5BronchialTc_21.wav", "Raw_Non_Asthma_Audio_1.h", "raw_non_asthma_audio_1"), # Bronchial
    (Dataset_Non_Asthma_Dir, "Kaggle_P1COPDMc_8.wav",     "Raw_Non_Asthma_Audio_2.h", "raw_non_asthma_audio_2"), # COPD
    (Dataset_Non_Asthma_Dir, "Kaggle_P3Healthy57S.wav",     "Raw_Non_Asthma_Audio_3.h", "raw_non_asthma_audio_3"), # Healthy
    (Dataset_Non_Asthma_Dir, "Kaggle_P14Pneumonia87C.wav",   "Raw_Non_Asthma_Audio_4.h", "raw_non_asthma_audio_4"), # Pneumonia
    (Dataset_Non_Asthma_Dir, "Noise_im_lang_022.wav",        "Raw_Non_Asthma_Audio_5.h", "raw_non_asthma_audio_5"), # Im lặng
    (Dataset_Non_Asthma_Dir, "Noise_postcard_013.wav",       "Raw_Non_Asthma_Audio_6.h", "raw_non_asthma_audio_6"), # Podcast
    (Dataset_Non_Asthma_Dir, "Noise_quat_phim_011.wav",      "Raw_Non_Asthma_Audio_7.h", "raw_non_asthma_audio_7"), # Quạt/Phím
]

# --- 3. HÀM XỬ LÝ CHÍNH ---
def Convert_Wav_To_C_Array(input_path, output_path, array_name):
    print(f"\n[*] Đang xử lý: {os.path.basename(input_path)} ...")
    
    if not os.path.exists(input_path):
        print(f"    [!] LỖI: Không tìm thấy file. Vui lòng kiểm tra lại tên file!")
        return

    # Load audio
    y, _ = librosa.load(input_path, sr=Target_Sr, mono=True)

    # Cắt hoặc bù dữ liệu cho đủ 80.000 mẫu
    if len(y) > Total_Samples:
        y = y[:Total_Samples]
    else:
        y = np.pad(y, (0, Total_Samples - len(y)), 'constant')

    # Chuyển đổi sang int16
    y_int16 = np.int16(y * 32767)

    # Tự động tạo Macro Guard (VD: RAW_ASTHMA_AUDIO_1_H)
    macro_name = os.path.basename(output_path).replace('.', '_').upper()

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("/* File được tự động tạo bởi script Python (Batch Mode) */\n")
        f.write(f"#ifndef {macro_name}\n")
        f.write(f"#define {macro_name}\n\n")
        f.write("#include <stdint.h>\n\n")
        
        f.write(f"const int16_t {array_name}[{Total_Samples}] = {{\n    ")
        
        for i, val in enumerate(y_int16):
            f.write(f"{val}")
            if i < Total_Samples - 1:
                f.write(", ")
            if (i + 1) % 15 == 0: 
                f.write("\n    ")
                
        f.write("\n};\n\n")
        f.write(f"#endif // {macro_name}\n")
        
    print(f"    [+] Thành công! Đã lưu: {os.path.basename(output_path)}")

if __name__ == "__main__":
    print("=========================================================")
    print(" BẮT ĐẦU GENERATE 8 FILE RAW AUDIO CHO ESP32-S3")
    print("=========================================================")
    
    for folder, wav_name, h_name, arr_name in Audio_Files_3:
        input_wav = os.path.join(folder, wav_name)
        output_h = os.path.join(Output_Dir_P3, h_name)
        Convert_Wav_To_C_Array(input_wav, output_h, arr_name)
        
    print("\n[+] HOÀN TẤT TOÀN BỘ QUÁ TRÌNH!")