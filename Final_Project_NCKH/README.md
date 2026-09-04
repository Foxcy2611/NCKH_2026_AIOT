# 🫁 Final Project — Edge AI & IoT hỗ trợ theo dõi hen suyễn

> **Đề tài NCKH:**  
> **Nghiên cứu, thiết kế và chế tạo hệ thống IoT ứng dụng TinyML hỗ trợ theo dõi và cảnh báo sớm cho bệnh nhân hen suyễn.**

Đây là thư mục chứa **source cuối cùng của hệ thống**, nơi tích hợp các thành phần đã được nghiên cứu và kiểm thử ở các prototype trước đó:

```text
AI Model
   +
Patient Edge Node
   +
IoT Gateway
   +
Qt6/QML Dashboard
   =
FINAL NCKH SYSTEM
```

Khác với các thư mục thử nghiệm như `AI_Training_Model/`, `Deploy_Model/`,
`ESP32-Sensor_Suite/` và `ESP32-Qt-Telemetry/`, thư mục này chỉ tập trung vào
**sản phẩm tích hợp cuối cùng**.

---

# 📂 Project Structure

```text
Final_Project_NCKH/
│
├── README.md
│
├── AI_Model/
│   ├── Asthma_Model.h
│   └── log_train.log
│
├── Patient_Node/
│   └── [ESP32-S3 final firmware]
│
├── Gateway/
│   └── [ESP32 final firmware]
│
└── Dashboard_Qt6/
    └── [Qt6 / QML final application]
```

## Vai trò từng thành phần

| Thành phần | Vai trò |
|---|---|
| `AI_Model/` | Model artifact được deploy lên Patient Node |
| `Patient_Node/` | Thiết bị cá nhân chạy pin, thu audio + TinyML + HR/SpO₂ |
| `Gateway/` | Nhận PatientEvent, thu môi trường, aggregation và network |
| `Dashboard_Qt6/` | Dashboard giám sát, lịch sử và cảnh báo |
| `README.md` | Overview và entry point của Final Project |

Các driver/prototype được phát triển trước đó **không bị xóa** khỏi repository:

```text
ESP32-Sensor_Suite/
ESP32-Qt-Telemetry/
```

Final Project sử dụng lại các thành phần đã ổn định thay vì viết lại toàn bộ từ đầu.

---

# 🧩 1. System Overview

Hệ thống gồm hai thiết bị embedded chính và một ứng dụng giám sát:

```text
                    ┌─────────────────────────┐
                    │     PATIENT NODE        │
                    │       ESP32-S3          │
                    │                         │
                    │ INMP441 ──► DSP ──► AI  │
                    │ MAX30102 ──► HR / SpO2  │
                    │ OLED + 3 Buttons        │
                    │ Battery                 │
                    └────────────┬────────────┘
                                 │
                              ESP-NOW
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │        GATEWAY          │
                    │          ESP32          │
                    │                         │
                    │ DHT22 / BMP280 / SGP30  │
                    │ NEO-M8N / A7680C        │
                    │ ESP-NOW RX              │
                    │ Aggregation             │
                    │ FreeRTOS                │
                    └────────────┬────────────┘
                                 │
                         Wi-Fi / LTE
                                 │
                                MQTT
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │      Qt6 / QML          │
                    │       Dashboard         │
                    │                         │
                    │ History / Charts / Alert│
                    │ Environment / Status    │
                    └─────────────────────────┘
```

Nguyên tắc chính:

> **Patient Node xử lý dữ liệu bệnh nhân tại Edge. Gateway chịu trách nhiệm thu thập, tổng hợp và đưa dữ liệu lên hệ thống mạng.**

---

# 🧠 2. AI Model

AI được freeze ở:

```text
AI MODEL v1.0
```

Model được nghiên cứu và kiểm thử bên ngoài thư mục Final:

```text
AI_Training_Model/
        ↓
Deploy_Model/
        ↓
AI_Model/
        ↓
Patient_Node
```

## 2.1. Model

```text
Architecture : DS-CNN
Task         : Binary Classification
Classes      : Asthma / Non-Asthma
Runtime      : TensorFlow Lite Micro
Target       : ESP32-S3
Quantization : Full INT8
```

