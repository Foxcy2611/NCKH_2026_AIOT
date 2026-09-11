# NCKH ASTHMA — SPECIFICATION HỢP NHẤT (Product Definition + System Architecture)

> Gộp từ `NCKH_PRODUCT_DEFINITION_FINAL.md` + `NCKH_SYSTEM_ARCHITECTURE_FINAL.md`.
> Phần trùng lặp giữa 2 bản (diagram pipeline, Quality Gate, ESP-NOW, state machine...) đã được hợp nhất về một bản duy nhất, ưu tiên bản diễn giải đầy đủ hơn; phần chỉ có ở một bản (button conflict table, task diagram Gateway, roadmap...) được giữ nguyên và chèn vào đúng vị trí.

**Phạm vi:** hoàn thành nguyên mẫu NCKH, không phải thiết bị y tế thương mại, không nhằm tự chẩn đoán bệnh.

**Đặc tả bảo mật đường truyền:** [Encrypt_AES-128-GCM.md](./Encrypt_AES-128-GCM.md). Khi nội dung liên quan đến cấu trúc packet, nonce, khóa, ACK/NACK hoặc retry, tài liệu bảo mật này là nguồn quy định chi tiết.

---

## 1. Tên đề tài & Mục tiêu

**Nghiên cứu, thiết kế và chế tạo hệ thống IoT ứng dụng TinyML hỗ trợ theo dõi và cảnh báo sớm cho bệnh nhân hen suyễn.**

Hệ thống là một nền tảng **AIoT hai node**:

- **Patient Edge Node** — thu âm hô hấp, DSP, chạy TinyML tại biên, đo HR/SpO₂ theo phiên, hiển thị kết quả cục bộ.
- **IoT Gateway** — thu thập môi trường, nhận sự kiện từ Patient Node, ghép dữ liệu, quản lý Wi-Fi/LTE/GPS, publish MQTT.
- **Dashboard Qt6/QML** — hiển thị dữ liệu hiện tại, lịch sử phiên đo, sự kiện âm thanh, môi trường, trạng thái thiết bị, cảnh báo.

Hệ thống hướng tới **hỗ trợ theo dõi và cảnh báo**, **không**:
- tự chẩn đoán bệnh hen suyễn;
- xác nhận chắc chắn một cơn hen;
- xác định mức độ nguy kịch lâm sàng;
- thay thế đánh giá của nhân viên y tế.

---

## 2. Kiến trúc tổng quan

```text
                    PATIENT
                       |
                       v
          +--------------------------+
          |      PATIENT NODE        |
          |       ESP32-S3-N16R8     |
          |                          |
          | INMP441                  |
          | MAX30102                 |
          | OLED SSD1306             |
          | CHECK / MONITOR / SLEEP  |
          | Battery                  |
          |                          |
          | DSP + DS-CNN INT8        |
          +------------+-------------+
                       |
              ESP-NOW + AES-128-GCM
                       |
                       v
          +--------------------------+
          |        GATEWAY           |
          |         ESP32            |
          |                          |
          | DHT22 / BMP280 / SGP30   |
          | NEO-M8N / A7680C         |
          |                          |
          | Aggregation / Storage    |
          | Wi-Fi / LTE / MQTT       |
          +------------+-------------+
                       |
                      MQTT
                       |
             +---------+----------+
             |                    |
             v                    v
         Database            Qt6/QML
                              Dashboard
```

---

## 3. Định nghĩa 2 thiết bị vật lý

### 3.1. Patient Edge Node

Thiết bị cá nhân nhỏ gọn, cầm tay, chạy pin, có thể mang theo.

**Phần cứng:** ESP32-S3-N16R8, INMP441 (I2S), MAX30102 (HR/SpO₂), OLED SSD1306, 3 nút (`CHECK` / `MONITOR` / `SLEEP-STOP`), Pin, ESP-NOW làm liên kết cục bộ đến Gateway.

**Form factor — Định hướng:**
> **Portable handheld respiratory monitor** — thiết bị cá nhân nhỏ, bỏ túi được, để bàn, đặt cạnh giường hoặc mang theo; khi cần kiểm tra người dùng chủ động đưa thiết bị đến gần vùng miệng.

**Không định hướng:** smartwatch đeo tay; microphone áp trực tiếp lên ngực; trạm cố định bắt buộc phải đến đo.

**Lý do không chọn smartwatch:**
- Cổ tay không phải vị trí tối ưu cho microphone hô hấp.
- Dễ nhiễu cơ học do cử động, ma sát dây đeo/quần áo, va chạm vỏ.
- Đo hô hấp vẫn phải đưa thiết bị gần miệng dù đeo tay.
- MAX30102 dạng finger measurement phù hợp thiết bị cầm tay hơn trong phạm vi NCKH hiện tại.

**Trách nhiệm:** thu audio I2S, VAD, rolling pre-trigger buffer PSRAM, Audio Quality Check, DSP, TinyML inference, voting, MAX30102 theo phiên, OLED interaction, low-power state, tạo payload sự kiện, mã hóa/xác thực AES-128-GCM, local event storage khi mất Gateway, ESP-NOW event TX và xử lý phản hồi bảo mật từ Gateway.

