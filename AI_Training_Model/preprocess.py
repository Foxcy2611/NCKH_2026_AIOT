import os
import librosa
import numpy as np

DATASET_PATH = "dataset"
LABEL = ["0_Asthma", "1_Others", "2_Background"] 
SR = 16000                                          # Sample Rate
DURATION = 4                                        # 4s
N_MFCC = 40                                         # Số sample của 1 mẫu file
N_FFT = 1024                                        # Số data 1 file cắt
HOP_LENGTH = 256                                    # Bước nhảy

def fix_length(y, sr, duration):
    # Tính độ dài: 4 * 160000 = 64000 ptu
    target = int(sr * duration)
    # Nếu lớn hơn yêu cầu => Cắt phần đuôi
    if len(y) >= target:
        return y[:target]
    return np.pad(y, (0, target - len(y)), mode='constant')

def pre_emphasis(y, coef = 0.97):
    # Công thức bộ lọc thông cao bậc 1
    # y[0]: giữ tín hiệu nguyên mẫu ban đầu
    return np.append(y[0], y[1:] - coef * y[:-1])

def extract_features(y, sr):
    # Gọi hàm trích xuất, auto return về mảng 2 chiều
    mfcc = librosa.feature.mfcc(y = y, sr = sr, 
                                n_mfcc = N_MFCC, 
                                n_fft = N_FFT, 
                                hop_length = HOP_LENGTH)
    
    # Công thức đạo hàm theo thời gian
    delta1 = librosa.feature.delta(mfcc, order=1)
    delta2 = librosa.feature.delta(mfcc, order=2)

    feat = []

    for matrix in [mfcc, delta1, delta2]:
        feat.append(np.mean(matrix, axis=1))
        feat.append(np.std(matrix, axis=1))

    return np.concatenate(feat)

features, label_list = [], []

print("Bắt đầu tiền xử lý ...")

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

            # 2. Fix độ dài (QUAN TRỌNG — phải làm trước MFCC)
            y = fix_length(y, SR, DURATION)

            # 3. Chuẩn hóa biên độ
            y = librosa.util.normalize(y)

            # 4. Pre-emphasis (boost tần số cao)
            y = pre_emphasis(y)

            # 5. Trích đặc trưng MFCC + Delta + Std
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
print("HOÀN THÀNH!")
print(f"  Tổng mẫu      : {X.shape[0]}")
print(f"  Số đặc trưng  : {X.shape[1]}  (40 MFCC × mean+std × 3 lớp)")
print(f"  Phân phối nhãn: {np.bincount(y).tolist()}")
print("  Đã lưu: X_features.npy  |  y_labels.npy")
print("="*45)