# Phase 1 — Kiểm tra model tĩnh và tài nguyên

Project này gộp hai thử nghiệm nền tảng ban đầu:

- Nạp model TFLite Micro trên ESP32-S3 và chạy tensor Asthma/Non-Asthma tĩnh.
- Đo thời gian `Invoke()`.
- Xác nhận `tensor_arena` 270 KB trong PSRAM là đủ cho model của phase này.
- Kiểm tra CPU chạy ở 240 MHz.

Đây là project kiểm chứng độc lập, không đọc INMP441 và không chạy pipeline
Mel-Spectrogram. Model chính thức và pipeline hoàn chỉnh nằm ở các phase sau.

Các kết luận đã gộp:

- Model tải và `AllocateTensors()` thành công.
- Tensor tĩnh có thể được nạp trực tiếp vào input INT8.
- Kích thước 200 KB không đủ; project dùng 270 KB có căn lề 16 byte trong
  PSRAM.
- Thời gian suy luận được đo trực tiếp bằng `esp_timer_get_time()`.
