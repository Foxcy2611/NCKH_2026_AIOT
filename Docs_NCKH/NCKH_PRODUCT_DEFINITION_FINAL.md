# NCKH ASTHMA — SPECIFICATION HỢP NHẤT (Product Definition + System Architecture)

> Gộp từ `NCKH_PRODUCT_DEFINITION_FINAL.md` + `NCKH_SYSTEM_ARCHITECTURE_FINAL.md`.
> Phần trùng lặp giữa 2 bản (diagram pipeline, Quality Gate, ESP-NOW, state machine...) đã được hợp nhất về một bản duy nhất, ưu tiên bản diễn giải đầy đủ hơn; phần chỉ có ở một bản (button conflict table, task diagram Gateway, roadmap...) được giữ nguyên và chèn vào đúng vị trí.

**Phạm vi:** hoàn thành nguyên mẫu NCKH, không phải thiết bị y tế thương mại, không nhằm tự chẩn đoán bệnh.

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
                    ESP-NOW
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

**Trách nhiệm:** thu audio I2S, VAD, rolling pre-trigger buffer PSRAM, Audio Quality Check, DSP, TinyML inference, voting, MAX30102 theo phiên, OLED interaction, low-power state, local event storage khi mất Gateway, ESP-NOW event TX.

**Không chịu trách nhiệm:** Wi-Fi credential, MQTT, TLS, cloud reconnect, GPS, LTE, environment sensing.

### 3.2. IoT Gateway

Vai trò: Gateway truyền thông, Environmental Node, Data Aggregator, Network Manager.

**Phần cứng:** ESP32, DHT22, BMP280, SGP30, NEO-M8N, A7680C, Wi-Fi, ESP-NOW. Nguồn cấp cố định; pin là tùy chọn nếu cần mobile. TFT là tùy chọn, không bắt buộc.

**Trách nhiệm:** ESP-NOW RX; đọc DHT22/BMP280/SGP30 định kỳ; Environment Snapshot; ghép PatientEvent + Environment Snapshot gần thời điểm tương ứng; quản lý sequence/history; local storage/queue; Wi-Fi; LTE qua A7680C; MQTT publish; GPS khi cần; optional TFT/status UI.

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
                      ESP-NOW
                         |
                         v
                      STANDBY
```

Monitor event xong có thể quay lại `AUTO_MONITOR`.

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
   -> DSP -> 3x Invoke/Voting -> Event -> ESP-NOW -> Return to MONITOR
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

| Current State | CHECK | MONITOR | SLEEP |
|---|---|---|---|
| STANDBY | Start Manual Check | Start Monitor | No-op / sleep |
| MANUAL_CAPTURE | Ignore | Ignore | Abort |
| PROCESSING | Ignore | Ignore | Abort safely |
| AUDIO_RESULT | Start Vital Check | Start Monitor optionally | Sleep |
| VITAL_CHECK | Ignore | Ignore | Abort |
| MONITOR | Ignore or contextual | Exit Monitor | Stop |
| ERROR | Retry/contextual | Monitor optional | Sleep |

Rule final có thể tinh chỉnh khi code UX, nhưng **không dùng long-press/double-click**.

---

## 9. Patient Node không tạo dữ liệu 24/7

Patient Node không thu thập/gửi dữ liệu bệnh nhân liên tục. Hoạt động theo phiên/sự kiện:

- Bấm CHECK → ghi âm 5s + AI + optional HR/SpO₂ → hoàn thành → tạo `PatientEvent` → gửi Gateway.
- Bật MONITOR → mic hoạt động liên tục chờ acoustic event → phát hiện & xử lý xong 1 sự kiện → mới tạo `PatientEvent` → gửi Gateway.
- HR/SpO₂ chỉ đo khi có phiên đo, không giả định đo liên tục 24/7.
- Không có phiên/sự kiện → không gửi dữ liệu bệnh nhân mới.
- Gateway tạm không khả dụng → Patient Node lưu event chưa đồng bộ, gửi lại khi kết nối khôi phục.

```text
KHÔNG CÓ PHIÊN/SỰ KIỆN -> Không gửi gì
CÓ CHECK -> Hoàn thành CHECK -> PatientEvent -> Gửi Gateway
CÓ MONITOR EVENT -> AI xử lý xong -> PatientEvent -> Gửi Gateway
```

---

## 10. Data models

### 10.1. PatientSession (trên Patient Node)

```cpp
struct PatientSession {
    uint32_t session_id;
    uint32_t sequence;
    uint64_t timestamp;

