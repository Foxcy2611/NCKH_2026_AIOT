# M4 — Bàn giao Gateway latest-state

Bản tích hợp ngày 2026-09-21, lấy Gateway(5).zip làm firmware đã test trên board.
Gateway_old.zip chỉ là mốc so sánh trước chuyển kiến trúc. Repo nền là
NCKH_2026_AIOT-1(2).zip; Gateway trong repo nền khác Gateway_old.

## Phạm vi bản PR
Thay thế Final_Project_NCKH/Gateway bằng bản latest-state đang hoạt động.
Giữ byte của toàn bộ source, header, platformio.ini và cấu hình từ Gateway(5).
Không sửa Patient_Node, các project thử nghiệm hay Docs_NCKH đã chốt của nhóm.
Cấu hình Wi-Fi/HiveMQ/khóa AES giữ nguyên theo yêu cầu chủ bản bàn giao.
Đây là PR tích hợp latest-state đã kiểm thử, chưa phải hoàn tất mọi tính năng revised.

## Kiến trúc
- Callback ESP-NOW chỉ chép MAC + packet vào raw RX queue ngắn hạn.
- TaskEspNow kiểm header/MAC, AES-GCM và payload; chống trùng/replay trong RAM.
- Event mới ghi đè current_node dưới mutex, tăng revision, đặt dirty; sau đó ACK.
- TaskSensor cập nhật EnvironmentSnapshot; TaskGatewayManager cập nhật current_gate.
- TaskConnManager quản lý trạng thái Wi-Fi/LTE; TaskMqttPublisher lấy snapshot,
  làm mới telemetry rồi dựng JSON cho mỗi lần thử gửi. Không giữ CompleteRecord backlog.
- Publish thành công chỉ xóa dirty nếu revision gửi vẫn là revision hiện tại.
- Reset mất latest, binding học được và lịch sử chống trùng trong RAM.
- ACK_ACCEPTED là Gateway nhận vào RAM; không phải xác nhận cloud/database.
- MQTT Wi-Fi publish QoS0: transport_send_ok không phải ACK lưu dữ liệu backend.
- Alert phụ best effort; backend có thể suy ra alert từ patient/event.

## Build và cấu hình
Mở Final_Project_NCKH/Gateway trong VSCode/PlatformIO. Baud 115200.
Platform espressif32@6.10.0, Arduino, PubSubClient@2.8.

| Environment | Sensor | Topic |
|---|---|---|
| esp32dev (mặc định) | Không có sensor, giá trị null | aiot/2026/... |
| gateway_synthetic | Giả lập môi trường | aiot/2026/test/... |
| gateway_hardware | DHT22/BMP280/SGP30 | aiot/2026/... |
| gateway_hardware_gps | Sensor + GPS | aiot/2026/... |
| gateway_wdt_test | Cố ý ngừng feed watchdog | Chỉ dùng kiểm thử reset |

Gateway đã test có MAC STA D4:E9:F4:E7:37:20, channel 6.
Config: include/Config/gateway_config.h và gateway_network_config.h.
LTE_ENABLED hiện vẫn là 1 trong file được cung cấp, dù không có LTE để test.
Nếu muốn bench Wi-Fi bỏ bước khởi tạo modem, đặt GATEWAY_LTE_ENABLED=0 rồi build/nạp lại.
Bản này không tự thay lựa chọn đó trong cấu hình đã test.

| Thiết bị | Chân mặc định |
|---|---|
| I2C SDA/SCL | 21 / 22 |
| DHT22 DATA | 25 |
| LTE RX/TX | 16 / 17, 115200 baud |
| GPS RX/TX | 16 / 17, 9600 baud |

GPS và LTE đang trùng chân 16/17: phải remap một UART trước khi bật cả hai phần cứng.
TLS đang dùng chế độ test insecure; giữ nguyên cấu hình đầu vào, không xác thực CA.

## Ghép Patient Node thật của nhóm
Header include/Secure_Protocol.h giống nguyên byte Patient_Node/shared/Secure_Protocol.h.
Hai khóa AES trong Patient_Node/src/EspNow_Client.cpp cũng khớp Gateway.
Tuy nhiên Patient Node của repo đang target MAC 02:00:00:00:00:01 và peer.channel=0.
Trước khi ghép board Gateway này:
- Đổi GATEWAY_MAC phía Node thành D4:E9:F4:E7:37:20.
- Cấu hình radio Node cùng channel 6; peer.channel=0 chỉ dùng channel radio hiện tại,
  không tự tìm channel của Gateway. Không chỉ đổi peer.channel mà bỏ qua radio.
- Đồng bộ channel router 2.4 GHz/Gateway/Node và reset Gateway nếu đổi Node trong chế độ học MAC.
Không sửa code Node của M1 trong PR M4 này. Chưa xác nhận end-to-end với Node thật.

Xem SCHEMA.md, REQUIREMENTS.md, VALIDATION.md và CHANGED_FILES.md.
