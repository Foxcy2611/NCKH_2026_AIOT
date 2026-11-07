# Chuẩn hóa dữ liệu

## Các gia đoạn chuẩn hóa
| Giai đoạn | Miền giá trị | Ý nghĩa |
|---|---|---|
| WAV sau khi đọc | [-1,1] | Biên độ âm thanh dạng số thực |
| Mel-Spectrogram dB |	[-80,0]	| Năng lượng theo thang dB |
| Đầu vào mô hình Keras |	[0,1] |	Mel đã chuẩn hóa |
| Đầu vào TFLite	int8 |  [-128,127]	| Biểu diễn lượng tử của [0,1] |
| Đầu ra sigmoid | [0,1] |	Xác suất lớp 1 = Non-Asthma |

## Luồng hiện tại

```text
PCM16
  ↓ đổi sang float
Waveform [-1, 1]
  ↓ lọc + pre-emphasis + Mel
Mel dB [-80, 0]
  ↓ (mel - (-80)) / 80
Tensor float [0, 1]
  ↓ lượng tử theo scale và zero_point
Tensor int8 [-128, 127]
```