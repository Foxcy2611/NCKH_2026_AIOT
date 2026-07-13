#include "Mel_Scale.h"

// ==== arduinoFFT ====
static float vReal[N_FFT];
static float vImag[N_FFT];
static float mel_filterbank[N_MELS][N_FREQ_BINS];
ArduinoFFT<float> FFT(vReal, vImag, N_FFT, (float)SAMPLE_RATE);

// ==== HÀM CHUYỂN ĐỔI ĐƠN VỊ THANG MEL
float Hz_to_Mel(float hz){
    return 2595.0f * log10f(1.0f + hz / 700.0f);
}

float Mel_to_Hz(float mel){
    return 700.0f * (powf(10.0f, mel / 2595.0f) - 1.0f);
}

// ==== STFT vs CENTER PADDING ==== 
// Thêm N_FFT/2 mẫu 0 tại 2 đầu giúp cơ chế center=True 
// Để tâm cửa sổ trượt bắt đầu tại t = 0
void Get_Centered_Frame(const float* input, 
    int Input_length, 
    int frame_idx, 
    float* Out_frame
){
    // 1. Độ dài cần đệm
    int pad = N_FFT / 2;
    
    // 2. Tính tọa độ xuất phát của khung window
    int start_idx = (frame_idx * HOP_LENGTH) - pad;

    // 3 Quest 1024 mẫu
    for(int i = 0 ; i < N_FFT ; i++){
        // a. Tọa độ thực đang soi 
        int real_idx = start_idx + i;
        
        // Nếu ngoài vùng 0 hoặc N - 1 sẽ là 0
        if(real_idx < 0 || real_idx >= Input_length){
            Out_frame[i] = 0.0f;
        } else {
            Out_frame[i] = input[real_idx];
        }
    }
}

// ==== Xây dựng ma trận - 64 bộ lọc ====
// Mỗi bộ lọc tam giác là 1 hàng ma trận, quy định trọng số
// mỗi bin tần số FFT đóng góp và dải mel
// Sau khi tín hiệu đi qua STFT, thì nó đi qua 64 bộ lọc này
// để trở thành Mel-Spectrogram cuối cùng
void Init_Mel_Filterbank(void){
    float mel_max = Hz_to_Mel(F_MAX);
    float mel_min = Hz_to_Mel(F_MIN);

    // 1. Chia đều tần số từ min đến max
    // Vs 64 hình tam giác xếp chồng, thì cần tới 66 điểm 
    float mel_points[N_MELS + 2];
    for(int i = 0 ; i < N_MELS + 2 ; i++){
        mel_points[i] = mel_min + (mel_max - mel_min) * i / (N_MELS + 1);
    }

    // 2. Đưa mốc mel về giá trị tần số
    // Khi này khoảng các chúng không còn đều nữa
    int bin_points[N_MELS + 2];
    for(int i = 0 ; i < N_MELS + 2 ; i++){
        float hz = Mel_to_Hz(mel_points[i]);

        bin_points[i] = (int)floorf((N_FFT + 1) * hz / SAMPLE_RATE);
    }

    for(int m = 0 ; m < N_MELS ; m++){
        for(int f = 0 ; f < N_FREQ_BINS ; f++){
            mel_filterbank[m][f] = 0.0f;
        }
    }

    // 3. Dựng khuôn 64 cái phễu
    for(int m = 1 ; m <= N_MELS ; m++){
        int f_left   = bin_points[m - 1];
        int f_center = bin_points[m];
        int f_right  = bin_points[m + 1];

        // Xườn dốc trái: Cần gần trung tâm thì 0.0 -> 1.0
        for(int f = f_left ; f < f_center ; f++){
            if(f >= 0 && f < N_FREQ_BINS && f_center != f_left){
                mel_filterbank[m - 1][f] = 
                (float)(f - f_left) / (f_center - f_left);
            }
        }

        // Xườn dốc phải: Càng xa trung tâm thì 1.0 -> 0.0
        for(int f = f_center ; f < f_right ; f++){
            if(f >= 0 && f < N_FREQ_BINS && f_center != f_right){
                mel_filterbank[m - 1][f] = 
                (float)(f_right - f) / (f_right - f_center);
            }
        }
    }
}

// ===== Tính toán =====
// Nó sẽ bơm 80.000 mẫu âm thanh để vắt
int Compute_Mel_Power_Spectrogram(
    const float* input,
    int input_length,
    float mel_power_out[][N_MELS],
    int max_frames
){
    float frame_buf[N_FFT];
    float power_spectrum[N_FREQ_BINS];

    // 1. Xác định số frame
    int num_frames = (input_length / HOP_LENGTH) + 1; 
    if(num_frames > max_frames) num_frames = max_frames;

    // 2. Lặp qua 129 frame, lấy 1024 tín hiệu
    for(int frame_idx = 0 ; frame_idx < num_frames ; frame_idx++){
        // 2.1. Cơ chế center=True Padding 0
        Get_Centered_Frame(input, input_length, frame_idx, frame_buf);

        // Chuyển hàng vào khay FFT 
        // Bản chất FFT biến đổi tạo ra âm dương số phức
        // Nhưng tín hiệu thu là vậy lý thời gian thực, nên phần phức = 0
        for(int i = 0 ; i < N_FFT ; i++){
            vReal[i] = frame_buf[i];
            vImag[i] = 0.0f;
        }

        // 2.2. Hann Window + FFT
        FFT.windowing(FFTWindow::Hann, FFTDirection::Forward);
        FFT.compute(FFTDirection::Forward);

        // 2.3. Đo đạc năng lượng
        // FFT trả về âm dương số phức, tính module để lấy năng lượng
        for(int k = 0 ; k < N_FREQ_BINS ; k++){
            power_spectrum[k] = vReal[k] * vReal[k] + vImag[k] * vImag[k];

        }

        // 2.4. Áp Mel Filterbank - Lưu Input thô chưa chuyển qua dB
        for(int m = 0 ; m < N_MELS ; m++){
            float mel_enegry = 0.0f;
            for(int k = 0 ; k < N_FREQ_BINS ; k++){
                mel_enegry += power_spectrum[k] * mel_filterbank[m][k];
            }

            mel_power_out[frame_idx][m] = mel_enegry;
        }
    }

    return num_frames;

    /*
    Ta có: 64 dải Mels
    */
}

void Power_To_dB_RefMax(
    float mel_power[][N_MELS],
    float mel_db_out[][N_MELS],
    int num_frames
){
    const float epsilon = 1e-10f;

    // 1. Tìm đỉnh lớn nhất
    float max_power = epsilon;
    for(int f = 0 ; f < num_frames ; f++){
        for(int m = 0 ; m < N_MELS ; m++){
            if(mel_power[f][m] > max_power){
                max_power = mel_power[f][m];
            }
        }
    }

    // 2. Cơ chế hàm librosa power_to_db: dB = 10*log10(power/max_power)
    // Khi đó, quay về đơn vị dB, vs giá trị max là 0
    for(int f = 0 ; f < num_frames ; f++){
        for(int m = 0 ; m < N_MELS ; m++){
            float p = mel_power[f][m];
            
            if(p < epsilon) p = epsilon;
            
            mel_db_out[f][m] = 10.0f * log10f(p / max_power);
        }
    }
}