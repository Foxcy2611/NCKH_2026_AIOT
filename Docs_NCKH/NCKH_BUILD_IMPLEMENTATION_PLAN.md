# NCKH BUILD IMPLEMENTATION PLAN

> **Mục đích:** Đây là file dùng để **bắt đầu và tiếp tục xây dựng project**.
>
> Hai tài liệu còn lại giữ vai trò tham chiếu:
>
> - `NCKH_PRODUCT_DEFINITION_FINAL.md` — định nghĩa sản phẩm cuối cùng.
> - `NCKH_SYSTEM_ARCHITECTURE_FINAL.md` — định nghĩa kiến trúc kỹ thuật.
>
> File này trả lời câu hỏi:
>
> > **“Bây giờ code cái gì trước, cái gì sau, DONE như thế nào?”**

---

# 0. Trạng thái hiện tại

## Đã hoàn thành

### TinyML / Training

- Dataset được chia theo bệnh nhân trước augmentation.
- Augmentation chỉ áp dụng cho tập train.
- Validation/Test giữ dữ liệu gốc.
- Min/Max normalization chỉ lấy từ tập train.
- DS-CNN đã train.
- Model đã lượng tử INT8.
- Model Python và model ESP32 là cùng artifact.
- Pipeline C++ tương đương pipeline Python về chức năng.
- Python và ESP32 đã đối chiếu cùng predicted class trên bộ validation đã kiểm tra.
- Đã kiểm thử raw audio qua loa → INMP441 → ESP32-S3.
- Đã có Voting 3 lần inference.
- Đã có VAD.
- Đã có điều kiện 4 block liên tiếp vượt threshold.
- Đã có rolling pre-trigger buffer 1 giây trong PSRAM.
- Đã có firmware test và firmware deployment gọn.

### AI Baseline

Tạm đóng băng:

```text
AI MODEL = v1.0 NCKH
```

Không retrain nếu không phát hiện lỗi hệ thống hoặc có yêu cầu nghiên cứu mới.

---

# 1. Mục tiêu build tiếp theo

Không build Gateway ngay.

Không build Dashboard ngay.

Không tích hợp toàn bộ module ngay.

## Mục tiêu gần nhất

Hoàn thiện:

> **Patient Node Final Firmware v1**

Bao gồm:

```text
3 Buttons
+
State Machine
+
Manual Respiratory Check
+
Audio Quality Gate
+
Auto Monitor
+
MAX30102 on-demand
+
PatientSession
+
PatientEvent
+
ESP-NOW
+
Low-power behavior
```

---

# 2. PHASE 1 — Refactor Patient Node thành State Machine

## 2.1. Tạo state

Gợi ý:

```cpp
enum class PatientState
{
    STANDBY,

    MANUAL_PREPARE,
    MANUAL_CAPTURE,

    AUDIO_QUALITY_CHECK,
    AI_PROCESSING,
    AUDIO_RESULT,

    VITAL_PREPARE,
    VITAL_MEASURING,

    MONITOR_LISTENING,
    MONITOR_CAPTURE,

    EVENT_SEND,

    ERROR_STATE,
    GO_TO_SLEEP
};
```

Không nhất thiết giữ chính xác tên này, nhưng state phải tách rõ:

- đang chờ;
- đang thu;
- đang AI;
- đang đo MAX30102;
- đang monitor;
- đang gửi event;
- đang ngủ.

---

## 2.2. Quy định 3 nút

### BUTTON_CHECK

Trong `STANDBY`:

```text
CHECK
→ Manual Respiratory Check
```

Trong `AUDIO_RESULT`:

```text
CHECK
→ MAX30102 HR/SpO2
```

### BUTTON_MONITOR

Trong `STANDBY`:

```text
MONITOR
→ Auto Monitor ON
```

Trong `MONITOR_LISTENING`:

```text
MONITOR
→ Stop Monitor
→ STANDBY
```

### BUTTON_SLEEP

Từ các state hợp lệ:

```text
SLEEP
→ abort_requested
→ cleanup
→ low power
```

