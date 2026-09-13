# Tổng quan mã nguồn Patient Node

## 1. Vai trò của Patient Node

Patient Node chạy trên ESP32-S3 và thực hiện các công việc chính:

1. Nhận thao tác từ ba nút `CHECK`, `MONITOR`, `SLEEP`.
2. Thu âm từ micro INMP441 qua I2S.
3. Kiểm tra chất lượng đoạn âm thanh.
4. Tiền xử lý Mel-Spectrogram và chạy mô hình TinyML DS-CNN INT8.
5. Thu nhịp tim và SpO₂ từ MAX30102 khi cảm biến sẵn sàng.
6. Tạo dữ liệu sự kiện của bệnh nhân.
7. Mã hóa dữ liệu bằng AES-128-GCM và gửi qua ESP-NOW.
8. Nhận, xác thực và xử lý ACK/NACK từ Gateway.
9. Hiển thị tiến trình trên OLED sau khi mô-đun giao diện được ghép hoàn chỉnh.

`State_Machine.cpp` là lõi điều phối. Các mô-đun còn lại chỉ thực hiện công việc chuyên biệt và trả kết quả về máy trạng thái.

---

## 2. Cấu trúc liên quan

```text
Patient_Node/
├── src/                         Mã hiện thực
│   ├── main.cpp
│   ├── State_Machine.cpp
│   ├── I2S_Mic.cpp
│   ├── Quality_Check.cpp
│   ├── DSP_Filter.cpp
│   ├── Mel_Scale.cpp
│   ├── Interface_Asthma.cpp
│   ├── PPG_Sensor.cpp
│   ├── Secure_Sender.cpp
│   ├── Secure_Response_Decryptor.cpp
│   ├── EspNow_Client.cpp
│   └── UI_Oled.cpp
├── include/                     Khai báo hàm công khai
├── shared/                      Trạng thái, pinout và giao thức dùng chung
└── common/                      Thuật toán metadata và tiện ích dùng chung
```

Các file `.cpp` trong `src/` được PlatformIO biên dịch trực tiếp. File `.cpp` đặt ở thư mục gốc `Patient_Node/` không tự động được biên dịch.

---

## 3. Trách nhiệm từng mô-đun

### `main.cpp`

Điểm vào của chương trình. `setup()` khởi tạo hệ thống theo thứ tự:

1. Serial.
2. Mel filter bank.
3. Mô hình TFLite Micro.
4. Micro I2S và các buffer âm thanh trong PSRAM.
5. State machine, metadata và nút nhấn.
6. ESP-NOW cùng hai chiều AES-GCM.
7. I²C, OLED và MAX30102 sẽ được nối thêm sau.

`loop()` hiện thực hiện ba việc liên tục:

```text
StateMachine_Run()
→ nếu payload sẵn sàng thì đưa vào EspNow_Client
→ EspNow_Process()
```

State machine chỉ rời `SESSION_READY` sau khi packet bảo mật đã được sao chép an toàn vào vùng chờ ACK.

### `State_Machine.cpp`

Là thuật toán lõi quản lý toàn bộ tiến trình của Node:

- Nhận cờ nút từ các hàm ngắt.
- Tạo và xóa `Patient_Session_t`.
- Gọi đúng mô-đun theo state hiện tại.
- Kiểm tra state trước khi nhận kết quả từ mô-đun con.
- Điều phối CHECK thủ công và MONITOR tự động.
- Tổng hợp ba lần dự đoán trong MONITOR.
- Tạo `Patient_Event_Payload_t` khi phiên hoàn tất.
- Trở về `STANDBY` hoặc tiếp tục `MONITOR_LISTENING` sau khi sự kiện đã vào pending.

Các state chính:

```text
STANDBY
MANUAL_CAPTURE
AUDIO_QUALITY
AI_PROCESSING
AUDIO_RESULT
VITAL_CHECK
SESSION_READY
MONITOR_LISTENING
MONITOR_CAPTURE
ERROR
```

