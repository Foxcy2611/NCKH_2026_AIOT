# Gateway MQTT một topic — hướng dẫn Qt6

## Topic và lịch gửi
- Dữ liệu thật: aiot/2026/gateway/data
- Chế độ gateway_synthetic: aiot/2026/test/gateway/data
- Mỗi chế độ chỉ gửi một topic. Publisher không còn gửi telemetry, patient/event, status, alert riêng.
- Gửi Complete Packet khi kết nối MQTT lại, khi có Node dirty và định kỳ 5 giây tính từ lần gửi thành công gần nhất. Cần có snapshot Gateway hợp lệ. Thất bại sẽ thử lại theo GATEWAY_MQTT_RETRY_MS.
- ESP-NOW vẫn dùng giao thức 16/16/56 byte đã sửa trước đó.

## Áp dụng bản vá (khuyên dùng cho dự án đang chạy)
1. Sao lưu dự án hiện tại.
2. Giải nén Gateway_OneTopic_Patch.zip, chép include và src vào dự án, thay thế các tệp cùng tên.
3. Trong include/Config/gateway_config.h, bảo đảm SECURE_ESPNOW_PACKET_SIZE là 56. Giữ cấu hình Wi-Fi, MQTT, chân phần cứng, MAC và kênh đang hoạt động. Bản vá không chép đè gateway_config.h hoặc gateway_network_config.h.
4. Build rồi Upload Gateway. Không cần sửa Patient Node vì thay đổi này chỉ ở MQTT Gateway.
5. Qt6 subscribe aiot/2026/gateway/data; khi thử cảm biến giả subscribe topic test tương ứng.

Bản đầy đủ Gateway_OneTopic_Full.zip xuất phát từ Gateway.rar, nên các cấu hình mạng/kênh vẫn theo bản RAR. Đối chiếu trước khi dùng: Gateway.rar có kênh 10, Patient_Node.rar có kênh 6. Giữ router, Gateway và Node cùng kênh theo cấu hình thực tế.

## Cấu trúc JSON đã triển khai
Đây là `schema_version=1`, `message_type=complete_packet`. Giữ tên `gate` và
`patient_event`; không dùng các tên `gateway`/`environment`/`patient` trong ví dụ
thiết kế sơ bộ trước đó.

| Đường dẫn | Dùng cho Qt6 |
|---|---|
| record_id | ID snapshot, thay đổi theo mỗi lần thử gửi; không dùng chống trùng sự kiện Node |
| event_id | ID sự kiện Node theo device/session/sequence, giữ nguyên khi retry; null khi Complete Packet không đính kèm Node |
| patient_age_ms | Tuổi sự kiện tính từ lúc Gateway nhận, không phải tuổi phép đo ở Node; null khi không đính kèm Node hoặc thời gian không hợp lệ |
| synthetic | Phân biệt dữ liệu thử |
| has_patient_event | Lần publish này có đính kèm Node Event mới/chưa publish thành công; bằng false thì `patient_event=null` |
| source.device_id, sequence | Định danh và số thứ tự gói Node |
| source.received_uptime_ms | Thời điểm Gateway nhận theo uptime, không phải UTC |
| gate.temperature, humidity, pressure | Nhiệt độ °C, độ ẩm %, áp suất hPa |
| gate.eco2, tvoc | eCO2 ppm, TVOC ppb |
| gate.latitude, longitude, gps_timestamp | GPS, thời gian Unix mili giây nếu có |
| gate.sensor_valid_mask | Bit 1 DHT22, 2 BMP280, 4 SGP30, 8 GPS |
| gate.timestamp, time_basis | Thời gian snapshot theo uptime_ms, không phải UTC |
| gate.wifi_connected, wifi_rssi_dbm | Kết nối/cường độ Wi-Fi |
| gate.lte_registered, lte_rssi_dbm | Trạng thái LTE từ lte_connected và cường độ |
| gate.mqtt_connected, uplink_type, operating_mode | MQTT; uplink 0 none/1 Wi-Fi/2 LTE; mode 0 HOME/1 OFFLINE/2 MOBILE |
| transport | wifi hoặc lte của bản tin |
| patient_event.heart_rate, spo2 | BPM và SpO2 %, null khi vitals_valid=false |
| patient_event.battery_node | Pin Node % |
| patient_event.classification, model_score | Mã phân loại và điểm tin cậy AI |
| patient_event.session_id, event_type, audio_quality, vitals_valid | Thông tin sự kiện Node |
| patient_event.timestamp, time_basis | null và unsynced, vì Node không truyền timestamp |
| status | Trạng thái hệ thống: gateway_id, uptime_ms, wifi_connected, mqtt_connected, wifi_rssi_dbm, lte_enabled, gps_enabled, node_valid, node_dirty, node_revision, free_heap_bytes, synthetic |
| alert.active | Kết quả cảnh báo của sự kiện gần nhất: classification != 0 và model_score >= 0.80 |
| alert.event_id | ID sự kiện tạo cảnh báo; null khi không cảnh báo |
| alert.severity, alert_type | warning / abnormal_classification khi active, ngược lại null |

## Quy tắc dashboard
- Cập nhật thẻ trạng thái và môi trường mỗi snapshot.
- Chỉ thêm một bản ghi bệnh nhân hoặc phát thông báo khi `event_id` mới. Cùng
  `event_id` là retry và không được ghi lặp.
- `alert.active` chỉ có ý nghĩa trong Complete Packet đang đính kèm Patient Event;
  Qt6 tự giữ kết quả gần nhất khi các packet định kỳ sau có `has_patient_event=false`.
- null là chưa có/không hợp lệ, không chuyển thành 0.
- node_valid là đã có dữ liệu, không phải bằng chứng Node đang online. node_dirty là trạng thái trước lần gửi hiện tại, không phải ACK từ backend.
- Theo dõi thời điểm nhận tại Qt6 để đánh dấu mất kết nối. Bản tin cũ có mqtt_connected=true không chứng minh Gateway còn online.
- Lưu ngày giờ nhận ở Qt6/backend; uptime không thay thế UTC.
- Chỉ lưu latest-state ở Gateway, không bảo đảm giữ đủ lịch sử sự kiện khi mất mạng. Không có mẫu âm thanh hay sóng RED/IR trong MQTT.
- Bản Wi-Fi vẫn dùng publish không retained; client mở sau sẽ chờ snapshot kế tiếp. Chưa bổ sung LWT.

## Kiểm tra đã chạy
- Build PlatformIO esp32dev SUCCESS.
- Native tests cũ PASS (record, JSON modes 0/2, Wi-Fi).
- Dashboard tests PASS modes 0/2: chưa có Node, Node dirty/clean, giữ event_id, tuổi dữ liệu, ngưỡng alert 0.80, null và giới hạn buffer.
- Bộ đệm dashboard JSON 4096 byte; MQTT Wi-Fi ít nhất 4352 byte.
- Chưa kiểm tra với broker/Qt6 hoặc modem LTE và hai bo thực tế.
