# NCKH PRODUCT DEFINITION — FINAL PROTOTYPE

## 1. Tên đề tài

**Nghiên cứu, thiết kế và chế tạo hệ thống IoT ứng dụng TinyML hỗ trợ theo dõi và cảnh báo sớm cho bệnh nhân hen suyễn.**

> **Phạm vi "Final" trong tài liệu này:** hoàn thành nguyên mẫu NCKH, không phải thiết bị y tế thương mại và không nhằm tự chẩn đoán bệnh.

---

## 2. Mục tiêu của sản phẩm

Hệ thống được xây dựng như một nền tảng **AIoT hai node**, trong đó:

- **Patient Edge Node** thực hiện thu âm hô hấp, xử lý DSP, chạy TinyML tại biên, đo HR/SpO₂ theo phiên và hiển thị kết quả cục bộ.
- **IoT Gateway** thu thập thông tin môi trường, nhận sự kiện từ Patient Node, ghép dữ liệu, quản lý kết nối Wi-Fi/LTE/GPS và publish dữ liệu lên MQTT.
- **Dashboard Qt6/QML** hiển thị dữ liệu hiện tại, lịch sử phiên đo, sự kiện âm thanh hô hấp, thông số môi trường, trạng thái thiết bị và cảnh báo.

Hệ thống hướng tới **hỗ trợ theo dõi và cảnh báo**, không tuyên bố:

- tự chẩn đoán bệnh hen suyễn;
- xác nhận chắc chắn một cơn hen;
- xác định mức độ nguy kịch lâm sàng;
- thay thế đánh giá của nhân viên y tế.

---

# 3. Định nghĩa sản phẩm cuối cùng

Hệ thống gồm **2 thiết bị vật lý chính**.

## 3.1. Patient Edge Node

Thiết bị cá nhân nhỏ gọn, cầm tay, chạy pin, có thể mang theo.

### Phần cứng chính

- ESP32-S3-N16R8.
- Microphone số INMP441, giao tiếp I2S.
- MAX30102 đo nhịp tim và SpO₂.
- OLED SSD1306.
- Ba nút:
  - `CHECK`
  - `MONITOR`
  - `SLEEP / STOP`
- Pin.
- ESP-NOW dùng làm liên kết cục bộ đến Gateway.

### Form factor

Không định hướng:

- smartwatch đeo tay;
- microphone áp trực tiếp lên ngực;
- trạm cố định bắt buộc người dùng phải đến đo.

Định hướng:

> **Portable handheld respiratory monitor** — một thiết bị cá nhân nhỏ, có thể bỏ túi, để bàn, đặt cạnh giường hoặc mang theo; khi cần kiểm tra người dùng chủ động đưa thiết bị đến gần vùng miệng.

### Lý do không chọn smartwatch

- Cổ tay không phải vị trí tối ưu cho microphone hô hấp.
- Dễ xuất hiện nhiễu cơ học do cử động, ma sát dây đeo/quần áo và va chạm vỏ.
- Khi đo hô hấp vẫn phải đưa thiết bị đến gần miệng.
- MAX30102 dạng finger measurement phù hợp hơn với một thiết bị cầm tay trong phạm vi NCKH hiện tại.

---

## 3.2. IoT Gateway

Thiết bị đóng vai trò:

- Gateway truyền thông.
- Environmental Node.
- Data Aggregator.
- Network Manager.

### Phần cứng chính

- ESP32.
- DHT22.
- BMP280.
- SGP30.
- NEO-M8N.
- A7680C.
- Wi-Fi.
- ESP-NOW.
- Nguồn cấp cố định; pin là tùy chọn nếu cần mobile operation.
- TFT là tùy chọn, không phải requirement bắt buộc.

### Vai trò

Gateway:

1. Nhận `PatientEvent` từ Patient Node.
2. Đọc dữ liệu môi trường định kỳ.
3. Ghép Patient Event với Environment Snapshot gần thời điểm tương ứng.
4. Quản lý lịch sử sequence/event.
5. Publish MQTT.
6. Dùng Wi-Fi ở nhà.
7. Dùng LTE khi Wi-Fi không có hoặc khi hoạt động mobile.
8. Dùng GPS khi cần vị trí trong mobile/emergency scenario.

---

# 4. Nguyên lý thu âm hô hấp

## 4.1. Microphone cuối cùng

**INMP441 được giữ làm microphone final cho nguyên mẫu NCKH.**

Không thay microphone chỉ vì một số file kiểm thử có biên độ âm thanh thấp.