## 2.2. Input specification

```text
16 kHz
5 seconds
80,000 samples
        ↓
Butterworth Bandpass
100–2000 Hz
        ↓
Pre-emphasis
0.97
        ↓
Mel-Spectrogram
64 × 129
        ↓
dB [-80, 0]
        ↓
Normalize [0, 1]
        ↓
INT8
        ↓
DS-CNN
```

## 2.3. Current AI baseline

```text
Train      : 1666
Validation : 108
Test       : 113

Test Accuracy : 86.73%
Asthma Recall : 90.00%
```

Đây là kết quả test độc lập của pipeline hiện tại, không phải peak validation accuracy.

## 2.4. Terminology

Output của hệ thống nên được hiểu là:

```text
ASTHMA_LIKE
NON_ASTHMA
```

Không mô tả output như:

```text
PATIENT_HAS_ASTHMA
DIAGNOSED_ASTHMA
SEVERE_ASTHMA_ATTACK
```

Hệ thống là prototype nghiên cứu hỗ trợ theo dõi/cảnh báo kỹ thuật,
không thay thế chẩn đoán y khoa.

---

# 👤 3. Patient Edge Node

## 3.1. Product concept

Patient Node là một thiết bị:

> **Portable handheld respiratory monitoring device**

Đặc điểm:

- chạy pin;
- kích thước nhỏ;
- có thể cầm tay;
- có thể bỏ túi;
- có thể đặt cạnh giường;
- có thể mang ra ngoài;
- không định hướng thành smartwatch;
- không yêu cầu đeo liên tục trên người.

Hardware chính:

```text
ESP32-S3-N16R8
INMP441
MAX30102
SSD1306 OLED
CHECK button
MONITOR button
SLEEP / STOP button
Battery
```

---

# 🎛️ 4. Patient Node Operating Modes

Patient Node dùng **3 nút vật lý riêng** để tránh long-press/double-click và làm state machine rõ ràng:

```text
┌────────┐   ┌─────────┐   ┌────────────┐
│ CHECK  │   │ MONITOR │   │ SLEEP/STOP │
└────────┘   └─────────┘   └────────────┘
```

---

## 4.1. STANDBY / SLEEP

Đây là trạng thái mặc định.

Khi không có phiên đo:

```text
INMP441  = OFF
I2S      = OFF
MAX30102 = OFF
OLED     = OFF / timeout
ESP-NOW  = OFF / low-power
ESP32-S3 = low power
```

Mục tiêu:

- giảm tiêu thụ pin;
- không thu audio vô nghĩa;
- không giả lập patient telemetry liên tục.

---

# 🩺 5. Button 1 — CHECK

CHECK là **Manual Respiratory Check**.

## Bước 1 — Audio Check

Người dùng:

1. Cầm Patient Node.
2. Đưa thiết bị gần vùng miệng.
3. Nhấn `CHECK`.

OLED hướng dẫn:

```text
PLACE NEAR MOUTH
        ↓
BREATHE
        ↓
RECORDING
```

Firmware thu **đúng 5 giây** để khớp input của model.

```text
CHECK
  ↓
5 s Audio Capture
  ↓
Audio Quality Gate
  ↓
DSP
  ↓
DS-CNN INT8
  ↓
3 × Invoke()
  ↓
Voting
  ↓
Audio Result
```

---

## 5.1. Audio Quality Gate

Quality Gate trả lời:

> "Bản audio 5 giây vừa thu có đủ chất lượng kỹ thuật để đưa vào model hay không?"

Nó không phải classifier.

Các metric dự kiến:

```text
RMS
Peak
Clipping count / ratio
Active block ratio
```

Các trạng thái:

```text
AUDIO_OK
AUDIO_TOO_WEAK
AUDIO_TOO_LOUD
AUDIO_INACTIVE
```

Threshold cuối cùng chỉ được calibration sau khi hoàn thiện:

```text
INMP441
+
acoustic opening
+
enclosure
+
final hardware
```

Nếu audio không đạt:

