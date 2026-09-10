# Tài liệu kỹ thuật Phase 2 — C++ và LiveMic

Thư mục này mô tả đúng implementation trong
`Deploy_Model/2_Test_Model_LiveMic`. Phase 2 dùng để kiểm chứng đường đi từ
PCM16 hoặc INMP441 đến tensor INT8 và kết quả TensorFlow Lite Micro trước khi
đưa các mô-đun đã ổn định vào Patient Node cuối.

```text
INMP441 / PCM16 nhúng
  → VAD + bộ đệm pre-trigger (chỉ khi chạy micro)
  → đoạn 5 giây, 80.000 mẫu
  → normalize + Butterworth + pre-emphasis
  → Mel-Spectrogram 64 × 129
  → chuẩn hóa [0, 1] + lượng tử INT8
  → DS-CNN trên TFLite Micro
  → kết quả từng lượt / bỏ phiếu ba đoạn thu
```

## Cấu hình kiểm thử

Các macro trong `include/Audio_IO/I2S_Mic.h` chọn đúng một chế độ:

| Macro | Mục đích |
|---|---|
| `RUN_PARITY_20_TEST` | Chạy 20 mảng PCM16 nhúng và so tensor/output với Python |
| `RUN_VALIDATION_108_TEST` | Nạp trực tiếp tensor validation vào model |
| `RUN_TEST_113_TEST` | Nạp trực tiếp tensor test vào model |
| `RUN_VAD_CALIBRATION_TEST` | Đo năng lượng nền/tín hiệu để chọn ngưỡng VAD |

Khi kiểm tra micro thật, cả bốn macro phải bằng `0`.

## Danh mục tài liệu

- [Thu âm I2S và state flow](./I2S_Mic_README.md)
- [Bộ đệm pre-trigger 1 giây](./Bo_Dem_Truoc_VAD_1_Giay.md)
- [Normalize, Butterworth và pre-emphasis](./DSP_Filter_README.md)
- [STFT và Mel-Spectrogram](./Mel_Scale_README.md)
- [Giao tiếp model INT8](./Interface_Asthma_README.md)

## Nguồn chuẩn và phạm vi

- Pipeline Python tham chiếu nằm trong `AI_Training_Model/` ở root repository.
- Model phase này là `include/Model_AI/Asthma_Model_3.h`.
- Nhật ký đối chiếu nằm trong `../logs/`.
- Phase này chưa chứa Quality Gate, MAX30102, OLED, PatientSession hay
  ESP-NOW; các phần đó thuộc `Final_Project_NCKH/Patient_Node`.

Tài liệu mô tả sự tương đương thuật toán và kết quả kiểm chứng đã thực hiện;
không dùng cụm từ “khớp 100%” nếu chưa có bằng chứng bit-exact trên phần cứng.
