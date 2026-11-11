# Tham số lõi audio/TinyML

Các tham số dưới đây mô tả mô-đun hoàn thiện từ `2_Test_Model_LiveMic` trước
khi được tích hợp và mở rộng thành `Final_Project_NCKH/Patient_Node`. Phase 3
không chứa Quality Gate, PPG, packet bảo mật hay toàn bộ state machine của Node.

- Phần cứng: ESP32-S3 N16R8 và INMP441.
- Tần số lấy mẫu: 16.000 Hz.
- Độ dài mỗi lần phân tích: 5 giây.
- Ring lịch sử: 1 giây trong PSRAM; chỉ truy hồi từ candidate onset.
- Ngưỡng phát hiện âm thanh: 75.
- Điều kiện kích hoạt: 4 khối liên tiếp, mỗi khối 256 mẫu.
- Độ trễ xác nhận VAD danh định: khoảng 64 ms; đoạn này được lấy lại từ ring.
- Tensor Arena đang cấp: 192 KiB (196.608 B) trong PSRAM. Phép đo tĩnh của đúng
  model C4 dùng 169.380 B, còn khoảng 27.228 B (~26,6 KiB) dự phòng. Project 1 và 2
  có thể giữ arena 1 MiB để profiling/kiểm chứng; đó không phải cấu hình firmware cuối.
- Đầu vào mô hình: `[1, 40, 129, 1]`, INT8.
- Ngưỡng ba trạng thái trên `p_non_asthma`: LOW=0,47 và HIGH=0,77.
- Số lần bỏ phiếu: 3.

Khi đổi micro, vỏ thiết bị, vị trí đặt hoặc môi trường sử dụng, cần đo lại ngưỡng
phát hiện âm thanh trong dự án `2_Test_Model_LiveMic`; không được tự suy ra ngưỡng
mới chỉ từ kết quả trên tập dữ liệu.
