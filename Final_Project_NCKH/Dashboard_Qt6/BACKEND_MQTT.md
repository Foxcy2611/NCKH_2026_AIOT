# Backend MQTT của Dashboard Qt6

## Luồng dữ liệu

```text
HiveMQ topic
    -> MqttBackend
    -> kiểm tra JSON Complete Packet
    -> DashboardData
    -> QML bindings
```

Frontend không còn tự random dữ liệu. Biểu đồ và các thẻ thông tin chỉ cập nhật
khi nhận được JSON hợp lệ từ topic MQTT.

## Cấu hình

Sửa `config/mqtt_config.json`, chủ yếu là trường `password`, rồi chạy lại CMake/build.
File cục bộ này bị Git bỏ qua để tránh đẩy mật khẩu lên kho mã. Trên máy mới,
copy `mqtt_config.example.json` thành `mqtt_config.json` rồi điền thông tin.
CMake sẽ copy cấu hình ra cạnh `appDashboard_Qt6.exe`.

Có thể ghi đè mà không sửa file bằng các biến môi trường:

- `NCKH_MQTT_HOST`
- `NCKH_MQTT_PORT`
- `NCKH_MQTT_USERNAME`
- `NCKH_MQTT_PASSWORD`
- `NCKH_MQTT_TOPIC`

## Google Maps

Trang Location hiển thị bản đồ thật bằng Google Maps Static API. Tọa độ đầu vào phải là
độ thập phân có dấu (`latitude`, `longitude`); driver NEO-M8N đã đổi từ NMEA
`ddmm.mmmm`/`dddmm.mmmm` sang định dạng này nên Qt không cần đổi thêm.

Trước khi chạy dashboard, đặt biến môi trường `NCKH_GOOGLE_MAPS_API_KEY` bằng khóa của
Google Cloud đã bật Maps Static API. Không ghi khóa trực tiếp vào source. Nếu chưa có khóa,
dashboard vẫn hiện tọa độ và cho phép bấm vùng bản đồ để mở vị trí bằng Google Maps trên
trình duyệt.

Khi GPS hiện tại không hợp lệ, dashboard giữ lại vị trí hợp lệ gần nhất và không đưa tọa độ
`0,0` lên bản đồ.

## Quy tắc xử lý

- Schema chính từ Gateway: `schema_version = 2`, `message_type = dashboard_snapshot`,
  object `gate` và `patient_event`.
- Vẫn nhận schema thử nghiệm cũ: `schema_version = 1`,
  `message_type = complete_packet`, object `gateway` và `node`.
- Với schema 2, `event_id` được dùng để tránh cộng lặp cùng một Patient Event vào
  lịch sử mỗi lần Gateway gửi snapshot định kỳ 5 giây.
- Tự kết nối lại sau 5 giây nếu mất MQTT.
- `has_patient_event = false`: chỉ cập nhật Gateway, không xóa Patient Event gần nhất.
- Trường cảm biến chỉ được dùng khi bit tương ứng trong `sensor_valid_mask` hợp lệ.
- `vitals_valid = false`: HR và SpO2 được đánh dấu không hợp lệ.
- Classification: `0 = Asthma-like`, `1 = Non-asthma`, `2 = Unsure`.
- Dữ liệu lịch sử trên biểu đồ giữ tối đa 14 điểm gần nhất.
