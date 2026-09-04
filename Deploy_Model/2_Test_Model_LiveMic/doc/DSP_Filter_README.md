# 🎚️ DSP_Filter — Bộ lọc tiền xử lý âm thanh (Butterworth + Pre-emphasis)

Thư viện thực hiện 2 bước lọc số trước khi đưa tín hiệu vào STFT: lọc thông dải Butterworth và lọc pre-emphasis, tương ứng `scipy.signal.lfilter` + hàm tự viết trong Python.

## Tương ứng hàm Python ↔ C++

| Python | C++ | Vai trò |
|---|---|---|
| `scipy.signal.butter(order, [low, high], btype='band', output='sos')` | Hệ số cứng `sos_coeffs[]` | Thiết kế bộ lọc (làm offline, chỉ tính 1 lần) |
| `scipy.signal.lfilter(b, a, data)` | `Butterworth_Process_Sample()` / `Butterworth_Process_Buffer()` | Áp bộ lọc lên tín hiệu (chạy runtime) |
| `Pre_Emphasis(signal, coef=0.97)` (hàm tự viết) | `Apply_Pre_Emphasis()` | Bù suy hao tần số cao |
| `librosa.util.normalize(y)` | `Normalize_To_Float()` | Chuẩn hóa biên độ về [-1, 1] |

---

## 1️⃣ Vì sao dùng dạng SOS (cascade biquad) thay vì Direct Form

Bộ lọc Butterworth bandpass bậc 5 khi biến đổi sang miền số (digital) trở thành bậc 10, cần 11 hệ số `b` và 11 hệ số `a`.

⚠️ **Vấn đề với Direct Form (11 hệ số 1 khối):** hệ số dao động rất lớn (từ `~68` xuống `~0.08`) — khi tính tổng-nhân trên `float`, sai số làm tròn tích lũy theo cấp số nhân qua hàng chục nghìn sample liên tiếp, dẫn tới **NaN** giữa file dài (đã từng gặp và fix).

✅ **Giải pháp — SOS (Second-Order Sections):** chia bộ lọc bậc 10 thành **5 bộ lọc bậc 2 (biquad) nối tiếp nhau**, mỗi biquad chỉ có 5 hệ số nhỏ (`b0, b1, b2, a1, a2`), không có hệ số nào vượt quá vài đơn vị → ổn định số học tốt hơn nhiều dù vẫn dùng `float`.

Hệ số được tính sẵn 1 lần bằng Python:
```python
scipy.signal.butter(5, [100, 2000]/nyq, btype='band', output='sos')
```
rồi hardcode trực tiếp vào C++ — không tính toán thiết kế filter runtime trên ESP32 (quá phức tạp, không cần thiết vì filter cố định).

---

## 2️⃣ `Butterworth_Process_Sample()` — Lọc từng sample qua 5 tầng nối tiếp

Mỗi biquad tính theo công thức Direct Form I:
```
y[n] = b0·x[n] + b1·x[n-1] + b2·x[n-2] - a1·y[n-1] - a2·y[n-2]
```

```cpp
float Butterworth_Process_Sample(float x_new) {
    float in = x_new;
    for (int s = 0; s < NUM_SECTIONS; s++) {
        const BiquadCoeffs& c = sos_coeffs[s];
        float out = c.b0*in + c.b1*sos_x1[s] + c.b2*sos_x2[s]
                    - c.a1*sos_y1[s] - c.a2*sos_y2[s];

        sos_x2[s] = sos_x1[s]; sos_x1[s] = in;   // dịch lịch sử input
        sos_y2[s] = sos_y1[s]; sos_y1[s] = out;  // dịch lịch sử output

        in = out;   // output của section này = input của section kế tiếp
    }
    return in;
}
```

`sos_x1, sos_x2, sos_y1, sos_y2` là **trạng thái trễ (delay line)** — bắt buộc `static` vì phải giữ nguyên giá trị giữa các lần gọi hàm liên tiếp (đang xử lý stream tín hiệu, không phải từng đoạn độc lập).

**`Butterworth_Reset()`** đưa toàn bộ trạng thái trễ về 0 — bắt buộc gọi trước khi xử lý 1 đoạn audio mới (5 giây mới), tránh dữ liệu cũ của lần đo trước làm nhiễu kết quả lần đo hiện tại.

---

## 3️⃣ `Apply_Pre_Emphasis()` — Bù suy hao tần số cao

Công thức: `y[n] = x[n] - 0.97 × x[n-1]`, khớp Python:
```python
np.append(signal[0], signal[1:] - coef * signal[:-1])
```

```cpp
void Apply_Pre_Emphasis(float* signal, int length){
    for(int i = length - 1; i >= 1; i--){
        signal[i] = signal[i] - Pre_Coef * signal[i - 1];
    }
    // signal[0] giữ nguyên, không đổi 
    // (Khớp np.append giữ signal[0])
}
```

⚠️ **Lưu ý quan trọng về thứ tự vòng lặp:** phải chạy **từ cuối về đầu** (`i--`, không phải `i++`). Vì phép tính `signal[i]` cần dùng giá trị **gốc chưa bị sửa** của `signal[i-1]`. Nếu chạy từ đầu ra cuối (thuận), `signal[i-1]` đã bị ghi đè bởi phép tính trước đó, làm sai toàn bộ kết quả (đây là bug đã từng gặp và fix).

---

## 4️⃣ `Normalize_To_Float()` — Chuẩn hóa biên độ về [-1, 1]

Khớp `librosa.util.normalize(y)` — chia toàn bộ tín hiệu cho giá trị tuyệt đối lớn nhất tìm được:

```cpp
void Normalize_To_Float(int16_t* input, float* output, int length){
    int32_t max_val = 0;   // dùng int32_t, KHÔNG dùng int16_t
    for(int i = 0; i < length; i++){
        int32_t abs_val = abs((int32_t)input[i]);
        if(abs_val > max_val) max_val = abs_val;
    }
    if(max_val == 0) max_val = 1;   // tránh chia 0 nếu tín hiệu toàn im lặng

    for(int i = 0; i < length; i++){
        output[i] = input[i] / (float)max_val;
    }
}
```

💡 **Vì sao dùng `int32_t` thay vì `int16_t` cho biến đếm:** giá trị `int16_t` nhỏ nhất có thể là `-32768`, nhưng `abs(-32768)` về mặt toán học bằng `32768` — con số này **vượt quá** giới hạn `int16_t` (`max 32767`). Nếu dùng `int16_t` để lưu kết quả `abs()`, sẽ xảy ra tràn số (overflow) khi mẫu chạm đúng đáy tuyệt đối, gây tính sai `max_val` trong trường hợp hiếm. Dùng `int32_t` loại bỏ hoàn toàn rủi ro này.