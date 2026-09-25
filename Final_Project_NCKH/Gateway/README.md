# Bản MQTT một topic

Xem HUONG_DAN_ONE_TOPIC.md và test/native/dashboard_example.json. Publisher dùng schema 2 tại aiot/2026/gateway/data (test mode: aiot/2026/test/gateway/data).

# Gateway — latest-state RAM

Bản firmware từ Gateway(5), đã được người dùng build và test Wi-Fi/HiveMQ/latest.
Source và cấu hình giữ nguyên bản đã test. Đọc hướng dẫn bàn giao tại
[Docs_Member/M4_Latest_State](../../Docs_Member/M4_Latest_State/README.md).

Mở thư mục này với PlatformIO, chọn gateway_synthetic để tái hiện bài test
(sensor giả, topic aiot/2026/test/...). esp32dev mặc định không sensor, publish null;
gateway_hardware dùng driver thật. Monitor 115200, ESP-NOW channel 6.

Chạy host tests: `python test/native/run_tests.py`.
Kiểm tra header chung trong repo: `python tools/check_shared_protocol.py`.
LTE và phần cứng sensor/GPS chưa được kiểm thử trong bản bàn giao này.
Wire đã đồng bộ Patient_Node: payload/response/packet = 16/16/56 byte.
Node không gửi timestamp; JSON patient_event.timestamp và event_timestamp của alert là null.
source.received_uptime_ms vẫn lưu thời điểm Gateway nhận gói.
