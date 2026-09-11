# NCKH ASTHMA — Phân công công việc 5 thành viên

> Dựa trên `NCKH_BUILD_IMPLEMENTATION_PLAN.md` (Build Plan = ACTIVE, Product/Architecture = FROZEN v0.1).
> Nguyên tắc bắt buộc xuyên suốt: mỗi phase merge phải có đủ **CODE + TEST + LOG + README cập nhật**; không gộp ≥2 subsystem chưa test riêng vào cùng lúc.
> Giao thức ESP-NOW và AES-128-GCM dùng chung được khóa theo [Encrypt_AES-128-GCM.md](./Encrypt_AES-128-GCM.md); Node và Gateway không tự định nghĩa hai bản packet khác nhau.

**Vai trò:**
- **M1** — AI/Firmware lead (State Machine, Audio Quality, 3-button logic, Patient Event, AES-GCM/ESP-NOW phía Node, Qt6)
- **M2** — OLED + TFT/UX Patient Node
- **M3** — Hardware/sản phẩm
- **M4** — Gateway firmware (AES-GCM/ESP-NOW phía Gateway)
- **M5** — Network/Backend

Yêu cầu:
- Struct dùng chung (`Patient_Session_t`, `Patient_Event_Payload_t`, `Gateway_Response_Payload_t`, `Secure_EspNow_Packet_t`, `EnvironmentSnapshot`, `CompleteRecord`) **không ai được tự sửa** mà không báo M1 và M4 trước. Ba struct truyền thông đầu/cuối phải dùng chung đúng tên, thứ tự trường và kích thước đã khóa trong tài liệu AES-GCM.
- `Secure_EspNow_Packet_t` là packet bảo mật 64 byte dùng ở cả hai chiều; nội dung nghiệp vụ nằm trong payload 24 byte đã mã hóa. M5 chỉ nhận dữ liệu đã được Gateway xác thực/giải mã, không dùng ciphertext làm schema MQTT.
- Mọi sự thay đổi đều trong [Final Project](../Final_Project_NCKH/), không nên tự ý push lên github kể cả nhánh `branch` cá nhân
- Mọi layout thiết kế, state hay phần cứng, ghi rõ vào [Docs Member](../Docs_Member/)

---

## M1 (AI/Firmware lead)

| # | Việc | Output bắt buộc | DONE khi |
|---|------|------------------|----------|
| 1 | State Machine + 3 nút (Phase 1) | enum `PatientState`, debounce ISR, log Serial transition | Bấm sai nút giữa capture/AI không phá flow; SLEEP thoát an toàn khỏi Monitor |
| 2 | Manual Check 5s acquisition (Phase 2) | Record đúng 80000 samples/16kHz, không VAD/pre-trigger | Dump raw khớp pipeline cũ |
| 3 | Audio Quality Gate (Phase 3) | `AudioQualityMetrics`/`AudioQuality`, threshold TBD ghi rõ README | Phân biệt đúng 5 case: im lặng / quá nhỏ / hợp lệ / clipping / đập ngắn |
| 4 | Nối TinyML vào Quality Gate (Phase 4) | `Audio_CheckQuality()` → DSP → DS-CNN → Voting → `AudioInferenceResult` | Quality FAIL không Invoke model; không regress kết quả |
| 5 | PatientSession (Phase 6) | Struct + Serial print đầy đủ sau mỗi CHECK | Audio-only vẫn hợp lệ (`vitals_valid=false`) |
| 6 | Auto Monitor vào state machine (Phase 7) | Pipeline VAD/PSRAM cũ chạy dưới state mới, dùng chung Quality Gate với Manual | Chạy lâu không crash |
| 7 | Patient Event + AES-GCM/ESP-NOW (Phase 8–9) | Build `Patient_Event_Payload_t`; mã hóa thành `Secure_EspNow_Packet_t`; sequence/nonce; pending retry; nhận và xác thực `Gateway_Response_Payload_t` | Chỉ xóa pending khi ACK bảo mật hợp lệ; retry gửi lại nguyên packet cũ; mất Gateway vẫn lưu local; ACK trùng không tạo dữ liệu trùng |
| 8 | Qt6/QML Dashboard (Phase 15) | Overview, Patient Session History, Respiratory Event History, HR/SpO2 History, Environment Charts, Gateway Status, Network Status, Alerts | Bắt đầu chỉ khi PatientEvent/EnvironmentSnapshot/CompleteRecord/MQTT schema đã chốt (đợi M4+M5); phân biệt rõ Current Environment vs Latest HR/SpO2 |
| 9 | Chốt calibration threshold cuối (Phase 17) | Số threshold final dựa trên đo thực nghiệm của M3 | — |
| 10 | Đánh giá AI metrics (Phase 18) | Accuracy/Precision/Recall/F1/Confusion Matrix | — |

