# Normalize waveform, Butterworth và quyết định bỏ pre-emphasis trong C4

[Mục lục C++](README.md)

## Mục lục

- [1. Peak normalization](#muc-1)
- [2. Thiết kế Butterworth](#muc-2)
- [3. Phương trình và state](#muc-3)
- [4. Vì sao dùng double trong IIR?](#muc-4)
- [5. Pre-emphasis](#muc-5)
- [6. Kiểm thử theo từng cấp](#muc-6)

<a id="muc-1"></a>

## 1. Peak normalization

Hàm `Normalize_To_Float` tìm `peak=max(abs(PCM))`, nếu peak=0 đặt1, rồi chia từng mẫu cho peak. Biên độ output nằm trong [-1,1]. Đây là chuẩn hóa riêng từng cửa sổ5 s.

Trị tuyệt đối cần nâng lên int32 trước: `abs(-32768)` không biểu diễn được bằng int16 dương. Source đã chuyển sample sang int32 để tính peak. Buffer output dùng float32.

Peak normalization giảm biến thiên gain tổng thể, nhưng không khôi phục tín hiệu bị clipping và không loại noise. Với hai tín hiệu chỉ khác một hệ số dương, lý tưởng normalize có thể tạo waveform giống nhau; nếu loa–mic làm thay đổi đáp ứng phổ hoặc thêm nhiễu, phép chia peak không xóa được domain shift đó.

<a id="muc-2"></a>

## 2. Thiết kế Butterworth

Python gọi:

```python
b, a = butter(5, [100/8000, 2000/8000], btype="band", output="ba")
y = lfilter(b, a, x, zi=None)
```

Nyquist=8.000 Hz; cutoff chuẩn hóa là0,0125 và0,25. Với bandpass, order5 trong thiết kế tạo transfer function bậc10, có11 hệ số B và11 hệ số A. Đừng dùng5 trạng thái rồi vẫn chép bộ hệ số bậc10. [SciPy butter](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.butter.html).

Source C++ đã lưu cố định hệ số trong [DSP_Filter.cpp](../../Final_Project_NCKH/Patient_Node/src/DSP_Filter.cpp), không thiết kế lại bộ lọc mỗi lần thu.

<a id="muc-3"></a>

## 3. Phương trình và state

Với a0=1:

```text
y[n] = Σ b[k] x[n-k] - Σ a[k] y[n-k], k hồi tiếp bắt đầu từ1
```

Implementation dùng Direct Form II Transposed:

```text
y = b0*x + state[0]
state[i] = state[i+1] + b[i+1]*x - a[i+1]*y  (i=0..8)
state[9] = b10*x - a10*y
```

Đây là cấu trúc của `scipy.signal.lfilter`; `zi=None` tương ứng trạng thái nghỉ ban đầu. [SciPy lfilter](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.lfilter.html).

`Butterworth_Reset` đặt10 trạng thái về0 trước mỗi clip. Bỏ reset làm clip sau phụ thuộc đuôi clip trước, trong khi Python xử lý các WAV độc lập. Reset sau từng sample lại phá hoàn toàn tính hồi tiếp.

<a id="muc-4"></a>

## 4. Vì sao dùng double trong IIR?

Hệ số và state là double; input float được nâng lên double, output y cast về float. Bộ lọc bậc cao dạng ba có thể nhạy với sai số hệ số và cộng/trừ; làm tròn sớm dễ tạo sai lệch tích lũy.

| Thành phần | Kiểu | Lý do trong implementation |
|---|---|---|
| Audio buffer | float32 | Giảm footprint80.000 mẫu |
| FILTER_B/A | double | Giữ độ chính xác hệ số |
| filter_state | double | Giảm sai số hồi tiếp |
| Sample output | float32 | Giao tiếp trực tiếp với FFT/Mel |

Dùng double ở IIR không có nghĩa toàn bộ DSP là float64. Khi đo parity, khác biệt từ cast output có thể tiếp tục truyền vào Mel.

SciPy khuyến nghị SOS cho nhiều bài toán lọc vì ổn định số tốt hơn. Tuy nhiên baseline dự án dùng ba/lfilter; thay sang SOS cần đo lại parity và ghi phiên bản. Không thay `lfilter` bằng `filtfilt`: lọc hai chiều có đáp ứng pha và điều kiện biên khác.

<a id="muc-5"></a>

## 5. Pre-emphasis: đối chứng lịch sử, không dùng trong C4

Pipeline F0 lịch sử từng dùng:

```text
y[0] = x[0]
y[n] = x[n] - 0.97*x[n-1], n>=1
```

Nếu triển khai in-place, phải duyệt từ cuối về đầu; duyệt xuôi làm `x[n-1]` trở thành output mới và thay đổi công thức.

Tại tần số0, độ lớn đáp ứng là `|1-0.97|=0.03`; gần Nyquist là `1+0.97=1.97`. Nó nhấn tương đối thành phần cao hơn, không phải tăng cùng gain cho mọi tần số.

Model cuối C4 đặt coefficient bằng `0`, vì vậy **không gọi bước pre-emphasis**. Thứ tự hiện hành là `peak normalize → Butterworth → STFT/Mel`. Không được áp dụng lại hệ số0,97 cho C4 chỉ vì tài liệu hoặc code lịch sử còn mô tả công thức này; làm vậy sẽ đổi phân bố feature so với lúc train.

<a id="muc-6"></a>

## 6. Kiểm thử theo từng cấp

| Tín hiệu kiểm tra | Quan sát mong đợi |
|---|---|
| Toàn0 | Không NaN/Inf, output0 |
| Impulse | So đáp ứng xung Python/C++ và kiểm tra reset |
| Sine trong dải | Có đáp ứng theo filter, không phát sinh năng lượng vô hạn |
| Sine ngoài dải | Suy giảm, không mặc định triệt tiêu tuyệt đối |
| PCM thực | MAE/max error và sai số sau Log-Mel |
| Chạy clip A rồi B | B giống chạy độc lập khi reset đúng |

Nếu cùng clip cho output khác giữa hai lần gọi, kiểm tra state và buffer trước khi kết luận lỗi model. Giá trị tolerance phải chọn sau đo, không tự gắn nhãn “bit-exact” từ việc hệ số trông giống nhau.

