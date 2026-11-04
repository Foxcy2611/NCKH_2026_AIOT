# Gateway: SMS khi patient_event = NON-ASTHMA

## Tính năng

- Chỉ kích hoạt sau khi Gateway **nhận và xác thực AES-GCM thành công** một
  `MSG_PATIENT_EVENT`, payload hợp lệ, cập nhật state thành công.
- Điều kiện: `session_id != 0` và `classification == 1` (NON-ASTHMA).
  `classification == 0` (ASTHMA), `== 2` (UNSURE), MQTT telemetry định kỳ,
  gateway synthetic telemetry, bản tin MQTT retry/reconnect: **không gửi SMS**.
- Số nhận: **0919332022**, cấu hình `GATEWAY_SMS_PHONE` trong
  `include/Config/gateway_config.h`.
- Mỗi `(device_id, session_id)` chỉ được **xếp một yêu cầu SMS** trong cache
  RAM 32 phiên gần nhất. Ngay cả khi Node gửi thêm nhiều sự kiện/sequence cho
  cùng phiên, Gateway không xếp tin thứ hai trong thời gian cache còn giữ phiên.
- Khi đủ điều kiện: `TaskEspNow -> GatewaySms_OnPatientEvent() -> smsQueue ->
  TaskSms -> A7680C_SendSMS()`. Worker không chặn ESP-NOW, MQTT hay cảm biến.
- Modem A7680C vẫn sẵn sàng gửi SMS khi uplink MQTT sử dụng Wi-Fi; **SMS không
  yêu cầu MQTT/Internet**, nhưng SIM phải có sóng, được đăng ký mạng và có
  khả năng gửi SMS. `GATEWAY_LTE_ENABLED` phải bằng 1; `GATEWAY_SMS_ENABLED`
  có thể đặt 0 để tắt SMS (ví dụ khi chạy thử tránh phát sinh cước).

## Nội dung SMS

Ví dụ `session_id=1234`, `model_score=0.96`:

    NCKH AIoT: Phien 1234 duoc phan loai NON-ASTHMA (96.0%). Ket qua chi mang tinh tham khao.

SMS dùng ký tự ASCII/GSM, không dấu để tránh lỗi encoding. Đánh giá AI chỉ mang
ý nghĩa tham khảo, không phải kết luận hoặc đảm bảo y tế.

## Các file liên quan

- `include/Config/gateway_config.h`: bật/tắt, điện thoại, queue, task.
- `include/System/gateway_sms.h`: quy tắc phân loại và cache chống trùng phiên.
- `src/task/task_espnow.cpp`: xếp SMS từ **event vừa chấp nhận**, không lấy
  `node_dirty` hay telemetry từ MQTT.
- `src/task/task_sms.cpp`: task xử lý SMS và ghi log.
- `src/sensor/ESP32_A7680C_AT.cpp`: lệnh AT+CMGF/CMGS/Ctrl+Z, có khóa
  **toàn giao dịch SMS** để tránh tranh UART với LTE/MQTT; xác nhận cả +CMGS và OK.
- `src/main.cpp`: tạo queue và task SMS.

## Cách test phần cứng

1. Dùng ESP32 Gateway với module A7680C nối theo cấu hình: ESP32 RX=GPIO16,
   ESP32 TX=GPIO26, UART 115200, chung GND, cấp nguồn cho module SIM đủ dòng
   theo datasheet/board. Lắp SIM có dịch vụ SMS và sóng di động.
2. Mở `Gateway/` trong VS Code + PlatformIO, chọn môi trường `esp32dev`
   hoặc `gateway_hardware`, build và nạp Gateway. Mở Serial Monitor 115200.
3. Gửi `patient_event` **hợp lệ đã AES-GCM xác thực** từ Patient Node,
   `session_id=1234`, `classification=1`, `model_score=0.96`.
4. Kiểm tra log: `[SMS] Queued NON-ASTHMA ...`, sau đó
   `[SMS] Sending ...` và `[SMS] SENT ...` khi modem trả ACK gửi thành công.
5. Gửi lại cùng session bằng packet trùng hoặc sequence mới: không có tin thứ
   hai (`[SMS] Skip repeated session=...` nếu sequence mới).
6. Tạo phiên khác với `classification=0` hoặc 2: không gửi. Chỉ telemetry
   hoặc reconnect MQTT cũng không gửi SMS.

Chạy host tests (không gửi SMS thật):

    python test/native/run_tests.py

## Lưu ý và giới hạn

- Cache chống trùng và queue đều **chỉ ở RAM**, không dùng NVS theo kiến trúc
  latest-state: restart Gateway làm mất lịch sử SMS, có thể gửi lại nếu Node
  tạo/gửi lại phiên cũ. Cache giữ 32 phiên gần nhất, không bảo đảm chống trùng
  vĩnh viễn sau nhiều phiên.
- Queue tối đa 8 yêu cầu. Nếu queue đầy, ghi `[SMS] ERROR queue full` và bỏ
  yêu cầu lần đó; chỉ packet mới được Gateway nhận sau đó mới có cơ hội xếp lại.
- Sau khi xếp, worker chờ modem khởi tạo tối đa 30 giây. Nếu modem chưa sẵn
  sàng hoặc lệnh SMS lỗi, ghi `[SMS] FAILED`, **không tự retry** vì khi modem
  mất phản hồi, không thể chắc chắn nhà mạng đã gửi hay chưa. Muốn gửi thử lại,
  tạo session_id mới. `[SMS] SENT` chỉ xác nhận modem nhận lệnh gửi, **không
  phải** bằng chứng SMS đã đến điện thoại đích.
- Modem A7680C thường phụ thuộc nguồn ổn định và tình trạng SIM/SMSC/mạng;
  số điện thoại có thể mất cước SMS. Test trước với SIM và module thực tế.
- Chưa build/nạp trên ESP32, chưa gửi SMS thật trong môi trường soạn code này.
