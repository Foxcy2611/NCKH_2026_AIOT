# Schema MQTT v1 — bản code hiện tại

Nguồn: Gateway/src/gateway_json.cpp; không phải schema revised đã hoàn tất.

| Topic production | Nội dung |
|---|---|
| aiot/2026/patient/event | Latest event dirty + telemetry mới |
| aiot/2026/gateway/telemetry | Telemetry định kỳ, không event |
| aiot/2026/gateway/status | Trạng thái gateway/dirty/revision |
| aiot/2026/alert | Alert phụ best effort |

Environment gateway_synthetic chèn /test sau aiot/2026.
Chu kỳ telemetry 5s, status 30s; event được gửi khi dirty và MQTT sẵn sàng.

## Event / telemetry
- schema_version: integer 1.
- record_id: string gateway_id-boot_id-record_sequence, mỗi phần hex 8 ký tự.
  Retry cùng revision giữ record_id nhưng telemetry có thể mới hơn.
- synthetic: boolean, phản ánh SENSOR_MODE==2; không tự phát hiện Node giả.
- has_patient_event: boolean.
- source: null khi telemetry; khi event có device_id (u32), sequence (u32),
  received_uptime_ms (u64, thời điểm nhận trên Gateway).
- gate: gateway_id, timestamp, time_basis="uptime_ms", operating_mode,
  uplink_type, sensor_valid_mask, temperature, humidity, pressure, tvoc, eco2,
  wifi_connected, wifi_rssi_dbm, lte_registered, lte_rssi_dbm, mqtt_connected,
  latitude, longitude, gps_timestamp.
- patient_event: null khi telemetry; khi event có session_id, timestamp,
  time_basis (unsynced khi timestamp=0, ngược lại node_reported_ms), event_type,
  classification, model_score, audio_quality, vitals_valid, heart_rate, spo2, battery_node.
- transport: wifi/lte/none.

Sensor invalid hoặc nonfinite được serialize null; HR/SpO2 null khi vitals_valid=false.
Temperature °C, humidity %RH, pressure hPa, TVOC ppb, eCO2 ppm.
Gate timestamp là uptime, không được diễn giải thành Unix time hoặc giờ đo Patient.
GPS timestamp khi có giá trị do driver tạo Unix milliseconds; không dùng lẫn time basis.
operating_mode: 0 HOME, 1 OFFLINE, 2 MOBILE (hiện suy từ mạng).
uplink_type: 0 NONE, 1 WIFI, 2 LTE. Mask bits 0 DHT22, 1 BMP280, 2 SGP30, 3 GPS.

## Status
schema_version, message_type=gateway_status, gateway_id, uptime_ms,
wifi_connected, mqtt_connected, wifi_rssi_dbm, lte_enabled, gps_enabled,
node_valid, node_dirty, node_revision, free_heap_bytes, synthetic.

## Alert
schema_version, message_type=patient_alert, alert_type=abnormal_classification,
severity=warning, record_id, gateway_id, source_device_id, source_sequence,
session_id, classification, model_score, event_timestamp, heart_rate, spo2.
Điều kiện hiện tại classification != 0 và model_score >= 0.80.
Alert event_timestamp giữ timestamp từ Node, không tự đảm bảo UTC.

## Quy tắc backend
Luôn cập nhật gate. Chỉ cập nhật patient/history khi has_patient_event=true.
Dedup retry bằng record_id; alert cùng record_id liên kết event, không thêm event thứ hai.
Không xem telemetry là phép đo Patient mới. Ghi received_at UTC phía backend riêng.
MQTT publish Wi-Fi QoS0 không bảo đảm backend đã nhận/lưu dù dirty đã về false.
Latest-state cố ý không gửi bù các Event đã bị ghi đè khi offline.
