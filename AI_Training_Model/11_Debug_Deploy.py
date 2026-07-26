"""
=========================================================
11. KIỂM TRA ĐỊNH DẠNG INPUT ĐẦU VÀO
Vẫn quy trình tiền xử lý với 1 mẫu Asthma
Nhằm kiểm tra đúng định dạng input đầu vào của Model khi train
(Kiểu, định dạng, các thành phần mẫu có đúng theo công thức Mel ?)
=========================================================
"""

import librosa
import numpy as np
import seaborn as sns
import librosa.display
import matplotlib.pyplot as plt
from scipy.signal import butter, lfilter

# Nền darkgrid
sns.set_theme(style="darkgrid")

# Thông số cài đặt
Sr = 16000
Duration = 5.0
Samples = int(Sr * Duration) # 80.000 mẫu

# Thông số bộ lọc Butterworth + Pre-emphasis
Low_Cut = 100.0
High_Cut = 2000.0
Order = 5

Pre_Coef = 0.97

# Thông số trích xuất
N_Mels = 64
Hop_Length = 625 # 80000 / 625 = 128
N_FFT = 1024 


# Chỉ cần tạo 1 thư mục gốc

# === Hàm bộ lọc ===
# Butterworth
def Butter_Bandpass(lowcut, highcut, fs, order):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq

    b, a = butter(order, [low, high], btype='band')
    return b, a

# Pre-emphasis
def Pre_Emphasis(signal, coef=0.97):
    return np.append(signal[0], signal[1:] - coef * signal[:-1])

# Áp dụng bộ lọc butterworth
def Apply_Bandpass_Filter(data, lowcut, highcut, fs, order):
    b, a = Butter_Bandpass(lowcut, highcut, fs, order)
    y = lfilter(b, a, data)
    return y

# === Hàm xuất và lưu ảnh phổ ===
def Save_Spectrogram_Image(mel_dB, title, filename):
    plt.figure(figsize=(10, 4))

    # Màu magma
    librosa.display.specshow(
        mel_dB,
        x_axis='time',
        y_axis='mel',
        sr=Sr,
        fmin=Low_Cut,
        fmax=High_Cut,
        hop_length=Hop_Length,
        cmap='magma'
    )
    plt.colorbar(format='%+2.0f dB')
    plt.title(title, fontsize=14, fontweight="bold")
    plt.tight_layout()
    
    # Lưu thẳng ra Dir_Output thay vì thư mục con
    plt.close()

# === Xử lý trích xuất Mel-Spectrogram ===
def Process_Audio_File(file_path):
    try:
        # 1. Load file
        y, _ = librosa.load(file_path, sr=Sr)
        y = librosa.util.fix_length(y, size=Samples)

        # 2. Chuẩn hóa biên độ về [-1, 1]
        y_norm = librosa.util.normalize(y)

        # 3. Bộ lọc Butterworth Bandpass
        y_bandpass = Apply_Bandpass_Filter(y_norm, Low_Cut, High_Cut, Sr, Order)

        # 4. Bộ lọc Pre-emphasis
        y_pre = Pre_Emphasis(y_bandpass, Pre_Coef)

        # 5. STFT & Màng lọc Mel-Spectrogram
        mel_spec = librosa.feature.melspectrogram(
            y=y_pre,
            sr=Sr,
            n_fft=N_FFT,
            hop_length=Hop_Length,
            n_mels=N_Mels,
            fmin=Low_Cut,
            fmax=High_Cut
        )

        # 6. Chuyển sang thang đo Logarit
        # Lưu ý ở tham số ref=np.max
        mel_spec_dB = librosa.power_to_db(mel_spec, ref=np.max)

        return mel_spec_dB

    except Exception as e:
        print(f"Lỗi khi xử lý {file_path}: {e}")
        return None



mel_db = Process_Audio_File("Dataset/0_Asthma/Orig_P14WheezingIU_66.wav")
print("Shape:", mel_db.shape)
print("Frame 0, 10 mel dau (Python):", mel_db[:10, 0])
print("Frame 64, 10 mel dau (Python):", mel_db[:10, 64])