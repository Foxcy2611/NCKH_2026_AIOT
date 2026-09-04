# 3_Model_Complete

Đây là bản triển khai gọn để ghép vào hệ thống IoT chính. Các chế độ kiểm tra,
tensor mẫu, âm thanh mẫu và log đối chiếu được giữ ở dự án
`2_Test_Model_LiveMic`, không đưa vào bản này.

Luồng chạy cố định:

1. INMP441 lấy mẫu ở 16 kHz.
2. Bỏ 100 khối đầu sau khi khởi động.
3. Duy trì bộ đệm vòng chứa 1 giây âm thanh gần nhất.
4. Chỉ kích hoạt khi 4 khối liên tiếp có năng lượng lớn hơn 75.
5. Ghép 1 giây đã giữ với 4 giây thu tiếp theo.
6. Lọc, tạo Mel-Spectrogram 64 x 129 và đổi về dB trong khoảng -80 đến 0.
7. Chuẩn hóa về 0 đến 1, lượng tử INT8 và chạy mô hình.
8. Kết luận sau ba lần đo.

Quy ước đầu ra:

- Lớp 0: phát hiện mẫu Asthma.
- Lớp 1: không phát hiện mẫu Asthma.
- Ngưỡng mô hình: 0,5.

Đây là công cụ hỗ trợ sàng lọc âm thanh, không thay thế chẩn đoán của bác sĩ.