**Việc cần làm ngay:** Bước 7 — phối hợp M4 khóa header giao thức chung, kiểm tra kích thước `24/24/64 byte`, rồi triển khai AES-GCM và luồng ESP-NOW phía Node. Chưa nối vào Session thật cho đến khi test mã hóa/giải mã độc lập đạt.

---

## M2 — OLED/UX Patient Node

| # | Việc | Điều kiện bắt đầu | Ghi chú |
|---|------|--------------------|---------|
| 1 | Chờ khung `PatientState` cơ bản từ M1 | Không cần đợi hoàn thiện 100%, chỉ cần enum + transition event | Trong lúc chờ: vẽ wireframe các màn trước |
| 2 | Module hiển thị subscribe vào state của M1 | Sau bước 1 | Không tự giữ logic điều hướng riêng. Màn bắt buộc: STANDBY / PLACE NEAR MOUTH / countdown / PLACE FINGER PRESS CHECK / AUDIO_RESULT / ERROR |
| 3 | Test bằng state giả lập | Sau bước 2 | Nhờ M1 chuyển state tay, kiểm tra từng màn hiện đúng |
| 4 | Thêm màn Audio Quality | Khi M1 xong bước 3 (Quality Gate) | Hiển thị TOO_WEAK/TOO_LOUD/INACTIVE/OK |
| 5 | Thêm màn HR/SpO2 | Khi M1+M3 xong MAX30102 | Bao gồm cả VITALS_NOT_AVAILABLE |
| 6 | Chuẩn bị màn Auto Monitor | Song song, trước khi M1 làm Phase 7 | MONITOR_LISTENING/MONITOR_CAPTURE |
| 7 | Thiết kế giao diện TFT đơn giản | Không cần đợi | Thiết kế giao diện cho màn TFT ở module Gateway hiển thị các thông tin đơn giản, có thể tham khảo ở [doc/Product](./NCKH_PRODUCT_DEFINITION_FINAL.md)

**Việc cần làm ngay:** Đợi M1 publish state enum ban đầu; tranh thủ vẽ wireframe trước.

---

## M3 — Hardware/sản phẩm

| # | Việc | Giao cho ai dùng | DONE khi |
|---|------|-------------------|----------|
| 1 | Kiểm tra toàn bộ thư viện | M1, M2, M4 dùng ngay | Kiểm tra các lib tự viết cho tất cả các module hoạt động ổn định sử dụng tại [ESP Sensor Suite](../ESP32-Sensor_Suite/README.md)
| 2 | Tạo header chứa sơ đồ chân | M1, M2 và cả M4 | Tạo 2 header chứa sơ đồ chân, thông số SPI, I2C, ... cho Node và Gateway để có thể bám vào |
| 3 | Chốt layout thiết kế sản phẩm | — | Ý tưởng sản phẩm ở [READEME](../README.md) hay [PRODUCT](./NCKH_PRODUCT_DEFINITION_FINAL.md) chỉ là ý tưởng, chốt thiết kế cho 2 sản phẩm
| 4 | Enclosure freeze (Phase 16) | — | Chỉ làm sau khi firmware/network ổn: vị trí mic/OLED/nút/MAX30102, kích thước Patient Node + Gateway (air vent, antenna, A7680C, GPS, power) |
| 5 | Đo power thực nghiệm (Phase 17–18) | Giao số cho M1 chốt threshold | I_standby / I_manual / I_monitor, sau khi enclosure gần cuối |

