# Backend MQTT của Dashboard Qt6

## Luồng dữ liệu

```text
HiveMQ topic
    -> MqttBackend
    -> kiểm tra JSON Complete Packet
    -> DashboardData
    -> QML bindings
```

Frontend không tự tạo dữ liệu ngẫu nhiên. Biểu đồ và các thẻ thông tin chỉ cập nhật
khi nhận được JSON hợp lệ từ topic MQTT.

## Cấu hình MQTT

Sửa `config/mqtt_config.json`, chủ yếu là trường `password`, rồi chạy lại CMake/build.
File cục bộ này bị Git bỏ qua để tránh đẩy mật khẩu lên kho mã. Trên máy mới, copy
`mqtt_config.example.json` thành `mqtt_config.json` rồi điền thông tin. CMake sẽ copy
cấu hình ra cạnh `appDashboard_Qt6.exe`.

Có thể ghi đè mà không sửa file bằng các biến môi trường:

- `NCKH_MQTT_HOST`
- `NCKH_MQTT_PORT`
- `NCKH_MQTT_USERNAME`
- `NCKH_MQTT_PASSWORD`
- `NCKH_MQTT_TOPIC`

## OpenStreetMap

Trang Location dùng trực tiếp `Qt Location`, `Qt Positioning` và plugin `osm` để hiển thị
OpenStreetMap. Cách này không cần Google Maps API key và không cần Qt WebEngine, nhưng máy
chạy dashboard vẫn cần Internet để tải các mảnh bản đồ. Qt tự lưu bộ nhớ đệm cho các mảnh
đã tải.

Tọa độ đầu vào phải là độ thập phân có dấu (`latitude`, `longitude`). Driver NEO-M8N đã
đổi từ NMEA `ddmm.mmmm`/`dddmm.mmmm` sang dạng này nên Qt không đổi đơn vị thêm lần nữa.

Khi GPS hiện tại không hợp lệ, dashboard giữ vị trí hợp lệ gần nhất và không đưa tọa độ
`0,0` lên bản đồ. Người dùng có thể kéo, phóng to/thu nhỏ hoặc nhấn nút đưa bản đồ về vị
trí Gateway mới nhất.

Yêu cầu khi build:

- Qt 6 có module `Location` và `Positioning` đúng phiên bản/đúng bộ biên dịch của Kit.
- CMake liên kết `Qt6::Location` và `Qt6::Positioning`.
- Máy chạy ứng dụng có plugin OSM và kết nối HTTPS hoạt động.

## Quy tắc xử lý

- Schema chính từ Gateway: `schema_version = 1`, `message_type = complete_packet`,
  object `gate` và `patient_event`.
- Dashboard chỉ nhận schema chính thức: `schema_version = 1`,
  `message_type = complete_packet`, object `gate` và `patient_event`.
- `event_id` được dùng để tránh cộng lặp cùng một Patient Event khi Gateway gửi lại
  sau lỗi MQTT.
- Tự kết nối lại sau 5 giây nếu mất MQTT.
- `has_patient_event = false`: `patient_event` phải là `null`; chỉ cập nhật Gateway
  và không xóa Patient Event gần nhất mà Qt6 đang giữ.
- Trường cảm biến chỉ được dùng khi bit tương ứng trong `sensor_valid_mask` hợp lệ.
- `vitals_valid = false`: HR và SpO2 được đánh dấu không hợp lệ.
- Classification: `0 = Asthma-like`, `1 = Non-asthma`, `2 = Unsure`.
- Dữ liệu lịch sử trên biểu đồ giữ tối đa 14 điểm gần nhất.
