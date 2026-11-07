# 2_Test_Model_LiveMic

Project kiểm tra đường đi đầy đủ trên ESP32-S3:

```text
RAW PCM16 nhúng hoặc INMP441
  -> audio 5 giây / 80.000 mẫu / 16 kHz
  -> normalize + Butterworth (không pre-emphasis)
  -> Mel-Spectrogram 40 x 129, FFT 2048
  -> lượng tử input INT8
  -> C4 V1 s44 / QAT INT8 trên TensorFlow Lite Micro
```

## Cấu hình cần đổi

- Model đã cố định tại `include/Model_AI/Asthma_Model.h`; header này dùng chung
  artifact cuối trong `Final_Project_NCKH/AI_Model`.
- Chọn nguồn kiểm tra tại `include/Audio_IO/I2S_Mic.h`:
  - `RUN_RAW_PCM16_TEST = 1`: chạy tự động 12 mẫu trong `Raw_PCM16_Test_Samples.h`.
  - `RUN_RAW_PCM16_TEST = 0`: đọc INMP441 thật, dùng VAD và vote ba lần.
  - `RUN_VAD_CALIBRATION_TEST = 1`: chỉ đo năng lượng VAD; không chạy model.

Hai header V1/V5 cũ đã được loại bỏ. Bộ RAW 12 mẫu chưa qua preprocess Python,
vì vậy nó kiểm tra đúng chuỗi
`PCM16 -> preprocess C++ -> model`. Các tensor Python 108/113 và bộ parity 20 cũ đã
được xóa khỏi project này; phép thử tensor trực tiếp thuộc
`../1_Test_Model_Static_Profiling`.

`platformio.ini` dùng `partitions_16mb.csv` với app partition 8 MiB vì 12 đoạn PCM16
và một model INT8 có thể vượt giới hạn 3 MiB của `huge_app.csv`.

Không dùng project này làm Patient Node hoàn chỉnh. Firmware tích hợp nằm tại
`../../Final_Project_NCKH/Patient_Node`.
