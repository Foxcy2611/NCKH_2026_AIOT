# 🫁 Edge AI & IoT: Hệ thống TinyML hỗ trợ theo dõi và cảnh báo sớm cho bệnh nhân hen suyễn

![ESP32](https://img.shields.io/badge/MCU-ESP32%20%7C%20ESP32--S3-red.svg)
![RTOS](https://img.shields.io/badge/Gateway-FreeRTOS-blue.svg)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![AI](https://img.shields.io/badge/AI-TensorFlow%20Lite%20Micro-orange.svg)
![C++](https://img.shields.io/badge/C++-00599C?style=for-the-badge&logo=c%2B%2B&logoColor=white)
![Qt](https://img.shields.io/badge/Qt-6-41CD52?style=for-the-badge&logo=qt&logoColor=white)
![Network](https://img.shields.io/badge/Network-ESP--NOW%20%7C%20WiFi%20%7C%204G%20LTE%20%7C%20MQTT-brightgreen.svg)

> 🔬 **Tên đề tài NCKH:**  
> **Nghiên cứu, thiết kế và chế tạo hệ thống IoT ứng dụng TinyML hỗ trợ theo dõi và cảnh báo sớm cho bệnh nhân hen suyễn.**

---

# 📝 Giới thiệu

Dự án phát triển một hệ thống nhúng phân tán gồm **hai thiết bị vật lý chính**:

1. **Patient Edge Node** — thiết bị cá nhân cầm tay chạy pin, thực hiện thu âm hô hấp, xử lý DSP, chạy TinyML trên ESP32-S3 và đo HR/SpO₂ theo phiên.
2. **IoT Gateway / Home Station** — thu thập dữ liệu môi trường, nhận PatientEvent qua ESP-NOW, ghép dữ liệu, quản lý Wi-Fi/LTE/GPS và publish dữ liệu lên MQTT.

Kiến trúc được xây dựng theo hướng **Edge-first**:

```text
Respiratory Audio
      |
      v
Patient Edge Node
DSP + TinyML
      |
  PatientEvent
      |
   ESP-NOW
      |
      v
IoT Gateway
Environment + Aggregation
      |
 Wi-Fi / LTE
      |
     MQTT
      |
      v
Qt6/QML Dashboard
```

TinyML được chạy **trực tiếp tại Patient Node**, do đó chức năng phân tích cốt lõi vẫn hoạt động ngay cả khi Gateway hoặc Internet không khả dụng.

> ⚠️ Hệ thống là nguyên mẫu nghiên cứu hỗ trợ theo dõi/cảnh báo kỹ thuật.  
> Không được xem là thiết bị tự chẩn đoán bệnh, xác nhận chắc chắn cơn hen hoặc đánh giá mức độ nguy kịch lâm sàng.

---

# 🚀 Tính năng nổi bật

- 🧠 **Edge AI trên ESP32-S3:**  
  DS-CNN INT8 chạy hoàn toàn on-device bằng TensorFlow Lite Micro.

- 🎤 **Respiratory Acoustic Pipeline:**  
  Thu âm INMP441 ở 16 kHz, xử lý Butterworth Bandpass → Pre-emphasis → Mel-Spectrogram → INT8 inference.

- 🛡️ **Audio Quality Gate:**  
  Đánh giá chất lượng đoạn audio 5 giây trước khi cho phép inference, dựa trên các chỉ số như RMS, peak, clipping và active blocks.

- 🧠 **Voting nhiều lần inference:**  
  Kết hợp nhiều lần `Invoke()` để tăng độ ổn định quyết định ở deployment.

- 🧠 **1 giây PSRAM Pre-trigger:**  
  Trong Monitor Mode, PSRAM luôn giữ 1 giây audio gần nhất để tránh mất phần đầu respiratory event khi VAD trigger trễ.

- ❤️ **HR / SpO₂ theo phiên:**  
  MAX30102 chỉ được bật khi người dùng chủ động thực hiện Vital Check, không giả lập continuous vital monitoring.

- 📡 **ESP-NOW Event Link:**  
  Patient Node gửi `PatientEvent` đã xử lý sang Gateway, không stream raw WAV trong vận hành bình thường.

- 🌤️ **Environmental Monitoring tại Gateway:**  
  DHT22, BMP280, SGP30 cung cấp Temperature, Humidity, Pressure, TVOC và eCO₂.

- 🌍 **Network linh hoạt:**  
  Wi-Fi dùng ở Home Mode; A7680C LTE dùng làm fallback hoặc mobile uplink; NEO-M8N dùng khi cần vị trí.

- ⏱️ **FreeRTOS trên Gateway:**  
  Gateway xử lý concurrent ESP-NOW, sensor, aggregation, Wi-Fi/LTE, MQTT và optional UI qua Task/Queue.

- 🖥️ **Qt6/QML Dashboard:**  
  Hiển thị Patient Sessions, respiratory events, HR/SpO₂ theo phiên, environment history, device/network status và alert.

---

# 🧩 Định nghĩa sản phẩm cuối cùng

## 1. Patient Edge Node

Thiết bị cá nhân nhỏ gọn, chạy pin, có thể:

- cầm tay;
- bỏ túi;
- để bàn;
- đặt gần đầu giường;
- mang theo khi ra ngoài.

### Phần cứng chính

- ESP32-S3-N16R8.
- INMP441.
- MAX30102.
- SSD1306 OLED.
- 3 nút:
  - `CHECK`
  - `MONITOR`
  - `SLEEP / STOP`
- Battery.
- ESP-NOW.

### Form factor

Định hướng:

> **Portable handheld respiratory monitor**

Không định hướng:

- smartwatch;
- microphone áp cố định lên ngực;
- far-field microphone nghe từ xa trong phòng.

---

## 2. IoT Gateway / Home Station

Gateway đóng vai trò:

- Environmental Node.
- ESP-NOW Receiver.
- Data Aggregator.
- Network Manager.
- MQTT Uplink.
- Optional local display station.

### Phần cứng chính

- ESP32.
- DHT22.
- BMP280.
- SGP30.
- NEO-M8N.
- A7680C.
- Wi-Fi.
- ESP-NOW.
- Optional TFT.
- Nguồn cấp liên tục; battery là tùy chọn cho mobile operation.

---

# 🏠 Các kịch bản vận hành

| Scenario | Patient Node | Gateway | Uplink |
|---|---|---|---|
| **Home Monitoring** | Portable / bedside | Đặt tại nhà | Wi-Fi → MQTT |
| **Portable Offline** | Mang theo | Ở nhà | Local result + sync later |
| **Mobile Connected** | Mang theo | Mang theo | LTE + GPS → MQTT |

---

## Home Monitoring

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

Gateway thường:

- always-on;
- đọc environment định kỳ;
- Wi-Fi primary;
- LTE standby/fallback;
- GPS thường OFF.

Patient Node phần lớn ở Standby và chỉ chạy khi user chủ động Check hoặc Monitor.

---

## Portable Offline

Khi Patient Node ra khỏi vùng Gateway:

```text
Patient Node
     X
   Gateway
```

Patient Node vẫn có thể:

- thu respiratory audio;
- Quality Check;
- chạy TinyML;
- đo HR/SpO₂;
- hiển thị kết quả OLED;
- lưu event chưa sync.

Khi trở lại gần Gateway, các event pending có thể được đồng bộ lại.

> Mất Gateway/Internet không làm mất chức năng Edge AI cốt lõi.

---

## Mobile Connected

Nếu cần realtime connectivity ngoài nhà:

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

Trong scenario này:

- LTE là primary uplink.
- GPS có thể được bật.
- Gateway có thể tiếp tục thu environment xung quanh.

---

# 🎛️ Patient Node Operating Modes

Patient Node dùng 3 nút vật lý riêng để tránh long-press/double-click phức tạp.

```text
[ CHECK ]   [ MONITOR ]   [ SLEEP ]
```

---

## 1. CHECK — Manual Respiratory Check

Người dùng đưa thiết bị đến gần vùng miệng rồi nhấn `CHECK`.

```text
CHECK
  |
  v
Record exact 5 s
  |
  v
Audio Quality Gate
  |
  v
DSP
  |
  v
DS-CNN INT8
  |
  v
3x Invoke / Voting
  |
  v
Audio Result
```

Sau khi có Audio Result, OLED yêu cầu:

```text
PLACE FINGER
PRESS CHECK
```

Nhấn `CHECK` lần thứ hai:

```text
MAX30102
   |
   v
HR / SpO2
```

Vital Check là **optional**. Nếu user nhấn `SLEEP`, phiên đo vẫn hợp lệ với `vitals_valid = false`.

---

## 2. MONITOR — Auto Acoustic Monitoring

Pipeline:

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
4 consecutive blocks > threshold
   |
   v
TRIGGER
   |
   v
1 s pre-trigger + 4 s post-trigger
   |
   v
Final 5 s audio
   |
   v
Quality Gate
   |
   v
DSP + DS-CNN + Voting
   |
   v
PatientEvent
```

MAX30102 mặc định **OFF** trong Monitor Mode vì không thể giả định user đang đặt ngón tay trên sensor.

---

## 3. SLEEP / STOP

`SLEEP` có ưu tiên cao nhất.

State machine sẽ:

- abort acquisition nếu cần;
- stop I2S;
- stop MAX30102;
- reset buffer/state;
- tắt OLED;
- tắt radio không cần thiết;
- đưa Patient Node về low-power state.

---

# 🎤 Audio Quality Gate

Quality Gate không phải classifier và không thay thế VAD.

## VAD

Trả lời:

> Có event đủ điều kiện để Auto Monitor bắt đầu capture chưa?

## Quality Gate

Trả lời:

> Final audio 5 giây vừa thu có đủ chất lượng kỹ thuật để model được phép inference không?

Flow:

```text
Final 5 s audio
      |
      v
Quality Gate
  |   |   |
  |   |   +--> INACTIVE
  |   +------> TOO_LOUD
  +----------> TOO_WEAK
      |
      v
     OK
      |
      v
DSP + TinyML
```

Các metric dự kiến:

- RMS.
- Peak.
- Clipping count/ratio.
- Active block count/ratio.

Threshold final sẽ được calibration trên final enclosure.

---

# 🧠 TinyML Pipeline

## Input

```text
Sample rate : 16 kHz
Duration    : 5 s
Samples     : 80,000
```

## Preprocessing

```text
Raw PCM
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
Mel 64 x 129
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
```

## Deployment

- Model: DS-CNN.
- Full INT8.
- TensorFlow Lite Micro.
- Target: ESP32-S3.

Pipeline C++ được triển khai **tương đương về thuật toán** với pipeline Python và đã được kiểm chứng bằng đối chiếu kết quả phân lớp.

Không claim bit-exact hoặc numerically identical giữa Python và ESP32.

---

# 🧪 Dataset & Training Methodology

Phiên bản model hiện tại ưu tiên phương pháp đánh giá đúng hơn metric đẹp.

- Chia dữ liệu theo bệnh nhân trước augmentation.
- Augmentation chỉ áp dụng cho train.
- Validation/Test giữ dữ liệu gốc.
- Min/Max normalization chỉ được học từ train.
- Hạn chế data leakage giữa các mẫu liên quan.

> 📌 Accuracy chính thức phải lấy từ model freeze mới nhất.  
> Phiên bản patient-wise split hiện tại cho kết quả khoảng **~87%**, thấp hơn phiên bản cũ nhưng đáng tin cậy hơn về phương pháp đánh giá.

---

# 🧠 Model output

Model được xem là:

> **Respiratory Acoustic Pattern Classifier**

Application-level output:

```text
ASTHMA_LIKE
NON_ASTHMA
```

Không sử dụng các nhãn kiểu:

```text
DIAGNOSED_ASTHMA
SEVERE_ATTACK
PATIENT_HAS_ASTHMA
```

Một tiếng ho hoặc âm thanh lớn có thể kích hoạt VAD nhưng không đồng nghĩa classifier sẽ trả `ASTHMA_LIKE`.

---

# 📦 PatientEvent

Patient Node không gửi raw audio trong normal operation.

Nó gửi **PatientEvent** đã được xử lý.

Concept:

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

Event types dự kiến:

```text
MANUAL_CHECK
MONITOR_EVENT
STATUS
```

---

# 📡 ESP-NOW Event Link

ESP-NOW được dùng làm:

> **Local event transport giữa Patient Node và Gateway**

Không dùng để stream raw WAV.

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

## Reliability

```text
Patient
   |
   | Event seq=N
   v
Gateway
   |
   | ACK seq=N
   v
Patient
```

Nếu ACK thất bại:

```text
synced = false
store local
```

Khi Gateway xuất hiện lại:

```text
retry pending events
```

Gateway giữ sequence history để chống duplicate.

---

# 🌤️ Gateway Environmental Sensing

## DHT22

- Temperature.
- Humidity.

## BMP280

- Pressure.
- Temperature.

## SGP30

- TVOC.
- eCO₂ / CO₂-equivalent.

> SGP30 không được mô tả là direct CO₂ sensor.

---

# 🧠 Gateway Data Aggregation

Gateway nhận:

```text
PatientEvent
```

và ghép với:

```text
EnvironmentSnapshot
+
Gateway Status
+
Optional GPS
```

thành:

```text
CompleteRecord
```

rồi publish MQTT.

```text
PatientEvent
      |
      v
Nearest Environment Snapshot
      |
      v
Gateway / Network Context
      |
      v
CompleteRecord
      |
      v
MQTT
```

Cloud không cần tự đoán hai stream độc lập nào thuộc cùng một patient session.

---

# ⏱️ Firmware Architecture

## Patient Node

Triết lý:

> **State-machine centric**

Application flow chính tuần tự:

```text
Standby
  |
Check / Monitor
  |
Acquire
  |
Quality
  |
Process
  |
Infer
  |
Display
  |
Send Event
```

Arduino ESP32 vẫn chạy trên FreeRTOS bên dưới, nhưng Patient Node không cần tự chia application thành nhiều task nếu không có lợi ích rõ ràng.

---

## Gateway

Triết lý:

> **FreeRTOS task centric**

Gateway phải xử lý concurrent:

- ESP-NOW.
- Environment sensors.
- Wi-Fi.
- LTE.
- MQTT.
- GPS.
- Storage.
- Optional TFT.

Task proposal:

```text
TaskEspNow
TaskSensor
TaskGatewayManager
TaskNetwork
TaskDisplay        optional
```

ESP-NOW callback chỉ enqueue packet và return; không làm heavy processing trực tiếp trong callback.

---

# 🛡️ Gateway Robustness

FreeRTOS không tự động bảo đảm mọi subsystem cô lập hoàn toàn.

Các driver/task cần:

- timeout;
- bounded retry;
- Queue timeout;
- Mutex timeout;
- non-blocking network reconnect;
- watchdog;
- tránh `while(1)` blocking không kiểm soát.

Mục tiêu:

```text
Sensor lỗi
→ MQTT / ESP-NOW vẫn hoạt động

Network lỗi
→ environment sensing vẫn hoạt động
```

---

# 🌐 Gateway Network Policy

## Home Mode

```text
Wi-Fi
  |
  v
MQTT
```

- Wi-Fi primary.
- LTE standby/fallback.
- GPS thường OFF.

## Mobile / Wi-Fi unavailable

```text
A7680C LTE
     |
     v
    MQTT
```

GPS bật khi cần location.

Patient Node không cần biết Gateway đang dùng Wi-Fi hay LTE.

---

# 📊 MQTT & Dashboard

## Prototype hiện có

Thư mục `ESP32-Qt-Telemetry/` là proof-of-concept ban đầu:

- `QtEnvDash-ESP32/`
- `Dashboard_DHT11/`

Prototype ban đầu có thể vẫn dùng DHT11, nhưng **Final Gateway sử dụng DHT22**.

## Final Dashboard

Qt6/QML Dashboard dự kiến hiển thị:

- Overview.
- Patient Sessions.
- Respiratory Events.
- HR / SpO₂ History.
- Environment Charts.
- Gateway Status.
- Network Status.
- Alerts.
- Optional Location / Map.

Dashboard phải phân biệt:

```text
Current Environment
```

với:

```text
Latest HR / SpO2 measurement
```

Không hiển thị một phép đo HR/SpO₂ cũ như realtime current value.

---

# 💾 Database / Persistent Storage

Backend persistent storage hiện **chưa khóa hoàn toàn**.

Firebase có thể tiếp tục được dùng nếu phù hợp với implementation cuối, nhưng MQTT schema và data model cần được chốt trước.

---

# 🔔 Alert Strategy

Gateway có thể có Alert Engine dựa trên các rule đã cấu hình.

Không claim TinyML trực tiếp xác định:

```text
"cơn hen nguy kịch"
```

hoặc tự động đưa ra kết luận lâm sàng.

Nếu một điều kiện cảnh báo được thỏa mãn, Gateway có thể:

- hiển thị local alert;
- publish MQTT;
- dùng LTE/SMS/call nếu chức năng này được hoàn thiện trong final scope;
- đính kèm GPS khi phù hợp.

---

# 🛠️ Hardware Requirements

## Patient Edge Node

- ESP32-S3-N16R8.
- INMP441.
- MAX30102.
- SSD1306 OLED.
- 3 buttons.
- Battery.
- Optional buzzer/status LED.

## IoT Gateway

- ESP32.
- DHT22.
- BMP280.
- SGP30.
- NEO-M8N.
- A7680C.
- Wi-Fi.
- ESP-NOW.
- Optional TFT.
- Power supply.

## Deferred / Future

- MLX90614 body-temperature measurement.

---

# 🔧 Driver Cảm biến

Thư mục `ESP32-Sensor_Suite/` chứa các driver C++ đã phát triển cho các module của dự án.

Các module lịch sử có thể bao gồm:

- DHT11 / DHT22.
- MAX30102.
- MLX90614.
- A7680C.
- BMP280.
- SGP30.
- NEO-M8N.
- SSD1306.

Không phải mọi driver trong Sensor Suite đều bắt buộc xuất hiện trong final hardware.

Mục tiêu của Sensor Suite:

- module hóa;
- API nhất quán;
- dễ tái sử dụng;
- có timeout;
- có khả năng phối hợp với FreeRTOS/Mutex khi cần.

---

# 📂 Tổ chức thư mục dự án

```text
NCKH_2026_AIOT/
│
├── AI_Training_Model/
│   └── Python training / preprocessing / evaluation
│
├── Deploy_Model/
│   ├── 1_Test_Model_Static_Profiling/
│   ├── 2_Test_Model_LiveMic/
│   ├── 3_Model_Complete/
│   └── 4_Test_Model_Official_Final/
│
├── ESP32_Pinout/
│
├── ESP32-Qt-Telemetry/
│   ├── QtEnvDash-ESP32/
│   └── Dashboard_DHT11/
│
├── ESP32-Sensor_Suite/
│
├── Final_Project_NCKH/
│   ├── Patient_Node/
│   ├── Gateway/
│   └── Dashboard/
│
└── docs/
    ├── NCKH_PRODUCT_DEFINITION_FINAL.md
    ├── NCKH_SYSTEM_ARCHITECTURE_FINAL.md
    └── NCKH_BUILD_IMPLEMENTATION_PLAN.md
```

---

# 🛠️ Môi trường phát triển

## AI

- Python 3.x.
- TensorFlow / Keras.
- librosa.
- scipy.
- numpy.

## Firmware

- PlatformIO.
- VS Code.
- Arduino framework cho ESP32 / ESP32-S3.
- TensorFlow Lite Micro.

## Dashboard

- Qt Creator.
- Qt6 / QML.
- MQTT client.

---

# 🔋 Power Strategy

## Patient Node

Ba mức tải chính:

```text
STANDBY
= low power

MANUAL CHECK
= high load trong thời gian ngắn

MONITOR
= active acoustic subsystem
```

Các giá trị cần đo thực nghiệm:

```text
I_standby
I_manual
I_monitor
```

Dung lượng battery sẽ được chốt sau khi có current profile.

## Gateway

Primary use:

```text
always-on power / USB adapter
```

Battery là optional cho backup/mobile use.

---

# 🧪 Experimental Evaluation dự kiến

## AI

- Accuracy.
- Precision.
- Recall.
- F1.
- Confusion Matrix.

## Deployment

- Python ↔ ESP32 classification parity.
- DSP latency.
- Inference latency.
- RAM / Flash / PSRAM.

## Audio

- VAD.
- 1 s pre-trigger.
- Quality Gate.
- Near-field acquisition.
- Noise scenarios.

## Power

- Standby current.
- Manual Check current.
- Monitor current.

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

---

# 📌 Trạng thái hiện tại

## ✅ Hoàn thành / ổn định

- Pipeline huấn luyện AI.
- Patient-wise split / train-only augmentation methodology.
- DS-CNN INT8.
- Python ↔ ESP32 deployment validation.
- Live microphone deployment trên ESP32-S3.
- Voting.
- VAD.
- 1 s PSRAM rolling pre-trigger buffer.

## 🚧 Đang triển khai

### Patient Node Final Firmware

- State Machine.
- 3 Buttons.
- Manual Check.
- Audio Quality Gate.
- MAX30102 session.
- Auto Monitor integration.
- PatientSession.
- PatientEvent.
- Low power.

### ESP-NOW

- PatientEvent packet.
- ACK.
- Sequence.
- Pending event re-sync.

### Gateway

- FreeRTOS skeleton.
- Environmental sensors.
- Aggregation.
- Wi-Fi / MQTT.
- LTE fallback/mobile.
- GPS policy.

### Dashboard

- Final MQTT schema.
- Qt6/QML overview/history/alert UI.

---

# 🗺️ Build Roadmap

```text
AI Model Freeze
      ✓
      |
      v
Patient State Machine
      |
      v
3 Buttons
      |
      v
Manual Check
      |
      v
Quality Gate
      |
      v
DSP + TinyML
      |
      v
MAX30102 Session
      |
      v
Auto Monitor
      |
      v
PatientEvent
      |
      v
ESP-NOW + ACK
      |
      v
Gateway FreeRTOS
      |
      v
Environment + Aggregation
      |
      v
Wi-Fi / MQTT
      |
      v
LTE / GPS
      |
      v
Qt Dashboard
      |
      v
Enclosure + Battery
      |
      v
Experimental Evaluation
      |
      v
Final NCKH Demo
```

Chi tiết từng phase xem:

[`NCKH_BUILD_IMPLEMENTATION_PLAN.md`](./Docs_NCKH/NCKH_BUILD_IMPLEMENTATION_PLAN.md)

---

# 📐 Design Principles

1. **Edge-first:** TinyML chạy tại Patient Node.
2. **Offline-capable:** Patient Node vẫn hoạt động khi Gateway/Internet mất.
3. **Near-field acquisition:** không claim far-field respiratory sensing.
4. **Quality-before-inference:** input quá yếu/không hợp lệ không bị ép model kết luận.
5. **Event/session-based patient data:** không giả lập continuous HR/SpO₂.
6. **Gateway aggregation:** patient + environment được ghép trước MQTT.
7. **Separation of responsibility:** Patient = sensing/AI; Gateway = network/environment/aggregation.
8. **No raw audio streaming by default.**
9. **No medical overclaim.**
10. **Prototype-first:** ưu tiên đúng phương pháp, ổn định, đo được và demo được.

---

# 👨‍🔬 NCKH

Dự án được phát triển phục vụ nghiên cứu khoa học sinh viên tại **Học viện Công nghệ Bưu chính Viễn thông (PTIT)**.

*Project workspace: ARM LAB - PTIT.*
