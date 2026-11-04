# Latest DHT22

Biến `latestDht22` trong TaskSensor giữ một cặp nhiệt độ/độ ẩm gần nhất.
Khởi động: cả hai giá trị NAN, valid=false; MQTT xuất null (NA trên dashboard).
Chỉ cập nhật cả cặp khi DHT22_ReadData trả về 0 và cả hai số hữu hạn, trong
miền nhiệt độ -40…80 °C, độ ẩm 0…100 %. Không trộn hai lần đo khác nhau.
Timeout, checksum lỗi, NAN/Infinity hoặc ngoài miền đều giữ nguyên cặp trước.

Snapshot được sao chép dưới khóa như trước. MQTT giữ nguyên JSON cũ:
gate.temperature, gate.humidity, gate.sensor_valid_mask; không thêm key mới.
Bit SENSOR_DHT22_VALID có nghĩa đã có cặp DHT22 sử dụng được trong RAM.
Sau lần đọc hợp lệ đầu tiên, lỗi đọc không xóa bit này, nên dashboard vẫn hiển
thị giá trị đã giữ. Bit không khẳng định lần đọc cảm biến vừa rồi thành công.

DHT22 không bị xóa bởi thời hạn ENV_SNAPSHOT_MAX_AGE_MS, theo yêu cầu luôn gửi
latest. Các cảm biến khác vẫn theo thời hạn cũ. Giá trị được giữ có thể đã cũ;
timestamp packet không phải timestamp của lần đo DHT22 gần nhất.
Cache reset về NA khi Gateway khởi động lại, không lưu NVS.
Mode 0 không đo nên vẫn NA; mode 1 dùng DHT22 thật; mode 2 cập nhật số giả lập.

ZIP bao gồm các thay đổi latest SpO2 trước đó (độc lập vitals_valid, JSON cũ).
Đã chạy đạt test host: DHT22 NA ban đầu, timeout/checksum/giá trị lỗi, cập nhật
cặp mới, giá trị biên, JSON khi snapshot cũ, restart; các test SpO2/JSON/dashboard/
Wi-Fi hiện có cũng đạt. Chưa build/nạp firmware hoặc thử trên ESP32 thật tại
môi trường này. Mở project rồi build/nạp như trước bằng PlatformIO.
