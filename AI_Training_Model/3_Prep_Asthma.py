import os
import glob
import random
import librosa
import numpy as np
from soundfile import write

# === Tham số ===
Target_Sr = 16000
Target_Duration = 5.0
# 80.000 mẫu
Target_Samples = int(Target_Sr * Target_Duration)
Target_Total_Files = 1000

# === Đường dẫn thư mục ===
Dir_Asthma_Raw = "Dataset/3_asthma"
Dir_Tu_Thu = "Dataset/2_TuThu"

Dir_Out_Asthma = "Dataset/0_Asthma"

os.makedirs(Dir_Out_Asthma, exist_ok=True)

# ===== List Def Mix Dataset =====
# === Mix asthma + noise có tỉ lệ SNR ===
# Tạp âm sẽ nhân vs hệ số 0.2 -> 0.7 => lúc vù vù, lúc be bé
def mix_with_noise(audio, noise_audio, min_gain=0.2, max_gain=0.7):
    coef = random.uniform(min_gain, max_gain)
    
    # Đảm bảo đủ độ dài 5s
    noise_audio = librosa.util.fix_length(noise_audio, size=Target_Samples)
    # Mix
    mixed_audio = audio + (noise_audio * coef)

    return mixed_audio

# === Cut thời gian hen và di chuyển ===
# Sử dụng thuật toán VAD, quét khoảng nào có năng lượng to nhất (asthma)
# Lấy nó làm vị trí trung tâm, di chuyển nó sang các vị trí khác trong file
def time_shift_on_silence(audio, silence_audio):
    # 1. Tính năng lượng tìm WHEEZING
    # Lấy phần lõi Asthma chèn ngẫu nhiên trên file im lặng
    silence_fixed = librosa.util.fix_length(silence_audio, size=Target_Samples)
    
    # Dùng RMS đo năng lượng
    rms_energy = librosa.feature.rms(y=audio)[0]

    # Xác định khung có năng lượng max
    max_energy_frame = np.argmax(rms_energy)

    # Quy đổi sang chỉ số mẫu
    center_idx = librosa.frames_to_samples(max_energy_frame)

    # 2. Cắt lõi lấy 2.5s
    # Cắt 2.5s từ vị trí trung tâm file asthma
    core_length = int(2.5 * Target_Sr) # 40000 mẫu
    haft_core = core_length // 2 # Dùng tâm đối xứng để cắt

    # Tính điểm đầu và kết thúc cắt
    start_cut = max(0, center_idx - haft_core)
    end_cut   = min(len(audio), center_idx + haft_core) 

    # 2.5s đặc trưng
    core_audio = audio[start_cut:end_cut]

    # Nếu ngắn hơn 2.5s thì thêm lặng
    core_audio = librosa.util.fix_length(core_audio, size=core_length)

    # 3. Chèn vào file im lặng
    # Chọn ngẫu nhiên 1 khoảng
    insert_idx = random.randint(0, Target_Samples - core_length)

    # Tạo bản sao file im lặng để cộng dồn
    shifted_audio = np.copy(silence_audio)
    shifted_audio[insert_idx : insert_idx + core_length] += core_audio 

    return shifted_audio   

# === Thêm nhiễu trắng ===
# White Gaussian Noise từ randn
# Mô phỏng chút tạp âm từ phần cứng khi thu từ INMP441
def add_white_noise(audio, noise_level=0.005):
    noise = np.random.randn(len(audio))
    agumented_audio = audio + noise_level * noise
    
    return agumented_audio

# === Co giãn thời gian ===
# Lúc thì tiếng WHEEZING nhanh, chậm tương ứng phổi con người
# Không làm thay đổi biên độ
def time_stretch(audio):
    # 0.8: chậm lại ; 1.2: nhanh hơn
    rate = random.uniform(0.8, 1.2)
    stretched = librosa.effects.time_stretch(y=audio, rate=rate)
    # fix độ dài về 5s
    stretched_fix = librosa.util.fix_length(stretched, size=Target_Samples)

    return stretched_fix

# === Dịch dải tần số ===
# Kéo toàn bộ dải âm thanh lên cao/xuống khoảng bé +- 1.5 semitones
# Giả lập phổi người lớn vs trẻ nhỏ về kích thước thanh quản và ống thở
def pitch_shift(audio):
    n_steps = random.uniform(-1.5, 1.5)
    shifted = librosa.effects.pitch_shift(y=audio, sr=Target_Sr, n_steps=n_steps)

    # fix độ dài
    shifted_fix = librosa.util.fix_length(shifted, size=Target_Samples)

    return shifted_fix