Không thực hiện cleanup nặng trong ISR.

---

## 2.3. DONE criteria Phase 1

Phase 1 DONE khi:

- Ba nút đọc ổn định.
- Không double trigger do bounce.
- State transition đúng.
- Nhấn sai nút trong lúc capture/processing không phá flow.
- Có thể log state bằng Serial để debug.
- `SLEEP` có thể thoát an toàn khỏi Monitor.

---

# 3. PHASE 2 — Manual Respiratory Check

## 3.1. User flow

```text
STANDBY
   |
 CHECK
   |
   v
OLED:
PLACE NEAR MOUTH
   |
   v
Countdown
   |
   v
Record exact 5 seconds
```

### Quan trọng

Manual Check:

- Không dùng VAD để quyết định có capture hay không.
- Không dùng 1 giây pre-trigger PSRAM.
- Thu đúng 5 giây input model.

---

## 3.2. Audio acquisition

Thông số:

```text
Sample rate = 16000 Hz
Duration    = 5 s
Samples     = 80000
```

Dữ liệu raw phải được lưu/stream theo cách tương thích pipeline hiện tại.

---

## 3.3. DONE criteria Phase 2

- Bấm CHECK bắt đầu đúng một phiên.
- OLED hướng dẫn rõ.
- Thu đúng 5 giây.
- Audio buffer không overflow.
- Không ảnh hưởng model deployment hiện tại.
- Có thể dump/test raw nếu cần debug.

---

# 4. PHASE 3 — Audio Quality Gate

## 4.1. Mục tiêu

Quality Gate trả lời:

> Final audio 5 giây có đủ chất lượng kỹ thuật để cho model inference không?

Không phải classifier.

Không phải VAD.

---

## 4.2. Metrics

Trong lúc capture cập nhật:

```cpp
struct AudioQualityMetrics
{
    float rms;
    int32_t peak;

    uint32_t clipped_samples;

    uint32_t active_blocks;
    uint32_t total_blocks;
};
```

Kết quả:

```cpp
enum class AudioQuality
{
    OK,
    TOO_WEAK,
    TOO_LOUD,
    INACTIVE
};
```

---

## 4.3. Quality logic v1

### TOO_WEAK

```text
RMS < QUALITY_MIN_RMS
```

### TOO_LOUD

```text
clipped_samples > CLIPPING_LIMIT
```

### INACTIVE

```text
active_blocks < MIN_ACTIVE_BLOCKS
```

### OK

Pass tất cả điều kiện.

---

## 4.4. Threshold

Chưa khóa hard-code như specification cuối.

Ban đầu:

```text
QUALITY_MIN_RMS      = TBD
CLIP_LEVEL           = TBD
MIN_ACTIVE_BLOCKS    = TBD
```

Thu log thực nghiệm rồi calibration sau.

---

## 4.5. DONE criteria Phase 3

Test ít nhất:

- Im lặng.
- Nói/thở quá nhỏ.
- Audio hợp lệ.
- Audio quá lớn/clipping.
- Một tiếng đập ngắn nhưng phần còn lại im lặng.

Firmware phải phân biệt được các case cơ bản.

---

# 5. PHASE 4 — Manual TinyML Pipeline

Sau khi Quality PASS:

```text
5 s raw
  |
  v
Butterworth 100–2000 Hz
  |
  v
Pre-emphasis 0.97
  |
  v
STFT / Mel
  |
  v
64 x 129
  |
  v
dB [-80, 0]
  |
  v
Normalize
  |
  v
INT8
  |
  v
DS-CNN
```

Sau đó thực hiện Voting như firmware hiện tại.

---

## 5.1. Output

Ví dụ:

```cpp
struct AudioInferenceResult
{
    uint8_t classification;

    float score;

    uint8_t asthma_votes;
    uint8_t non_asthma_votes;

    AudioQuality quality;
};
```

---

## 5.2. DONE criteria Phase 4

