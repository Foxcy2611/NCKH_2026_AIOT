# I2S_Mic — thu âm, VAD và điều phối pipeline

INMP441 giao tiếp với ESP32-S3 bằng **I2S**. Tên file này dùng `I2S`, không dùng
`I2C`.

## Cấu hình thu

| Thuộc tính | Giá trị |
|---|---:|
| Sample rate | 16 kHz |
| DMA format | 32 bit, kênh phải |
| PCM dùng trong pipeline | 16 bit |
| Kích thước khối | 256 mẫu |
| Hệ số khuếch đại số | 1 |
| Độ dài input | 80.000 mẫu, 5 giây |

Dữ liệu DMA được dịch phải 16 bit, giới hạn trong miền PCM16 rồi mới đưa vào
bộ đệm. Hệ số khuếch đại được giữ ở 1 để tránh clipping trước bước normalize.

## State flow khi chạy micro thật

```text
LISTENING → RECORDING → PROCESSING → INTERFACE → LISTENING
```

### `LISTENING`

- Bỏ 100 khối đầu sau reset, khoảng 1,6 giây.
- Tích lũy 16.000 mẫu gần nhất trong bộ đệm vòng PSRAM.
- Chỉ bật xét VAD sau khi bộ đệm đã đủ 1 giây.
- Tính trung bình trị tuyệt đối cho từng khối 256 mẫu.
- Xác nhận trigger khi bốn khối liên tiếp vượt ngưỡng 75.

### `RECORDING`

- Tại trigger, chép 16.000 mẫu pre-trigger theo đúng thứ tự thời gian.
- Thu thêm 64.000 mẫu để đủ 80.000 mẫu.
- Với `RUN_PARITY_20_TEST=1`, bước đọc micro được thay bằng mảng PCM16 nhúng.

### `PROCESSING`

1. Normalize PCM16 theo trị tuyệt đối lớn nhất.
2. Butterworth bandpass bậc 5, 100–2.000 Hz.
3. Pre-emphasis với hệ số 0,97.
4. STFT 1.024 điểm, hop 625 và 64 dải Mel.
5. Đổi power sang dB với `ref=max` và `top_db=80`.

### `INTERFACE`

- Chuẩn hóa dB từ `[-80, 0]` sang `[0, 1]`.
- Lượng tử về tensor INT8 `[1, 64, 129, 1]`.
- Chạy TFLite Micro và áp ngưỡng `p(Non-Asthma)=0,5`.
- Khi chạy micro bình thường, mỗi đoạn thu tạo một vote. Sau ba đoạn
  capture/inference độc lập, firmware mới in kết luận bỏ phiếu.
- Sau mỗi lượt, firmware làm mới pre-trigger và quay lại `LISTENING`.

Ba vote không phải ba lần `Invoke()` trên cùng một tensor. Chúng là ba lượt
thu và suy luận riêng biệt.

## Chế độ test

Các macro trong `include/Audio_IO/I2S_Mic.h` loại trừ lẫn nhau ở compile time.
Direct-tensor test bỏ qua micro và toàn bộ DSP; VAD calibration bỏ qua Mel và
model; parity PCM16 giữ DSP để so tensor cuối với Python.

`NON_ASTHMA` không có nghĩa là người dùng chắc chắn khỏe mạnh. Đây chỉ là lớp
còn lại trong bài toán phân loại âm thanh hiện tại.
