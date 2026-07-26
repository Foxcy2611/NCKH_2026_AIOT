# 🎵 Mel_Scale — Cơ chế trích xuất Mel-Spectrogram

Thư viện này thực hiện lại (re-implement) chính xác quy trình `librosa.feature.melspectrogram()` bằng C++, để đảm bảo kết quả khớp với dữ liệu đã dùng lúc train model bằng Python.

## Tương ứng hàm Python ↔ C++

| Python (librosa) | C++ | Vai trò |
|---|---|---|
| `librosa.hz_to_mel()` (nội bộ) | `Hz_to_Mel()` | Đổi Hz sang thang Mel |
| `librosa.mel_to_hz()` (nội bộ) | `Mel_to_Hz()` | Đổi Mel sang Hz |
| `librosa.filters.mel()` | `Init_Mel_Filterbank()` | Dựng ma trận 64 bộ lọc tam giác |
| `librosa.stft()` (bên trong `melspectrogram`) | `Get_Centered_Frame()` + phần FFT trong `Compute_Mel_Power_Spectrogram()` | Biến đổi Fourier theo từng khung thời gian |
| `librosa.feature.melspectrogram()` | `Compute_Mel_Power_Spectrogram()` | Toàn bộ pipeline STFT → áp Mel filterbank |
| `librosa.power_to_db(ref=np.max)` | `Power_To_dB_RefMax()` | Chuyển năng lượng sang thang dB |

---

## 1️⃣ `Hz_to_Mel()` / `Mel_to_Hz()` — Công thức Slaney 📐

⚠️ **Quan trọng:** `librosa.feature.melspectrogram()` mặc định dùng `htk=False`, nghĩa là dùng **thang Slaney**, KHÔNG PHẢI thang HTK (`2595*log10(1+f/700)`). Đây là điểm dễ nhầm lẫn nhất khi tự viết lại bằng tay.

Công thức Slaney có 2 đoạn:
- **Tuyến tính** với `f < 1000 Hz`: `mel = f / f_sp`, với `f_sp = 200/3 ≈ 66.667`
- **Logarit** với `f >= 1000 Hz`: `mel = min_log_mel + ln(f/1000) / logstep`, với `logstep = ln(6.4)/27`

```cpp
float Hz_to_Mel(float hz){
    const float f_sp = 200.0f / 3.0f;
    const float min_log_hz = 1000.0f;
    const float min_log_mel = min_log_hz / f_sp;      // = 15.0
    const float logstep = logf(6.4f) / 27.0f;

    if (hz < min_log_hz) return hz / f_sp;             // đoạn tuyến tính
    return min_log_mel + logf(hz / min_log_hz) / logstep;  // đoạn logarit
}
```

`Mel_to_Hz()` là hàm nghịch đảo, dùng `expf()` thay cho `logf()` ở nhánh logarit.

💡 **Tại sao quan trọng:** dải tần quan tâm của dự án (`100–2000 Hz`) nằm ngay quanh điểm gãy `1000 Hz` — nếu dùng nhầm công thức HTK, vị trí các tam giác Mel sẽ lệch đáng kể, khiến model nhận input sai lệch dù DSP các bước khác đều đúng.

---

## 2️⃣ `Get_Centered_Frame()` — Mô phỏng `center=True` 🎯

`librosa.stft()` mặc định `center=True`: trước khi cắt frame, tín hiệu được **đệm thêm `N_FFT/2` mẫu 0 vào cả 2 đầu**, giúp frame đầu tiên "căn giữa" đúng tại mốc thời gian t=0.

```cpp
void Get_Centered_Frame(const float* input, int Input_length, int frame_idx, float* Out_frame){
    int pad = N_FFT / 2;
    int start_idx = (frame_idx * HOP_LENGTH) - pad;   
    // offset ảo, có thể âm

    for(int i = 0; i < N_FFT; i++){
        int real_idx = start_idx + i;
        // Nằm ngoài dữ liệu thật -> coi như 0 (vùng pad)
        Out_frame[i] = (real_idx < 0 || real_idx >= Input_length) ? 0.0f : input[real_idx];
    }
}
```

