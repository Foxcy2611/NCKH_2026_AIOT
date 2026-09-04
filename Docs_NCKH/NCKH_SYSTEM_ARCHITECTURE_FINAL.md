# NCKH SYSTEM ARCHITECTURE — TECHNICAL FREEZE v0.1

## 1. Tổng quan kiến trúc

```text
                    PATIENT
                       |
                       v
          +--------------------------+
          |      PATIENT NODE        |
          |       ESP32-S3           |
          |                          |
          | INMP441                  |
          | MAX30102                 |
          | OLED                     |
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
          | DHT22                    |
          | BMP280                   |
          | SGP30                    |
          | NEO-M8N                  |
          | A7680C                   |
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

# 2. Phân chia trách nhiệm

## 2.1. Patient Node

Patient Node chịu trách nhiệm:

- Thu audio I2S.
- VAD.
- Rolling pre-trigger buffer trong PSRAM.
- Audio Quality Check.
- DSP.
- TinyML inference.
- Voting.
- MAX30102 theo phiên.
- OLED interaction.
- Low-power state.
- Local event storage khi mất Gateway.
- ESP-NOW event TX.

Patient Node **không chịu trách nhiệm**:

- Wi-Fi credential management.
- MQTT.
- TLS.
- Cloud reconnect.
- GPS.
- LTE.
- Environment sensing.

---

## 2.2. Gateway

Gateway chịu trách nhiệm:

- ESP-NOW RX.
- DHT22/BMP280/SGP30.
- Environment Snapshot.
- Patient Event aggregation.
- Sequence/history.
- Local storage/queue.
- Wi-Fi.
- LTE via A7680C.
- MQTT.
- GPS khi cần.
- Optional TFT/status UI.

---

# 3. AI pipeline

## 3.1. Input

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
STFT / Mel Filterbank
        |
        v
64 x 129 Mel
        |
        v
dB [-80, 0]
        |
        v
Normalize [0,1]
        |
        v
INT8 Quantization
        |
        v
DS-CNN
        |
        v
Classification
```

## 3.2. Classification terminology

Output application-level:

- `ASTHMA_LIKE`
- `NON_ASTHMA`

Không dùng:

- `DIAGNOSED_ASTHMA`
- `SEVERE_ATTACK`
- `PATIENT_HAS_ASTHMA`

---

# 4. Audio acquisition paths

## 4.1. Manual Check

```text
CHECK
  |
  v
Record exact 5 seconds
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
Result
```

Không dùng pre-trigger 1 s.

---

## 4.2. Auto Monitor

```text
MONITOR
  |
  v
Continuous I2S
  |
  v
Rolling 1 s PSRAM
  |
  v
VAD
  |
  v
4 consecutive active blocks
  |
  v
Trigger
  |
  +-------------------+
  |                   |
1 s pre            4 s post
  |                   |
  +---------+---------+
            |
            v
      Final 5 s audio
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
```

---

# 5. Audio Quality Gate

## 5.1. API concept

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
```

Concept API:

```cpp
AudioQuality Audio_CheckQuality(
    const int16_t* audio,
    size_t samples,
    AudioQualityMetrics* metrics
);
```

## 5.2. Metrics

Dự kiến sử dụng:

- RMS.
- Peak.
- Clipping ratio/count.
- Active block count/ratio.

Threshold final:

**TBD sau enclosure + hardware calibration.**

## 5.3. Quan hệ với VAD

```text
VAD:
"Có event đủ điều kiện để AUTO bắt đầu capture chưa?"

QUALITY GATE:
"Final 5 s đã thu có đủ chất lượng để model được phép inference chưa?"
```

Hai module không thay thế nhau.

---

# 6. Patient Node State Machine

## 6.1. High-level

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
                  | SESSION READY|
                  +------+------+
                         |
                      ESP-NOW
                         |
                         v
                      STANDBY
```

Monitor event xong có thể quay lại `AUTO_MONITOR`.

---

# 7. Button behavior

## 7.1. CHECK

### Trong STANDBY

- Bắt đầu Manual Respiratory Check.

### Trong AUDIO_RESULT

- Bắt đầu HR/SpO₂ measurement.

### Trong MONITOR_ALERT / event result

- Có thể bắt đầu HR/SpO₂ measurement nếu UX final cần.

---

## 7.2. MONITOR

### Trong STANDBY

- Bật Auto Monitor.

### Trong MONITOR

- Tắt Monitor và quay về Standby.

Không dùng long-press.

---

## 7.3. SLEEP / STOP

Ưu tiên cao.

- Đặt `abort_requested`.
- State machine cleanup peripheral.
- Enter low power.

Không xử lý heavy cleanup trong ISR.

---

# 8. Button conflict policy

