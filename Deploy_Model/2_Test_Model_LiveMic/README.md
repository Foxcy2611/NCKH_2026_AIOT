# Phase 2 — Kiểm thử pipeline C++ và micro trực tiếp

Project này kiểm chứng pipeline TinyML trên ESP32-S3 ở hai mức:

1. **Parity có kiểm soát:** nạp tensor INT8 hoặc PCM16 nhúng để đối chiếu với
   kết quả Python.
2. **LiveMic:** thu INMP441, kích hoạt bằng VAD, tạo đoạn 5 giây rồi chạy toàn
   bộ DSP và model trên thiết bị.

```text
INMP441 / PCM16
  → 5 giây audio
  → normalize + Butterworth + pre-emphasis
  → Mel-Spectrogram 64 × 129
  → INT8
  → DS-CNN / TFLite Micro
```

Khi chạy LiveMic, firmware bỏ 100 khối I2S khởi động, tạo bộ đệm vòng 1 giây,
chờ bốn khối liên tiếp vượt ngưỡng VAD 75 rồi thu thêm 4 giây. Kết luận voting
được tạo từ ba đoạn capture/inference riêng biệt.

Các chế độ kiểm chứng được chọn trong `include/Audio_IO/I2S_Mic.h`; khi chạy
micro thật, tất cả macro test phải bằng `0`. Model sử dụng là
`include/Model_AI/Asthma_Model_3.h`.

- [Tài liệu kỹ thuật](./doc/README.md)
- [Nhật ký kiểm thử](./logs/README.md)

Phase này không phải firmware Patient Node hoàn chỉnh: chưa có Quality Gate,
MAX30102, OLED, PatientSession hay ESP-NOW. Bản rút gọn sau kiểm chứng nằm ở
`../3_Model_Complete`; source tích hợp cuối nằm trong
`../../Final_Project_NCKH/Patient_Node`.
