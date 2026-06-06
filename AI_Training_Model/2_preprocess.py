import os
import librosa
import numpy as np

DATASET_PATH = "dataset"
LABEL = ["0_Asthma", "1_Others", "2_Background"] 
SR = 16000                                          # Sample Rate
DURATION = 4                                        # 4s
N_MFCC = 40                                         
N_FFT = 1024                                        
HOP_LENGTH = 256   
N_MELS = 40                                         # PHẢI LÀ 40 ĐỂ KHỚP C++
N_SAMPLES  = int(SR * DURATION)                     

def fix_length(y, target_length):
    if len(y) >= target_length:
        return y[:target_length]
    return np.pad(y, (0, target_length - len(y)), mode='constant')

def pre_emphasis(y, coef = 0.97):
    return np.append(y[0], y[1:] - coef * y[:-1])

# Sửa lại hàm: Chỉ nhận mảng y đã được tiền xử lý thô
def extract_features(y, sr):
    # 1. Trích xuất MFCC (Ép center=False để C++ không bị lệch)
    # Khớp fmin=80 với file C++
    mfcc = librosa.feature.mfcc(y=y, sr=sr,
                                n_mfcc=N_MFCC,
                                n_fft=N_FFT,
                                hop_length=HOP_LENGTH,
                                n_mels=N_MELS,
                                fmin=80, 
                                center=False)

    # 2. Tính Delta 1 và 2
    d1 = librosa.feature.delta(mfcc, order=1)
    d2 = librosa.feature.delta(mfcc, order=2)

    # 3. Gộp mảng theo thứ tự CHUẨN CỦA C++:
    # [120 số Mean (mfcc, d1, d2)] + [120 số Std (mfcc, d1, d2)] = 240 số
    
    mean_feat = []
    std_feat = []
    
    for mat in [mfcc, d1, d2]:
        mean_feat.append(np.mean(mat, axis=1))  # (40,)
        std_feat.append(np.std(mat, axis=1))    # (40,)
        
    # Nối tất cả Mean, rồi mới nối tất cả Std
    feat = mean_feat + std_feat 
    return np.concatenate(feat)   # Ra chuẩn (240,)

# ========================================================
features, label_list = [], []

print("Bắt đầu tiền xử lý (Phiên bản đồng bộ C++)...")

for label_idx, label_name in enumerate(LABEL):
    folder_path = os.path.join(DATASET_PATH, label_name)

    if not os.path.exists(folder_path):
        print(f"  Không tìm thấy: {folder_path}")
        continue

    wav_files = [f for f in os.listdir(folder_path) if f.endswith(".wav")]
    print(f"\n  [{label_name}] — {len(wav_files)} file")

    ok, skip = 0, 0
    for filename in wav_files:
        file_path = os.path.join(folder_path, filename)
        try:
            # 1. Đọc file
            y, sr = librosa.load(file_path, sr=SR, mono=True)

            # 2. Cắt/Ghép chuẩn 64000 mẫu
            y = fix_length(y, N_SAMPLES)

            # 3. Normalize (Về khoảng -1 đến 1)
            y = librosa.util.normalize(y)

            # 4. Pre-emphasis (Nhấn mạnh tần số cao)
            y = pre_emphasis(y)

            # 5. Rút trích đúng 240 đặc trưng
            feat = extract_features(y, SR)

            features.append(feat)
            label_list.append(label_idx)
            ok += 1

        except Exception as e:
            print(f"    Lỗi {filename}: {e}")
            skip += 1

    print(f"    Xử lý OK: {ok}  |  Bỏ qua: {skip}")

# ─── ĐÓNG GÓI & LƯU ─────────────────────────────────────────
X = np.array(features)   # (N, 240)
y = np.array(label_list) # (N,)

np.save("X_features.npy", X)
np.save("y_labels.npy",   y)

print("\n" + "="*45)
print("HOÀN THÀNH TIỀN XỬ LÝ ĐỒNG BỘ!")
print(f"  Tổng mẫu X      : {X.shape}")
print("="*45)