```text
Quality Gate
     ↓
   FAIL
     ↓
OLED: RETRY / MOVE CLOSER
```

Không ép AI đưa ra kết luận từ input không hợp lệ.

---

## 5.2. Vì sao Manual Check không cần pre-trigger?

Manual Check đã có hành động bắt đầu rõ ràng:

```text
User
 ↓
CHECK
 ↓
Record 5 s
```

Do đó không cần:

```text
1 s pre-trigger
```

Pre-trigger chỉ phục vụ Auto Monitor.

---

# ❤️ 6. CHECK lần 2 — MAX30102

Sau khi Audio Result hoàn thành, OLED có thể yêu cầu:

```text
PLACE FINGER
PRESS CHECK
```

Người dùng nhấn `CHECK` lần thứ hai.

```text
MAX30102 ON
     ↓
HR / SpO₂ measurement
     ↓
Complete Patient Session
```

Lý do tách riêng:

- AI inference có thể mất tài nguyên;
- MAX30102 chỉ cần hoạt động khi người dùng thực sự đặt ngón tay;
- UX rõ ràng;
- dễ test;
- không cần giữ MAX30102 chạy liên tục.

Nếu người dùng không đo:

```text
vitals_valid = false
```

Session audio vẫn hợp lệ.

---

# 👂 7. Button 2 — MONITOR

MONITOR là Auto Acoustic Monitoring.

```text
MONITOR
   ↓
INMP441 + I2S ON
   ↓
Rolling 1 s PSRAM
   ↓
VAD
   ↓
4 consecutive blocks > threshold
   ↓
TRIGGER
   ↓
1 s pre-trigger + 4 s post-trigger
   ↓
5 s final audio
   ↓
Quality Gate
   ↓
DSP
   ↓
DS-CNN
   ↓
3 × Invoke / Voting
   ↓
PatientEvent
```

---

## 7.1. Vai trò thực sự của 1 s PSRAM

`1 s PSRAM` **không phải noise baseline**.

Nó là:

> **Rolling pre-trigger buffer**

Trong Monitor Mode, VAD cần 4 block liên tiếp vượt threshold để xác nhận event.

Trong thời gian đó, event có thể đã bắt đầu.

Vì vậy:

```text
             VAD TRIGGER
                  │
                  ▼
───────────────┬──┬──────────────────► time
               │  │
       1 s     │  │      4 s
    pre-trigger│  │    post-trigger
               │  │
═══════════════╪══╪═══════════════════
     PSRAM     │  │     I2S capture
═══════════════╪══╪═══════════════════
               │
               ▼
          Final 5 seconds
```

Nhờ đó:

```text
1 s trước trigger
+
4 s sau trigger
=
5 s input cho AI
```

Không dùng 1 s buffer này cho Manual Check.

---

# 🛑 8. Button 3 — SLEEP / STOP

Nút này có mức ưu tiên cao.

Dùng để:

- dừng Monitor;
- hủy phiên đo;
- đưa hệ thống về trạng thái an toàn;
- chuyển sang low power.

ISR không làm cleanup nặng.

ISR chỉ đặt:

```text
abort_requested = true
```

State machine xử lý:

```text
Stop I2S
   ↓
Stop MAX30102
   ↓
Clear temporary buffers
   ↓
Update OLED
   ↓
Disable communication as needed
   ↓
Enter SLEEP
```

---

# 🔄 9. Patient State Machine

Application chính của Patient Node được thiết kế theo **State Machine**, không lấy FreeRTOS task làm kiến trúc chính.

Một state machine ở mức khái niệm:

```text
                         ┌──────────────┐
                         │   STANDBY    │
                         └──────┬───────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
                  CHECK                   MONITOR
                    │                       │
                    ▼                       ▼
             MANUAL_PREPARE        MONITOR_LISTENING
                    │                       │
                    ▼                       ▼
             MANUAL_CAPTURE             VAD
                    │                       │
                    ▼                       ▼
              QUALITY_CHECK              TRIGGER
                    │                       │
                    ▼                       ▼
               AI_PROCESSING          MONITOR_CAPTURE
                    │                       │
                    ▼                       ▼
               AUDIO_RESULT            QUALITY_CHECK
                    │                       │
               CHECK lần 2                  ▼
                    │                   AI_PROCESSING
                    ▼                       │
              VITAL_MEASURING              ▼
                    │                   EVENT_SEND
                    └──────────┬────────────┘
                               ▼
                            STANDBY
```