Đây là lý do với `80000` mẫu và `HOP_LENGTH=625`, số frame thực tế là `129` (không phải `128 = 80000/625`) — có thêm 1 frame do padding.

---

## 3️⃣ `Init_Mel_Filterbank()` — Dựng 64 bộ lọc tam giác + Slaney-norm 🔺

**Bước 1️⃣ — chia đều 66 điểm theo thang Mel** (64 tam giác chồng lấn cần 66 điểm biên: trái, đỉnh, phải mỗi cặp tam giác kề nhau dùng chung điểm).

**Bước 2️⃣ — quy đổi các điểm Mel về lại Hz và chỉ số bin FFT:**
```cpp
bin_points[i] = (int)floorf((N_FFT + 1) * hz / SAMPLE_RATE);
```

**Bước 3️⃣ — dựng tam giác 0→1→0** cho mỗi dải Mel:
```cpp
// Sườn trái: tăng dần 0 -> 1
mel_filterbank[m-1][f] = 
(float)(f - f_left) / (f_center - f_left);
// Sườn phải: giảm dần 1 -> 0
mel_filterbank[m-1][f] = 
(float)(f_right - f) / (f_right - f_center);
```

**Bước 4️⃣ — Slaney-norm (khớp `norm='slaney'` mặc định của librosa):**
```cpp
float enorm = 2.0f / (hz_points[m + 1] - hz_points[m - 1]);
mel_filterbank[m - 1][f] *= enorm;
```
Mục đích: chuẩn hóa mỗi tam giác theo **độ rộng băng thông Hz** của chính nó, để mọi dải Mel có diện tích tích phân bằng nhau — nếu thiếu bước này, các dải Mel ở tần số cao (băng thông rộng hơn) sẽ luôn có năng lượng tổng lớn hơn một cách giả tạo, không phản ánh đúng bản chất tín hiệu.

---

## 4️⃣ `Compute_Mel_Power_Spectrogram()` — STFT + Áp filterbank 🌊

Với mỗi trong 129 frame:
1. **Cắt frame** bằng `Get_Centered_Frame()`.
2. **Windowing:** `FFT.windowing(FFTWindow::Hann, ...)` — nhân từng mẫu với hệ số cửa sổ Hann (khớp `window='hann'` mặc định của `librosa.stft`), làm mượt biên frame, tránh rò rỉ phổ (spectral leakage).
3. **FFT:** `FFT.compute(FFTDirection::Forward)` — biến đổi sang miền tần số.
4. **Power spectrum:** `power[k] = re[k]² + im[k]²` — chỉ lấy `N_FREQ_BINS = N_FFT/2+1 = 513` bin đầu (phổ FFT đối xứng, nửa sau dư thừa). Khớp `power=2.0` mặc định của `librosa.feature.melspectrogram`.
5. **Áp Mel filterbank:** nhân ma trận `power_spectrum × mel_filterbank` — gộp 513 bin tần số chi tiết thành 64 dải Mel.

---

## 5️⃣ `Power_To_dB_RefMax()` — Chuyển sang thang dB 🔊

Khớp `librosa.power_to_db(mel_spec, ref=np.max)` (mặc định `top_db=80`):

**Bước 1:** `dB = 10 * log10(power / max_power)` — với `max_power` là giá trị lớn nhất toàn ma trận (`ref=np.max` khiến đỉnh luôn là 0dB).

**Bước 2 — clip đáy (`top_db=80`):** không cho giá trị nào thấp hơn `(max_dB - 80)`. Nếu thiếu bước này, các vùng năng lượng rất thấp (khoảng lặng) sẽ rơi tự do xuống rất âm (có thể -150dB trở lên), tạo phân bố khác hẳn so với dữ liệu lúc train — đây từng là nguồn gốc 1 bug nghiêm trọng đã fix.

```cpp
float floor_db = max_db - top_db;
if(mel_db_out[f][m] < floor_db) mel_db_out[f][m] = floor_db;
```

💡 **Lưu ý:** đây là `dB = 10*log10(...)`, không phải `20*log10(...)` — vì đầu vào là **power** (năng lượng), không phải amplitude.