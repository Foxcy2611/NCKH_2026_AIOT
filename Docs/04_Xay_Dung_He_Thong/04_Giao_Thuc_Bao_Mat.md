# Hợp đồng Node - Gateway - Dashboard và bảo mật

[Trang chủ tài liệu](../README.md)

## Mục lục

- [1. Ba tầng dữ liệu](#muc-1)
- [2. Node payload 16 byte](#muc-2)
- [3. Secure packet 56 byte](#muc-3)
- [4. Gateway response và retry](#muc-4)
- [5. Metadata và chống replay](#muc-5)
- [6. Hợp đồng JSON và giá trị thiếu](#muc-6)
- [7. Nguyên tắc khi thay đổi giao thức](#muc-7)

<a id="muc-1"></a>

## 1. Ba tầng dữ liệu

| Tầng | Nội dung | Kích thước/định dạng |
|---|---|---|
| Kết quả phiên Node | Session, loại sự kiện, AI, quality, sinh hiệu | Plaintext packed 16 byte |
| Truyền Node ↔ Gateway | Header, nonce, ciphertext, tag xác thực | Secure packet 56 byte |
| Gateway → MQTT → Dashboard | Patient event tùy chọn cùng Gate/sensor/network | JSON `complete_packet`, schema 1 |

Không dùng trực tiếp cấu trúc C++ làm JSON. Gateway giải mã, kiểm tra và ánh xạ field. Không có WAV, FFT hoặc Mel tensor trong packet vô tuyến.

### Chuỗi dữ liệu tích hợp hiện hành

```text
Patient_Session_t
  → Node_Payload_t 16 byte
  → AES-128-GCM / Secure_Packet_t 56 byte
  → ESP-NOW
  → Gateway xác thực tag, chống trùng và giải mã
  → Response_Payload_t 16 byte
  → Secure ACK/NACK qua AES-128-GCM + ESP-NOW
  → Node retry hữu hạn hoặc kết thúc phiên
  → Gateway ghép EnvironmentSnapshot và latest-state
  → complete_packet JSON
  → Wi-Fi hoặc LTE
  → MQTT
  → Dashboard Qt6/QML
```

Raw PCM, Log-Mel và tensor INT8 chỉ tồn tại trong Patient Node. Hai chiều
Node–Gateway dùng cùng vỏ `Secure_Packet_t`; `message_type` xác định ciphertext là
Patient Event hay Gateway Response.

<a id="muc-2"></a>

## 2. Node payload 16 byte

| Offset byte | Trường | Kiểu | Ý nghĩa |
|---:|---|---|---|
| 0 | `session_id` | uint32 | ID phiên |
| 4 | `event_type` | uint8 | Manual=0, Monitor=1, Status=2 |
| 5 | `classification` | uint8 | Asthma=0, Non-Asthma=1, Unsure=2 |
| 6 | `model_score` | float 32 bit | Score theo class/luật vote |
| 10 | `audio_quality` | uint8 | OK=0, yếu=1, lớn/clipping=2, ít hoạt động=3 |
| 11 | `vitals_valid` | uint8 | Phiên có sinh hiệu hợp lệ |
| 12 | `heart_rate` | uint16 | HR; 0 khi không có số đo hợp lệ |
| 14 | `spo2` | uint8 | SpO2; 0 khi không có số đo hợp lệ |
| 15 | `battery_node` | uint8 | Trường pin theo implementation hiện hành |

Nguồn hợp đồng dùng chung: [Secure_Protocol.h](../../Final_Project_NCKH/Patient_Node/shared/Secure_Protocol.h). `packed` và kiểm tra sizeof giúp giữ đúng 16 byte. Node và Gateway cần cùng thứ tự field, enum, kiểu float và cách serialize; bằng kích thước chưa đủ chứng minh tương thích.

Header chỉ dành chỗ cho battery không chứng minh đã có phép đo pin đã hiệu chuẩn. Tương tự, event STATUS được định nghĩa không có nghĩa mọi luồng trạng thái đều đã được triển khai.

### Model score không đồng nhất với p_non

Model sigmoid sinh `p_non_asthma`. Node hiện ánh xạ:

| Kết quả | Score ghi theo inference hiện hành |
|---|---|
| Asthma | `1 - p_non` |
| Non-Asthma | `p_non` |
| Unsure | Giá trị nhánh Unsure đang dùng `1 - p_non`; không phải xác suất của một lớp thứ ba |
| MONITOR có đa số | Trung bình score của các lần thuộc class thắng |
| MONITOR hòa 1/1/1 | Unsure, score 0 |

Vì vậy không đặt nhãn `p_non` cho mọi `model_score` nhận trên Dashboard. Unsure là vùng quyết định hậu xử lý của model nhị phân, không phải neuron softmax thứ ba.

<a id="muc-3"></a>

## 3. Secure packet 56 byte

```text
Header/AAD 12 byte
  magic(2) + version(1) + message_type(1)
  + device_id(4) + sequence(4)
Nonce      12 byte
Ciphertext 16 byte
GCM tag    16 byte
Tổng       56 byte
```

Magic hiện là `0xA57A`, version 1; message type phân biệt patient event và Gateway response. Header được xác thực như AAD: không mã hóa header nhưng sửa header sẽ làm kiểm tra tag thất bại.

AES-128-GCM dùng key theo hướng truyền và nonce ngẫu nhiên. Tài liệu không sao chép khóa thật. Điều kiện quan trọng của GCM là không tái sử dụng nonce với cùng key cho các plaintext khác nhau. Retry gửi lại nguyên packet đã tạo, không tạo một thông điệp mới với nội dung khác nhưng giữ nonce.

GCM bảo vệ bí mật và tính toàn vẹn payload trên đường Node–Gateway. Nó không tự bảo vệ đoạn MQTT; TLS, credential và cấu hình broker là vấn đề riêng.

<a id="muc-4"></a>

## 4. Gateway response và retry

Response plaintext cũng dài 16 byte:

- Target device ID: 4 byte.
- Session ID: 4 byte.
- Response code: 1 byte.
- Reserved: 7 byte.

Node chỉ chấp nhận phản hồi hợp lệ sau xác thực và đối chiếu với phiên pending. Callback gửi thành công của ESP-NOW chỉ phản ánh tầng radio; cần response của Gateway để kết luận phiên đã được chấp nhận.

Cấu hình hiện có một lần gửi đầu và tối đa 3 lần retry, không phải tổng cộng 3 lần gửi. Timeout callback khoảng 1 s, timeout ACK khoảng 2 s và khoảng cách retry khoảng 1 s. Các mốc này không tạo một deadline tuyệt đối đơn giản bằng 3 s.

| Phản hồi/tình trạng | Xử lý khái quát |
|---|---|
| ACK accepted | Hoàn tất phiên |
| ACK duplicate | Gateway đã có gói; Node cũng hoàn tất |
| NACK busy/internal có thể retry | Lập lịch gửi lại theo giới hạn |
| NACK không hỗ trợ/không thể khắc phục | Kết thúc thất bại theo logic hiện hành |
| Không có ACK/callback lỗi | Retry; hết lượt báo lỗi cuối |

Khi kết thúc thất bại, Node về STANDBY; không có bảo đảm lưu packet lâu dài để gửi lại sau reboot.

<a id="muc-5"></a>

## 5. Metadata và chống replay

`Packet_Metadata` tạo device ID từ eFuse MAC, session ngẫu nhiên khác 0 và sequence có lưu Preferences/NVS. Điều này khác việc lưu toàn bộ payload trong NVS.

Gateway lưu cửa sổ chống trùng và sequence đã thấy trong RAM. Bộ đếm giúp loại một số gói cũ trong thời gian chạy, nhưng không phải cơ chế chống replay bền vững xuyên reboot hoàn chỉnh. Cần mô tả đúng giới hạn khi đánh giá bảo mật.

Công cụ đối chiếu: [check_shared_protocol.py](../../Final_Project_NCKH/Gateway/tools/check_shared_protocol.py). Công cụ kiểm tra source không thay thế phép thử tương tác với packet thật.

<a id="muc-6"></a>

## 6. Hợp đồng JSON và giá trị thiếu

Gateway tạo record kèm `schema_version=1`, `message_type="complete_packet"` và `has_patient_event`. Gói chứa patient event có thông tin nguồn và event ID; gói Gate định kỳ không bắt buộc mang lại event bệnh nhân.

| Trường/khái niệm | Ý nghĩa khi hiển thị |
|---|---|
| Event ID | Nhận diện một sự kiện Node, dùng chống trùng |
| Record ID | Nhận diện record uplink; không thay thế event ID |
| `vitals_valid` | Tính hợp lệ sinh hiệu của sự kiện hiện tại |
| HR/SpO2 cache | Giá trị gần nhất có thể từ phiên trước |
| Sensor valid mask | Cho biết nhóm sensor có dữ liệu dùng được |
| `null` | Không có số đo hợp lệ, không phải 0 |
| Uptime | Thời gian từ boot, không phải UTC |
| `alert.active` | Chính sách cảnh báo Gateway, khác raw classification |

Gateway hiện đặt alert khi có patient event Asthma với score >=0.80. Node có thể phân loại Asthma tại score thấp hơn mức đó; hai tầng cần được hiệu chỉnh và giải thích cùng nhau.

<a id="muc-7"></a>

## 7. Nguyên tắc khi thay đổi giao thức

1. Không thêm field vào packed struct một phía mà quên Gateway.
2. Nếu đổi ý nghĩa score hoặc enum, cập nhật parser/UI và test, không chỉ header.
3. Nếu sửa format dây truyền, cân nhắc version và compatibility rõ ràng.
4. Kiểm tra packet lỗi/tag sai/duplicate/replay và ACK sai session.
5. Không log plaintext nhạy cảm, key hoặc credential để tiện debug.
6. Kiểm tra quyền truy cập broker và lưu trữ Dashboard nếu đưa ra ngoài môi trường thử nghiệm.

Toàn bộ cơ chế trên là thành phần kỹ thuật của nguyên mẫu. Chưa có cơ sở để tuyên bố hệ thống đạt chứng nhận an toàn y tế hoặc kiểm thử xâm nhập hoàn chỉnh.