    uint8_t classification;
    float model_score;

    uint8_t audio_quality;

    bool vitals_valid;
    uint16_t heart_rate;
    uint8_t spo2;

    uint8_t battery;
    bool synced;
};
```

Nếu user bỏ qua HR/SpO₂ → `vitals_valid = false`. Không coi là lỗi.

### 10.2. PatientEventPacket (ESP-NOW payload)

```cpp
struct PatientEventPacket {
    uint32_t device_id;
    uint32_t sequence;
    uint32_t session_id;
    uint64_t timestamp;

    uint8_t event_type;

    uint8_t classification;
    float model_score;

    uint8_t audio_quality;

    bool vitals_valid;
    uint16_t heart_rate;
    uint8_t spo2;

    uint8_t battery;
};
```

---

## 11. ESP-NOW — vai trò final

Giữ ESP-NOW làm **local event transport**, không stream raw audio. Patient Node không dùng Wi-Fi/MQTT trực tiếp, chỉ gửi event/session.

```text
Patient Node -> ESP-NOW -> Gateway -> Wi-Fi/LTE -> MQTT
```

**Lợi ích:** giảm độ phức tạp Patient Node, giảm power, không Wi-Fi credentials, không MQTT reconnect, không TLS/broker logic, giữ Patient Node độc lập với Internet.

### 11.1. Reliability

```text
Patient Node --PatientEvent seq=N--> Gateway --ACK seq=N--> Patient Node
```

- ACK nhận được → `synced = true`.
- Timeout → `store local`, `synced = false`.
- Gateway xuất hiện lại → `retry pending events`.
- Gateway giữ `last_sequence_per_patient` để tránh duplicate.

---

## 12. Gateway — Aggregation & Environment

### 12.1. Aggregation flow

```text
PatientEvent -> Get nearest EnvironmentSnapshot -> Get GatewayStatus
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
Patient Node -> ESP-NOW -> Home Gateway -> Wi-Fi -> MQTT -> Qt Dashboard
```
Gateway: always-on, đo môi trường định kỳ, Wi-Fi primary uplink, GPS thường OFF, LTE standby/fallback.
Patient Node: portable, Standby phần lớn thời gian, Manual Check khi cần, Monitor Mode khi user chủ động bật.

### 13.2. Portable Offline

Người dùng mang Patient Node ra khỏi vùng Gateway. Patient Node vẫn hoạt động: Manual Check, TinyML, HR/SpO2, OLED Result, Local event storage. ESP-NOW gửi thất bại → `event.synced = false`; quay lại gần Gateway → `sync pending events`.

> **Nguyên tắc:** Mất Gateway/Internet không làm mất chức năng TinyML cốt lõi.

### 13.3. Mobile Connected

```text
Patient Node -> ESP-NOW -> Gateway -> A7680C LTE -> MQTT
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
TaskEspNow -> PatientEventQueue -> TaskGatewayManager
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
                    ESP-NOW
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

**ESP-NOW:** Exact packet schema, Retry count, ACK timeout, Re-sync algorithm, Channel management.

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
    PatientEvent, sequence, ACK, local retry

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
    latency, memory, power, ESP-NOW reliability, Wi-Fi/LTE, end-to-end demo

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
14. **ESP-NOW** giữ làm local event link, không stream raw audio lên cloud.
15. **Wi-Fi** là home uplink; **LTE** là fallback/mobile uplink; **GPS** dùng khi mobile/alert, không cần luôn bật ở nhà.
16. **Dashboard phân biệt** dữ liệu continuous và event/session based.
17. Hệ thống hỗ trợ **monitoring/warning, không tự chẩn đoán**.