**Không chịu trách nhiệm:** Wi-Fi credential, MQTT, TLS, cloud reconnect, GPS, LTE, environment sensing.

### 3.2. IoT Gateway

Vai trò: Gateway truyền thông, Environmental Node, Data Aggregator, Network Manager.

**Phần cứng:** ESP32, DHT22, BMP280, SGP30, NEO-M8N, A7680C, Wi-Fi, ESP-NOW. Nguồn cấp cố định; pin là tùy chọn nếu cần mobile. TFT là tùy chọn, không bắt buộc.

**Trách nhiệm:** ESP-NOW RX; xác thực và giải mã AES-128-GCM; chống nhận trùng; tạo ACK/NACK đã mã hóa; đọc DHT22/BMP280/SGP30 định kỳ; Environment Snapshot; ghép Patient Event đã giải mã với Environment Snapshot gần thời điểm tương ứng; quản lý sequence/history; local storage/queue; Wi-Fi; LTE qua A7680C; MQTT publish; GPS khi cần; optional TFT/status UI.

---

## 4. Nguyên lý thu âm hô hấp

### 4.1. Microphone final

**INMP441 được giữ làm microphone final cho nguyên mẫu NCKH.** Không đổi microphone chỉ vì một số file test có biên độ thấp.

Các file Asthma độc lập dùng để playback qua loa Bluetooth có thể có mức âm nhỏ; một số trường hợp cần đưa microphone gần loa (`< ~6 cm`) để mức tín hiệu đủ lớn, VAD vượt threshold, pipeline bắt đầu capture. Đây là **giới hạn acquisition/operating condition**, không phải lỗi deployment nếu pipeline vẫn suy luận ổn khi tín hiệu đủ chất lượng.

### 4.2. Near-field acquisition

Định nghĩa: **Near-field respiratory acoustic acquisition**. Không claim nghe wheezing ổn định từ xa hay hoạt động như microphone far-field toàn phòng. Trong Manual Check, người dùng đưa Patient Node gần vùng miệng trước khi đo. Khoảng cách chính thức chốt sau khi hoàn thiện enclosure và kiểm thử final hardware.

---

## 5. AI Model — v1.0 (Frozen)

Model hiện tại tạm đóng băng làm **AI Final v1.0 cho NCKH**.

- Kiến trúc: DS-CNN, Full INT8, TensorFlow Lite Micro, target ESP32-S3.
- Input pipeline:

```text
Raw PCM 16 kHz / 5 s
        |
        v
Butterworth Bandpass 100–2000 Hz
        |
        v
Pre-emphasis 0.97
        |
        v
STFT / Mel Filterbank -> 64 x 129 Mel
        |
        v
dB range [-80, 0] -> Normalize [0,1]
        |
        v
INT8 Quantization
        |
        v
DS-CNN -> Classification
```

**Dataset methodology (ưu tiên tính đúng đắn hơn accuracy đẹp):**
- Chia dữ liệu theo bệnh nhân trước augmentation.
- Chỉ augmentation tập train; Validation/Test giữ dữ liệu gốc.
- Min/max normalization chỉ lấy từ tập train.
- Hạn chế data leakage giữa các mẫu cùng bệnh nhân/họ hàng dữ liệu.
- Accuracy có thể thấp hơn phiên bản cũ nhưng đáng tin cậy hơn nếu pipeline đánh giá đã đúng.

**Deployment parity:** Python và ESP32 dùng cùng một model artifact; pipeline C++ tương đương thuật toán và kết quả phân lớp với Python (không claim bit-exact); bộ validation đối chiếu Python ↔ ESP32 đạt cùng predicted class trên toàn bộ tập kiểm tra đã dùng.

**Classification terminology (application-level):**
- Dùng: `ASTHMA_LIKE` (tương đương `Asthma-like`), `NON_ASTHMA` (tương đương `Non-Asthma`)
- **Không dùng:** `DIAGNOSED_ASTHMA`, `SEVERE_ATTACK`, `PATIENT_HAS_ASTHMA`

**Model đang phát hiện gì?** Không định nghĩa là cough detector / asthma diagnosis model / attack severity model. Định nghĩa đúng là:
> **Respiratory Acoustic Pattern Classifier** — input là đoạn âm thanh hô hấp 5 giây, output `Asthma-like` / `Non-Asthma`.

Một tiếng ho lớn có thể làm VAD trigger nhưng không có nghĩa classifier bắt buộc trả `Asthma-like`. Model chỉ có cơ sở phát hiện nếu đoạn âm thanh chứa pattern tương tự lớp Asthma đã học (vd wheezing/respiratory acoustic features trong dataset).

---

## 6. Audio Quality Gate

### 6.1. Mục đích

Quality Check **không phân loại Asthma**. Nó trả lời: *đoạn audio 5 giây vừa thu có đủ điều kiện kỹ thuật để cho phép TinyML inference hay không?*

### 6.2. Quan hệ với VAD (2 module không thay thế nhau)

```text
VAD: "Có event đủ điều kiện để AUTO bắt đầu capture chưa?"
QUALITY GATE: "Final 5 s đã thu có đủ chất lượng để model được phép inference chưa?"
```