`SLEEP/STOP` có thể interrupt flow hợp lệ bằng `abort_requested`.

---

# 📦 10. Patient Session

Một phiên đo có thể gồm:

```text
Audio Result
+
Optional HR/SpO₂
+
Battery
+
Timestamp
+
Sync status
```

Concept:

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

Nếu không đo MAX30102:

```text
vitals_valid = false
```

không được coi là lỗi.

---

# 📡 11. PatientEvent

Patient Node không gửi raw audio lên Gateway trong operation bình thường.

Thay vào đó nó tạo:

```text
PatientEvent
```

Concept:

```cpp
struct PatientEventPacket {
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

Các event chính:

```text
MANUAL_CHECK
MONITOR_EVENT
STATUS
```

Không truyền:

```text
Raw PCM
Mel Spectrogram
Tensor
Model internals
```

---

# 📶 12. ESP-NOW

ESP-NOW được sử dụng như:

> **Local Event Transport**

Luồng:

```text
Patient Node
     │
     │ PatientEvent
     ▼
  ESP-NOW
     │
     ▼
  Gateway
```

Patient Node không cần đảm nhiệm:

```text
Wi-Fi
MQTT
TLS
Cloud reconnect
LTE
```

Điều này giúp:

- giảm firmware complexity;
- giảm power;
- không cần Wi-Fi credentials;
- giữ Edge AI hoạt động độc lập với Internet.

---

# 🔐 13. ESP-NOW Reliability

PatientEvent có:

```text
sequence
session_id
timestamp
```

Luồng ACK:

```text
Patient Node
     │
     │ Event seq=N
     ▼
  Gateway
     │
     │ ACK seq=N
     ▼
Patient Node
```

Nếu ACK thành công:

```text
synced = true
```

Nếu timeout:

```text
synced = false
        ↓
local storage
```

Khi Gateway xuất hiện lại:

```text
pending events
      ↓
retry / sync
```

Gateway giữ sequence history để tránh duplicate.

---

# 🏠 14. Gateway / Home Station

Gateway là thiết bị thứ hai của hệ thống.

Vai trò:

```text
Environmental Node
        +
ESP-NOW Receiver
        +
Patient Data Aggregator
        +
Network Manager
        +
MQTT Uplink
        +
Optional Local Display
```

Hardware:

```text
ESP32
DHT22
BMP280
SGP30
NEO-M8N
A7680C
Wi-Fi
ESP-NOW
Optional TFT
```

Gateway ưu tiên nguồn cấp liên tục ở nhà.

---

# 🌡️ 15. Environmental Sensing

## DHT22

```text
Temperature
Humidity
```

## BMP280

```text
Pressure
Temperature
```

## SGP30

```text
TVOC
eCO₂ / CO₂-equivalent
```

> SGP30 không được mô tả là cảm biến đo trực tiếp CO₂.

---

# 🧵 16. Gateway FreeRTOS Architecture

Gateway là nơi FreeRTOS thực sự có giá trị.

Khác Patient Node:

```text
Patient Node
= State Machine centric

Gateway
= RTOS Task centric
```

Gateway phải xử lý đồng thời:

```text
ESP-NOW
Environment
Wi-Fi
MQTT
LTE
GPS
Storage
Optional TFT
```

Kiến trúc khái niệm:

```text
                    Gateway
                       │
       ┌───────────────┼────────────────┐
       │               │                │
       ▼               ▼                ▼
  ESP-NOW Task     Sensor Task      Network Task
       │               │                │
       ▼               ▼                ▼
PatientEvent      Environment       Wi-Fi/LTE
Queue             Snapshot              │
       │                                ▼
       └───────────┐                  MQTT
                   ▼
           Gateway Manager
                   │
          ┌────────┴────────┐
          ▼                 ▼
       Storage        CompleteRecord