Các file Asthma độc lập dùng để playback qua loa Bluetooth có thể có mức âm nhỏ; một số trường hợp cần đưa microphone gần loa, khoảng `< ~6 cm`, để:

- mức tín hiệu đủ lớn;
- VAD vượt threshold;
- pipeline bắt đầu capture.

Điều này được xem là **giới hạn acquisition / operating condition**, không phải lỗi deployment nếu pipeline vẫn suy luận ổn khi tín hiệu đủ chất lượng.

---

## 4.2. Near-field acquisition

Thiết bị được định nghĩa là hệ thống thu âm hô hấp theo kiểu:

> **Near-field respiratory acoustic acquisition**

Không claim khả năng:

- nghe wheezing ổn định từ khoảng cách xa;
- hoạt động như microphone far-field trong toàn phòng.

Trong Manual Check, người dùng nên đưa Patient Node gần vùng miệng trước khi bắt đầu đo.

Khoảng cách chính thức sẽ được chốt sau khi hoàn thiện enclosure và kiểm thử final hardware.

---

# 5. Model TinyML — AI v1.0

Model hiện tại được tạm đóng băng làm **AI Final v1.0 cho NCKH**.

## 5.1. Model

- DS-CNN.
- Full INT8.
- TensorFlow Lite Micro.
- Target: ESP32-S3.

## 5.2. Input

- Sampling rate: `16 kHz`.
- Duration: `5 s`.
- Butterworth Bandpass: `100–2000 Hz`.
- Pre-emphasis: `0.97`.
- Mel-Spectrogram: `64 × 129`.
- dB range: `-80 → 0 dB`.
- Normalize về `[0,1]`.
- Quantize INT8.

## 5.3. Dataset methodology

Phiên bản hiện tại ưu tiên tính đúng đắn của phương pháp đánh giá:

- Chia dữ liệu theo bệnh nhân trước augmentation.
- Chỉ augmentation tập train.
- Validation/Test giữ dữ liệu gốc.
- Min/max normalization chỉ lấy từ tập train.
- Hạn chế data leakage giữa các mẫu cùng bệnh nhân/họ hàng dữ liệu.

Accuracy có thể thấp hơn phiên bản cũ nhưng đáng tin cậy hơn nếu pipeline đánh giá đã đúng.

## 5.4. Deployment parity

Đã xác nhận:

- Python và ESP32 dùng cùng một model artifact.
- Pipeline C++ tương đương về thuật toán và kết quả phân lớp với Python.
- Không claim bit-exact hoặc trùng tuyệt đối mọi giá trị số.
- Bộ validation được đối chiếu Python ↔ ESP32 đạt cùng predicted class trên toàn bộ tập kiểm tra đã sử dụng.

---

# 6. Model đang phát hiện gì?

Không định nghĩa model là:

- cough detector;
- asthma diagnosis model;
- attack severity model.

Định nghĩa:

> **Respiratory Acoustic Pattern Classifier**

Input là một đoạn âm thanh hô hấp 5 giây.

Output:

- `Asthma-like`
- `Non-Asthma`

Một tiếng ho lớn có thể làm VAD trigger nhưng không có nghĩa classifier bắt buộc phải trả `Asthma-like`.

Model chỉ có cơ sở phát hiện nếu đoạn âm thanh chứa pattern tương tự lớp Asthma đã học, ví dụ các đặc trưng wheezing/respiratory acoustic có trong dataset.

---

# 7. Audio Quality Check

## 7.1. Mục đích

Quality Check không phân loại Asthma.

Nó trả lời:

> Đoạn audio 5 giây vừa thu có đủ điều kiện kỹ thuật để cho phép TinyML inference hay không?

## 7.2. Chạy trên đúng 5 giây input

Không thêm 1 giây noise baseline trong final hiện tại.

Không đổi input thành 6 giây.

Không dùng 1 giây noise + 4 giây breathing.

Pipeline:

```text
Final 5-second audio
        |
        v
Audio Quality Check
        |
    +---+---+
    |       |
  FAIL     PASS
    |       |
  Retry     v
          DSP
           |
         DS-CNN
```

## 7.3. Metrics dự kiến

Trong lúc thu audio có thể cập nhật liên tục:

- RMS.
- Peak.
- Clipping count.
- Active block count / active ratio.

Các trạng thái:

- `AUDIO_OK`
- `AUDIO_TOO_WEAK`
- `AUDIO_TOO_LOUD`
- `AUDIO_INACTIVE`

Các threshold cụ thể chưa khóa, cần calibration trên final enclosure/hardware.

---

# 8. Pre-trigger buffer 1 giây trong PSRAM

## 8.1. Chức năng thực sự