| Current State | CHECK | MONITOR | SLEEP |
|---|---|---|---|
| STANDBY | Start Manual Check | Start Monitor | No-op / sleep |
| MANUAL_CAPTURE | Ignore | Ignore | Abort |
| PROCESSING | Ignore | Ignore | Abort safely |
| AUDIO_RESULT | Start Vital Check | Start Monitor optionally | Sleep |
| VITAL_CHECK | Ignore | Ignore | Abort |
| MONITOR | Ignore or contextual | Exit Monitor | Stop |
| ERROR | Retry/contextual | Monitor optional | Sleep |

Rule final có thể tinh chỉnh khi code UX, nhưng không dùng long-press/double-click.

---

# 9. Patient Session model

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

Nếu user bỏ qua HR/SpO₂:

```text
vitals_valid = false
```

Không coi là lỗi.

---

# 10. ESP-NOW Protocol

## 10.1. Vai trò

ESP-NOW là:

> **local event transport**

Không stream raw audio.

Patient Node không cần Wi-Fi/MQTT.

---

## 10.2. Packet concept

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

## 10.3. Reliability

```text
Patient Node
    |
    | PatientEvent seq=N
    v
Gateway
    |
    | ACK seq=N
    v
Patient Node
```

Nếu ACK:

```text
synced = true
```

Nếu timeout:

```text
store local
synced = false
```

Khi Gateway xuất hiện lại:

```text
retry pending events
```

Gateway giữ:

```text
last_sequence_per_patient
```

để tránh duplicate.

---

# 11. Gateway aggregation

Khi nhận PatientEvent:

```text
PatientEvent
      |
      v
Get nearest EnvironmentSnapshot
      |
      v
Get GatewayStatus
      |
      v
Optional GPS
      |
      v
Build CompleteRecord
      |
      v
MQTT Publish
```

Cloud không cần tự ghép hai stream rời rạc nếu Gateway đã aggregate.

---

# 12. Environment acquisition

Gateway lấy định kỳ:

## DHT22

- Temperature.
- Humidity.

## BMP280

- Pressure.
- Temperature.

## SGP30

- TVOC.
- eCO₂ / CO₂-equivalent.

Không mô tả SGP30 là direct CO₂ sensor.

---

# 13. Gateway operating modes

## 13.1. HOME MODE

```text
ESP-NOW RX
Environment sensing
Wi-Fi primary
MQTT
GPS usually OFF
LTE standby/fallback
```

Gateway thường được cấp nguồn liên tục.

---

## 13.2. MOBILE MODE

```text
ESP-NOW RX
Environment optional/periodic
LTE primary
GPS ON when needed
MQTT
```

Dùng khi user muốn realtime outside-home connectivity.

---

# 14. Network policy

## Home

```text
Wi-Fi -> MQTT
```

## Wi-Fi unavailable

```text
A7680C LTE -> MQTT
```

## Mobile

```text
A7680C LTE -> MQTT
```

Patient Node không biết uplink hiện tại là Wi-Fi hay LTE.

---

# 15. ESP-NOW + Wi-Fi coexistence

Khi Gateway dùng Wi-Fi + ESP-NOW:

- Cả hai dùng cùng radio 2.4 GHz.
- ESP-NOW peer và Wi-Fi AP phải phù hợp về channel.
- Prototype NCKH chấp nhận cấu hình AP channel cố định hoặc cơ chế đồng bộ channel đơn giản.

Nếu Wi-Fi coexistence gây vấn đề:

```text
ESP-NOW local link
+
LTE uplink
```

là đường thay thế.

---

# 16. LTE data policy

Không upload raw audio liên tục.

Chỉ publish:

- PatientEvent.
- Environment telemetry.
- Device status.
- Alert.
- Optional GPS.

Mục tiêu:

- giảm data usage;
- giảm latency;
- giữ privacy;
- đúng tinh thần TinyML edge processing.

---

# 17. Patient Node firmware architecture

## 17.1. Design philosophy

**State-machine centric.**

Không chia toàn bộ ứng dụng thành nhiều FreeRTOS tasks nếu không cần.

Arduino ESP32 vẫn chạy trên FreeRTOS ở tầng framework.

Có thể dùng task nền riêng cho I2S nếu implementation cần, nhưng application flow chính vẫn là state machine.

---

# 18. Gateway firmware architecture

## 18.1. Design philosophy

**RTOS task centric.**

Gateway phải concurrent:

- ESP-NOW.
- Environment sensors.
- Wi-Fi.
- LTE.
- MQTT.
- GPS.
- Storage.
- Optional TFT.

---

## 18.2. Task proposal

```text
TaskEspNow
    |
    v
PatientEventQueue
    |
    v
TaskGatewayManager
    |
    +-------> Storage
    |
    +-------> PublishQueue
                    |
                    v
              TaskNetwork/MQTT
```

Song song:

```text
TaskSensor
    |
    v
EnvironmentSnapshot

TaskGps
    |
    v
LocationSnapshot
```

Optional:

```text
TaskDisplay
```

---

# 19. Gateway robustness rules

RTOS không tự đảm bảo fault isolation.

Các rule:

- Driver có timeout.
- Không `while(1)` blocking không kiểm soát.
- Queue có timeout.
- Mutex có timeout.
- Reconnect network non-blocking hoặc bounded.
- Task Watchdog.
- Retry có giới hạn.
- Một sensor lỗi không được làm treo MQTT/ESP-NOW.
- Network lỗi không được làm dừng environment acquisition.

---

# 20. Data categories

## Periodic data

- Environment telemetry.
- Gateway status.
- Heartbeat.

## Event/session data

- Manual Respiratory Check.
- Auto Monitor Event.
- HR/SpO₂.
- Alert.
- Sync status.

---

# 21. Dashboard data model philosophy

Dashboard phải phân biệt:

```text
Current Environment
```

với:

```text
Latest HR/SpO2 measurement
```

Không hiển thị HR/SpO₂ cũ như realtime current value nếu user không đang được đo.

Các màn hình dự kiến:

- Overview.
- Patient Sessions.
- Respiratory Events.
- Environment History.
- Alerts.
- Device Status.
- Network Status.
- Location/Map.

---

# 22. UI hierarchy

## Patient OLED

Measurement interaction.

## Gateway TFT

Optional local home status.

## Qt6/QML

Full historical/analytical dashboard.

Nếu Gateway TFT được dùng, không cần bắt buộc LVGL nếu UI chỉ gồm text/icon/bar đơn giản.

---

# 23. Power architecture

## Patient Node

Ba mức tải:

```text
STANDBY
= lowest power

MANUAL CHECK
= high load, short duration

MONITOR
= continuous active acoustic subsystem
```

Cần đo thật:

- `I_standby`
- `I_manual`
- `I_monitor`

Battery size chỉ chốt sau khi có current profile.

---

## Gateway

Primary use:

- always-on USB/power adapter.

Battery:

- optional backup/mobile.

---

# 24. Các parameter chưa khóa

## Audio

- Final VAD threshold.
- `QUALITY_MIN_RMS`.
- Clip threshold.
- Active-block ratio.
- Enclosure acoustic response.

## Patient Node

- Deep sleep vs light sleep.
- Battery capacity.
- MAX30102 measurement duration.
- OLED timeout.
- Event storage size.

## ESP-NOW

- Exact packet schema.
- Retry count.
- ACK timeout.
- Re-sync algorithm.
- Channel management.

## Gateway

- Sensor sampling period.
- MQTT QoS.
- Wi-Fi/LTE failover policy.
- GPS activation policy.
- TFT requirement.

## Cloud/UI

- MQTT topics.
- Database.
- Alert rules.
- Dashboard layout.

---

# 25. Implementation roadmap

```text
PHASE 1 — AI FREEZE
    DONE

PHASE 2 — PATIENT NODE LOGIC
    - State machine
    - 3 buttons
    - Quality Gate
    - Manual Check
    - Monitor Mode
    - MAX30102 session
    - low power

PHASE 3 — ESP-NOW EVENT LINK
    - PatientEvent
    - sequence
    - ACK
    - local retry

PHASE 4 — GATEWAY RTOS
    - SensorTask
    - EspNowTask
    - GatewayManager
    - Network/MQTT
    - storage

PHASE 5 — NETWORK
    - Wi-Fi primary
    - LTE fallback/mobile
    - GPS policy

PHASE 6 — MQTT DATA MODEL
    - topics
    - JSON schema
    - telemetry
    - events
    - alerts

PHASE 7 — QT6/QML DASHBOARD
    - overview
    - charts/history
    - patient sessions
    - alerts
    - map/network

PHASE 8 — FINAL HARDWARE
    - enclosure
    - battery
    - acoustic port
    - optional TFT
    - final wiring/PCB decision

PHASE 9 — EXPERIMENTAL EVALUATION
    - AI metrics
    - Python↔ESP32 parity
    - acoustic quality
    - VAD
    - latency
    - memory
    - power
    - ESP-NOW reliability
    - Wi-Fi/LTE
    - end-to-end demo

PHASE 10 — FINAL NCKH REPORT
```

---

# 26. Final technical principles

1. Model final ưu tiên methodology đúng hơn accuracy đẹp.
2. INMP441 được giữ cho NCKH final.
3. Near-field là điều kiện acquisition chính.
4. Quality Gate kiểm tra final 5 s trước inference.
5. 1 s PSRAM chỉ là pre-trigger buffer cho Auto Monitor.
6. Patient Node dùng state machine.
7. Gateway dùng FreeRTOS vì concurrency thực sự cần.
8. ESP-NOW được giữ làm local event link.
9. Gateway aggregate patient + environment trước MQTT.
10. Wi-Fi là home uplink; LTE là fallback/mobile uplink.
11. GPS dùng khi mobile/alert, không cần luôn bật ở nhà.
12. Patient Node vẫn hoạt động offline khi mất Gateway.
13. Không stream raw audio lên cloud.
14. Dashboard phân biệt dữ liệu continuous và event/session based.
15. Hệ thống hỗ trợ monitoring/warning, không tự chẩn đoán.