### 6.3. Chạy trên đúng 5 giây input

Không thêm 1s noise baseline, không đổi input thành 6s, không dùng 1s noise + 4s breathing.

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
          DSP -> DS-CNN
```

### 6.4. API concept

```cpp
enum AudioQuality {
    AUDIO_OK,
    AUDIO_TOO_WEAK,
    AUDIO_TOO_LOUD,
    AUDIO_INACTIVE
};

struct AudioQualityMetrics {
    float rms;
    int32_t peak;
    uint32_t clipped_samples;
    uint32_t active_blocks;
};

AudioQuality Audio_CheckQuality(
    const int16_t* audio,
    size_t samples,
    AudioQualityMetrics* metrics
);
```

Metrics dự kiến (cập nhật liên tục trong lúc thu): RMS, Peak, Clipping count/ratio, Active block count/ratio.

**Threshold cụ thể chưa khóa** — cần calibration trên final enclosure/hardware.

---

## 7. Pre-trigger buffer 1 giây trong PSRAM

Không phải noise baseline, không phải Quality Gate. Đây là:
> **Rolling pre-trigger buffer cho Auto Monitor**

Trong Monitor Mode, VAD cần xác nhận đủ 4 block liên tiếp vượt threshold; khi VAD trigger, âm thanh có thể đã bắt đầu trước đó.

```text
          VAD trigger
              |
--------------|------------------> time
  1 s before  |    4 s after
==============|===================
    PSRAM     |     Capture
```

Kết quả: `1s pre-trigger + 4s post-trigger = 5s final audio` → giảm nguy cơ mất phần đầu respiratory event.

**Manual Check không cần pre-trigger** vì user chủ động bắt đầu capture (`CHECK → Record exact 5 seconds`).

---

## 8. Patient Node — 3 chế độ & State Machine

Dùng **3 nút vật lý riêng** để tránh logic long-press/double-click phức tạp: `[ CHECK ]  [ MONITOR ]  [ SLEEP ]`

### 8.1. High-level state diagram

```text
                    +-----------+
                    |  STANDBY  |
                    +-----+-----+
                    /           \
                 CHECK         MONITOR
                  /               \
                 v                 v
        +---------------+   +---------------+
        | MANUAL CHECK  |   | AUTO MONITOR  |
        +-------+-------+   +-------+-------+
                \                 /
                 \               /
                  v             v
                  +-------------+
                  | PROCESSING  |
                  +------+------+
                         |
                         v
                  +-------------+
                  | AUDIO RESULT|
                  +------+------+
                         |
                 optional CHECK
                         |
                         v
                  +-------------+
                  | VITAL CHECK |
                  +------+------+
                         |
                         v
                  +-------------+
                  |SESSION READY|
                  +------+------+
                         |
              Build payload + AES-GCM
                         |
                  Lưu pending + gửi
                         |
                  Chờ ACK/NACK nền
                         |
                         v
                      STANDBY
```

Monitor event xong có thể quay lại `AUTO_MONITOR`.

Việc chờ phản hồi và retry thuộc bộ quản lý truyền thông, không tạo thêm trạng thái chặn cho luồng đo chính. Sau khi lưu bản sao packet mã hóa vào hàng đợi, state machine có thể về `STANDBY` hoặc tiếp tục `AUTO_MONITOR`.

### 8.2. Mode 0 — STANDBY/SLEEP

Dùng khi thiết bị đang mang theo, trong túi, không có phiên đo. Mục tiêu: tiết kiệm pin, không thu dữ liệu vô nghĩa khi sensor không ở vị trí phù hợp.

Trạng thái dự kiến: INMP441 OFF, I2S OFF, MAX30102 OFF, OLED OFF, ESP-NOW OFF, ESP32-S3 low-power/deep-sleep tùy implementation final.

### 8.3. Button 1 — CHECK

**Bước 1 — Respiratory Check:** cầm Patient Node → đưa gần vùng miệng → nhấn `CHECK`.

```text
CHECK -> OLED instruction -> Record exact 5s -> Quality Check
   +---- FAIL --> Retry message
   PASS -> DSP -> 3x Invoke/Voting -> Audio Result
```

**Bước 2 — Optional HR/SpO₂:** OLED yêu cầu `PLACE FINGER / PRESS CHECK`. Nhấn `CHECK` lần 2: `MAX30102 ON -> HR/SpO2 -> Complete Patient Session`.
Nếu user không muốn đo: nhấn `SLEEP` — session vẫn hợp lệ với `HR/SpO2 = unavailable`.

**Lợi ích:** không ép MAX30102 chạy lúc AI xử lý nặng; UX rõ ràng; dễ debug; test riêng Audio Check nhanh; MAX30102 chỉ bật khi thật sự có ngón tay.

**Button behavior theo state:**
- Trong `STANDBY` → bắt đầu Manual Respiratory Check.
- Trong `AUDIO_RESULT` → bắt đầu HR/SpO₂ measurement.
- Trong `MONITOR_ALERT`/event result → có thể bắt đầu HR/SpO₂ nếu UX final cần.

### 8.4. Button 2 — MONITOR (Auto Monitor pipeline)

```text
MONITOR -> INMP441+I2S ON -> 1s rolling PSRAM -> VAD continuous
   -> 4 consecutive blocks > threshold -> TRIGGER
   -> 1s pre + 4s post -> 5s final audio -> Quality Check
   -> DSP -> 3x Invoke/Voting -> Event Payload -> AES-GCM Packet
   -> Lưu pending -> ESP-NOW -> Return to MONITOR