`1 s PSRAM` không phải noise baseline và không phải Quality Gate.

Nó là:

> **Rolling pre-trigger buffer cho Auto Monitor**

Trong Monitor Mode, VAD cần một khoảng thời gian để xác nhận đủ 4 block liên tiếp vượt threshold. Khi VAD trigger, âm thanh có thể đã bắt đầu trước đó.

Vì vậy:

```text
          VAD trigger
              |
--------------|------------------> time
  1 s before  |    4 s after
==============|===================
    PSRAM     |     Capture
```

Kết quả:

```text
1 s pre-trigger
+
4 s post-trigger
=
5 s final audio
```

Nhờ đó giảm nguy cơ mất phần đầu của respiratory event.

## 8.2. Manual Check

Manual Check không cần pre-trigger vì user chủ động bắt đầu capture.

```text
CHECK
  |
  v
Record exact 5 seconds
```

---

# 9. Ba chế độ của Patient Node

Patient Node dùng **3 nút vật lý riêng** để tránh logic long-press/double-click phức tạp.

```text
[ CHECK ]   [ MONITOR ]   [ SLEEP ]
```

---

## 9.1. Mode 0 — STANDBY / SLEEP

Dùng khi:

- thiết bị đang được mang theo;
- nằm trong túi;
- không có phiên đo.

Mục tiêu:

- tiết kiệm pin;
- không thu dữ liệu vô nghĩa khi sensor không ở vị trí phù hợp.

Trạng thái dự kiến:

- INMP441 OFF.
- I2S OFF.
- MAX30102 OFF.
- OLED OFF.
- ESP-NOW OFF.
- ESP32-S3 low-power/deep-sleep tùy implementation final.

---

## 9.2. Button 1 — CHECK

### Bước 1 — Respiratory Check

Người dùng:

1. Cầm Patient Node.
2. Đưa gần vùng miệng.
3. Nhấn `CHECK`.

Firmware:

```text
CHECK
 |
 v
OLED instruction
 |
 v
Record exact 5 s
 |
 v
Quality Check
 |
 +---- FAIL --> Retry message
 |
 PASS
 |
 v
DSP
 |
 v
3x Invoke / Voting
 |
 v
Audio Result
```

### Bước 2 — Optional HR/SpO₂

Sau khi có Audio Result, OLED yêu cầu:

```text
PLACE FINGER
PRESS CHECK
```

Nhấn `CHECK` lần thứ hai:

```text
MAX30102 ON
    |
    v
HR / SpO2
    |
    v
Complete Patient Session
```

Nếu user không muốn đo HR/SpO₂:

```text
SLEEP
```

Session vẫn hợp lệ với:

```text
HR/SpO2 = unavailable
```

### Lợi ích

- Không ép MAX30102 chạy trong lúc AI đang xử lý nặng.
- UX rõ ràng.
- Dễ debug.
- Có thể test riêng Audio Check rất nhanh.
- MAX30102 chỉ bật khi thật sự có ngón tay.

---

## 9.3. Button 2 — MONITOR

Đây là pipeline Auto Monitor hiện tại.

```text
MONITOR
   |
   v
INMP441 + I2S ON
   |
   v
1 s rolling PSRAM
   |
   v
VAD continuous
   |
   v
4 consecutive blocks > threshold
   |
   v
TRIGGER
   |
   v
1 s pre + 4 s post
   |
   v
5 s final audio
   |
   v
Quality Check
   |
   v
DSP
   |
   v
3x Invoke / Voting
   |
   v
Event
   |
   v
ESP-NOW
   |
   v
Return to MONITOR
```

### MAX30102 trong Monitor Mode

Mặc định:

```text
MAX30102 = OFF
```

Lý do:

- không thể giả định người dùng đang đặt ngón tay trên sensor;
- Monitor Mode tập trung vào acoustic monitoring.

Nếu Monitor phát hiện event đáng chú ý, OLED có thể yêu cầu user thực hiện HR/SpO₂ check bằng nút `CHECK`.

---

## 9.4. Button 3 — SLEEP / STOP

Có ưu tiên cao nhất.

Dùng để:

- dừng Monitor;
- hủy phiên Check nếu cần;
- cleanup peripheral;
- đưa thiết bị về low power.

Không thực hiện cleanup phức tạp trong ISR.

ISR chỉ đặt flag, state machine xử lý:

```text
Stop I2S
Stop MAX30102
Reset buffers/state
OLED OFF
ESP-NOW OFF
Enter sleep
```

---

# 10. Patient Node không tạo dữ liệu bệnh nhân 24/7

Đây là quyết định có chủ ý.

Dữ liệu Patient Node gồm:

