# Gateway tương thích Patient Node 56 byte

Đã đồng bộ nguyên bản Secure_Protocol.h của Patient_Node.rar: payload 16, response 16, packet 56 byte. ACK/NACK bỏ gateway_timestamp và time_valid. Node không truyền timestamp nên JSON patient_event.timestamp và alert.event_timestamp trả null; thời gian nhận vẫn ở source.received_uptime_ms.

## Áp dụng bản vá vào dự án đang chạy (khuyên dùng)
1. Sao lưu dự án Gateway hiện tại.
2. Giải nén Gateway_Patch_56byte.zip rồi chép hai thư mục include và src vào thư mục dự án, đồng ý thay thế các tệp cùng tên.
3. Trong include/Config/gateway_config.h, đổi SECURE_ESPNOW_PACKET_SIZE từ 64 thành 56. Giữ nguyên cấu hình Wi-Fi, kênh và chân phần cứng hiện đang sử dụng. Bản vá không chép đè tệp cấu hình này.
4. Build môi trường đang dùng, Upload vào Gateway, mở monitor 115200. Không cần đổi Patient Node nếu đang dùng đúng bản Patient_Node.rar đã gửi.
5. Sau khi Node gửi sự kiện, kiểm tra Gateway có [RX] ACCEPT, accepted tăng, node_valid=1; Node nhận ACK.

## Bản đầy đủ
Gateway_Fixed_56byte.zip chứa dự án từ Gateway.rar đã sửa, bỏ cache build và cấu hình IDE cũ. Nếu sử dụng bản đầy đủ, cần đối chiếu cấu hình mạng và kênh với dự án đang chạy trước khi nạp: bản RAR Gateway có ESPNOW_CHANNEL=10, bản RAR Patient Node có ESP_NOW_CHANNEL=6. Router, Gateway và Node phải cùng kênh; địa chỉ MAC Gateway trong Node phải đúng bo thực tế. Không thay các giá trị này tùy ý nếu hệ thống hiện đã kết nối.

## Kiểm tra
- Header giao thức giống từng byte với Patient Node.
- Khóa AES hai chiều khớp giữa hai bản RAR.
- Native tests: dữ liệu/độ dài giao thức, JSON chế độ 0 và 2, Wi-Fi mock đều PASS.
- PlatformIO esp32dev: build SUCCESS. Cảnh báo TFT TOUCH_CS có sẵn, không ảnh hưởng bản sửa gói tin.
- Chưa thử truyền ACK/NACK trên hai bo vật lý.