```

**MAX30102 trong Monitor Mode = OFF mặc định** — không thể giả định người dùng đang đặt ngón tay trên sensor; Monitor Mode tập trung vào acoustic monitoring. Nếu Monitor phát hiện event đáng chú ý, OLED có thể yêu cầu user thực hiện HR/SpO₂ check bằng nút `CHECK`.

**Button behavior:** Trong `STANDBY` → bật Auto Monitor. Trong `MONITOR` → tắt Monitor, quay về Standby. Không dùng long-press.

### 8.5. Button 3 — SLEEP/STOP

Ưu tiên cao nhất. Dùng để dừng Monitor, hủy phiên Check nếu cần, cleanup peripheral, đưa thiết bị về low power.

Không cleanup phức tạp trong ISR — ISR chỉ đặt flag `abort_requested`, state machine xử lý:
```text
Stop I2S -> Stop MAX30102 -> Reset buffers/state -> OLED OFF -> ESP-NOW OFF -> Enter sleep
```

### 8.6. Button conflict policy

| State | CHECK | MONITOR | SLEEP |
|---|---|---|---|
| STANDBY | Manual Capture | Monitor Listening | No-op / sleep |
| MANUAL_CAPTURE | Bỏ qua | Bỏ qua | Hủy phiên |
| AUDIO_QUALITY | Bỏ qua | Bỏ qua | Hủy phiên |
| AI_PROCESSING | Bỏ qua | Bỏ qua | Đánh dấu dủy, xử lý sau khi AI xong |
| AUDIO_RESULT | Đo HR/SpO2 | Bỏ qua | Bỏ đo sinh hiệu, sang Session Ready |
| VITAL_CHECK | Bỏ qua | Bỏ qua | Dừng đo, vẫn giữ phiên audio |
| MONITOR_LISTENING | Bỏ qua | Tắt Monitor | Tắt Monitor |
| MONITOR_CAPTURE | Bỏ qua | Bỏ qua | Hủy đoạn đang thu |
| ERROR | Thử lại tùy lỗi | Bỏ qua | Về Standby |

- ABORT - Hủy phiên: Chen ngang hành động đang thực hiện, reset tiến trình (Mục 8.5) đưa về STANDBY
- SLEEP: Ngủ, tắt mô hình và chỉ được tắt khi đang ở STANDBY

---

## 9. Patient Node không tạo dữ liệu 24/7

Patient Node không thu thập/gửi dữ liệu bệnh nhân liên tục. Hoạt động theo phiên/sự kiện:

- Bấm CHECK → ghi âm 5s + AI + optional HR/SpO₂ → hoàn thành → tạo `Patient_Event_Payload_t` → mã hóa và gửi Gateway.
- Bật MONITOR → mic hoạt động liên tục chờ acoustic event → phát hiện & xử lý xong 1 sự kiện → mới tạo payload, mã hóa và gửi Gateway.
- HR/SpO₂ chỉ đo khi có phiên đo, không giả định đo liên tục 24/7.
- Không có phiên/sự kiện → không gửi dữ liệu bệnh nhân mới.
- Gateway tạm không khả dụng → Patient Node lưu event chưa đồng bộ, gửi lại khi kết nối khôi phục.

```text
KHÔNG CÓ PHIÊN/SỰ KIỆN -> Không gửi gì
CÓ CHECK -> Hoàn thành CHECK -> Payload -> AES-GCM Packet -> Gateway
CÓ MONITOR EVENT -> AI xử lý xong -> Payload -> AES-GCM Packet -> Gateway
```

`esp_now_send()` thành công chỉ cho biết tầng truyền đã gửi xong, không chứng minh Gateway đã xác thực và xử lý nội dung. Vì vậy phản hồi nghiệp vụ vẫn bắt buộc:

| Trường hợp tại Gateway | Gateway xử lý | Patient Node xử lý |
|---|---|---|
| Packet mới, tag hợp lệ | Giải mã, nhận Event một lần và gửi `ACK_ACCEPTED` đã mã hóa | Xác thực ACK, xóa đúng packet khỏi pending |
| Packet hợp lệ nhưng trùng `device_id + sequence` | Không lưu/publish lần hai; gửi `ACK_DUPLICATE` đã mã hóa | Coi là đã đồng bộ và xóa pending |
| Sai kích thước, MAC, magic, phiên bản hoặc tag | Im lặng loại bỏ; không sử dụng dữ liệu và không phản hồi | Hết timeout thì gửi lại **đúng packet mã hóa cũ** |
| Gateway tạm bận nhưng packet đã xác thực | Có thể gửi `NACK_BUSY` đã mã hóa | Chờ khoảng retry rồi gửi lại packet cũ |
| Hết số lần retry | Không liên quan | Giữ bản sao local, đánh dấu chưa đồng bộ; không khóa state machine |

`authentication_tag` của AES-GCM thay cho CRC32: vừa phát hiện dữ liệu bị sửa, vừa xác thực thiết bị có đúng khóa. Không dùng thêm CRC32 trong packet bảo mật.

---

## 10. Data models

### 10.1. `Patient_Session_t` — dữ liệu cục bộ trên Patient Node

```cpp
typedef struct {
    uint32_t session_id;
    Event_Type_t event_type;
    Audio_Quality_t audio_quality;
    Interface_TinyML_t classification;
    float model_score;
    bool vitals_valid;
    uint16_t heart_rate;
    uint8_t spo2;
    uint64_t event_timestamp;
} Patient_Session_t;
```

Nếu người dùng bỏ qua HR/SpO₂ → `vitals_valid = false`; đây vẫn là một phiên hợp lệ. `device_id`, `sequence`, trạng thái gửi và số lần retry thuộc lớp packet/hàng đợi truyền thông, không thuộc Session.

### 10.2. Hai payload logic trước mã hóa

```text
Node -> Gateway: Patient_Event_Payload_t      = 24 byte plaintext tạm
Gateway -> Node: Gateway_Response_Payload_t   = 24 byte plaintext tạm
```

- `Patient_Event_Payload_t` chứa `session_id`, thời gian sự kiện, loại sự kiện, kết quả AI, chất lượng audio, HR/SpO₂ và pin.
- `Gateway_Response_Payload_t` chứa Node đích, `session_id` được phản hồi, thời gian Gateway, cờ thời gian hợp lệ, mã ACK/NACK và vùng dự phòng.
- Payload chỉ tồn tại trước mã hóa hoặc sau giải mã thành công; không gửi trực tiếp qua ESP-NOW.

### 10.3. `Secure_EspNow_Packet_t` — packet bảo mật dùng chung hai chiều

```text
+------------------+----------+------------------+--------------------+
| HEADER / AAD     | NONCE    | CIPHERTEXT       | AUTHENTICATION TAG |
| 12 byte          | 12 byte  | 24 byte          | 16 byte            |
+------------------+----------+------------------+--------------------+
                         Tổng: 64 byte