Nút `SLEEP` có ưu tiên cao nhất. Khi đang thu hoặc xử lý, nút này yêu cầu hủy phiên. Tại `AUDIO_RESULT` hoặc `VITAL_CHECK`, nút này mang ý nghĩa bỏ qua sinh hiệu nhưng vẫn giữ kết quả âm thanh.

### `I2S_Mic.cpp`

Phụ trách micro INMP441:

- Khởi tạo I2S RX 16 kHz.
- Chuyển mẫu 32 bit của INMP441 về mẫu signed 16 bit.
- Cấp phát audio buffer, float buffer và pre-roll buffer trong PSRAM.
- CHECK thủ công: thu 80.000 mẫu, tương đương 5 giây.
- MONITOR: đọc từng chunk, tính VAD và duy trì bộ đệm trước kích hoạt 1 giây.
- Sau khi VAD kích hoạt, ghép pre-roll với phần âm thanh tiếp theo để tạo đủ đoạn 5 giây.
- Cung cấp buffer cho kiểm tra chất lượng và tiền xử lý.

CHECK thủ công thu theo vòng lặp chặn cho tới khi đủ mẫu, nhưng vẫn kiểm tra yêu cầu `SLEEP` sau mỗi chunk. MONITOR sử dụng các hàm từng bước để không khóa vòng lặp chính.

### `Quality_Check.cpp`

Đánh giá đoạn âm thanh trước khi chạy TinyML:

- RMS toàn đoạn.
- Peak lớn nhất.
- Số mẫu clipping.
- Tỷ lệ block có hoạt động âm thanh.

Kết quả trả về:

- `AUDIO_OK`.
- `AUDIO_TOO_WEAK`.
- `AUDIO_TOO_LOUD`.
- `AUDIO_INACTIVE`.

Mẫu lỗi trong CHECK chuyển sang `ERROR`. Mẫu lỗi trong MONITOR bị bỏ và hệ thống quay lại lắng nghe; mẫu lỗi không được tính là một vote.

### `DSP_Filter.cpp`

Thực hiện các bước xử lý tín hiệu trước Mel-Spectrogram:

1. Đổi mẫu `int16_t` về `float`.
2. Lọc Butterworth trong dải quan tâm.
3. Pre-emphasis với hệ số hiện hành `0.97`.

Trạng thái bộ lọc được reset trước mỗi đoạn âm thanh để các phiên không ảnh hưởng lẫn nhau.

### `Mel_Scale.cpp`

Chuyển tín hiệu âm thanh thành đầu vào của mô hình:

- Sample rate: 16 kHz.
- FFT: 1.024 điểm.
- Hop length: 625 mẫu.
- 64 Mel bins.
- 129 frames.
- Dải tần: 100–2.000 Hz.
- Dùng frame căn giữa giống pipeline Python.
- Chuyển Mel power sang dB với mốc là giá trị lớn nhất của mẫu.

Mel filter bank được cấp phát trong PSRAM bằng `Init_Mel_Filterbank()`.

### `Interface_Asthma.cpp`

Phụ trách mô hình DS-CNN đã lượng tử INT8:

- Cấp phát Tensor Arena 270 KiB trong PSRAM.
- Kiểm tra model, kiểu tensor và kích thước đầu vào `[1, 64, 129, 1]`.
- Chuẩn hóa Mel dB từ miền huấn luyện `[-80, 0]` về `[0, 1]`.
- Lượng tử input sang `int8_t` theo scale và zero-point của tensor.
- Gọi TFLite Micro `Invoke()`.
- Giải lượng tử output thành xác suất.

Ngưỡng kết luận hiện hành:

```text
P(non-asthma) <= 0.45  → ASTHMA_LIKE
P(non-asthma) >= 0.65  → NON_ASTHMA
0.45 < P < 0.65        → UNSURE
```

Giá trị đưa về state machine dùng `Interface_TinyML_t`:

```text
0 = INTERFACE_UNSURE
1 = INTERFACE_ASTHMA_LIKE
2 = INTERFACE_NON_ASTHMA
```