# === MAIN ===
def main():
    print("Bắt đầu chuẩn hóa và HACK dữ liệu Asthma")

    # 1. Đọc list file gốc, trả về list link file wav
    raw_asthma_files = glob.glob(os.path.join(Dir_Asthma_Raw, "*.wav"))
    noise_files      = glob.glob(os.path.join(Dir_Tu_Thu, "*.wav"))
    # 2. Phân loại 3 tạp âm tự thu
    silence_files = []
    podcast_files = []
    fan_key_files = []

    for f in noise_files:
        name = os.path.basename(f).lower()

        if "im_lang" in name:
            silence_files.append(f)
        elif "postcard" in name:
            podcast_files.append(f)
        elif "quat_phim" in name:
            fan_key_files.append(f)

    # Dict lưu file gốc 
    processed_orig = []

    ## B1: Lưu sẵn 288 file asthma vào folder
    print(f"\n[1/2] Đang xử lý {len(raw_asthma_files)} file Asthma gốc...")
    for filepath in raw_asthma_files:
        audio, _ = librosa.load(filepath, sr=Target_Sr)
        audio_fixed = librosa.util.fix_length(audio, size=Target_Samples)

        # Lưu vào Dict
        processed_orig.append(audio_fixed)

        # Lưu file chuẩn
        base_name = os.path.basename(filepath)
        out_path = os.path.join(Dir_Out_Asthma, f"Orig_{base_name}")
        write(out_path, audio_fixed, Target_Sr)

    ## B2: Sinh data ảo đủ 1000 mẫu
    curr_cnt = len(processed_orig)
    needed_cnt = Target_Total_Files - curr_cnt

    print(f"\n[2/2] Đang sinh thêm {needed_cnt} mẫu ảo (Augmentation)...")

    aug_method_label = [
        'podcast',
        'fan_key',
        'silence',
        'white_noise',
        'time_stretch',
        'pitch_shift'   
    ]

    for i in range(needed_cnt):
        # Chọn ngẫu nhiên 1 file
        base_audio = random.choice(processed_orig)

        # Chọn ngẫu nhiên 1 Phương Pháp
        method = random.choice(aug_method_label)

        try:
            if method == 'podcast' and podcast_files:
                noise_path = random.choice(podcast_files)
                noise_audio, _ = librosa.load(noise_path, sr=Target_Sr)
                final_audio = mix_with_noise(base_audio, noise_audio, min_gain=0.2, max_gain=0.6)
                prefix = "Aug_Pod_"
                
            elif method == 'fan_key' and fan_key_files:
                noise_path = random.choice(fan_key_files)
                noise_audio, _ = librosa.load(noise_path, sr=Target_Sr)
                final_audio = mix_with_noise(base_audio, noise_audio, min_gain=0.3, max_gain=0.7)
                prefix = "Aug_Fan_Key_"
                
            elif method == 'silence' and silence_files:
                noise_path = random.choice(silence_files)
                noise_audio, _ = librosa.load(noise_path, sr=Target_Sr)
                final_audio = time_shift_on_silence(base_audio, noise_audio)
                prefix = "Aug_Sil_"
                
            elif method == 'white_noise':
                final_audio = add_white_noise(base_audio)
                prefix = "Aug_WNoise_"
                
            elif method == 'time_stretch':
                final_audio = time_stretch(base_audio)
                prefix = "Aug_Stretch_"
                
            elif method == 'pitch_shift':
                final_audio = pitch_shift(base_audio)
                prefix = "Aug_Pitch_"
                
            # Đảm bảo chắc chắn lần cuối là đúng 5 giây
            final_audio = librosa.util.fix_length(final_audio, size=Target_Samples)
            
            # Ghi file
            out_path = os.path.join(Dir_Out_Asthma, f"{prefix}gen_{i:04d}.wav")
            write(out_path, final_audio, Target_Sr)
            
        except Exception as e:
            print(f"Lỗi ở mẫu {i} (phương pháp {method}): {e}")

    final_files = len(glob.glob(os.path.join(Dir_Out_Asthma, "*.wav")))
    print("\n==========================================")
    print("ĐÃ HOÀN THÀNH!")
    print(f"Tổng số file hiện có trong 0_Asthma: {final_files} / 1000")
    print("==========================================")

if __name__ == "__main__":
    main()