```

Hai chiều đều truyền đúng `Secure_EspNow_Packet_t`. Trường `message_type` trong Header/AAD cho biết ciphertext chứa Patient Event hay Gateway Response. Hai chiều dùng khóa AES-128 riêng. Định nghĩa trường, cách sinh nonce và mã phản hồi nằm trong [Encrypt_AES-128-GCM.md](./Encrypt_AES-128-GCM.md).

---

## 11. ESP-NOW — vai trò final

Giữ ESP-NOW làm **local event transport**, không stream raw audio. Patient Node không dùng Wi-Fi/MQTT trực tiếp, chỉ gửi packet sự kiện đã được AES-128-GCM bảo vệ. `peer.encrypt = false`; bảo mật được thực hiện thống nhất ở tầng ứng dụng.

```text
Patient Node -> AES-GCM -> ESP-NOW -> Verify/Decrypt tại Gateway -> Wi-Fi/LTE -> MQTT
```

**Lợi ích:** giảm độ phức tạp Patient Node, giảm power, không Wi-Fi credentials, không MQTT reconnect, không TLS/broker logic, giữ Patient Node độc lập với Internet.

### 11.1. Reliability

```text
Patient Node --Encrypted Event seq=N--> Gateway --Encrypted ACK/NACK seq=N--> Patient Node
```

- Chỉ công nhận ACK/NACK sau khi đúng MAC Gateway, Header/AAD, `sequence`, `session_id` và GCM tag.
- `ACK_ACCEPTED` hoặc `ACK_DUPLICATE` hợp lệ → xóa packet khỏi pending, đánh dấu đã đồng bộ.
- Timeout hoặc phản hồi không hợp lệ → giữ local và retry theo giới hạn.
- Gateway xuất hiện lại → retry các packet pending.
- Gateway lưu dấu `device_id + sequence` để ACK packet trùng nhưng không lưu/publish Event lần hai.

### 11.2. Cơ chế hàng đợi

Lưu lại **nguyên bản packet 64 byte sau mã hóa** cùng trạng thái/thời gian/số lần retry để Node tự động gửi lại đúng packet đó khi chưa nhận được ACK hợp lệ — không dựng lại payload, không tạo nonce mới và không tăng sequence cho cùng một Event.

Nói ngắn gọn: nó là "bộ nhớ tạm" giữ nguyên gói tin + tiến trình gửi, tách
biệt khỏi state machine chính, để việc chờ ACK/retry chạy song song mà
không cần Node đứng yên đợi Gateway phản hồi. Nếu hết retry, packet vẫn được giữ trong vùng lưu cục bộ để đồng bộ lại sau.

### 11.3. Quy tắc bảo mật bắt buộc

- Không đọc hoặc publish ciphertext như dữ liệu nghiệp vụ.
- Chỉ dùng plaintext sau khi `authentication_tag` đã được xác thực.
- Node → Gateway và Gateway → Node dùng hai khóa khác nhau.
- Một nonce không được dùng cho hai plaintext khác nhau dưới cùng một khóa.
- Retry phải gửi lại nguyên packet cũ; chỉ Event hoặc Response mới được sinh nonce mới.
- Không log khóa, plaintext nhạy cảm hoặc toàn bộ nonce/tag ở bản firmware phát hành.

---

## 12. Gateway — Aggregation & Environment

### 12.1. Aggregation flow

```text
Verified/Decrypted Patient Event -> Get nearest EnvironmentSnapshot -> Get GatewayStatus
   -> Optional GPS -> Build CompleteRecord -> MQTT Publish
