# Triển khai TinyML trên ESP32-S3

Thư mục được chốt thành ba dự án độc lập:

## 1_Test_Model_Static_Profiling

Gộp hai bước thử model tĩnh và đo tài nguyên. Dùng để kiểm tra TFLite Micro,
Tensor Arena, thời gian suy luận, RAM và bộ nhớ chương trình mà không cần micro.
Đây là dự án nền tảng, không phải firmware dùng cuối.

## 2_Test_Model_LiveMic

Bản nghiên cứu và kiểm chứng đầy đủ. Dự án giữ:

- Tiền xử lý C++ tương ứng pipeline Python.
- INMP441, VAD, bộ đệm trước kích hoạt 1 giây và bỏ phiếu ba lần.
- Mẫu PCM16 đối chiếu Python–C++.
- 108 tensor validation và 113 tensor test.
- Chế độ đo năng lượng để hiệu chỉnh VAD khi phần cứng hoặc môi trường đổi.

Tài liệu kỹ thuật nằm tại [doc](./2_Test_Model_LiveMic/doc/README.md).

## 3_Model_Complete

Bản gọn để ghép vào hệ thống IoT. Chỉ giữ đường chạy thật từ micro đến kết quả,
không chứa dữ liệu thử, nhánh kiểm tensor, hiệu chuẩn hay log lịch sử.

Các tham số hiện tại đã khóa: 16 kHz, 5 giây, Mel 64 x 129, dB từ -80 đến 0,
ngưỡng model 0,5, VAD 75 với 4 khối liên tiếp, bộ đệm trước kích hoạt 1 giây và
Tensor Arena 270 KB trong PSRAM.

Hệ thống chỉ hỗ trợ sàng lọc mẫu âm thanh; không thay thế chẩn đoán y khoa.