```

ESP-NOW callback không thực hiện heavy processing.

Callback chỉ:

```text
Receive
  ↓
Queue
  ↓
Return
```

Task bên ngoài callback mới xử lý packet.

---

# 🧩 17. Gateway Data Aggregation

Gateway nhận:

```text
PatientEvent
```

sau đó lấy context gần thời điểm event:

```text
PatientEvent
     +
EnvironmentSnapshot
     +
GatewayStatus
     +
Optional GPS
     ↓
CompleteRecord
```

Sau đó:

```text
CompleteRecord
      ↓
MQTT
```

Điều này giúp Gateway thực sự đóng vai trò **Gateway/Aggregator**, thay vì chỉ là một sensor box khác.

---

# 🌐 18. Gateway Network Policy

## HOME MODE

```text
Patient Node
     ↓
 ESP-NOW
     ↓
 Gateway
     ↓
  Wi-Fi
     ↓
  MQTT
```

Gateway:

```text
Wi-Fi      = Primary
LTE        = Standby / Fallback
GPS        = Usually OFF
```

---

## MOBILE MODE

Khi cần realtime connectivity ngoài nhà:

```text
Patient Node
     ↓
 ESP-NOW
     ↓
 Gateway
     ↓
 A7680C LTE
     ↓
 MQTT
```

GPS có thể được bật khi cần location.

Gateway **không bắt buộc** phải luôn được mang theo Patient Node.

---

# 🚶 19. Portable Offline Mode

Nếu Patient Node ra khỏi vùng Gateway:

```text
Patient Node
       X
     Gateway
```

Patient Node vẫn có thể:

```text
Manual Check
     ↓
Quality Gate
     ↓
TinyML
     ↓
HR / SpO₂
     ↓
OLED Result
```

Nếu không gửi được ESP-NOW:

```text
Store local event
```

Khi quay lại vùng Gateway:

```text
Pending Event
     ↓
ESP-NOW
     ↓
ACK
     ↓
synced = true
```

Nguyên tắc:

> **Mất Gateway hoặc Internet không làm mất chức năng Edge AI cốt lõi của Patient Node.**

---

# 📊 20. Dashboard Qt6 / QML

`Dashboard_Qt6/` là giao diện giám sát cuối.

Pipeline:

```text
Patient Node
      ↓
ESP-NOW
      ↓
Gateway
      ↓
MQTT
      ↓
Qt6 / QML
```

Dashboard tập trung vào:

- Patient Sessions.
- Respiratory Events.
- HR / SpO₂ history.
- Environment history.
- Alerts.
- Gateway status.
- Network status.
- Optional location/map.

---

## 20.1. Data semantics

Dashboard phải phân biệt:

```text
Current Environment
```

và:

```text
Latest Patient Measurement
```

Ví dụ:

```text
Latest Patient Check
22:04

HR      81 bpm
SpO₂    97%
Result  ASTHMA_LIKE
```

Không hiển thị một HR/SpO₂ cũ như:

```text
CURRENT HR = 81
```

nếu thiết bị không thực sự đang đo.

---

# 🖥️ 21. UI Hierarchy

## Patient OLED

```text
Measurement Interaction
```

Ví dụ:

```text
READY
PLACE NEAR MOUTH
RECORDING
PROCESSING
AUDIO TOO WEAK
RESULT
PLACE FINGER
HR / SpO₂
MONITORING
BATTERY
GATEWAY STATUS
```

## Gateway TFT

Nếu sử dụng:

```text
Local Home Station Status
```

Hiển thị:

```text
Latest Event
Environment
Network
Wi-Fi / LTE
Gateway status
```

Không bắt buộc phải dùng LVGL nếu giao diện chỉ là text/icon/bar đơn giản.

## Qt6/QML

```text
Full Monitoring Dashboard
```

Phù hợp cho:

```text
History
Charts
Events
Alerts
Analytics
Network
Location
```

---

# 🔋 22. Power Architecture

## Patient Node

Ba mức tải chính:

```text
STANDBY
    ↓
lowest power

MANUAL CHECK
    ↓
high load / short duration

