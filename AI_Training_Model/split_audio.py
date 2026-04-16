import os
import librosa
import soundfile as sf

FILE_GOC = "th3.wav"               
THU_MUC_LUU = "dataset/2_Background"   
TEN_TIEN_TO_1 = "quat_phim" 
TEN_TIEN_TO_2 = "im_lang" 
TEN_TIEN_TO_3 = "postcard"                

DO_DAI_GIAY = 5.0                        
SR = 16000                                

def bam_am_thanh():
    os.makedirs(THU_MUC_LUU, exist_ok=True)
    
    print(f"Đang load file gốc: {FILE_GOC} (Tần số {SR}Hz)...")

    y, sr = librosa.load(FILE_GOC, sr=SR)
    # => trả về mảng tín hiệu và tần số

    # 5 giây * 16000 = 80,000 data cho 1 file
    samples_per_chunk = int(DO_DAI_GIAY * SR) 
    
    # Tính tổng số file nhỏ sẽ thu được (// : Lấy phần nguyên)
    total_chunks = len(y) // samples_per_chunk
    
    print(f"Bắt đầu băm thành {total_chunks} file nhỏ...")
    
    for i in range(total_chunks):
        # Xác định điểm đầu và cuối của khúc âm thanh
        start = i * samples_per_chunk
        end = start + samples_per_chunk
        
        # Cắt lấy mảng dữ liệu (Slicing)
        chunk = y[start:end]
        
        # Đặt tên file:
        file_name = f"{TEN_TIEN_TO_3}_{i:03d}.wav"
        file_path = os.path.join(THU_MUC_LUU, file_name)
        
        # Thư viện Soundfile ra tay xuất mảng ra file .wav vật lý
        sf.write(file_path, chunk, SR)
        
    print("\n" + "="*45)
    print("ĐÃ BĂM XONG!")
    print(f"Kiểm tra kết quả tại: {THU_MUC_LUU}")
    print("="*45)

if __name__ == "__main__":
    try:
        bam_am_thanh()
    except FileNotFoundError:
        print(f" LỖI: Không tìm thấy file '{FILE_GOC}'")