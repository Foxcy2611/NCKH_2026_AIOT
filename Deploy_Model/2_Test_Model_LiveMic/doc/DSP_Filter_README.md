# DSP_Filter — normalize, Butterworth và pre-emphasis

Mô-đun `src/DSP_Filter.cpp` triển khai ba bước đầu của pipeline C++ theo đúng
thứ tự đang dùng trong Python:

```text
PCM16 → normalize theo peak → Butterworth bandpass → pre-emphasis
```

## Đối chiếu Python và C++

| Python | C++ | Vai trò |
|---|---|---|
| `librosa.util.normalize(y)` | `Normalize_To_Float()` | Chuẩn hóa từng đoạn theo trị tuyệt đối lớn nhất |
| `scipy.signal.butter(5, ..., btype="band")` | `FILTER_B[]`, `FILTER_A[]` | Hệ số bandpass 100–2.000 Hz được tính offline |
| `scipy.signal.lfilter(b, a, y)` | `Butterworth_Process_Sample()` | Lọc Direct Form II Transposed |
| `np.append(y[0], y[1:] - 0.97*y[:-1])` | `Apply_Pre_Emphasis()` | Tiền nhấn tần số cao |

## Normalize PCM16

`Normalize_To_Float()` tìm `max(abs(sample))` trên toàn bộ 80.000 mẫu rồi chia
từng mẫu cho giá trị đó. Biến trung gian dùng `int32_t`, vì
`abs(-32768) = 32768` không biểu diễn được bằng `int16_t`. Với đoạn toàn 0,
mẫu chia được thay bằng 1 để tránh chia cho 0.

```cpp
output[i] = input[i] / static_cast<float>(max_val);
```

## Butterworth bandpass

Pipeline hiện tại **không dùng SOS**. Nó dùng đúng mảng hệ số `b/a` của bộ lọc
Butterworth bandpass bậc 5 do SciPy sinh ra. Sau biến đổi bandpass, phương trình
truyền có bậc thực tế 10.

Implementation là **Direct Form II Transposed**, cùng cấu trúc trạng thái với
`scipy.signal.lfilter`:

```text
y       = b[0]·x + z[0]
z[i]    = z[i+1] + b[i+1]·x - a[i+1]·y
z[last] = b[last]·x - a[last]·y
```

Hệ số và `filter_state` dùng `double` để giảm sai lệch tích lũy so với SciPy
float64; output từng mẫu được trả về `float` cho các bước nhúng tiếp theo.

`Butterworth_Reset()` phải được gọi trước mỗi đoạn audio mới. Nếu giữ delay
line từ lượt trước, đầu đoạn hiện tại sẽ bị ảnh hưởng bởi lịch sử không thuộc
cùng một phép đo.

## Pre-emphasis

Công thức:

```text
y[0] = x[0]
y[n] = x[n] - 0,97 × x[n-1], với n ≥ 1
```

Hàm sửa buffer tại chỗ nên vòng lặp bắt buộc đi từ cuối về đầu. Nếu đi xuôi,
`x[n-1]` đã bị ghi đè và kết quả không còn khớp với biểu thức Python.

## Điều kiện giữ parity

- Không đổi thứ tự normalize → Butterworth → pre-emphasis.
- Không thêm gain trước normalize nếu chưa kiểm tra clipping.
- Không thay hệ số `b/a` bằng thiết kế SOS khác chỉ vì cùng thông số danh nghĩa.
- Reset trạng thái filter cho từng đoạn 5 giây.
- Khi sửa thuật toán, chạy lại PCM16 parity và so đủ 8.256 phần tử tensor INT8.