MONITOR
    ↓
continuous acoustic subsystem
```

Các đại lượng cần đo:

```text
I_standby
I_manual
I_monitor
```

Battery capacity chỉ nên chốt sau khi có current profile thực tế.

---

## Gateway

Home-first:

```text
USB / external power
```

Battery chỉ là tùy chọn cho mobile operation.

---

# 🔄 23. End-to-End Data Flow

## Manual Check

```text
User
 ↓
CHECK
 ↓
5 s Audio
 ↓
Quality Gate
 ↓
DSP
 ↓
DS-CNN INT8
 ↓
3× Invoke / Voting
 ↓
Audio Result
 ↓
CHECK lần 2
 ↓
MAX30102
 ↓
PatientSession
 ↓
PatientEvent
 ↓
ESP-NOW
 ↓
Gateway
 ↓
Environment Aggregation
 ↓
CompleteRecord
 ↓
MQTT
 ↓
Qt6 Dashboard
```

---

## Auto Monitor

```text
MONITOR
 ↓
Continuous I2S
 ↓
1 s PSRAM rolling buffer
 ↓
VAD
 ↓
4 consecutive active blocks
 ↓
1 s pre-trigger + 4 s post-trigger
 ↓
5 s audio
 ↓
Quality Gate
 ↓
DSP
 ↓
DS-CNN
 ↓
Voting
 ↓
PatientEvent
 ↓
ESP-NOW
 ↓
Gateway
 ↓
MQTT
 ↓
Dashboard
```

---

# 🧪 24. Experimental Evaluation

Final Project cần được đánh giá theo nhiều lớp.

## AI

```text
Accuracy
Precision
Recall
F1
Confusion Matrix
```

## Embedded Deployment

```text
Python ↔ ESP32 parity
DSP latency
Inference latency
RAM
Flash
PSRAM
```

## Audio

```text
Quality Gate
VAD
Near-field acquisition
Noise scenarios
```

## Power

```text
Standby current
Manual current
Monitor current
```

## Communication

```text
ESP-NOW success rate
ACK / retry
Gateway loss / reconnect
Wi-Fi
LTE fallback
```

## End-to-End

```text
Patient Check
      ↓
TinyML
      ↓
ESP-NOW
      ↓
Gateway
      ↓
MQTT
      ↓
Dashboard
```

Đo latency từ lúc Patient Node hoàn thành event đến khi Dashboard nhận được dữ liệu.

---

# 🛠️ 25. Build Order

Không tích hợp toàn bộ hệ thống cùng một lúc.

Thứ tự triển khai:

```text
AI Model v1.0
     ✓
     ↓
Patient State Machine
     ↓
3 Buttons
     ↓
Manual Check
     ↓
Audio Quality Gate
     ↓
DSP + TinyML
     ↓
MAX30102 Session
     ↓
Auto Monitor
     ↓
PatientSession
     ↓
PatientEvent
     ↓
ESP-NOW + ACK
     ↓
Gateway FreeRTOS
     ↓
Environment Sensors
     ↓
Aggregation
     ↓
Wi-Fi / MQTT
     ↓
LTE / GPS
     ↓
Qt6 Dashboard
     ↓
Enclosure + Battery
     ↓
Experimental Evaluation
     ↓
Final NCKH Demo
```

---

# 📚 26. Tài liệu liên quan

Các tài liệu thiết kế chi tiết nằm ở thư mục sibling:

```text
../Docs_NCKH/
```

## Product Definition

`NCKH_PRODUCT_DEFINITION_FINAL.md`

Dùng khi cần trả lời:

> **Sản phẩm cuối là gì? Người dùng sử dụng nó như thế nào?**

Bao gồm:

- form factor;
- Patient Node;
- Gateway;
- 3 buttons;
- Manual Check;
- Monitor;
- Home / Portable / Mobile.

---

## System Architecture

`NCKH_SYSTEM_ARCHITECTURE_FINAL.md`

Dùng khi cần trả lời:

> **Hệ thống được tổ chức và giao tiếp như thế nào?**

Bao gồm:

- State Machine;
- PatientSession;
- PatientEvent;
- ESP-NOW;
- Gateway aggregation;
- FreeRTOS;
- MQTT;
- network flow.

---

## Build Implementation Plan

`NCKH_BUILD_IMPLEMENTATION_PLAN.md`

Dùng khi cần trả lời:

> **Bây giờ phải code cái gì trước, DONE khi nào?**

Đây là tài liệu ưu tiên khi bắt đầu một phase implementation mới.

---

# 🧱 27. Relationship với các thư mục bên ngoài

```text
AI_Training_Model/
       │
       │ Training / Evaluation
       ▼
