# Tích hợp Gateway latest-state RAM và MQTT

Gateway trong repo còn luồng task/queue cũ, không khớp yêu cầu chỉ giữ Patient Event
mới nhất khi mất mạng. PR thay Gateway bằng bản Gateway(5) đã build và test trên board.

## Thay đổi
- Callback -> raw RX queue -> AES-GCM/dedup -> current_node RAM -> secure ACK.
- current_gate cập nhật định kỳ, CompleteRecord chỉ dựng khi publish.
- Revision bảo vệ dirty của Event mới khi lần gửi trước hoàn tất.
- Wi-Fi MQTT JSON, telemetry/status định kỳ và alert best effort.
- Xóa các source task/network cũ bị thay thế; không chép đè để lại implementation trùng.
- Kèm README, schema v1, bảng đối chiếu revised, kiểm tra header chung và kết quả test.
- Giữ toàn bộ source/config của bản Gateway(5), gồm cấu hình mạng và khóa của nhóm.
- Dependency Gateway: espressif32@6.10.0, Arduino, PubSubClient@2.8; sensor drivers
  và LTE adapter đi kèm được liệt kê trong CHANGED_FILES.md.

## Kiểm tra
Người dùng đã build/nạp Gateway(5), test gửi event, duplicate và mất Wi-Fi -> chỉ gửi
latest khi kết nối lại. Native record/JSON/Wi-Fi mock chạy lại PASS.
Chưa build PlatformIO trong môi trường đóng gói; build tại repo trên máy trước push.

## Phạm vi còn lại
Không tuyên bố hoàn tất toàn bộ revised. Giữ wire 24/24/64 khớp Node hiện tại;
Docs revised ghi 16/16/56 cần M1/M4 chuyển đồng thời. LTE chưa test phần cứng,
failover khi Wi-Fi còn connected nhưng mất broker chưa có. Xem REQUIREMENTS.md
cho battery, fusion nhiệt độ, mode policy, TFT và các mục chưa triển khai.
ACK chỉ xác nhận RAM; reset mất latest; MQTT transport success chưa phải backend ACK.