```

Cloud không cần tự ghép hai stream rời rạc nếu Gateway đã aggregate.

### 12.2. Environment acquisition

- **DHT22:** Temperature, Humidity.
- **BMP280:** Pressure, Temperature.
- **SGP30:** TVOC, eCO₂/CO₂-equivalent — không mô tả là direct CO₂ sensor.

---

## 13. Ba kịch bản vận hành sản phẩm

### 13.1. Home Monitoring

```text
Patient Node -> AES-GCM/ESP-NOW -> Home Gateway -> Wi-Fi -> MQTT -> Qt Dashboard
```
Gateway: always-on, đo môi trường định kỳ, Wi-Fi primary uplink, GPS thường OFF, LTE standby/fallback.
Patient Node: portable, Standby phần lớn thời gian, Manual Check khi cần, Monitor Mode khi user chủ động bật.

### 13.2. Portable Offline

Người dùng mang Patient Node ra khỏi vùng Gateway. Patient Node vẫn hoạt động: Manual Check, TinyML, HR/SpO2, OLED Result, Local event storage. ESP-NOW gửi thất bại → giữ nguyên packet mã hóa trong hàng đợi chưa đồng bộ; quay lại gần Gateway → gửi lại các packet pending.

> **Nguyên tắc:** Mất Gateway/Internet không làm mất chức năng TinyML cốt lõi.

### 13.3. Mobile Connected

```text
Patient Node -> AES-GCM/ESP-NOW -> Gateway -> A7680C LTE -> MQTT
```
LTE là primary uplink, GPS có thể ON, Environment sensors tiếp tục đo môi trường xung quanh. Gateway không bắt buộc phải luôn đi theo Patient Node — chế độ mở rộng khi cần mobile realtime.

---

## 14. Gateway operating modes & Network policy

### 14.1. HOME MODE
```text
ESP-NOW RX / Environment sensing / Wi-Fi primary / MQTT / GPS usually OFF / LTE standby/fallback
```
Gateway thường cấp nguồn liên tục.

### 14.2. MOBILE MODE
```text
ESP-NOW RX / Environment optional/periodic / LTE primary / GPS ON when needed / MQTT
```

### 14.3. Network policy

- Home: `Wi-Fi -> MQTT`
- Wi-Fi unavailable: `A7680C LTE -> MQTT`
- Mobile: `A7680C LTE -> MQTT`
- Patient Node không biết uplink hiện tại là Wi-Fi hay LTE.

### 14.4. ESP-NOW + Wi-Fi coexistence

Cả hai dùng chung radio 2.4GHz; ESP-NOW peer và Wi-Fi AP phải phù hợp channel. Prototype NCKH chấp nhận cấu hình AP channel cố định hoặc cơ chế đồng bộ channel đơn giản. Nếu coexistence gây vấn đề: `ESP-NOW local link + LTE uplink` là đường thay thế.

### 14.5. LTE data policy

Không upload raw audio liên tục. Chỉ publish: PatientEvent, Environment telemetry, Device status, Alert, Optional GPS. Mục tiêu: giảm data usage, giảm latency, giữ privacy, đúng tinh thần TinyML edge processing.

---

## 15. Kiến trúc firmware

### 15.1. Patient Node — State-machine centric

Không chia toàn bộ ứng dụng thành nhiều FreeRTOS tasks nếu không cần. Arduino ESP32 vẫn chạy trên FreeRTOS ở tầng framework; có thể dùng task nền riêng cho I2S nếu implementation cần, nhưng application flow chính vẫn là state machine.

### 15.2. Gateway — RTOS task centric

Gateway phải concurrent: ESP-NOW, Environment sensors, Wi-Fi, LTE, MQTT, GPS, Storage, optional TFT.

**Task proposal:**
```text
TaskEspNow RX -> RawSecurePacketQueue -> Verify/Decrypt -> PatientEventQueue
                                                    |
                                                    +-> Encrypted ACK/NACK TX
PatientEventQueue -> TaskGatewayManager
                                        +-------> Storage
                                        +-------> PublishQueue -> TaskNetwork/MQTT

