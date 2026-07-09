"""
=========================================================
4. Chuẩn hóa biên độ về [-1, 1] và đo đạc phổ Asthma
=> Để chốt lowcut highcut cho butterworth
=========================================================
"""
import librosa
import matplotlib.pyplot as plt
import numpy as np
import os

# CẤU HÌNH ĐƯỜNG DẪN 3 FILE TEST 
# Sử dụng 3 bộ test để so sánh kết quả
# Test 1
# FILE_NOISE    = "Dataset/2_TuThu/quat_phim_026.wav"
# FILE_ASTHMA   = "Dataset/3_asthma/P15WheezingRS_72.wav"
# FILE_RAW      = "Dataset/4_Raw_Non_Asthma/P1Healthy29S.wav"

# Test 2
# FILE_NOISE    = "Dataset/2_TuThu/postcard_014.wav"
# FILE_ASTHMA   = "Dataset/3_asthma/P3AsthmaIE_13.wav"
# FILE_RAW      = "Dataset/4_Raw_Non_Asthma/P1BronchialTc_1.wav"

# Test 3
FILE_NOISE    = "Dataset/2_TuThu/im_lang_013.wav"
FILE_ASTHMA   = "Dataset/3_asthma/P36WheezingRL_179.wav"
FILE_RAW      = "Dataset/4_Raw_Non_Asthma/P3COPDPr_21.wav"
 

# Hàm đọc file, chuẩn hóa, phân tích STFT 
# và vẽ Spectrum (Tần số vs Độ lớn)

def analyze_spectrum(file_path, ax, title, color_theme):
    print(f"🔍 Đang phân tích: {file_path}")
    
    # 1. Đọc file
    y, sr = librosa.load(file_path, sr=16000)

    # 2. Chuẩn hóa biên độ
    y_norm = librosa.util.normalize(y)

    # 3. Phân tích STFT để lấy độ lớn theo tần số
    D = np.abs(librosa.stft(y_norm))
    mean_freq = np.mean(D, axis=1) # Trung bình cộng năng lượng theo thời gian
    frequencies = librosa.fft_frequencies(sr=sr) # Lấy trục tần số làm trục x

    # VẼ BIỂU ĐỒ 
    # (Trục X: Tần số, Trục Y: Độ lớn)
    ax.plot(frequencies, mean_freq, color=color_theme, linewidth=1.5)
    ax.fill_between(frequencies, mean_freq, color=color_theme, alpha=0.3)
    
    ax.set_title(title, fontsize=12, fontweight='bold')
    
    # Giới hạn trục X từ 0 đến 4000Hz (khu vực bắt bệnh hô hấp)
    ax.set_xlim([0, 4000]) 
    
    # Kẻ các mốc chuẩn để soi tần số cắt (Butterworth cutoff)
    ax.axvline(x=50, color='gray', linestyle='--', label='50Hz')
    ax.axvline(x=150, color='orange', linestyle='--', label='150Hz')
    ax.axvline(x=1000, color='purple', linestyle='--', label='1000Hz')
    ax.axvline(x=2000, color='blue', linestyle='--', label='2000Hz')
    
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend(loc='upper right')

def main():
    # Tạo 3 khung tranh xếp dọc
    fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(12, 10))
    fig.suptitle('TÌM TẦN SỐ CẮT (LOWCUT / HIGHCUT)', fontsize=16, fontweight='bold')

    # Vẽ vào từng khung tranh
    analyze_spectrum(FILE_ASTHMA, axes[0], "1. ASTHMA (Có tiếng rít Wheezing)", 'red')
    analyze_spectrum(FILE_RAW, axes[1], "2. NON-ASTHMA (Bệnh khác Asthma)", 'green')
    analyze_spectrum(FILE_NOISE, axes[2], "3. NOISE (Tạp âm)", 'gray')

    # Chú thích rõ ràng trục X và Y ở biểu đồ dưới cùng
    axes[2].set_xlabel('TRỤC X: TẦN SỐ (Hz) --->', fontsize=12, fontweight='bold')
    axes[1].set_ylabel('TRỤC Y: ĐỘ LỚN NĂNG LƯỢNG', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()

"""
- Chốt hạ
+ Low cut: 100Hz
+ High cut: 2000
"""