Deploy_Model/
       │
       │ Deployment validation
       ▼
AI_Model/
       │
       ▼
Patient_Node


ESP32-Sensor_Suite/
       │
       │ Tested reusable drivers
       ├──────────────► Patient_Node
       │
       └──────────────► Gateway


ESP32-Qt-Telemetry/
       │
       │ MQTT ↔ Qt6 prototype
       ▼
Dashboard_Qt6


Docs_NCKH/
       │
       ├── Product Definition
       ├── System Architecture
       └── Build Plan
       │
       ▼
Final_Project_NCKH/
```

Nguyên tắc:

> Prototype dùng để nghiên cứu và xác minh từng subsystem. `Final_Project_NCKH/` là nơi tích hợp những subsystem đã ổn định thành sản phẩm cuối.

---

# 🚫 28. Những thứ không thuộc trách nhiệm của Patient Node

Patient Node **không** đảm nhiệm:

```text
Wi-Fi management
MQTT
TLS
Cloud reconnect
LTE
GPS
Environment sensing
```

Patient Node tập trung vào:

```text
Audio
DSP
Quality Gate
VAD
TinyML
Voting
MAX30102
OLED
State Machine
Low Power
ESP-NOW
Local Event Storage
```

---

# 🚫 29. Những thứ không thuộc trách nhiệm của Gateway

Gateway không chạy TinyML respiratory inference thay Patient Node.

Gateway tập trung vào:

```text
ESP-NOW RX
Environment
Aggregation
Storage
Wi-Fi
LTE
MQTT
GPS
RTOS
Optional TFT
```

---

# 🧭 30. Design Principles

### 1. Edge-first

TinyML chạy trực tiếp trên ESP32-S3.

### 2. Offline-capable

Patient Node vẫn thực hiện được chức năng cốt lõi khi mất Gateway/Internet.

### 3. Near-field acquisition

INMP441 được sử dụng trong điều kiện near-field; không claim khả năng nghe respiratory sound ổn định từ xa.

### 4. Quality-before-inference

Audio không đạt chất lượng kỹ thuật không được ép đưa vào inference.

### 5. Event/session-based patient data

Không giả lập HR/SpO₂ continuous nếu MAX30102 không thực sự được sử dụng liên tục.

### 6. Gateway aggregation

Gateway ghép PatientEvent với environmental context trước khi publish MQTT.

### 7. Separation of responsibility

```text
Patient Node = Patient sensing + Edge AI
Gateway      = Environment + Aggregation + Network
Dashboard    = Monitoring + History + Visualization
```

### 8. No raw audio streaming

Raw PCM không được upload liên tục lên cloud.

### 9. No medical overclaim

Hệ thống hỗ trợ theo dõi và cảnh báo kỹ thuật, không thay thế chẩn đoán y khoa.

### 10. NCKH-first

Ưu tiên:

```text
Correct methodology
+
Stable implementation
+
Measurable results
+
Reproducibility
+
Demonstrable final system
```

hơn việc tối ưu metric hoặc feature một cách thiếu kiểm soát.

---

# 🚦 31. Current Status

## ✅ AI

```text
Dataset methodology             DONE
DS-CNN training                 DONE
INT8 quantization               DONE
Python ↔ ESP32 validation       DONE
Live microphone validation      DONE
VAD                             DONE
1 s PSRAM pre-trigger           DONE
3-vote inference                DONE
AI v1.0                         FROZEN
```

## 🚧 Patient Node

```text
State Machine
3 Buttons
Manual Check
Quality Gate
MAX30102 session
Auto Monitor integration
PatientSession
PatientEvent
ESP-NOW ACK / retry
Low-power behavior
```

## 🚧 Gateway

```text
FreeRTOS architecture
ESP-NOW receiver
DHT22
BMP280
SGP30
Aggregation
Wi-Fi / MQTT
LTE fallback
GPS
```

## 🚧 Dashboard

```text
MQTT schema
Qt6/QML integration
Overview
History
Charts
Alerts
Device status
```

---

# 🎓 32. Final NCKH Demonstration

Demo cuối nên thể hiện được ít nhất:

## Scenario A — Manual Check

```text
CHECK
 → 5 s audio
 → Quality Gate
 → TinyML
 → HR / SpO₂
 → ESP-NOW
 → Gateway
 → MQTT
 → Qt Dashboard
