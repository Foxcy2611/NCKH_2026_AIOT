#include "DSP_Preprocessing/Mel_Scale.h"

// ==== arduinoFFT ====
static float vReal[N_FFT];
static float vImag[N_FFT];
static float mel_filterbank[N_MELS][N_FREQ_BINS];
ArduinoFFT<float> FFT(vReal, vImag, N_FFT, (float)SAMPLE_RATE);

// ==== HÀM CHUYỂN ĐỔI ĐƠN VỊ THANG MEL
// Dựa trên sự mặc định hàm mel spectrogram với Salney (htk=False): (Wikipedia)
// m(f) = 3f/200 vs f < 1000 ; = 15 + 27.log_6.4(f/1000) vs f >= 1000
// Tùy theo cách chọn theo htk hay salney mà cách ta xây dựng Mel Filterbank khác nhau
// Nhưng suy cho cùng đều chung 1 mục đích: 
// + Mô phỏng cơ chế tai người
// + Gom nhóm và nén phổ tần số gốc (STFT)
// + Giữ đặc trưng âm quan trọng
float Hz_to_Mel(float hz){
    const float f_sp = 200.0f / 3.0f;           // 66.667
    const float min_log_hz = 1000.0f;
    const float min_log_mel = min_log_hz / f_sp; // = 15.0
    // logf() = ln()
    // log_a(B) = ln(B) / ln(a)
    const float logstep = logf(6.4f) / 27.0f; 

    if (hz < min_log_hz) {
        // m(f) = 3f/200
        return hz / f_sp; // f / (200/3) = 3f/200
    } else {
        // m(f) =  15      +  ln(hz / 1000) / (ln(6.4) / 27)
        return min_log_mel + logf(hz / min_log_hz) / logstep;
    }
}

float Mel_to_Hz(float mel){
    const float f_sp = 200.0f / 3.0f;
    const float min_log_hz = 1000.0f;
    const float min_log_mel = min_log_hz / f_sp;
    const float logstep = logf(6.4f) / 27.0f;

    if (mel < min_log_mel) {
        return mel * f_sp;
    } else {
        return min_log_hz * expf(logstep * (mel - min_log_mel));
    }
}


