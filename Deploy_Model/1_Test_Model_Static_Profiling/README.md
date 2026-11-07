# Phase 1 — Kiểm tra model tĩnh và tài nguyên

Project này gộp hai thử nghiệm nền tảng ban đầu:

- Nạp model TFLite Micro trên ESP32-S3.
- Chạy 12 tensor Asthma/Non-Asthma tĩnh đã được preprocess và lượng tử hóa bằng Python.
- Đo thời gian `Invoke()` theo `min/avg/max` sau một lượt warm-up.
- Cấp trước tensor arena 1 MiB trong PSRAM, đọc `arena_used_bytes()` và đề xuất mức thử tiếp theo.
- Đo internal RAM, PSRAM, độ ổn định qua 3 vòng và khả năng tương thích operator.
- Đối chiếu nhãn thật và output INT8 với Python trên cùng model đang chọn.
- Kiểm tra CPU chạy ở 240 MHz.

Đây là project kiểm chứng độc lập, không đọc INMP441 và không chạy pipeline
Mel-Spectrogram. Model chính thức và pipeline hoàn chỉnh nằm ở các phase sau.

Các kết luận đã gộp:

- Model tải và `AllocateTensors()` thành công mới được phép chạy benchmark.
- Tensor tĩnh chỉ được nạp khi type, số byte, scale và zero-point khớp model.
- Thời gian suy luận được đo trực tiếp bằng `esp_timer_get_time()`.

## Model đang kiểm tra

Nhánh mặc định đang bật để đo là `combo_pre0_mel40_fft2048__V1__s44 / QAT_INT8`:

```text
include/combo_pre0_mel40_fft2048__V1__s44/QAT_INT8/Asthma_Model.h
include/combo_pre0_mel40_fft2048__V1__s44/QAT_INT8/Static_Test_Tensors.h
```

Hai header có cùng input `(40, 129, 1)`, cùng scale/zero-point và cùng SHA-256
model trong `deployment_manifest.json`. Có thể đổi model bằng nhóm macro
`PROFILE_MODEL_*` ở đầu `src/Test_Model_Static_Profiling.cpp`, nhưng chỉ được bật
đúng một macro tại một thời điểm.

Để tái tạo artifact V3 trước khi upload, chạy:

```powershell
py -3.11 AI_Training_Model/Phase4_Deployment_Artifacts/Prepare_V3_PTQ_INT8_Static_Profiling.py
```

Script tái sử dụng 12 input tensor C4 tương thích và suy luận lại output Python
bằng chính `V3_PTQ_INT8.tflite` để phép kiểm tra parity không dùng kết quả model cũ.

Sau khi upload, chờ đến khối `TARGET BENCHMARK SUMMARY - REPORT SECTION 10.2` để
lấy Model Flash size, Tensor Arena, Peak RAM estimate, latency, operator
compatibility và stability.

## Kết quả Tensor Arena của C4 QAT INT8

Log `log/C4_QAT.log` đo `arena_used_bytes() = 169380 B`, tương đương khoảng
165,4 KiB. Arena 1 MiB trong project này chỉ là vùng đo rộng để tìm mức sử dụng
thật, không phải đề xuất cấu hình production.

| Mức cấp phát | Dung lượng | Phần dư so với 169380 B | Nhận xét |
|---|---:|---:|---|
| 180 KiB | 184320 B | 14940 B (~14,6 KiB) | Chạy được về mặt số học nhưng biên khá mỏng |
| 192 KiB | 196608 B | 27228 B (~26,6 KiB) | Mức thử tiếp theo được khuyến nghị |
| 280 KiB | 286720 B | 117340 B (~114,6 KiB) | Cấu hình hiện hành, an toàn nhưng dư nhiều |

Không hạ arena chỉ dựa trên phép trừ. Sau khi đổi phải build/upload bằng đúng
phiên bản TensorFlow Lite Micro, xác nhận `AllocateTensors()` thành công, kiểm
tra `arena_used_bytes()`, chạy đủ tensor parity và theo dõi biên PSRAM. Nếu
192 KiB ổn định thì mới đồng bộ mức đó sang `3_Model_Complete` và Patient Node.