- Manual Check chạy trọn flow.
- Không regress kết quả so với deployment hiện tại.
- Quality FAIL thì không Invoke model.
- Quality PASS thì model chạy.
- Voting hoạt động đúng.
- OLED hiện result.

---

# 6. PHASE 5 — MAX30102 theo phiên

## 6.1. Flow

Sau Audio Result:

```text
OLED:
AUDIO COMPLETE

PLACE FINGER
PRESS CHECK
```

User nhấn CHECK:

```text
MAX30102 ON
   |
   v
Finger detect
   |
   v
Collect
   |
   v
HR / SpO2
```

Không chạy MAX30102 mặc định trong Monitor Mode.

---

## 6.2. Timeout

Phải có timeout.

Ví dụ concept:

```text
No finger
→ timeout
→ VITALS_NOT_AVAILABLE
```

Không block vô hạn.

---

## 6.3. DONE criteria Phase 5

- Finger present → đo được HR/SpO₂.
- Finger absent → timeout sạch.
- User nhấn SLEEP → abort sạch.
- Không làm crash Audio/AI state.

---

# 7. PHASE 6 — PatientSession

Sau Manual Check:

```cpp
struct PatientSession
{
    uint32_t session_id;
    uint32_t sequence;

    uint64_t timestamp;

    AudioInferenceResult audio;

    bool vitals_valid;
    uint16_t heart_rate;
    uint8_t spo2;

    uint8_t battery_percent;

    bool synced;
};
```

---

## 7.1. Session rules

### Audio only

Nếu user không đo MAX30102:

```text
vitals_valid = false
```

Session vẫn hợp lệ.

### Audio + vitals

Nếu đã đo:

```text
vitals_valid = true
```

---

## 7.2. DONE criteria Phase 6

Có thể Serial print một `PatientSession` hoàn chỉnh sau mỗi CHECK.

---

# 8. PHASE 7 — Auto Monitor

Đưa pipeline cũ vào state machine mới.

## 8.1. Flow

```text
MONITOR
  |
  v
I2S continuous
  |
  v
Rolling PSRAM buffer 1 s
  |
  v
VAD
  |
  v
4 consecutive blocks > threshold
  |
  v
TRIGGER
```

Khi trigger:

```text
1 s pre-trigger
+
4 s post-trigger
=
5 s final audio
```

Sau đó:

```text
Quality Gate
    |
   PASS
    |
    v
DSP
    |
    v
3x Invoke / Voting
```

---

## 8.2. Monitor result

MAX30102 không tự chạy.

Monitor Event gồm:

```text
Audio result
Audio quality
Timestamp
Battery
```

Vitals:

```text
invalid / unavailable
```

---

## 8.3. DONE criteria Phase 7

- Monitor chạy lâu không crash.
- Rolling PSRAM đúng.
- VAD trigger đúng flow.
- 1 s pre-trigger không mất.
- Quality Gate dùng chung được với Manual.
- Inference xong quay lại Monitor.
- MONITOR button stop được.
- SLEEP abort được.

---

# 9. PHASE 8 — PatientEvent

## 9.1. Event types

```cpp
enum class PatientEventType
{
    MANUAL_CHECK,
    MONITOR_EVENT,
    STATUS
};
```

---

## 9.2. Packet concept

```cpp
struct PatientEventPacket
{
    uint32_t device_id;

    uint32_t sequence;
    uint32_t session_id;

    uint64_t timestamp;

    uint8_t event_type;

    uint8_t classification;
    float model_score;

    uint8_t asthma_votes;
    uint8_t non_asthma_votes;

    uint8_t audio_quality;

    bool vitals_valid;
    uint16_t heart_rate;
    uint8_t spo2;

    uint8_t battery_percent;
};
```

Không gửi:

- raw PCM;
- Mel Spectrogram;
- tensor;
- model internals.

---

# 10. PHASE 9 — ESP-NOW Event Link

## 10.1. Flow

```text
Patient Node
     |
 PatientEvent
     |
     v
 ESP-NOW
     |
     v
 Gateway
```

---

## 10.2. ACK