Mọi mô-đun hiển thị hoặc truyền dữ liệu phải dùng đúng ánh xạ này.

### `PPG_Sensor.cpp`

Phụ trách MAX30102 theo cách gọi từng bước:

- Khởi tạo cảm biến.
- Đọc FIFO mà không giữ vòng lặp quá lâu.
- Phát hiện không có ngón tay.
- Thu đủ mẫu và tính nhịp tim/SpO₂.
- Trả kết quả hoặc timeout cho state machine.

State machine chỉ gọi `MAX30102_Poll()` sau khi khởi tạo cảm biến thành công và đã gọi:

```cpp
StateMachine_SetVitalsAvailable(true);
```

Khi chưa có MAX30102, người dùng có thể nhấn `SLEEP` tại bước sinh hiệu để bỏ qua. Payload vẫn hợp lệ với `vitals_valid = 0`, `heart_rate = 0`, `spo2 = 0`.

### `Secure_Sender.cpp`

Mã hóa sự kiện Node → Gateway:

1. Nhận `Patient_Event_Payload_t` 24 byte.
2. Tạo header/AAD gồm magic, version, message type, device ID và sequence.
3. Sinh nonce 12 byte ngẫu nhiên cho sự kiện mới.
4. Mã hóa payload bằng AES-128-GCM.
5. Sinh authentication tag 16 byte.
6. Trả về `Secure_EspNow_Packet_t` đúng 64 byte.

Nonce chỉ được sinh khi tạo sự kiện mới. Khi retry, tuyệt đối không mã hóa lại; phải gửi nguyên packet đã lưu.

### `Secure_Response_Decryptor.cpp`

Xác thực và giải mã phản hồi Gateway → Node:

- Kiểm tra magic, version và `MSG_GATEWAY_RESPONSE`.
- Kiểm tra Gateway ID và sequence đang chờ.
- Xác thực tag AES-GCM trước khi sử dụng plaintext.
- Giải mã thành `Gateway_Response_Payload_t` 24 byte.
- Kiểm tra target device ID, session ID, response code và cờ thời gian.
- Xóa kết quả đầu ra nếu xác thực hoặc giải mã thất bại.

### `EspNow_Client.cpp`

Điều phối việc gửi, nhận phản hồi và retry:

- Khởi tạo Wi-Fi STA và ESP-NOW.
- Đăng ký callback gửi và nhận.
- Khởi tạo hai khóa AES riêng cho hai chiều truyền.
- Chỉ giữ một packet pending tại một thời điểm.
- Sinh sequence, mã hóa và sao chép packet vào pending.
- Callback chỉ ghi cờ và sao chép dữ liệu ngắn; không chạy AES trong callback Wi-Fi.
- `EspNow_Process()` giải mã phản hồi, xử lý timeout và retry trong vòng lặp chính.

Chuỗi trạng thái gửi thông thường:

```text
IDLE → QUEUED → SENDING → ACK_PENDING → ACK_CONFIRMED
```

Khi có lỗi:

```text
SENDING hoặc ACK_PENDING
→ RETRY_WAIT
→ gửi lại nguyên packet
→ RETRY_EXCEEDED nếu vẫn thất bại
```

Quy tắc phản hồi:

- `ACK_ACCEPTED`: hoàn thành và xóa pending.
- `ACK_DUPLICATE`: cũng hoàn thành vì Gateway đã nhận bản trước.
- `NACK_BUSY`: chờ rồi retry.
- `NACK_INTERNAL`: retry có giới hạn.
- `NACK_UNSUPPORTED`: dừng sự kiện hiện tại.
- Sai MAC, kích thước, tag, sequence hoặc session ID: bỏ phản hồi.

Cấu hình hiện tại dùng MAC Gateway, Gateway ID và hai khóa AES tạm đặt ở đầu file. Phải thay bằng cấu hình thật trước khi ghép Gateway.

### `UI_Oled.cpp`

Vị trí dành cho lớp giao diện OLED của Patient Node. File này hiện chưa được ghép hoàn chỉnh.

