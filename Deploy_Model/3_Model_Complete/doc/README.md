# Tham số đã khóa

- Phần cứng: ESP32-S3 N16R8 và INMP441.
- Tần số lấy mẫu: 16.000 Hz.
- Độ dài mỗi lần phân tích: 5 giây.
- Bộ đệm trước kích hoạt: 1 giây trong PSRAM.
- Ngưỡng phát hiện âm thanh: 75.
- Điều kiện kích hoạt: 4 khối liên tiếp, mỗi khối 256 mẫu.
- Tensor Arena: 270 KB trong PSRAM.
- Đầu vào mô hình: `[1, 64, 129, 1]`, INT8.
- Ngưỡng phân lớp: 0,5.
- Số lần bỏ phiếu: 3.

Khi đổi micro, vỏ thiết bị, vị trí đặt hoặc môi trường sử dụng, cần đo lại ngưỡng
phát hiện âm thanh trong dự án `2_Test_Model_LiveMic`; không được tự suy ra ngưỡng
mới chỉ từ kết quả trên tập dữ liệu.
