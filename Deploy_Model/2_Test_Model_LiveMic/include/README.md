# Cấu trúc include

- `Audio_IO/I2S_Mic.h`: chọn chế độ RAW/LiveMic/VAD và khai báo state audio.
- `DSP_Preprocessing/DSP_Filter.h`: normalize, Butterworth, pre-emphasis.
- `DSP_Preprocessing/Mel_Scale.h`: STFT, Mel Slaney và power-to-dB.
- `Model_AI/Inference_Asthma.h`: API khởi tạo và chạy inference.
- `Model_AI/Asthma_Model.h`: model cuối `C4 V1 s44 / QAT_INT8`.
- `Raw_PCM16_Test/Raw_PCM16_Test_Samples.h`: 12 đoạn RAW PCM16, 6 Asthma và
  6 Non-Asthma, mỗi đoạn 80.000 mẫu.

Project không còn phụ thuộc model V1/V5 lịch sử, các header tensor
validation/test hoặc bộ parity 20 cũ.