Khi tích hợp cần bảo đảm:

- I²C chỉ được khởi tạo một lần bằng chân trong `Board_Pinout.h`.
- OLED và MAX30102 có thể dùng chung bus I²C.
- Hàm vẽ không dùng `delay()` dài.
- Chỉ đổi màn hình khi state hoặc dữ liệu cần hiển thị thay đổi.
- Hoạt ảnh được giới hạn tốc độ, không làm chậm thu âm, TinyML hoặc ESP-NOW.
- Ánh xạ kết quả AI đúng với `Interface_TinyML_t`.

---

## 4. Dữ liệu đi qua hệ thống

### Dữ liệu cục bộ

`Patient_Session_t` lưu thông tin của một lần CHECK hoặc một sự kiện MONITOR:

- Session ID.
- Loại sự kiện.
- Chất lượng âm thanh.
- Kết luận và điểm mô hình.
- Nhịp tim, SpO₂ và cờ hợp lệ.
- Thời điểm bắt đầu sự kiện.

### Plaintext gửi đi

State machine chuyển session thành `Patient_Event_Payload_t` 24 byte. Battery hiện đang để `0` vì chưa nối mô-đun nguồn.

### Packet truyền qua ESP-NOW

```text
Header/AAD      12 byte, không mã hóa nhưng được xác thực
Nonce           12 byte
Ciphertext      24 byte
Authentication  16 byte
--------------------------------
Tổng            64 byte
```

AES-GCM đã cung cấp kiểm tra toàn vẹn và xác thực packet. `Checksum_CRC32` hiện không tham gia luồng packet bảo mật này.

---

## 5. Luồng CHECK thủ công

```text
STANDBY
→ người dùng nhấn CHECK
→ tạo session EVENT_MANUAL_CHECK
→ MANUAL_CAPTURE: thu 5 giây
→ AUDIO_QUALITY: kiểm tra chất lượng
```

Nếu âm thanh lỗi:

```text
→ ERROR
→ nhấn CHECK để tạo phiên và thu lại
→ hoặc nhấn SLEEP để hủy về STANDBY
```

Nếu âm thanh đạt:

```text
→ AI_PROCESSING
→ DSP + Mel-Spectrogram + DS-CNN
→ AUDIO_RESULT
```

Sau khi có kết quả:

```text
Nhấn CHECK
→ VITAL_CHECK
→ MAX30102 trả kết quả
→ SESSION_READY
```

Hoặc:

```text
Nhấn SLEEP tại AUDIO_RESULT/VITAL_CHECK
→ bỏ qua sinh hiệu
→ SESSION_READY
```

Cuối phiên:

```text
Tạo plaintext 24 byte
→ AES-GCM tạo packet 64 byte
→ lưu pending
→ gửi ESP-NOW
→ state machine trở về STANDBY
```

CHECK chỉ suy luận một lần, không vote ba lần.

---

## 6. Luồng MONITOR

```text
STANDBY
→ nhấn MONITOR
→ MONITOR_LISTENING
→ micro warmup, duy trì pre-roll 1 giây và chạy VAD
```

Khi VAD kích hoạt:

```text
→ tạo hoặc tiếp tục session EVENT_MONITOR_EVENT
→ MONITOR_CAPTURE
→ hoàn thiện đoạn thu 5 giây
→ AUDIO_QUALITY
```

Nếu âm thanh lỗi, đoạn đó bị bỏ và hệ thống quay lại `MONITOR_LISTENING` mà không tăng vote.

Nếu âm thanh đạt:

```text
→ AI_PROCESSING
→ lưu kết quả vote
→ nếu chưa đủ 3 vote thì quay lại MONITOR_LISTENING
```

Sau ba vote hợp lệ:

- Lớp có số vote lớn nhất được chọn.
- Điểm cuối là trung bình điểm của các vote thuộc lớp thắng.
- Trường hợp `1-1-1` trả về `UNSURE`.
- MONITOR không yêu cầu đo MAX30102.

