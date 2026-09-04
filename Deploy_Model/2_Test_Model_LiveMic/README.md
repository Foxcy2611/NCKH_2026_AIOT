# Phase 2 — Kiểm thử pipeline C++ và micro trực tiếp

Đây là project phát triển/kiểm chứng đầy đủ của phần TinyML trên ESP32-S3:

- Đối chiếu tensor Python–ESP32 bằng dữ liệu PCM/tensor nhúng.
- Thu INMP441 ở 16 kHz, một kênh, khung 32 bit chuyển về PCM16.
- VAD ngưỡng 75, cần 4 khối liên tiếp.
- Bỏ 100 khối I2S đầu sau reset.
- Giữ bộ đệm vòng 1 giây và thu thêm 4 giây để đủ 5 giây.
- Chạy chuẩn hóa, Butterworth, pre-emphasis, Mel-Spectrogram và model INT8.
- Bỏ phiếu 3 lượt trước khi đưa ra kết luận.

Các chế độ kiểm chứng được chọn trong `include/Audio_IO/I2S_Mic.h`. Khi chạy
micro thật, tất cả macro kiểm tra phải bằng 0.

Model sử dụng: `include/Model_AI/Asthma_Model_3.h`.

Project này giữ header tensor và tài liệu đối chiếu để phục vụ nghiên cứu. Bản
tinh gọn dùng tích hợp hệ thống nằm ở `../3_Model_Complete`.