**Việc cần làm ngay:** Bước 1 — driver INMP441/nút/OLED thô. M1 và M2 đang cần để bắt đầu code.

---

## M4 — Gateway firmware

| # | Việc | Điều kiện bắt đầu | DONE khi |
|---|------|--------------------|----------|
| 1 | FreeRTOS skeleton (Phase 10) | Có thể bắt đầu sớm, song song với M1 (không phụ thuộc AI) | `TaskEspNow`, `TaskSensor`, `TaskGatewayManager`, `TaskNetwork`; callback RX chỉ sao chép MAC + packet 64 byte vào `RawSecurePacketQueue`, không giải mã/aggregate trong callback |
| 2 | AES-GCM RX/TX phía Gateway | Sau khi M1 và M4 khóa header giao thức chung | Ngoài callback: kiểm MAC/Header, xác thực tag, giải mã Event, chống trùng; tạo `Gateway_Response_Payload_t`, mã hóa ACK/NACK bằng khóa chiều Gateway → Node |
| 3 | Test nhận packet từ Node giả lập | Ngay sau bước 2 | Đủ ca: packet hợp lệ, sửa ciphertext/tag, sai MAC/sequence, packet trùng, timeout và ACK giả; dữ liệu sai không lọt vào hàng đợi nghiệp vụ |
| 4 | Sensor Layer (Phase 11) | Khi M3 giao driver DHT22/BMP280/SGP30 | `EnvironmentSnapshot`; 1 sensor lỗi không sập cả hệ |
| 5 | Test và tích hợp TWDT | Trong cùng bước 4 | Phục hồi mạch nếu có tiến trình gây treo (dòng 1-wire và Wi-Fi) |
| 6 | Aggregator (Phase 12) | Sau bước 4 | Ghép `Patient_Event_Payload_t` **đã xác thực/giải mã** + `EnvironmentSnapshot` gần nhất → `CompleteRecord` |
| 7 | Bàn giao schema cho M5 | Sau bước 6 | `CompleteRecord` ổn định; không đưa nonce/ciphertext/tag/khóa vào MQTT |
| 8 | Đánh giá Communication (Phase 18) | — | Tỉ lệ ESP-NOW thành công, ACK/retry, chống duplicate, Gateway loss/reconnect, packet bị sửa và phản hồi giả |

**Việc cần làm ngay:** Dựng FreeRTOS skeleton + `RawSecurePacketQueue`, sau đó dùng cùng header với M1 để test AES-GCM bằng packet giả lập trước khi nhận Event thật.

---

## M5 — Network/Backend

| # | Việc | Điều kiện bắt đầu | Ghi chú |
|---|------|--------------------|---------|
| 1 | Nghiên cứu MQTT client + soạn nháp schema | Ngay bây giờ, song song | Dựa trên `Patient_Event_Payload_t` đã được Gateway giải mã, `EnvironmentSnapshot` và `CompleteRecord`; không dựa trên packet mã hóa 64 byte |
| 2 | Wi-Fi + MQTT (Phase 13) | Chờ M4 có `CompleteRecord` ổn định (Phase 12) | Publish CompleteRecord; schema nháp 4 nhóm: patient event / environment / gateway status / alert; README ghi rõ "chưa khóa" |
| 3 | LTE + GPS (Phase 14) | Sau khi Wi-Fi/MQTT ổn | A7680C fallback theo policy HOME (Wi-Fi primary, LTE standby, GPS OFF) và MOBILE (LTE primary, GPS ON khi cần) |
| 4 | Phối hợp với M1 làm Dashboard | Khi M1 bắt đầu Phase 15 | Cung cấp MQTT client mẫu/schema cuối |
| 5 | Đánh giá End-to-end latency (Phase 18) | — | Patient Check → TinyML → AES-GCM/ESP-NOW → Gateway xác thực/giải mã → MQTT → Dashboard |

**Việc cần làm ngay:** Nghiên cứu trước thư viện MQTT client cho ESP32 và soạn nháp schema JSON, để không mất thời gian khi đến lượt (sau Phase 12 của M4).