Sau đó hệ thống tạo, mã hóa và enqueue sự kiện rồi tự quay lại `MONITOR_LISTENING`.

Nhấn MONITOR lần nữa để tắt chế độ này và trở về `STANDBY`.

---

## 7. Luồng phản hồi ESP-NOW

```text
Node tạo và lưu packet pending
→ gọi esp_now_send()
→ callback báo kết quả gửi ở tầng RF
→ nếu RF thành công, chờ phản hồi nghiệp vụ từ Gateway
→ callback nhận sao chép packet phản hồi
→ EspNow_Process() xác thực và giải mã
```

Gửi RF thành công không đồng nghĩa Gateway đã chấp nhận dữ liệu. Chỉ `ACK_ACCEPTED` hoặc `ACK_DUPLICATE` hợp lệ mới kết thúc pending.

Nếu mất phản hồi, Node gửi lại nguyên packet, cùng nonce, sequence, ciphertext và tag. Hiện packet được giữ trong RAM; reset hoặc mất nguồn khi đang chờ ACK sẽ làm mất pending.

Nếu Gateway gửi thời gian hợp lệ, Node lưu:

```text
time_offset = gateway_timestamp - millis()
```

Các timestamp tiếp theo được tính từ `millis()` cộng offset. Trước lần đồng bộ đầu tiên, timestamp gửi đi bằng `0`.

---

## 8. Metadata

`Packet_Metadata.cpp` cung cấp:

- `device_id`: rút gọn từ MAC/eFuse của ESP32-S3.
- `session_id`: số ngẫu nhiên mới cho mỗi phiên.
- `sequence`: tăng cho mỗi packet mới và lưu trong NVS.
- `timestamp`: Unix time theo offset Gateway cung cấp.

Sequence chỉ tăng khi tạo packet mới. Retry không được gọi `PacketMetadata_NextSequence()` lần nữa.

---

## 9. Các nguyên tắc khi mở rộng

1. Không xử lý nặng, gọi I²C, chạy AES hoặc in log dài trong ISR/callback ESP-NOW.
2. Không sinh packet mới khi retry.
3. Không cho state machine rời `SESSION_READY` trước khi packet đã nằm an toàn trong pending.
4. Không ghi đè pending cũ bằng sự kiện mới.
5. Không chạy TinyML nếu `AudioQuality_Check()` trả về lỗi.
6. Không thay đổi tham số DSP/Mel độc lập với pipeline Python đã đóng băng.
7. Không coi RF send callback là ACK của Gateway.
8. OLED không được dùng `delay()` làm dừng vòng lặp chính.
9. OLED và MAX30102 phải dùng pin từ `Board_Pinout.h`, không khai báo chân riêng trong thư viện.
10. Khi thay đổi `Secure_Protocol.h`, Node và Gateway phải cùng dùng đúng một định nghĩa cấu trúc.

---

## 10. Trạng thái hiện tại

Đã có và đã build chung trong Patient Node:

- Thu âm CHECK và MONITOR.
- Pre-roll 1 giây và VAD.
- Kiểm tra chất lượng âm thanh.
- Pipeline DSP/Mel tương ứng pipeline Python.
- DS-CNN INT8 trên TFLite Micro.
- State machine và vote MONITOR ba lần.
- Metadata.
- AES-128-GCM chiều gửi.
- Giải mã ACK/NACK chiều nhận.
- Pending, timeout và retry ESP-NOW.

Chưa hoàn tất kiểm thử tích hợp:

- OLED trong `UI_Oled.cpp`.
- MAX30102 trên phần cứng thật.
- MAC, Gateway ID và khóa AES triển khai thật.
- Vòng truyền Node ↔ Gateway bằng hai bo mạch thật.
- Battery và quản lý nguồn.

Sau khi OLED được ghép và kiểm thử không gây trễ, Patient Node có thể được chốt ở mức **hoàn thiện mã nguồn, chờ kiểm thử tích hợp Gateway/MAX30102**.
