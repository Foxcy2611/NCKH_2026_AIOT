# NCKH ASTHMA — Phân công công việc 5 thành viên

> Dựa trên `NCKH_BUILD_IMPLEMENTATION_PLAN.md` (Build Plan = ACTIVE, Product/Architecture = FROZEN v0.1).
> Nguyên tắc bắt buộc xuyên suốt: mỗi phase merge phải có đủ **CODE + TEST + LOG + README cập nhật**; không gộp ≥2 subsystem chưa test riêng vào cùng lúc.

**Vai trò:**
- **M1** — AI/Firmware lead (State Machine, Audio Quality, 3-button logic, PatientEvent, Qt6)
- **M2** — OLED + TFT/UX Patient Node
- **M3** — Hardware/sản phẩm
- **M4** — Gateway firmware
- **M5** — Network/Backend

Yêu cầu:
- Struct dùng chung (`PatientEventPacket`, `PatientSession`, `EnvironmentSnapshot`, `CompleteRecord`) **không ai được tự sửa** mà không báo M1 (struct patient) hoặc M4 (struct environment) trước.
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
| 7 | PatientEvent + ESP-NOW (Phase 8–9) | `PatientEventPacket`, ACK, sequence, pending retry | Mất Gateway → lưu pending → reconnect → sync, không duplicate |
| 8 | Qt6/QML Dashboard (Phase 15) | Overview, Patient Session History, Respiratory Event History, HR/SpO2 History, Environment Charts, Gateway Status, Network Status, Alerts | Bắt đầu chỉ khi PatientEvent/EnvironmentSnapshot/CompleteRecord/MQTT schema đã chốt (đợi M4+M5); phân biệt rõ Current Environment vs Latest HR/SpO2 |
| 9 | Chốt calibration threshold cuối (Phase 17) | Số threshold final dựa trên đo thực nghiệm của M3 | — |
| 10 | Đánh giá AI metrics (Phase 18) | Accuracy/Precision/Recall/F1/Confusion Matrix | — |

**Việc cần làm ngay:** Bước 1 — refactor state machine. M2 và M3 đang chờ API state của bạn để cắm vào.

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
| 1 | FreeRTOS skeleton (Phase 10) | Có thể bắt đầu sớm, song song với M1 (không phụ thuộc AI) | `TaskEspNow`, `TaskSensor`, `TaskGatewayManager`, `TaskNetwork`; queue `PatientEventQueue`; không parse/aggregate trong callback |
| 2 | Test nhận packet từ Node giả lập | Ngay sau bước 1 | Dùng packet mẫu, không cần đợi Patient Node hoàn chỉnh |
| 3 | Sensor Layer (Phase 11) | Khi M3 giao driver DHT22/BMP280/SGP30 | `EnvironmentSnapshot`; 1 sensor lỗi không sập cả hệ |
| 4 | Test và tíc hợp TWDT | Trong cùng bước 3 | Phục hồi mạch nếu có tiến trình gây treo (Dòng 1-wire và WiFi) |
| 4 | Aggregator (Phase 12) | Sau bước 3 | Ghép `PatientEventPacket` + `EnvironmentSnapshot` gần nhất → `CompleteRecord` |
| 5 | Bàn giao schema cho M5 | Sau bước 4 | `CompleteRecord` ổn định |
| 6 | Đánh giá Communication (Phase 18) | — | ESP-NOW success rate, ACK/retry, Gateway loss/reconnect |

**Việc cần làm ngay:** Dựng FreeRTOS skeleton + queue ngay, dùng packet giả lập để test trong lúc chờ M1 hoàn thiện ESP-NOW thật.

---

## M5 — Network/Backend

| # | Việc | Điều kiện bắt đầu | Ghi chú |
|---|------|--------------------|---------|
| 1 | Nghiên cứu MQTT client + soạn nháp schema | Ngay bây giờ, song song | Dựa trên struct `PatientEventPacket`/`EnvironmentSnapshot` đã có |
| 2 | Wi-Fi + MQTT (Phase 13) | Chờ M4 có `CompleteRecord` ổn định (Phase 12) | Publish CompleteRecord; schema nháp 4 nhóm: patient event / environment / gateway status / alert; README ghi rõ "chưa khóa" |
| 3 | LTE + GPS (Phase 14) | Sau khi Wi-Fi/MQTT ổn | A7680C fallback theo policy HOME (Wi-Fi primary, LTE standby, GPS OFF) và MOBILE (LTE primary, GPS ON khi cần) |
| 4 | Phối hợp với M1 làm Dashboard | Khi M1 bắt đầu Phase 15 | Cung cấp MQTT client mẫu/schema cuối |
| 5 | Đánh giá End-to-end latency (Phase 18) | — | Patient Check → TinyML → ESP-NOW → Gateway → MQTT → Dashboard |

**Việc cần làm ngay:** Nghiên cứu trước thư viện MQTT client cho ESP32 và soạn nháp schema JSON, để không mất thời gian khi đến lượt (sau Phase 12 của M4).