TaskSensor -> EnvironmentSnapshot
TaskGps -> LocationSnapshot
Optional: TaskDisplay
```

### 15.3. Gateway robustness rules

RTOS không tự đảm bảo fault isolation. Rules:
- Driver có timeout.
- Không `while(1)` blocking không kiểm soát.
- Queue có timeout; Mutex có timeout.
- Reconnect network non-blocking hoặc bounded.
- Task Watchdog.
- Retry có giới hạn.
- Một sensor lỗi không được làm treo MQTT/ESP-NOW.
- Network lỗi không được làm dừng environment acquisition.

---

## 16. Data categories

- **Periodic data:** Environment telemetry, Gateway status, Heartbeat.
- **Event/session data:** Manual Respiratory Check, Auto Monitor Event, HR/SpO₂, Alert, Sync status.

---

## 17. UI hierarchy

```text
┌────────────────────────────────────────────────────┐
│                  PATIENT NODE                      │
│                     OLED                           │
│                                                    │
│  • Hướng dẫn bệnh nhân                             │
│  • CHECK / MONITOR                                 │
│  • Recording / Processing                          │
│  • HR / SpO₂                                       │
│  • Kết quả AI                                      │
│  • Error / Retry                                   │
└──────────────────────┬─────────────────────────────┘
                       │
              AES-GCM / ESP-NOW
                       │
                       ▼
┌────────────────────────────────────────────────────┐
│                     GATEWAY                        │
│                  ST7735 1.8"                       │
│                                                    │
│  • Gateway status                                  │
│  • Patient connection                              │
│  • Environment                                     │
│  • Network                                         │
│  • Last Event                                      │
│                                                    │
│       CHỈ HIỂN THỊ — KHÔNG THAO TÁC                │
└──────────────────────┬─────────────────────────────┘
                       │
                    WiFi/LTE
                       │
                       ▼
┌────────────────────────────────────────────────────┐
│                    Qt6                             │
│                                                    │
│  • History                                         │
│  • Charts                                          │
│  • Events                                          │
│  • Alerts                                          │
│  • GPS                                             │
│  • Detailed monitoring                             │
└────────────────────────────────────────────────────┘
```

### 17.1. Patient OLED — Measurement interaction UI

Hiển thị: READY, PLACE NEAR MOUTH, RECORDING, PROCESSING, AUDIO TOO WEAK, PLACE FINGER, HR/SpO₂, RESULT, MONITORING, BATTERY, GATEWAY STATUS.

```text
┌────────────────────────┐
│      PATIENT NODE      │
├────────────────────────┤
│                        │
│       READY            │
│                        │
│   [CHECK]              │
│   [MONITOR]            │
│                        │
├────────────────────────┤
│ B1 CHECK  B2 MONITOR   │
│       B3 SLEEP         │
└────────────────────────┘
```

### 17.2. Gateway TFT — Optional local status (nếu có)

Chỉ phục vụ: latest event, environment, gateway/network status, Wi-Fi/LTE state. Không cần bắt buộc LVGL nếu UI chỉ gồm text/icon/bar đơn giản.

```text
┌────────────────────────┐
│ GATEWAY        ● ONLINE│ 
├────────────────────────┤
│ ┌────────────────────┐ │
│ │ PATIENT            │ │
│ │     ● CONNECTED    │ │
│ │                    │ │
│ │  NON-ASTHMA        │ │
│ │  Last: 14:32       │ │
│ └────────────────────┘ │
│                        │
│ ┌──────────┬─────────┐ │
│ │  28.4°C  │   71%   │ │
│ │   TEMP   │  HUM    │ │
│ └──────────┴─────────┘ │
│                        │
│ ┌────────────────────┐ │
│ │ WiFi ●  MQTT ●     │ │
│ │ LTE  ○             │ │
│ └────────────────────┘ │
└────────────────────────┘
```

### 17.3. Qt6/QML Dashboard — History + Analytics + Monitoring UI

Hiển thị: Patient Sessions, Respiratory Events, HR/SpO₂ history, Environment, Gateway status, Alerts, Location, Network state.

```text
┌─────────────────────────────────────────────────────┐
│                  PATIENT MONITOR                    │
├───────────────┬─────────────────────────────────────┤
│ Patient       │ Respiratory Events                  │
│               │                                     │
│ Last result   │     ╭──╮                            │
│ Non-Asthma    │  ╭──╯  ╰──╮                         │
│               │──╯         ╰───                     │
│ HR 82 BPM     │                                     │
│ SpO₂ 97%      │                                     │
├───────────────┴─────────────────────────────────────┤
│ Environment                                         │
│ Temperature / Humidity / eCO₂ / TVOC                │
├─────────────────────────────────────────────────────┤
│ Event History                                       │
│ 14:32  Check       Non-Asthma   HR 82  SpO₂ 97%     │
│ 13:17  Acoustic   Asthma-like   Quality OK          │
│ 11:05  Check       Non-Asthma   HR 79  SpO₂ 98%     │
└─────────────────────────────────────────────────────┘
```

**Dashboard data model philosophy:** phải phân biệt `Current Environment` với `Latest HR/SpO2 measurement` — không hiển thị HR/SpO₂ cũ như realtime current value nếu user không đang được đo.

**Các màn hình dự kiến:** Overview, Patient Sessions, Respiratory Events, Environment History, Alerts, Device Status, Network Status, Location/Map.

---

## 18. Power architecture

### 18.1. Patient Node

Ba mức tải:
```text
STANDBY = lowest power
MANUAL CHECK = high load, short duration
MONITOR = continuous active acoustic subsystem
```
Cần đo thật: `I_standby`, `I_manual`, `I_monitor`. Battery size chỉ chốt sau khi có current profile.

### 18.2. Gateway

Primary use: always-on USB/power adapter. Battery: optional backup/mobile.

---

## 19. Các parameter chưa khóa (TBD)

**Audio:** Final VAD threshold, `QUALITY_MIN_RMS`, Clip threshold, Active-block ratio, Enclosure acoustic response.

**Patient Node:** Deep sleep vs light sleep, Battery capacity, MAX30102 measurement duration, OLED timeout, Event storage size.

**ESP-NOW/AES-GCM:** schema packet v1 đã khóa ở 64 byte; còn TBD: Retry count, thời gian timeout/backoff, Re-sync algorithm, Channel management, cách nạp/thay khóa và quy tắc phục hồi khi mất đồng bộ thời gian.

**Gateway:** Sensor sampling period, MQTT QoS, Wi-Fi/LTE failover policy, GPS activation policy, TFT requirement.

**Cloud/UI:** MQTT topics, Database, Alert rules, Dashboard layout.

---

## 20. Implementation roadmap

```text
PHASE 1 — AI FREEZE                    DONE

