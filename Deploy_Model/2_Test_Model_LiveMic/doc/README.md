# Tổng quan phase kiểm thử LiveMic

```text
INMP441
→ VAD + bộ đệm trước kích hoạt
→ đoạn PCM16 dài 5 giây
→ chuẩn hóa + Butterworth + pre-emphasis
→ Mel-Spectrogram 64 × 129
→ lượng tử INT8
→ TFLite Micro
→ bỏ phiếu 3 lượt
```

Pipeline chuẩn Python nằm trong `AI_Training_Model`. Phase này giữ các chế độ
đối chiếu cần thiết để chứng minh từng tầng trước khi chạy micro thật.

Tài liệu chi tiết:

- `DSP_Filter_README.md`
- `Mel_Scale_README.md`
- `Interface_Asthma_README.md`
- `I2C_Mic_README.md`
- `Bo_Dem_Truoc_VAD_1_Giay.txt`
