# Mel_Scale — STFT và Mel-Spectrogram

Mô-đun `src/Mel_Scale.cpp` tái hiện các lựa chọn quan trọng của librosa để biến
một đoạn 5 giây thành ma trận Mel `64 × 129`.

## Tham số khóa

| Tham số | Giá trị |
|---|---:|
| Sample rate | 16.000 Hz |
| `n_fft` | 1.024 |
| `hop_length` | 625 |
| Số FFT bin một phía | 513 |
| Số dải Mel | 64 |
| Dải tần | 100–2.000 Hz |
| Mel scale | Slaney, `htk=False` |
| Mel normalization | `norm="slaney"` |
| STFT padding | `center=True`, zero padding |
| Window | Hann tuần hoàn |
| Power | bình phương biên độ, `power=2` |
| dB | `ref=np.max`, `top_db=80` |

## 1. Thang Mel Slaney

Librosa mặc định dùng Slaney, gồm đoạn tuyến tính dưới 1.000 Hz và đoạn logarit
từ 1.000 Hz trở lên. Đây không phải công thức HTK
`2595·log10(1 + f/700)`. Sự khác biệt quan trọng vì dải 100–2.000 Hz đi qua
đúng điểm chuyển 1.000 Hz.

`Hz_to_Mel()` và `Mel_to_Hz()` trong C++ triển khai cặp biến đổi này để tạo 66
mốc biên cho 64 tam giác.

## 2. Center padding và số frame

`Get_Centered_Frame()` mô phỏng `librosa.stft(center=True)` bằng cách xem như
có `n_fft/2 = 512` mẫu 0 ở hai đầu. Với 80.000 mẫu và hop 625:

```text
num_frames = floor(80.000 / 625) + 1 = 129
```

Frame đầu có tâm tại thời điểm 0; vùng nằm ngoài tín hiệu thật nhận giá trị 0.

## 3. Cửa sổ Hann tuần hoàn

Code nhân cửa sổ thủ công:

```text
w[i] = 0,5 - 0,5·cos(2πi / N), 0 ≤ i < N
```

Không gọi trực tiếp Hann window của `arduinoFFT`, vì biến thể dùng mẫu đối xứng
`N-1` không khớp cửa sổ tuần hoàn mà pipeline Python đang dùng.

## 4. Mel filterbank

Filterbank có `64 × 513 = 32.832` trọng số `float` và được cấp phát trong
PSRAM. Với mỗi FFT bin, code dùng tần số thật:

```text
f[k] = k × sample_rate / n_fft
```

Sau đó tính trực tiếp độ dốc trái/phải của từng tam giác. Implementation hiện
tại **không làm tròn các mốc Mel về chỉ số FFT bin**.

Mỗi tam giác được nhân hệ số chuẩn hóa diện tích Slaney:

```text
enorm = 2 / (right_hz - left_hz)
```

## 5. Power và dB

Sau FFT, power một phía là:

```text
power[k] = real[k]² + imag[k]²
```

Power được nhân với filterbank để tạo `mel_power[mel][frame]`, rồi đổi sang dB:

```text
dB = 10·log10(max(power, 1e-10) / max_power)
```

Đỉnh toàn ma trận là 0 dB và mọi giá trị dưới `-80 dB` bị clip. Vì đầu vào là
power, hệ số đúng là 10, không phải 20.

## 6. Layout sang model

Output được lưu theo thứ tự `[mel][frame]`. `Interface_Asthma.cpp` flatten bằng:

```text
index = mel_index × 129 + frame_index
```

tạo 8.256 phần tử cho tensor `[1, 64, 129, 1]`.

## Điều kiện giữ parity

- Giữ Slaney scale và Slaney normalization.
- Giữ center padding, Hann tuần hoàn và 129 frame.
- Không làm tròn mốc tam giác về FFT bin.
- Giữ `ref=max`, `top_db=80` và layout `[mel][frame]`.
- Sau mọi thay đổi, so tensor INT8 với dữ liệu Python trước khi đánh giá model.
