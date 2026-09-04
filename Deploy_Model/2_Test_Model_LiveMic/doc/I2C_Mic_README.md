# I2S_Mic — thu âm và điều phối pipeline

Luồng chạy micro thật:

```text
LISTENING → RECORDING → PROCESSING → INTERFACE → LISTENING
```

## LISTENING

- Bỏ 100 khối đầu sau reset, khoảng 1,6 giây.
- Tích lũy 16.000 mẫu gần nhất trong bộ đệm vòng PSRAM.
- Tính trung bình trị tuyệt đối của từng khối 256 mẫu.
- Chỉ kích hoạt khi 4 khối liên tiếp vượt ngưỡng 75.

## RECORDING

- Chép một giây trước kích hoạt vào `audio_buffer`.
- Thu thêm 64.000 mẫu để đủ tổng cộng 80.000 mẫu, tương đương 5 giây.

## PROCESSING

1. Chuẩn hóa theo trị tuyệt đối lớn nhất.
2. Butterworth 100–2.000 Hz.
3. Pre-emphasis 0,97.
4. STFT và 64 dải Mel.
5. Đổi power sang dB với đáy -80 dB.

## INTERFACE

- Chuẩn hóa dB theo tham số train và lượng tử INT8.
- Chạy TFLite Micro.
- Lớp 0 là Asthma; lớp 1 là Non-Asthma.
- Bỏ phiếu 3 lượt và quay lại tạo bộ đệm một giây mới.

Non-Asthma không đồng nghĩa với bình thường; lớp này còn chứa các bệnh hô hấp
khác và âm thanh môi trường.