PHASE 2 — PATIENT NODE LOGIC
    State machine, 3 buttons, Quality Gate, Manual Check,
    Monitor Mode, MAX30102 session, low power

PHASE 3 — ESP-NOW EVENT LINK
    Payload 24 byte, AES-128-GCM packet 64 byte, directional keys,
    sequence, secure ACK/NACK, chống trùng, local retry

PHASE 4 — GATEWAY RTOS
    SensorTask, EspNowTask, GatewayManager, Network/MQTT, storage

PHASE 5 — NETWORK
    Wi-Fi primary, LTE fallback/mobile, GPS policy

PHASE 6 — MQTT DATA MODEL
    topics, JSON schema, telemetry, events, alerts

PHASE 7 — QT6/QML DASHBOARD
    overview, charts/history, patient sessions, alerts, map/network

PHASE 8 — FINAL HARDWARE
    enclosure, battery, acoustic port, optional TFT, final wiring/PCB decision

PHASE 9 — EXPERIMENTAL EVALUATION
    AI metrics, Python↔ESP32 parity, acoustic quality, VAD,
    latency, memory, power, ESP-NOW reliability, AES-GCM tamper/replay tests,
    Wi-Fi/LTE, end-to-end demo

PHASE 10 — FINAL NCKH REPORT
```

> Lưu ý: roadmap này là roadmap kỹ thuật theo hệ thống con (từ Architecture doc). Kế hoạch phân công theo 5 thành viên/thứ tự phase cụ thể nằm ở file `NCKH_PHAN_CONG_CONG_VIEC.md` riêng.

---

## 21. Nguyên tắc thiết kế cuối cùng (hợp nhất)

1. **Edge-first:** TinyML chạy cục bộ trên ESP32-S3.
2. **Offline-capable:** Patient Node vẫn hoạt động khi mất Gateway/Internet.
3. **Near-field acoustic acquisition:** không claim far-field.
4. **Quality-before-inference:** audio quá yếu/không hợp lệ không nên bị ép model kết luận.
5. **Event-based patient data:** không giả lập dữ liệu continuous nếu sensor không thật sự dùng liên tục.
6. **Gateway aggregation:** Gateway ghép patient + environment trước khi MQTT.
7. **Separation of responsibility:** Patient Node = sensing/AI; Gateway = network/environment/aggregation.
8. **No medical overclaim:** chỉ hỗ trợ theo dõi/cảnh báo.
9. **Prototype NCKH scope:** ưu tiên tính đúng, ổn định, demo được, đánh giá được — hơn tối ưu như sản phẩm thương mại.
10. **Model final ưu tiên methodology đúng** hơn accuracy đẹp.
11. **INMP441 giữ cho NCKH final**; Near-field là điều kiện acquisition chính.
12. **Quality Gate** kiểm tra final 5s trước inference; **1s PSRAM** chỉ là pre-trigger buffer cho Auto Monitor (không phải noise baseline).
13. **Patient Node dùng state machine**; **Gateway dùng FreeRTOS** vì concurrency thực sự cần.
14. **ESP-NOW + AES-128-GCM:** ESP-NOW giữ làm local event link; Event và ACK/NACK đều được mã hóa/xác thực ở tầng ứng dụng, không stream raw audio lên cloud.
15. **Wi-Fi** là home uplink; **LTE** là fallback/mobile uplink; **GPS** dùng khi mobile/alert, không cần luôn bật ở nhà.
16. **Dashboard phân biệt** dữ liệu continuous và event/session based.
17. Hệ thống hỗ trợ **monitoring/warning, không tự chẩn đoán**.
18. **Không tin dữ liệu trước khi xác thực:** Gateway/Node chỉ xử lý plaintext sau khi GCM tag hợp lệ; tag thay CRC32 trong packet bảo mật.
