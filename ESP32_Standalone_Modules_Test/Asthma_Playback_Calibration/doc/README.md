# Tham số đã khóa

- Phần cứng: ESP32-S3 N16R8 và INMP441.
- Tần số lấy mẫu: 16.000 Hz.
- Độ dài mỗi lần phân tích: 5 giây.
- Ring lịch sử: 1 giây trong PSRAM; chỉ truy hồi từ candidate onset.
- Ngưỡng phát hiện âm thanh: 75.
- Điều kiện kích hoạt: 4 khối liên tiếp, mỗi khối 256 mẫu.
- Độ trễ xác nhận VAD danh định: khoảng 64 ms; đoạn này được lấy lại từ ring.
- Tensor Arena: 280 KiB trong PSRAM.
- Đầu vào mô hình: `[1, 40, 129, 1]`, INT8.
- Ngưỡng ba trạng thái trên `p_non_asthma`: LOW=0,20 và HIGH=0,95.
- Số lần bỏ phiếu: 3.

Khi đổi micro, vỏ thiết bị, vị trí đặt hoặc môi trường sử dụng, cần đo lại ngưỡng
phát hiện âm thanh trong dự án `2_Test_Model_LiveMic`; không được tự suy ra ngưỡng
mới chỉ từ kết quả trên tập dữ liệu.
