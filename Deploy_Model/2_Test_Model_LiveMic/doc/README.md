# Tài liệu kỹ thuật — C++ preprocess và LiveMic

Mục tiêu của phase này là kiểm tra cùng một pipeline C++ bằng hai nguồn đầu vào:

1. 12 đoạn RAW PCM16 nhúng để chạy lặp lại, không phụ thuộc micro.
2. INMP441 thật với VAD, bộ đệm trước kích hoạt một giây và vote ba lần.

## Chế độ

| Macro | Tác dụng |
|---|---|
| `RUN_RAW_PCM16_TEST` | Chạy 12 RAW PCM16 qua toàn bộ preprocess C++ và model |
| `RUN_VAD_CALIBRATION_TEST` | Chỉ đo phân bố năng lượng từ INMP441 |

Để chạy LiveMic thật, đặt cả hai macro bằng `0`.

Model được cố định là `C4 V1 s44 / QAT_INT8`. Mốc output Python lưu trong
header RAW phải được tái tạo bằng Phase 4 từ đúng model này.

Các phép thử tensor INT8 trực tiếp đã thuộc phase static profiling và không còn nằm
trong project này.

- [I2S và state flow](./I2S_Mic_README.md)
- [Bộ đệm trước VAD một giây](./Bo_Dem_Truoc_VAD_1_Giay.md)
- [DSP filter](./DSP_Filter_README.md)
- [Mel-Spectrogram](./Mel_Scale_README.md)
- [Inference INT8](./Inference_Asthma_README.md)
