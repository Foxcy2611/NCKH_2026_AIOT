# Mel filterbank Slaney và chuyển Log-Mel

[Mục lục C++](README.md)

## Mục lục

- [1. Vai trò của filterbank](#muc-1)
- [2. Chuyển đổi Hz ↔ Mel](#muc-2)
- [3. Trọng số tam giác](#muc-3)
- [4. Bộ nhớ và tích lũy](#muc-4)
- [5. Log-Mel ref-max](#muc-5)
- [6. Layout đưa vào mạng](#muc-6)
- [7. Kiểm chứng filterbank và dB](#muc-7)

<a id="muc-1"></a>

## 1. Vai trò của filterbank

Mỗi frame có1.025 power bins; model C4 cần40 dải Mel. Filterbank là ma trận W kích thước40×1.025:

```text
M[m,t] = Σ(k=0..1024) W[m,k] * P[k,t]
```

W không phải weights học bằng backpropagation. Nó được dựng từ cấu hình frontend cố định trước khi suy luận; weights CNN được học ở bước training riêng.

Source: [Init_Mel_Filterbank và Power_To_dB_RefMax](../../Final_Project_NCKH/Patient_Node/src/Mel_Scale.cpp).

<a id="muc-2"></a>

## 2. Chuyển đổi Hz ↔ Mel

Implementation dùng Slaney, phù hợp `htk=False`:

```text
f_sp = 200/3
m(f) = f/f_sp                                  nếu f<1000
m(f) = 15 + ln(f/1000)/(ln(6.4)/27)            nếu f>=1000

f(m) = m*f_sp                                 nếu m<15
f(m) = 1000*exp((m-15)*ln(6.4)/27)             nếu m>=15
```

40 filter cần42 điểm biên/đỉnh. Lấy42 điểm đều trên Mel từ100 đến2000 Hz, rồi đổi lại Hz. Đều trên Mel không có nghĩa đều trên Hz ở toàn dải.

Hàm Hz_to_Mel/Mel_to_Hz public dùng float. Khi dựng bảng, source dùng lambda và điểm double rồi lưu weight cuối thành float32 để giảm sai lệch vị trí đỉnh.

<a id="muc-3"></a>

## 3. Trọng số tam giác

Với filter m có `left, center, right` và bin tần số `f_k=k*16000/2048`:

```text
lower = (f_k - left)/(center-left)
upper = (right-f_k)/(right-center)
triangle = max(0, min(lower, upper))
W[m,k] = triangle * 2/(right-left)
```

Không làm tròn ba đỉnh thành chỉ số bin rồi dựng tam giác nguyên. Source tính slope ở đúng tần số thực của từng bin, đặc biệt quan trọng khi dải Mel hẹp hơn hoặc xấp xỉ một vài bin FFT.

Slaney normalization chia theo độ rộng dải để điều chỉnh diện tích tam giác. Nó không phải chuẩn hóa để tổng các weight rời rạc bằng1; cũng không phải chuẩn hóa từng cột FFT. [librosa.filters.mel](https://librosa.org/doc/0.11.0/generated/librosa.filters.mel.html).

<a id="muc-4"></a>

## 4. Bộ nhớ và tích lũy

Filterbank có `40*1025=41.000` float, tương ứng164.000 byte. `Init_Mel_Filterbank` cấp phát trong PSRAM với alignment16. Nếu đã có pointer, hàm không cấp phát lại.

Mỗi Mel energy được cộng trong float:

```cpp
float energy = 0.0f;
for (int k = 0; k < 1025; ++k)
    energy += power_spectrum[k] * mel_filterbank[m*1025+k];
```

Sai số cộng dồn có thể khác phép nhân ma trận NumPy/BLAS. Độ tương đương phải đo trên kết quả, không suy ra từ việc cùng có1.025 phép nhân.

<a id="muc-5"></a>

## 5. Log-Mel ref-max

Implementation tìm `ref=max(max(M),1e-10)` trên toàn bộ40×129 rồi tính:

```text
D[m,t] = 10*log10(max(M[m,t],1e-10)/ref)
floor_db = max(D) - 80
D[m,t] = max(D[m,t], floor_db)
```

Reference là cực đại toàn cửa sổ, không phải max từng frame hoặc từng dải. Dùng10log cho power;20log dành cho biên độ trước khi bình phương. Ý nghĩa ref/amin/top_db được đối chiếu trong [librosa.power_to_db](https://librosa.org/doc/0.11.0/generated/librosa.power_to_db.html).

Với tín hiệu có năng lượng bình thường, cực đại bằng0 dB và floor thường -80 dB. Nếu mọi power đều0, epsilon làm toàn ma trận dB thành0; điều đó không có nghĩa âm rất lớn. Đây là ví dụ vì sao silence phải xét trên PCM.

Hàm cho phép input/output cùng buffer: max power được tính xong trước vòng ghi dB; mỗi ô được đọc rồi thay tại chính ô đó.

<a id="muc-6"></a>

## 6. Layout đưa vào mạng

`mel_spectrogram_buffer[m][t]` lưu liên tục theo C row-major. Index tensor:

```text
index = m*129 + t
```

Model NHWC nhận batch1, height40 Mel, width129 time, channel1. Flatten theo time-major `t*40+m` tạo tensor cùng số phần tử nhưng sai nội dung không gian.

Các ảnh matplotlib có thể xoay trục để trình bày. Không dùng hướng của ảnh trên màn hình làm chuẩn để suy ra thứ tự dữ liệu trong memory.

<a id="muc-7"></a>

## 7. Kiểm chứng filterbank và dB

Lưu W của Python/C++ cùng shape rồi đo max/mean absolute difference. So Mel power trước khi đổi dB, sau đó so dB để xác định lỗi ở chiếu phổ hay log.

Nếu phổ yếu có relative error lớn, xem thêm absolute error và floor epsilon; chia sai số cho giá trị gần0 có thể làm số phần trăm vô nghĩa. Với dB đã clip, ghi tỷ lệ ô chạm -80 và vị trí các sai số lớn.

Đổi n_mels/fmin/fmax cần dựng lại filterbank và dùng model phù hợp. Không chỉ sửa macro để ép input model cũ nhận shape mới.

