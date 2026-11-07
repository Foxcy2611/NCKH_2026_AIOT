# 3_Model_Complete

Đây là bước hoàn thiện lõi audio/TinyML kế thừa trực tiếp từ
`2_Test_Model_LiveMic`. Phase 2 dùng PCM16/micro thật để kiểm chứng parity của
pipeline C++ với Python; Phase 3 giữ lại đúng chuỗi thu âm, DSP, Mel, lượng tử
input và inference đã kiểm chứng, sau đó bổ sung VAD, ring buffer và bỏ phiếu
ba lần để tạo một mô-đun chạy độc lập gọn hơn.

`3_Model_Complete` **không phải firmware Patient Node cuối cùng**. Patient Node
được phát triển tiếp từ lõi này và bổ sung Quality Gate, state machine CHECK /
MONITOR, kiểm tra micro, MAX30102, OLED, nút bấm, quản lý nguồn, đóng gói packet
và truyền ESP-NOW bảo mật. Vì vậy việc Phase 3 không có `Quality_Check.cpp` là
đúng phạm vi, không có nghĩa Patient Node bỏ qua Quality Gate.

Các chế độ kiểm tra, tensor mẫu, âm thanh mẫu và log đối chiếu vẫn được giữ ở
`2_Test_Model_LiveMic`, không đưa vào bản này.

Luồng chạy cố định:

1. INMP441 lấy mẫu ở 16 kHz.
2. Bỏ 100 khối đầu sau khi khởi động.
3. Duy trì ring buffer chứa 1 giây âm thanh gần nhất để truy hồi onset.
4. Chunk active đầu tiên được đánh dấu là candidate onset; chỉ xác nhận khi
   4 chunk liên tiếp có năng lượng lớn hơn 75 (khoảng 64 ms).
5. Khi xác nhận, lấy audio từ candidate onset trong ring rồi thu tiếp đến đủ
   đúng 5 giây tính từ onset; không đưa toàn bộ 1 giây lịch sử vào model.
6. Lọc, không pre-emphasis, tạo Mel-Spectrogram 40 x 129 với FFT 2048 và đổi về dB trong khoảng -80 đến 0.
7. Chuẩn hóa về 0 đến 1, lượng tử INT8 và chạy mô hình.
8. Kết luận sau ba lần đo.

Quy ước đầu ra:

- Lớp 0: phát hiện mẫu Asthma.
- Lớp 1: không phát hiện mẫu Asthma.
- Ngưỡng ba trạng thái đã chốt cho C4: `p_non_asthma <= 0,47` là Asthma,
  `p_non_asthma >= 0,77` là Non-Asthma, khoảng giữa là Unsure.
- Mốc `0,50` chỉ là baseline nhị phân dùng trong báo cáo model, không phải luật
  quyết định của Patient Node cuối.
- Serial Monitor in `raw`, `p_non_asthma`, phần trăm hai lớp và kết luận.
- Mỗi cửa sổ 5 giây in thống kê PCM: `min`, `max`, `mean`, `std` và `rms`.
- Sau 3 vote in thống kê độ ổn định của `p_non_asthma`: `min`, `max`, `mean`
  và `std`.

Đây là công cụ hỗ trợ sàng lọc âm thanh, không thay thế chẩn đoán của bác sĩ.

## Model triển khai đã chốt

- Phiên bản: **combo_pre0_mel40_fft2048__V1__s44 / QAT INT8**.
- Header duy nhất: `include/Model_AI/Asthma_Model.h`.
- Symbol: `model_data` và `model_data_len`.
- Mảng model dùng `__attribute__((aligned(4)))`.
- Các header model V1/V5 lịch sử đã được loại bỏ khỏi bản Complete.
