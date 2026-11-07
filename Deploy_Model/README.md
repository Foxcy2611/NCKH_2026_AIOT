# Triển khai TinyML trên ESP32-S3

Thư mục gồm ba dự án kiểm chứng liên tiếp, hiện cùng dùng model cuối
`combo_pre0_mel40_fft2048__V1__s44 / QAT_INT8` (C4 V1 s44):

## 1_Test_Model_Static_Profiling

Gộp hai bước thử model tĩnh và đo tài nguyên. Dùng để kiểm tra TFLite Micro,
Tensor Arena, thời gian suy luận, RAM và bộ nhớ chương trình mà không cần micro.
Đây là dự án nền tảng, không phải firmware dùng cuối.

## 2_Test_Model_LiveMic

Bản nghiên cứu và kiểm chứng đầy đủ. Dự án giữ:

- Tiền xử lý C++ tương ứng pipeline Python.
- INMP441, VAD, bộ đệm trước kích hoạt 1 giây và bỏ phiếu ba lần.
- Mẫu PCM16 đối chiếu Python–C++.
- 12 mẫu PCM16 cố định được sinh từ cùng manifest Phase 4.
- Chế độ đo năng lượng để hiệu chỉnh VAD khi phần cứng hoặc môi trường đổi.

Tài liệu kỹ thuật nằm tại [Tài liệu kĩ thuật](./2_Test_Model_LiveMic/doc/README.md).

## 3_Model_Complete

Bản gọn để ghép vào hệ thống IoT. Chỉ giữ đường chạy thật từ micro đến kết quả,
không chứa dữ liệu thử, nhánh kiểm tensor, hiệu chuẩn hay log lịch sử.

Các tham số hiện tại: 16 kHz, 5 giây, FFT 2048, Mel 40 x 129,
không pre-emphasis, dB từ -80 đến 0,
VAD 75 với 4 khối liên tiếp, bộ đệm trước kích hoạt 1 giây và Tensor Arena
280 KiB trong PSRAM. Ngưỡng phân loại phải lấy từ bước Classification Threshold.

Hệ thống chỉ hỗ trợ sàng lọc mẫu âm thanh; không thay thế chẩn đoán y khoa.
