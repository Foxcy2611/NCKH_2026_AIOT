"""
=========================================================
8. TRÍCH XUẤT MẪU ĐẶC TRƯNG
Lấy trực tiếp 2 file thuộc Asthma và Non-Asthma, đi qua 
tiền xử lý để lấy làm 2 mẫu test đầu vào bộ não TFLite
=========================================================
"""

import os
import librosa
import numpy as np
from scipy.signal import butter, lfilter


# 1. CẤU HÌNH INPUT/OUTPUT VÀ TẠO FOLDER
Audio_Asthma = "Dataset/0_Asthma/Orig_P55WheezingRS_272.wav" 
Audio_Non_Asthma = "Dataset/1_Non_Asthma/Kaggle_P2COPDMc_12.wav"
Dir_Output = "8_Exported_C_Headers" 

os.makedirs(Dir_Output, exist_ok=True) 

# 2. CÁC THAM SỐ VÀ BỘ LỌC TỪ BẢN TRAIN
Sr = 16000
Duration = 5.0
Samples = int(Sr * Duration) # 80000 mẫu

Low_Cut = 100.0
High_Cut = 2000.0
Order = 5
Pre_Coef = 0.97

N_Mels = 64
Hop_Length = 625 
N_FFT = 1024 

def Butter_Bandpass(lowcut, highcut, fs, order):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a

def Pre_Emphasis(signal, coef=0.97):
    return np.append(signal[0], signal[1:] - coef * signal[:-1])

def Apply_Bandpass_Filter(data, lowcut, highcut, fs, order):
    b, a = Butter_Bandpass(lowcut, highcut, fs, order)
    y = lfilter(b, a, data)
    return y

# 3. HÀM XỬ LÝ VÀ XUẤT FILE ĐA NĂNG
def Export_to_C(audio_path, output_filename, array_name, macro_name):
    print(f"\nĐang xử lý: {audio_path}")

    # --- BƯỚC 1: TIỀN XỬ LÝ ---
    y, _ = librosa.load(audio_path, sr=Sr)
    y_fixed = librosa.util.fix_length(y, size=Samples)

    # 1. Chuẩn hóa biên độ
    y_norm = librosa.util.normalize(y_fixed)

    # 2. Lọc Bandpass
    y_bandpass = Apply_Bandpass_Filter(y_norm, Low_Cut, High_Cut, Sr, Order)

    # 3. Lọc Pre-emphasis
    y_pre = Pre_Emphasis(y_bandpass, Pre_Coef)

    # 4. Mel-Spectrogram & Log-Scale
    mel_spec = librosa.feature.melspectrogram(
        y=y_pre, sr=Sr, n_fft=N_FFT, hop_length=Hop_Length, 
        n_mels=N_Mels, fmin=Low_Cut, fmax=High_Cut
    )
    mel_spec_dB = librosa.power_to_db(mel_spec, ref=np.max)

    print("-" * 50)
    print(f"   [BƯỚC 1] Ảnh phổ gốc (Float32, dB)")
    print(f"   + Kích thước ma trận 2D: {mel_spec_dB.shape}")
    print(f"   + Giá trị (Min - Max)  : {np.min(mel_spec_dB):.2f} đến {np.max(mel_spec_dB):.2f}")

    # --- BƯỚC 2: LƯỢNG TỬ HÓA VỀ INT8 ---
    db_min = np.min(mel_spec_dB)
    db_max = np.max(mel_spec_dB)
    mel_normalized = (mel_spec_dB - db_min) / (db_max - db_min)
    # Quy mức [0, 1] về int8 dạng [-128, 127]
    mel_int8 = np.clip((mel_normalized * 255.0) - 128.0, -128, 127).astype(np.int8)

    print("-" * 50)
    print(f"   [BƯỚC 2] Sau khi lượng tử hóa xuống Int8 (-128 đến 127)")
    print(f"   + Kích thước ma trận 2D: {mel_int8.shape}")
    print(f"   + Dữ liệu góc trên cùng: \n{mel_int8[:3, :3]}") 

    # --- BƯỚC 3: ĐÚC THÀNH C HEADER ---
    flattened_data = mel_int8.flatten()
    
    print("-" * 50)
    print(f"   [BƯỚC 3] Đập dẹp thành mảng 1D (Flatten)")
    print(f"   + Kích thước mảng 1D   : {flattened_data.shape}")
    print(f"   + Tổng số phần tử      : {len(flattened_data)}")
    
    formatted_rows = []
    for i in range(0, len(flattened_data), 12):
        chunk = flattened_data[i:i+12]
        formatted_rows.append("    " + ", ".join([f"{val:>4}" for val in chunk]))
    
    c_array = ",\n".join(formatted_rows)
    out_path = os.path.join(Dir_Output, output_filename)

    with open(out_path, "w") as f:
        f.write(f"// Nguon: {os.path.basename(audio_path)}\n")
        f.write(f"#ifndef {macro_name}\n#define {macro_name}\n\n")
        f.write(f"const int {array_name}_len = {len(flattened_data)};\n\n")
        f.write(f"const signed char {array_name}[] = {{\n{c_array}\n}};\n\n#endif\n")

    print("-" * 50)
    print(f"Xuất thành công: {output_filename} (Mảng: {array_name})\n")

def main():
    Export_to_C(Audio_Asthma, "Sample_Asthma_1.h", "sample_asthma_data", "SAMPLE_ASTHMA_1_H")
    Export_to_C(Audio_Non_Asthma, "Sample_Non_Asthma_1.h", "sample_non_asthma_data", "SAMPLE_NON_ASTHMA_1_H")
    
    print("==========================================")
    print("HOÀN TẤT TẠO 2 FILE C HEADER!")
    print("==========================================")

if __name__ == "__main__":
    main()