```text
Patient
   |
   | seq=105
   v
Gateway
   |
   | ACK 105
   v
Patient
```

Nếu ACK OK:

```text
synced = true
```

Nếu fail:

```text
synced = false
store local
```

---

## 10.3. Local retry

Khi Gateway xuất hiện lại:

```text
pending events
    |
    v
retry send
```

Gateway phải chống duplicate bằng sequence.

---

## 10.4. DONE criteria Phase 9

- Patient → Gateway nhận packet.
- ACK hoạt động.
- Test mất Gateway.
- Patient không crash.
- Event được lưu pending.
- Gateway trở lại → sync thành công.
- Duplicate không được publish hai lần.

---

# 11. PHASE 10 — Gateway FreeRTOS Skeleton

Sau khi Patient + ESP-NOW hoàn chỉnh mới build Gateway.

## 11.1. Task gợi ý

```text
TaskEspNow
TaskSensor
TaskGatewayManager
TaskNetwork
TaskDisplay       optional
```

GPS có thể tách task riêng khi cần.

---

## 11.2. Queue flow

```text
ESP-NOW callback
      |
      v
PatientEventQueue
      |
      v
TaskGatewayManager
```

Không parse/aggregate/MQTT trực tiếp trong callback.

---

# 12. PHASE 11 — Gateway Sensor Layer

Integrate lần lượt:

```text
DHT22
  |
BMP280
  |
SGP30
```

Tạo:

```cpp
struct EnvironmentSnapshot
{
    float temperature;
    float humidity;

    float pressure;

    uint16_t tvoc;
    uint16_t eco2;

    uint64_t timestamp;

    uint32_t valid_mask;
};
```

Không để sensor lỗi block cả Gateway.

---

# 13. PHASE 12 — Gateway Aggregator

Gateway nhận:

```text
PatientEvent
```

rồi lấy:

```text
nearest/current EnvironmentSnapshot
```

ghép thành:

```cpp
struct CompleteRecord
{
    PatientEventPacket patient;
    EnvironmentSnapshot environment;

    // optional:
    // GPS
    // gateway network state
};
```

---

# 14. PHASE 13 — Wi-Fi + MQTT

HOME MODE:

```text
Gateway
  |
 Wi-Fi
  |
 MQTT
```

Patient Node vẫn chỉ ESP-NOW.

---

## 14.1. MQTT data chưa khóa

Sẽ định nghĩa sau khi `CompleteRecord` ổn.

Các nhóm dự kiến:

```text
patient event
environment
gateway status
alert
```

---

# 15. PHASE 14 — LTE + GPS

Sau Wi-Fi MQTT ổn mới thêm:

```text
A7680C
+
NEO-M8N
```

## HOME

```text
Wi-Fi primary
LTE standby/fallback
GPS mostly OFF
```

## MOBILE

```text
LTE primary
GPS ON when needed
```

Không làm LTE/GPS trước Wi-Fi MQTT.

---

# 16. PHASE 15 — Qt6/QML Dashboard

Chỉ bắt đầu thiết kế dashboard khi đã chốt:

```text
PatientEvent
EnvironmentSnapshot
CompleteRecord
MQTT schema
```

Dashboard tối thiểu:

```text
Overview
Patient Session History
Respiratory Event History
HR / SpO2 History
Environment Charts
Gateway Status
Network Status
Alerts
Location optional
```

---

# 17. PHASE 16 — Hardware / Enclosure Freeze

Sau firmware/network ổn mới chốt:

## Patient Node

- Vị trí INMP441.
- Acoustic opening.
- OLED.
- 3 buttons.
- MAX30102 finger placement.
- Battery.
- USB/power.
- Kích thước enclosure.

## Gateway

- Air vents cho sensor môi trường.
- Antenna layout.
- A7680C.
- GPS antenna.
- Power.
- Optional TFT.

---

# 18. PHASE 17 — Calibration

Sau enclosure:

## Audio

Chốt:

```text
VAD_THRESHOLD
QUALITY_MIN_RMS
CLIPPING_LIMIT
MIN_ACTIVE_BLOCKS
```

