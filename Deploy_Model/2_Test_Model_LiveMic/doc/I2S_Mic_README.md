# I2S Mic và luồng audio

## RAW PCM16 test

Khi `RUN_RAW_PCM16_TEST=1`, firmware không cài driver I2S. Mỗi mẫu trong
`Raw_PCM16_Test_Samples.h` được chép vào buffer 80.000 mẫu và đi qua nguyên pipeline
C++ trước khi inference. Sau 12 mẫu, chương trình in accuracy theo nhãn thật và
chênh lệch output so với mốc Python của model F0.

## INMP441 thật

Khi `RUN_RAW_PCM16_TEST=0`, driver I2S đọc mẫu 32-bit từ INMP441 và chuyển về PCM16.
Luồng hoạt động:

```text
LISTENING -> RECORDING -> PROCESSING -> INFERENCE -> LISTENING
```

- Bỏ 100 block đầu để micro ổn định.
- Tích lũy bộ đệm vòng một giây.
- Kích hoạt khi bốn block liên tiếp vượt VAD 75.
- Chép một giây pre-roll và thu thêm bốn giây.
- Chạy DSP, Mel, inference và vote ba lượt độc lập.

`RUN_VAD_CALIBRATION_TEST=1` chỉ đo năng lượng nền/tín hiệu và không khởi tạo model.
