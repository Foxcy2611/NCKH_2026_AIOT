"""
=========================================================
5. Trích xuất ra phổ Mel-Spectrogram (Bản gộp chung Folder)
Chuẩn hóa biên độ
Lọc nhiễu Butterworth + Pre-emphasis
Framing & Windowing
STFT
Mel-Scale
Not MFCC yeppp
=========================================================
"""

import os
import glob
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

# Link thư mục (Gộp chung output)
Dir_Asthma     = "Dataset/0_Asthma"
Dir_Non_Asthma = "Dataset/1_Non_Asthma"
Dir_Output     = "5_Output_Features"

# Chỉ cần tạo 1 thư mục gốc
os.makedirs(Dir_Output, exist_ok=True)

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
    plt.savefig(os.path.join(Dir_Output, filename), dpi=150)
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
        mel_spec_dB = librosa.power_to_db(mel_spec, ref=np.max)

        return mel_spec_dB

    except Exception as e:
        print(f"Lỗi khi xử lý {file_path}: {e}")
        return None
    
# Chương trình chính MAIN
def main():
    print("🚀 Bắt đầu trích xuất tranh phổ MEL-SPECTROGRAM...")

    X_data   = []
    Y_labels = []

    # Xử lý nhãn 0_ASTHMA
    Asthma_Files = glob.glob(os.path.join(Dir_Asthma, "*.wav"))
    print(f"\nĐang xử lý {len(Asthma_Files)} file Asthma (Nhãn 0)...")

    for idx, f in enumerate(Asthma_Files):
        features = Process_Audio_File(f)
        if features is not None:
            X_data.append(features)

            Y_labels.append(0) 
            
            # Chỉ lưu ảnh mẫu cho 3 file đầu tiên để đánh giá
            if idx < 3:
                base_name = os.path.basename(f).replace('.wav', '.png')
                Save_Spectrogram_Image(
                    features, 
                    f"Mel-Spectrogram ASTHMA: {base_name}",
                    f"Class0_{base_name}"
                )

        # Xem tiến độ
        if (idx + 1) % 100 == 0:
            print(f"  -> Đã xong {idx + 1} file...")

    # Xử lý nhãn 1_NON_ASTHMA
    Non_Asthma_Files = glob.glob(os.path.join(Dir_Non_Asthma, "*.wav"))
    print(f"\nĐang xử lý {len(Non_Asthma_Files)} file Non-Asthma (Nhãn 1)...")

    for idx, f in enumerate(Non_Asthma_Files):
        features = Process_Audio_File(f)

        if features is not None:
            X_data.append(features)
            Y_labels.append(1)

            # Chỉ lưu ảnh mẫu cho 3 file đầu tiên để đánh giá
            if idx < 3:
                base_name = os.path.basename(f).replace('.wav', '.png')
                Save_Spectrogram_Image(
                    features, 
                    f"Mel-Spectrogram NON-ASTHMA: {base_name}",
                    f"Class1_{base_name}"
                )

        # Xem tiến độ
        if (idx + 1) % 100 == 0:
            print(f"  -> Đã xong {idx + 1} file...")        

    X_data   = np.array(X_data)
    Y_labels = np.array(Y_labels)
    
    # Thêm chiều thứ tư là kênh màu (Tự động là 1)    
    X_data   = X_data[..., np.newaxis]

    print("\n==========================================")
    print(f"HOÀN THÀNH! Kích thước X_data: {X_data.shape}")
    print(f"Kích thước Y_labels: {Y_labels.shape}")
    
    # Lưu file .npy ra
    np.save(os.path.join(Dir_Output, "X_data_mel.npy"), X_data)
    np.save(os.path.join(Dir_Output, "Y_labels_mel.npy"), Y_labels)
    
    print(f"Ma trận và Ảnh phổ đã được lưu chung tại thư mục: {Dir_Output}")
    print("==========================================")

if __name__ == "__main__":
    main()

"""
Output ta có 2 file
+ X_data_mel: 1 mảng 4 chiều (đơn vị dB, các giá trị đều <= 0)
-> 2000 phần tử ứng vs số lượng file âm thanh
-> 64: Chiều cao của ảnh (Trục Y - 64 dải tần số Mel)
-> 129: Số pixel 1 ảnh (Trục X - Thời gian) 
Vì ngầm center=true ở melspec (tự động căn giữa ô thời gian nên cần độn thêm 0)
-> 1: Kênh màu

+ Y_labels_mel: mảng 1 chiều chứa đáp án cho từng mẫu
-> 0: Asthma
-> 1: Non-Asthma
"""