- Manual Check sessions.
- Auto Monitor acoustic events.
- HR/SpO₂ theo phiên.
- Battery/status event.

Không giả định:

- HR continuous 24/7.
- SpO₂ continuous 24/7.
- audio 24/7 trong mọi tình huống.

Monitoring được chia:

```text
Environment:
periodic / continuous via Gateway

Patient:
event/session based

Audio:
continuous only when MONITOR is enabled
```

---

# 11. ESP-NOW — vai trò final

Giữ ESP-NOW.

Không dùng Patient Node để kết nối Wi-Fi/MQTT trực tiếp.

Patient Node chỉ gửi event/session.

```text
Patient Node
     |
  ESP-NOW
     |
     v
Gateway
     |
 Wi-Fi/LTE
     |
    MQTT
```

Lợi ích:

- giảm độ phức tạp Patient Node;
- giảm power;
- không Wi-Fi credentials;
- không MQTT reconnect;
- không TLS/broker logic;
- giữ Patient Node độc lập với Internet.

ESP-NOW là **event-based transport**, không stream raw audio.

---

# 12. Ba kịch bản vận hành sản phẩm

## 12.1. Home Monitoring

```text
Patient Node
     |
  ESP-NOW
     |
     v
Home Gateway
     |
    Wi-Fi
     |
    MQTT
     |
     v
Qt Dashboard
```

Gateway:

- always-on;
- đo môi trường định kỳ;
- Wi-Fi là primary uplink;
- GPS thường OFF;
- LTE standby/fallback.

Patient Node:

- portable;
- Standby phần lớn thời gian;
- Manual Check khi cần;
- Monitor Mode khi user chủ động bật.

---

## 12.2. Portable Offline

Người dùng mang Patient Node ra khỏi vùng Gateway:

```text
Patient Node
     X
  Gateway
```

Patient Node vẫn hoạt động:

```text
Manual Check
TinyML
HR/SpO2
OLED Result
Local event storage
```

Nếu ESP-NOW gửi thất bại:

```text
event.synced = false
```

Khi quay lại gần Gateway:

```text
sync pending events
```

Nguyên tắc:

> Mất Gateway/Internet không làm mất chức năng TinyML cốt lõi.

---

## 12.3. Mobile Connected

Khi cần realtime connectivity ngoài nhà:

```text
Patient Node
     |
  ESP-NOW
     |
     v
Gateway
     |
 A7680C LTE
     |
     v
   MQTT
```

Lúc này:

- LTE là primary uplink.
- GPS có thể ON.
- Environment sensors có thể tiếp tục đo môi trường xung quanh.

Gateway không bắt buộc phải luôn đi theo Patient Node; đây là chế độ mở rộng khi cần mobile realtime.

---

# 13. Nguyên tắc UI

## Patient OLED

Vai trò: **measurement interaction UI**

Hiển thị:

- READY.
- PLACE NEAR MOUTH.
- RECORDING.
- PROCESSING.
- AUDIO TOO WEAK.
- PLACE FINGER.
- HR/SpO₂.
- RESULT.
- MONITORING.
- BATTERY.
- GATEWAY STATUS.

## Gateway TFT

Tùy chọn.

Nếu có chỉ phục vụ:

- latest event;
- environment;
- gateway/network status;
- Wi-Fi/LTE state.

Không bắt buộc dùng LVGL.

## Qt6/QML Dashboard

Vai trò: **history + analytics + monitoring UI**

Hiển thị:

- Patient Sessions.
- Respiratory Events.
- HR/SpO₂ history.
- Environment.
- Gateway status.
- Alerts.
- Location.
- Network state.

---

# 14. Các nguyên tắc thiết kế cuối cùng

1. **Edge-first:** TinyML chạy cục bộ trên ESP32-S3.
2. **Offline-capable:** Patient Node vẫn hoạt động khi mất Gateway/Internet.
3. **Near-field acoustic acquisition:** không claim far-field.
4. **Quality-before-inference:** audio quá yếu/không hợp lệ không nên bị ép model kết luận.
5. **Event-based patient data:** không giả lập dữ liệu continuous nếu sensor không thật sự được sử dụng liên tục.
6. **Gateway aggregation:** Gateway ghép patient + environment trước khi MQTT.
7. **Separation of responsibility:** Patient Node = sensing/AI; Gateway = network/environment/aggregation.
8. **No medical overclaim:** chỉ hỗ trợ theo dõi/cảnh báo.
9. **Prototype NCKH scope:** ưu tiên tính đúng, ổn định, demo được và đánh giá được hơn là tối ưu như sản phẩm thương mại.