// ==== STFT vs CENTER PADDING ==== 
// Tác dụng: Thêm N_FFT/2 mẫu 0 tại 2 đầu theo cơ chế center=True 
// Để tâm cửa sổ trượt bắt đầu tại t = 0
void Get_Centered_Frame(
    const float* input, 
    int Input_length, 
    int frame_idx, 
    float* Out_frame
){
    // 1. Độ dài cần đệm
    int pad = N_FFT / 2;
    
    // 2. Tính tọa độ xuất phát của khung window
    int start_idx = (frame_idx * HOP_LENGTH) - pad;

    // 3. Quét 1024 mẫu
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
// 1. Hàm khởi tạo (Setup): Tính toán và tạo sẵn ma trận trọng số 64 hàng x 513 cột
// (Tất cả được chuẩn hóa Slaney-Norm - Nói cách khác là dựng 64 tam giác FFT)
// 2. Mỗi bộ lọc tam giác là 1 hàng ma trận, quy định trọng số, mỗi bin tần số FFT đóng góp và dải mel
// Âm thanh được cắt thành từng khung ngắn, đi qua FFT tạo ra hàng trăm giá trị f chi tiết
// 3. Lấy các trăm giá trị đó đi qua ma trận 64 hàng để trở thành Mel-Spectrogram cuối cùng
void Init_Mel_Filterbank(void){
    // 1. Đổi tần số cao nhất và thấp nhất sang Mel
    float mel_max = Hz_to_Mel(F_MAX);
    float mel_min = Hz_to_Mel(F_MIN);

    // 2. Để vẽ đc 64 tam giác (3 đỉnh) thì cần thêm 2 điểm cho bắt đầu và kết thúc
    float mel_points[N_MELS + 2]; // Các điểm đều nhau 
    // Vòng lặp chia khoảng cách min-max thành 66 điểm bằng nhau
    for(int i = 0 ; i < N_MELS + 2 ; i++){
        mel_points[i] = mel_min + (mel_max - mel_min) * i / (N_MELS + 1);
    }
    // 3. Định vị các đỉnh tam giác
    int bin_points[N_MELS + 2]; // Dựa vào giá trị Mel->Tần số mà xem nó thuộc ô (bin) nào của FFT
    float hz_points[N_MELS + 2]; // Dựa 66 điểm cách nhau trên thang Mel, quy về Hz 
    for(int i = 0 ; i < N_MELS + 2 ; i++){
        float hz = Mel_to_Hz(mel_points[i]);
        hz_points[i] = hz; 
        bin_points[i] = (int)floorf((N_FFT + 1) * hz / SAMPLE_RATE); // công thức xác định bin
    }
        // 64 hàng (mel) x 513 cột (f)
    for(int m = 0 ; m < N_MELS ; m++){
        for(int f = 0 ; f < N_FREQ_BINS ; f++){
            mel_filterbank[m][f] = 0.0f;
        }
    }

    // 4. Vẽ sườn tam giác
    // + Trái: Tăng dần từ 0->1
    // + Phải: Giảm dần từ 1->0
    // Lấy tỉ lệ khoảng cách để tạo ra 0->1 hay 1->0
    for(int m = 1 ; m <= N_MELS ; m++){
        int f_left   = bin_points[m - 1];
        int f_center = bin_points[m];
        int f_right  = bin_points[m + 1];

        for(int f = f_left ; f < f_center ; f++){
            if(f >= 0 && f < N_FREQ_BINS && f_center != f_left){
                mel_filterbank[m - 1][f] = 
                (float)(f - f_left) / (f_center - f_left);
            }
        }
        for(int f = f_center ; f < f_right ; f++){
            if(f >= 0 && f < N_FREQ_BINS && f_center != f_right){
                mel_filterbank[m - 1][f] = 
                (float)(f_right - f) / (f_right - f_center);
            }
        }

        // 5. Slaney-norm — chuẩn hóa theo diện tích (khớp librosa norm='slaney' mặc định) ====
        /* 
        - Bản chất thang đo Mel có mật độ dày đặc ở tần số thấp và thưa thớt tần số cao
        => Các tam giác sẽ có diện tích khác nhau rất nhiều (Vì khác đáy, cùng chiều cao = 1)
        - Nếu đỉnh mọi tam giác đều bằng 1 (chiều cao = 1), thì tam giác rộng ở tần số cao sẽ gom nhiều năng lượng âm thanh
        => Mạng neuron sẽ bị mù, cần chuẩn hóa theo diện tích (norm)

        => Slaney-norm: Bắt diện tích mọi tam giác (dù rộng hay hẹp) = 1
        S_all_tam_giac = 1 (Diện tích ở đây đc coi là tổng sức mạnh gom năng lượng)
        
        - Theo diện tích tam giác: S = 0.5 . a . h (a-đáy ; h-chiều cao)
        + a: ứng với độ rộng dải tần: hz_points[m + 1] - hz_points[m - 1]
        + S = 1 => h = 2/a
        */
        float enorm = 2.0f / (hz_points[m + 1] - hz_points[m - 1]);
        for(int f = 0 ; f < N_FREQ_BINS ; f++){
            mel_filterbank[m - 1][f] *= enorm;
        }
    }
}

// ===== Tính toán =====
// Nó sẽ bơm 80.000 mẫu âm thanh để vắt ra bức ảnh 2D cuối cùng
int Compute_Mel_Power_Spectrogram(
    const float* input,
    int input_length,
    float mel_power_out[][MAX_FRAMES],
    int max_frames
){
    static float frame_buf[N_FFT];
    static float power_spectrum[N_FREQ_BINS];

    // 1. Xác định số frame
    int num_frames = (input_length / HOP_LENGTH) + 1; // 80.000 / 625 + 1 = 129
    if(num_frames > max_frames) num_frames = max_frames;

    // 2. Lặp qua 129 frame, lấy 1024 tín hiệu
    for(int frame_idx = 0 ; frame_idx < num_frames ; frame_idx++){
        // 2.1. Cơ chế center=True Padding 0
        Get_Centered_Frame(input, input_length, frame_idx, frame_buf);

        // Chuyển hàng vào khay FFT 
        // Bản chất FFT biến đổi vs input và output là số âm dương phức (a + bi)
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
        // FFT thu đc hàng trăm, đi qua filterbank để thu Mel-Spectrogram
        for(int m = 0 ; m < N_MELS ; m++){
            float mel_enegry = 0.0f;
            for(int k = 0 ; k < N_FREQ_BINS ; k++){
                mel_enegry += power_spectrum[k] * mel_filterbank[m][k];
            }

            mel_power_out[m][frame_idx] = mel_enegry;
        }
    }

    return num_frames;
}

// ===== Log-Mel Scaling vs hệ quy chiếu ref_max =====
// Chuyển đổi sang đơn vị dB vs ref_max: Giá trị năng lượng dB max = 0 
// Năng lượng âm thanh thay đổi theo cấp số nhân, nên nhét vào mạng neuron sẽ nổ

void Power_To_dB_RefMax(
    float mel_power[][MAX_FRAMES],
    float mel_db_out[][MAX_FRAMES],
    int num_frames
){
    Serial.println("[DEBUG] Dang chay ban co TOP_DB CLIP - v2"); 
    const float epsilon = 1e-10f; // Chặn trường hợp P = 0 vì ko có log10(0)
    const float top_db = 80.0f; // thêm mặc định của power to db

    // 1. Tìm đỉnh lớn nhất
    float max_power = epsilon;
    for(int m = 0 ; m < N_MELS ; m++){
        for(int f = 0 ; f < num_frames ; f++){
            if(mel_power[m][f] > max_power){
                max_power = mel_power[m][f];
            }
        }
    }

    // 2. Cơ chế hàm librosa power_to_db: 
    // dB = 10*log10(power/max_power) - Công thức chuyển đổi năng lượng sang dB (Google)
    // Khi đó, quay về đơn vị dB, vs giá trị max là 0
    // Tính db thô
    float max_db = -INFINITY;
    for(int m = 0 ; m < N_MELS ; m++){
        for(int f = 0 ; f < num_frames ; f++){
            float p = mel_power[m][f];
            
            if(p < epsilon) p = epsilon; // Khi p = ep ; log10(1) = log10(0...1) = 0
            
            float db = 10.0f * log10f(p / max_power);
            mel_db_out[m][f] = db;

            if(db > max_db) max_db = db;
        }
    }

    // 3. Không cho giá trị nào thấp hơn (Phòng trừ nhiễu do môi trường)
    // Khi đó năng lượng sẽ rất thấp (Vdu: -150), cần phòng trừ
    float floor_db = max_db - top_db; // = -80
    for(int m = 0 ; m < N_MELS ; m++){
        for(int f = 0 ; f < num_frames ; f++){
            if(mel_db_out[m][f] < floor_db){
                mel_db_out[m][f] = floor_db;
            }
        }
    }
    /*
    Đây là output cuối cùng để làm input Interface
    Gồm 129 x 64 = 8256 phần tử
    */
}