Không calibration threshold quá sớm khi chưa có final acoustic enclosure.

---

# 19. PHASE 18 — Experimental Evaluation

## AI

- Accuracy.
- Precision.
- Recall.
- F1.
- Confusion Matrix.

## Deployment

- Python ↔ ESP32 parity.
- Inference latency.
- DSP latency.
- RAM.
- Flash.
- PSRAM.

## Audio

- Quality Gate.
- VAD.
- Near-field acquisition.
- Noise scenarios.

## Power

Đo:

```text
I_standby
I_manual
I_monitor
```

## Communication

- ESP-NOW success rate.
- ACK/retry.
- Gateway loss/reconnect.
- Wi-Fi.
- LTE fallback.

## End-to-end

```text
Patient Check
   |
   v
TinyML
   |
   v
ESP-NOW
   |
   v
Gateway
   |
   v
MQTT
   |
   v
Dashboard
```

Đo end-to-end latency.

---

# 20. PHASE 19 — Final NCKH Demo

Demo đề xuất:

## Scenario A — Manual Check

```text
Patient Node
→ CHECK
→ audio
→ TinyML
→ HR/SpO2
→ ESP-NOW
→ Gateway
→ MQTT
→ Qt Dashboard
```

## Scenario B — Monitor

```text
MONITOR
→ VAD
→ pre-buffer
→ AI event
→ Gateway
→ Dashboard
```

## Scenario C — Gateway loss

```text
Patient Node standalone
→ local result
→ local event storage
```

Sau reconnect:

```text
sync history
```

## Scenario D — Network fallback

```text
Wi-Fi unavailable
→ LTE
→ MQTT
```

nếu LTE được hoàn thiện trong final scope.

---

# 21. Việc cần làm NGAY

## Step 1

Không đụng Gateway.

Mở firmware Patient Node hiện tại.

## Step 2

Refactor thành:

```text
PatientState
+
Button events
```

## Step 3

Làm `CHECK` Manual 5-second acquisition.

## Step 4

Viết:

```cpp
Audio_CheckQuality()
```

## Step 5

Nối lại DSP + DS-CNN + Voting.

## Step 6

Thêm MAX30102 bằng CHECK lần 2.

## Step 7

Mới đưa pipeline Monitor cũ vào state machine.

---

# 22. Quy tắc build

Mỗi Phase chỉ chuyển tiếp khi có:

```text
CODE
+
TEST
+
LOG/RESULT
+
README cập nhật
```

Không tích hợp nhiều subsystem chưa test cùng lúc.

Ví dụ:

```text
Quality Gate chưa test
+
ESP-NOW chưa test
+
MAX30102 chưa test
```

thì không nhét cả ba vào một lần.

---

# 23. Thứ tự tài liệu cần đọc

Khi bắt tay code:

```text
1. NCKH_BUILD_IMPLEMENTATION_PLAN.md
```

Đây là file chính.

Khi không nhớ sản phẩm phải hoạt động như thế nào:

```text
2. NCKH_PRODUCT_DEFINITION_FINAL.md
```

Khi cần xem state machine, packet, RTOS, data flow:

```text
3. NCKH_SYSTEM_ARCHITECTURE_FINAL.md
```

Tóm lại:

```text
BUILD PLAN
   |
   +--> PRODUCT DEFINITION   khi cần hiểu WHY/WHAT
   |
   +--> SYSTEM ARCHITECTURE  khi cần hiểu HOW
```

---

# 24. Freeze hiện tại

```text
PRODUCT DEFINITION      = v0.1 FROZEN
SYSTEM ARCHITECTURE     = v0.1 FROZEN
BUILD IMPLEMENTATION    = ACTIVE
```

Hai file đầu không chỉnh liên tục theo từng bug code.

Mọi thay đổi implementation nhỏ ghi vào Build Plan hoặc README module.

Chỉ sửa Product/Architecture khi có thay đổi thực sự về thiết kế hệ thống.