```

## Scenario B — Auto Monitor

```text
MONITOR
 → VAD
 → 1 s pre-trigger
 → 5 s audio
 → Quality Gate
 → TinyML
 → Event
 → Gateway
 → Dashboard
```

## Scenario C — Gateway Loss

```text
Patient Node
 → local inference
 → local event storage
```

Sau đó:

```text
Gateway available
 → sync pending event
```

## Scenario D — Network Fallback

```text
Wi-Fi unavailable
       ↓
A7680C LTE
       ↓
MQTT
```

---

# 📌 33. Definition of Done

Final Project chỉ được xem là hoàn thành khi:

```text
[ ] Patient Node chạy ổn định
[ ] 3 button hoạt động đúng state
[ ] Manual Check hoàn chỉnh
[ ] Quality Gate hoạt động
[ ] TinyML inference ổn định
[ ] 3-vote hoạt động
[ ] MAX30102 session hoạt động
[ ] Monitor Mode hoạt động
[ ] 1 s PSRAM pre-trigger đúng
[ ] PatientEvent ổn định
[ ] ESP-NOW ACK/retry hoạt động
[ ] Gateway RTOS ổn định
[ ] Environment sensing hoạt động
[ ] Gateway aggregation hoạt động
[ ] Wi-Fi/MQTT hoạt động
[ ] LTE fallback/mobile được kiểm thử nếu nằm trong scope final
[ ] Qt6 Dashboard nhận dữ liệu
[ ] Local event storage / resync hoạt động
[ ] Power profile được đo
[ ] Communication reliability được đo
[ ] End-to-end latency được đo
[ ] Final enclosure/hardware được hoàn thiện
[ ] Final NCKH demo chạy end-to-end
```

---

# 🏁 Final Architecture

```text
                         ┌───────────────────────┐
                         │     PATIENT NODE      │
                         │       ESP32-S3        │
                         │                       │
                         │ INMP441               │
                         │ MAX30102              │
                         │ OLED                  │
                         │ 3 Buttons             │
                         │ Battery               │
                         │                       │
                         │ State Machine         │
                         │ DSP                   │
                         │ Quality Gate          │
                         │ VAD                   │
                         │ DS-CNN INT8           │
                         │ Voting                │
                         │ Local Storage         │
                         └───────────┬───────────┘
                                     │
                                ESP-NOW
                              PatientEvent
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │       GATEWAY         │
                         │        ESP32          │
                         │                       │
                         │ DHT22 / BMP280        │
                         │ SGP30                 │
                         │ NEO-M8N               │
                         │ A7680C                │
                         │                       │
                         │ FreeRTOS              │
                         │ Aggregation           │
                         │ Storage               │
                         │ Wi-Fi / LTE           │
                         │ MQTT                  │
                         └───────────┬───────────┘
                                     │
                              Wi-Fi / LTE
                                     │
                                    MQTT
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │     Qt6 / QML         │
                         │      Dashboard        │
                         │                       │
                         │ Sessions              │
                         │ Respiratory Events    │
                         │ HR / SpO₂             │
                         │ Environment           │
                         │ Alerts                │
                         │ History / Charts      │
                         └───────────────────────┘
```

> **Final Project = Edge AI + Patient Sensing + Local Event Communication + Environmental Context + IoT Gateway + Monitoring Dashboard.**
