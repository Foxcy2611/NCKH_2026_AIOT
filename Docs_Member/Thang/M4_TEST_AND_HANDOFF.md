# Checklist nghiệm thu M4 và bàn giao M5

## So với yêu cầu Docs_NCKH
| Mục | Hiện trạng code | Kiểm chứng còn lại |
|---|---|---|
| FreeRTOS / callback chỉ copy | Có sẵn; thêm kiểm tra tạo task | Build và chạy idle |
| Secure RX/TX | Giữ logic đang test được của bro | Regression n/d/c/r, sai MAC, fake ACK |
| Sensor layer | Đã nối 3 driver, timeout I2C, retry init độc lập | Rút/cắm từng sensor |
| TWDT | Bốn task đăng ký/feed; queue wait có timeout | Chạy env watchdog test |
| Aggregator | Event + snapshot; telemetry độc lập; stale mask; backpressure | So Serial của hai board |
| Schema M5 | Struct giữ nguyên, mô tả bên dưới | M5 thống nhất time basis / định danh event JSON |
| Communication evaluation | Có counter, test sender thủ công có sẵn | Đo thực nghiệm, lưu log và tính tỷ lệ |

## Trình tự test (chưa chạy trên board)
1. Nạp esp32dev; để không có Node ít nhất 60s: telemetry khoảng 5s, mask=0, không reset. Có `nan` ở float là đúng, không phải giá trị đo 0.
2. Mở Patient_Node_Test trên S3, giữ MAC Gateway trong test_config.h đúng board, channel giống nhau. Gõ `n`: ACK_ACCEPTED, accepted tăng 1, một record patient=1.
3. Gõ `d` hoặc `r`: ACK_DUPLICATE, không phát sinh thêm patient record. Record patient=0 định kỳ vẫn bình thường.
4. Gõ `c`: auth_failed tăng; không patient record mới. Đây là kiểm thử sửa ciphertext; chưa thay thế kiểm thử sửa tag riêng.
5. Lệnh `o` gửi previous_packet: nếu sequence vẫn trong history 16 mục thì ACK_DUPLICATE là đúng. Muốn chứng minh replay bị loại, phải phát lại packet đã nằm ngoài cửa sổ 16 mục, không chỉ nhấn o sau hai packet.
6. Tắt Gateway, gõ n, chờ timeout; bật lại, clear pending bằng x nếu cần rồi r. Sender hiện manual-only, không tự retry. Ghi kết quả reconnect riêng, đừng coi timeout test là đo retry tự động.
7. Nạp gateway_synthetic: mask=0x07, so các số cố định trong README. Không dùng số giả làm kết quả đo nghiên cứu.
8. Nạp gateway_hardware khi cần: rút từng sensor; sensor khác và ESP-NOW vẫn chạy; cắm lại BMP/SGP thử init tối đa khoảng 5s, SGP chờ thêm warmup 15s. DHT lỗi xóa validity khi lần đọc kế tiếp thất bại.
9. Nạp gateway_wdt_test: sau 15s task sensor ngừng feed; dự kiến TWDT reset sau khoảng 10s. Ghi log reset_reason và panic; sau đó nạp lại esp32dev.
10. Burn-in bản thường; lưu firmware/env, thời gian, số packet gửi, ACK nhận tại Node, duplicate, replay, drop, heap, reset. Chưa có log thì trạng thái NOT RUN, không ghi PASS.

## Chỉ số communication
- Success = số event duy nhất được ACK hợp lệ tại Node / số event duy nhất gửi ×100%.
- Không dùng `ack_queued` làm ACK-delivery: counter này chỉ đếm esp_now_send chấp nhận xếp hàng.
- Tách số lần phát RF / event duy nhất / retry; log Node là nguồn cho timeout và ACK latency.
- Counter Gateway là số quan sát tại thời điểm log; các counter không được chụp đồng thời.
- Queue full ở raw/patient tăng dropped; BUSY giữ nguyên packet để retry.
- Queue đầu ra đầy: Aggregator giữ patient record và chờ, không âm thầm bỏ event đã ACK; telemetry có thể drop.
- ACK_ACCEPTED xác nhận vào RAM queue, không xác nhận cloud hoặc ghi flash. Mất nguồn vẫn có thể mất event.

## Giới hạn security giữ từ bản đầu vào
Theo phạm vi bro chốt, đợt này không thiết kế lại security. History và MAC learning ở RAM: reboot Gateway mất history; không chứng minh chống replay xuyên reboot. Gateway đang phục vụ một Node; sequence reset ở Node có thể bị coi là cũ khi Gateway chưa reset. Phải phối hợp M1 nếu cần đổi policy/persist sequence. Không tuyên bố đạt các ca fake ACK, wrong MAC, replay xuyên reboot khi chưa có log.

## Giao diện cho M5
Nhận `CompleteRecord` qua `completeRecordQueue`; thay thân TaskNetwork để dùng publisher thật. Không thêm consumer thứ hai vào cùng queue vì sẽ chia record giữa hai consumer.
`CompleteRecord` alias `Complete_Packet_t`; giữ nguyên thứ tự/type trường trong `include/Config/gateway_types.h`.
- `has_patient_event=0`: chỉ gate; patient_event được zero-init và M5 phải bỏ qua.
- `has_patient_event=1`: kèm payload bệnh nhân đã xác thực.
- `gate.timestamp`: uptime Gateway 64-bit ms tại tạo record, KHÔNG UTC. `patient_event.timestamp` thuộc time basis của Node; không trừ hai số để đo latency nếu chưa đồng bộ.
- `sensor_valid_mask`: bit0 DHT22 (temperature+humidity), bit1 BMP280 (pressure), bit2 SGP30 (eco2+tvoc), bit3 GPS. Đợt này không fallback nhiệt độ BMP vì snapshot hiện không có provenance cho nguồn nhiệt độ.
- Float không hợp lệ = NaN trong RAM; M5 serialize JSON thành null. Gas integer 0 chỉ có nghĩa khi bit SGP30 valid; không dùng 0 suy ra lỗi.
- GPS chưa dùng: bit3=0, latitude/longitude NaN, gps_timestamp=0.
- Offline: operating_mode=1, uplink_type=0; wifi/lte/mqtt connected=0. RSSI=0 không có nghĩa khi disconnected.
- Bản synthetic không có field riêng trong struct để nhận diện: không nối build này lên hệ thống dữ liệu thật.
- Struct C++ nội bộ có padding; không publish raw sizeof(struct), không tự xem đây là wire format.
- Không đưa nonce/ciphertext/tag/khóa vào MQTT. device_id/sequence hiện chỉ ở PatientEventEnvelope, chưa nằm trong CompleteRecord; M5/M1 cần chốt metadata ngoài struct nếu cần dedup đa Node. Không tự thay shared struct.

## API TWDT tham khảo
https://docs.espressif.com/projects/esp-idf/en/v4.4.8/esp32/api-reference/system/wdts.html

## Nhật ký kết quả
| Test | Kết quả hiện tại | Log |
|---|---|---|
| Native record/protocol tests | PASS trên host | test/native/RESULT.txt |
| Build esp32dev / hardware / synthetic / wdt | NOT RUN | Cần PlatformIO toolchain |
| Firmware chạy hai ESP | NOT RUN bản sửa | Bro lưu Serial hai board |
| Sensor fault / watchdog reset / burn-in | NOT RUN | Cần phần cứng |
