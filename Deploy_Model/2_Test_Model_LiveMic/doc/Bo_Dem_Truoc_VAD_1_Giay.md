# Bộ đệm 1 giây trước khi VAD kích hoạt

## Mục đích

VAD chỉ xác nhận sự kiện sau khi bốn khối liên tiếp vượt ngưỡng. Trong khoảng
chờ này, tiếng thở hoặc tiếng khò khè có thể đã bắt đầu. Bộ đệm vòng giữ lại
âm thanh ngay trước thời điểm xác nhận để đoạn 5 giây không bị mất phần đầu.

Đây là **pre-trigger buffer**, không phải noise baseline và không thay thế VAD.

## Tham số hiện tại

| Tham số | Giá trị |
|---|---:|
| Sample rate | 16.000 Hz |
| Kích thước khối I2S | 256 mẫu, khoảng 16 ms |
| Warm-up | 100 khối, khoảng 1,6 giây |
| Bộ đệm vòng | 16.000 mẫu PCM16 |
| Dung lượng | 32.000 byte, khoảng 31,25 KiB PSRAM |
| Ngưỡng VAD | Trung bình trị tuyệt đối `> 75` |
| Điều kiện xác nhận | 4 khối liên tiếp, khoảng 64 ms |
| Đoạn sau kích hoạt | 64.000 mẫu, 4 giây |
| Tổng input | 80.000 mẫu, 5 giây |

## Trình tự hoạt động

1. Sau khi khởi tạo, firmware bỏ 100 khối đầu để I2S/micro ổn định.
2. Mỗi khối mới được ghi vào `pre_roll_buffer` trong PSRAM.
3. VAD chưa được xét cho đến khi bộ đệm có đủ 16.000 mẫu hợp lệ.
4. Firmware tính trung bình trị tuyệt đối của 256 mẫu trong khối hiện tại.
5. Bộ đếm VAD tăng khi năng lượng vượt 75 và về 0 khi không đạt ngưỡng.
6. Khi đủ bốn khối liên tiếp, firmware chép bộ đệm vòng sang đầu
   `audio_buffer` theo đúng thứ tự thời gian.
7. Trạng thái `RECORDING` thu thêm 64.000 mẫu để hoàn thành đoạn 5 giây.
8. Sau inference, chỉ số ghi, số mẫu hợp lệ và bộ đếm VAD được làm mới; firmware
   phải tạo lại lịch sử 1 giây trước lượt kế tiếp.

```text
warm-up 1,6 s
  → tích lũy pre-trigger 1 s
  → VAD xác nhận sau 4 khối hoạt động
  → copy 1 s lịch sử
  → thu tiếp 4 s
  → DSP + TinyML
  → reset lịch sử pre-trigger
```

## Chi tiết quan trọng

- Khối dùng để xác nhận VAD đã được ghi vào bộ đệm trước khi kiểm tra ngưỡng;
  vì vậy nó nằm trong phần pre-trigger được sao chép.
- Micro và bộ đệm chạy liên tục khi ở trạng thái lắng nghe, nhưng model chỉ
  chạy sau khi đã có đủ 80.000 mẫu.
- Manual Check của Patient Node cuối thu chủ động đủ 5 giây và không cần
  pre-trigger.
- Giá trị 75 phải được hiệu chuẩn lại nếu thay micro, gain, vị trí lỗ âm hoặc
  enclosure; có thể dùng `RUN_VAD_CALIBRATION_TEST` để thu thống kê nền/tín hiệu.
