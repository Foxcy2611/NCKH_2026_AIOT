# SpO2 gần nhất, giữ cấu trúc JSON cũ

SpO2 không phụ thuộc vitals_valid nữa. Sau xác thực AES-GCM, kiểm tra nguồn,
cấu trúc và chống replay, Gateway xét riêng giá trị spo2:
- 1…100: cập nhật latest_spo2, dù vitals_valid bằng 0 hay 1.
- 0 hoặc 101…255: giữ nguyên cache. Payload uint8_t không chứa chuỗi NA.
- Chưa từng có số đo hợp lệ: JSON là null.
- Cache nằm trong RAM, giữ qua publish/mất MQTT, reset khi Gateway khởi động lại.
Ví dụ 98 → 0 → 255 → 97 cho đầu ra 98 → 98 → 98 → 97, kể cả cờ false.

## MQTT và dashboard
Không thêm key MQTT. Đã bỏ key cấp gốc latest_spo2 của bản trước.
patient_event.spo2 luôn lấy cache, không kiểm tra vitals_valid.
vitals_valid vẫn gửi nguyên trạng; heart_rate vẫn null khi cờ false.
JSON alert và TFT cũng dùng cache SpO2. Raw Node event được giữ nguyên trong RAM.

Giữ chính sách cũ: telemetry không có event mới vẫn có patient_event = null.
Trong loại packet đó không có trường SpO2 riêng. Không gửi lại event đã publish.
Topic, schema_version, tên/kiểu trường và giao thức ESP-NOW 16/56 byte giữ nguyên.
Cache thêm vào struct chỉ dùng nội bộ Gateway, cho Node được liên kết hiện tại.
Giá trị cache có thể cũ, không phải phép đo mới tại timestamp event hiện tại.

Nếu MQTT-to-dashboard dùng vitals_valid để ẩn SpO2, bên đó vẫn cần bỏ điều kiện
này cho riêng SpO2 và đọc patient_event.spo2 trực tiếp. Gateway không thể thay
đổi điều kiện trong mã dashboard. Khi patient_event = null, giữ số đang hiển thị.

## Kiểm thử
Chạy python test/native/run_tests.py và python test/native/run_dashboard_tests.py
(cần g++ trong PATH). Đã đạt kiểm thử host: cache, cờ false với HR khác 0,
NA/ngoài miền, payload validation, JSON/dashboard, buffer, revision, Wi-Fi mock.
Mutex giả lập trên host. Chưa kiểm thử ESP32/MQTT thật.
Build firmware trước đó bị chặn do quyền ghi cache PlatformIO của môi trường.
ZIP chỉ chứa source; chạy pio run -e esp32dev trên máy phát triển để build/nạp.
