# Test Complete Packet -> JSON -> MQTT -> Qt6

Project này giả lập phần cuối của Gateway:

```text
Complete_Packet_t -> JSON -> MQTT broker -> Qt6 Dashboard
```

## Chuẩn bị

Mở `include/test_config.h` và sửa:

- `TEST_WIFI_SSID`
- `TEST_WIFI_PASSWORD`
- thông tin MQTT nếu Gateway đổi broker

Topic mặc định:

```text
nckh/aiot2026/complete_packet
```

## Dữ liệu mô phỏng

Nếu tự động gửi đang bật, cứ 5 giây project gửi lần lượt:

1. Chỉ có dữ liệu Gateway (`has_patient_event = false`).
2. Patient Event `ASTHMA` (`classification = 0`).
3. Patient Event `NON-ASTHMA` (`classification = 1`).
4. Patient Event `UNSURE` (`classification = 2`).

Trường `synthetic = true` trong JSON xác nhận đây là dữ liệu giả lập, không phải dữ liệu bệnh nhân thật.

Các số đo môi trường, GPS, pin, model score, HR và SpO₂ được sinh ngẫu nhiên
trong khoảng hợp lý. `gateway_id`, quy ước classification, trạng thái kết nối thật
và timestamp không được sinh ngẫu nhiên vì chúng mang ý nghĩa định danh/trạng thái.

Có thể điều khiển từ Serial Monitor:

- `a`: gửi ASTHMA.
- `n`: gửi NON-ASTHMA.
- `u`: gửi UNSURE.
- `g`: gửi Gateway-only.
- `t`: bật/tắt tự động gửi.

## Quy tắc JSON

- `Complete_Packet_t` chỉ là cấu trúc nội bộ, không gửi raw binary lên MQTT.
- Khi `has_patient_event = false`, trường `node` trong JSON bằng `null`.
- Khi `vitals_valid = false`, `heart_rate` và `spo2` bằng `null`.
- Cảm biến không hợp lệ theo `sensor_valid_mask` được gửi bằng `null`.
- Timestamp của bản test là `millis()` nên JSON ghi rõ `timestamp_basis = "uptime_ms"`.

## Lưu ý Qt6

Project này hoàn thiện phía phát. Dashboard Qt6 hiện vẫn dùng dữ liệu giả trực tiếp trong QML, vì vậy cần bổ sung phần subscribe topic MQTT và phân tích JSON trước khi giao diện tự cập nhật từ broker.
