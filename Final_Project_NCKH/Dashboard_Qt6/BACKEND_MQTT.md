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

## Quy tắc xử lý

- Chỉ nhận `schema_version = 1` và `message_type = complete_packet`.
- Tự kết nối lại sau 5 giây nếu mất MQTT.
- `has_patient_event = false`: chỉ cập nhật Gateway, không xóa Patient Event gần nhất.
- Trường cảm biến chỉ được dùng khi bit tương ứng trong `sensor_valid_mask` hợp lệ.
- `vitals_valid = false`: HR và SpO2 được đánh dấu không hợp lệ.
- Classification: `0 = Asthma-like`, `1 = Non-asthma`, `2 = Unsure`.
- Dữ liệu lịch sử trên biểu đồ giữ tối đa 14 điểm gần nhất.
