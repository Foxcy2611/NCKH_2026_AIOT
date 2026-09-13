# QT6 Dashboard - Data Display Note

**Source:** `Complete_Packet_t`

---

## I. Complete Packet Control

### `has_patient_event`

**Ý nghĩa:**
- `0`: packet chỉ chứa dữ liệu Gateway.
- `1`: packet chứa Gateway + một Patient Event mới.

**Quy tắc Dashboard:**
- `Gate_Payload` luôn được cập nhật.
- `Patient_Event` chỉ được cập nhật khi `has_patient_event == 1`.
- Khi `has_patient_event == 0`, **KHÔNG** lấy lại `patient_event` trong packet để giả làm dữ liệu realtime mới.

---

## II. Gateway - General Status

### 1. `gateway_id`
- **Hiển thị:** Gateway ID — ví dụ: `Gateway #01`
- **Mục đích:** Xác định Gateway đang gửi dữ liệu.

### 2. `timestamp`
- **Hiển thị:** Last Gateway Update — ví dụ: `23:15:42`
- **Mục đích:** Cho biết thời điểm telemetry Gateway gần nhất.

### 3. `operating_mode`
- **Các trạng thái:** `HOME` / `OFFLINE` / `MOBILE`
- **Hiển thị:**
  - `Operating Mode: HOME`
  - `Operating Mode: MOBILE`
  - `Operating Mode: OFFLINE`

### 4. `battery_gate`
- **Hiển thị:** `Gateway Battery: 82%`
- **Quy ước:**
  - `0...100` = phần trăm pin
  - `255` = Battery unavailable / error

---

## III. Environment

| Field | Hiển thị | Đơn vị | Nguồn | Ghi chú |
|---|---|---|---|---|
| `temperature` | Temperature | °C | Fusion DHT22 + BMP280 (Gateway xử lý) | Nếu một sensor lỗi thì fallback sensor còn hoạt động |
| `humidity` | Humidity | %RH | DHT22 | |
| `pressure` | Air Pressure | hPa | BMP280 | |
| `tvoc` | TVOC | ppb (dự kiến) | SGP30 | |
| `eco2` | eCO2 | ppm (dự kiến) | SGP30 | Là CO2-equivalent, không phải cảm biến CO2 trực tiếp |

---

## IV. Sensor Health

**Field:** `sensor_valid_mask`

| Bit | Ý nghĩa |
|---|---|
| BIT 0 | `SENSOR_DHT22_VALID` |
| BIT 1 | `SENSOR_BMP280_VALID` |
| BIT 2 | `SENSOR_SGP30_VALID` |
| BIT 3 | `SENSOR_GPS_VALID` |

**Dashboard nên có khu vực "SENSOR STATUS":**

```
DHT22       [ OK / ERROR ]
BMP280      [ OK / ERROR ]
SGP30       [ OK / ERROR ]
GPS         [ OK / NO FIX / OFF ]
```

**Quy tắc fallback:**
- DHT22 lỗi → Humidity → `N/A / ERROR`; Temperature có thể fallback BMP280
- BMP280 lỗi → Pressure → `N/A / ERROR`; Temperature có thể fallback DHT22
- Cả DHT22 + BMP280 lỗi → Temperature → `N/A / ERROR`
- SGP30 lỗi → TVOC → `N/A / ERROR`; eCO2 → `N/A / ERROR`
- GPS invalid → Không dùng latitude / longitude để cập nhật map

---

## V. Network Status

### 1. `uplink_type`
- **Các trạng thái:** `NONE` / `WIFI` / `LTE`
- **Hiển thị:**
  - `Current Uplink: Wi-Fi`
  - `Current Uplink: LTE`
  - `Current Uplink: Offline`

### 2. `wifi_connected`
- **Hiển thị:** `Wi-Fi: Connected` / `Wi-Fi: Disconnected`

### 3. `wifi_rssi_dbm`
- **Hiển thị:** `Wi-Fi Signal: -57 dBm` (có thể dùng số dBm hoặc signal bars)

### 4. `lte_registered`
- **Hiển thị:** `LTE: Registered` / `LTE: Not Registered`

### 5. `lte_rssi_dbm`
- **Hiển thị:** `LTE Signal: -83 dBm` (có thể dùng số dBm hoặc signal bars)

### 6. `mqtt_connected`
- **Hiển thị:** `MQTT: Connected` / `MQTT: Disconnected`
- **Lưu ý:** Wi-Fi/LTE Connected không đồng nghĩa MQTT Connected.

---

## VI. Location / GPS

### 1. `latitude`
- **Hiển thị:** Latitude, hoặc dùng trực tiếp cho Map

### 2. `longitude`
- **Hiển thị:** Longitude, hoặc dùng trực tiếp cho Map

### 3. `gps_timestamp`
- **Hiển thị:** Last GPS Update
- **Mục đích:** Biết tọa độ là GPS fix mới hay tọa độ cache cũ.

### 4. GPS Status
- Không có field riêng — lấy từ `sensor_valid_mask & SENSOR_GPS_VALID`

**HOME MODE:** GPS có thể lấy vị trí một lần rồi giữ cache. Không cần update liên tục.

**MOBILE MODE:** GPS update định kỳ/liên tục. LTE dùng để upload vị trí lên cloud.

---

## VII. Patient Event

> **CHỈ update phần này khi `has_patient_event == 1`**

### 1. `session_id`
- **Hiển thị:** Session ID
- **Mục đích:** Nhóm dữ liệu thuộc cùng một phiên đo.

### 2. `timestamp`
- **Hiển thị:** Event Time
- **Lưu ý:** Đây là timestamp của Patient Event, khác timestamp của Gate Payload.

### 3. `event_type`
- **Hiển thị:** Event Type
- **Ví dụ (tùy enum sau này):** Manual Check / Monitor Event / Alert / ...

### 4. `classification`
- **Hiển thị:** AI Classification
- **Ví dụ (tùy enum model):** Normal / Asthma-like / ...
- Không hiển thị trực tiếp số enum nếu UI final.

### 5. `model_score`
- **Hiển thị:** Confidence — ví dụ: `93.2%`
- Nếu `model_score` lưu dạng `0.932` → Qt6 tính: `0.932 * 100 = 93.2%`

### 6. `audio_quality`
- **Hiển thị:** Audio Quality
- **Ví dụ (tùy enum):** GOOD / LOW / INVALID / ...

### 7. `vitals_valid`
Biến điều khiển HR/SpO2:
- `vitals_valid == 1` → Hiển thị Heart Rate, SpO2
- `vitals_valid == 0` → Hiển thị `HR: N/A`, `SpO2: N/A` (không dùng HR/SpO2 cũ)

### 8. `heart_rate`
- **Hiển thị:** `Heart Rate: xx BPM`
- Chỉ hợp lệ khi `vitals_valid == 1`

### 9. `spo2`
- **Hiển thị:** `SpO2: xx %`
- Chỉ hợp lệ khi `vitals_valid == 1`

### 10. `battery_node`
- **Hiển thị:** `Patient Node Battery: xx %`
- **Quy ước:** `0...100` = phần trăm pin; `255` = unavailable / read error

---

## VIII. Dashboard Main Sections

### 1. Overview
Hiển thị nhanh: Gateway Mode, Current Uplink, MQTT Status, Gateway Battery, Node Battery, Temperature, Humidity, Latest Patient Classification, Latest HR, Latest SpO2, Last Update

### 2. Patient Status
Hiển thị: Latest Event Time, Event Type, AI Classification, Model Confidence, Audio Quality, Heart Rate, SpO2, Patient Node Battery, Session ID

> **Lưu ý:** Đây là "LATEST PATIENT EVENT", KHÔNG phải continuous realtime patient data.

### 3. Environment
Hiển thị: Temperature, Humidity, Pressure, TVOC, eCO2

Có thể có graph history: Temperature vs Time, Humidity vs Time, Pressure vs Time, TVOC vs Time, eCO2 vs Time

### 4. Device / Sensor Status
- **Gateway:** Gateway ID, Gateway Battery
- **Sensors:** DHT22 status, BMP280 status, SGP30 status, GPS status
- **Patient Node:** Node Battery, Last Patient Event Time

### 5. Network Status
Hiển thị: Operating Mode, Current Uplink, Wi-Fi Connected, Wi-Fi RSSI, LTE Registered, LTE RSSI, MQTT Connected

**Ví dụ:**
```
Mode          : HOME
Uplink        : Wi-Fi
Wi-Fi RSSI    : -55 dBm
LTE           : Standby / Registered
LTE RSSI      : -88 dBm
MQTT          : Connected
```

### 6. Location
Hiển thị: Map, Latitude, Longitude, Last GPS Update, GPS Status

- **HOME:** Vị trí có thể ít thay đổi.
- **MOBILE:** Map cập nhật theo GPS mới.

### 7. Patient Event History

Mỗi khi `has_patient_event == 1`, Backend thêm một Event mới vào history/database.

Mỗi record có thể chứa: Event timestamp, Session ID, Event Type, Classification, Confidence, Audio Quality, HR, SpO2, Node Battery

**Ví dụ:**
```
23:14:32
Manual Check
Asthma-like
Confidence 93.2%
HR 82 BPM
SpO2 97%
Battery 78%
```

---

## IX. Important Backend Rule

Mỗi `Complete_Packet` nhận được:

**1. LUÔN update:**
- Gateway status
- Environment
- Network
- GPS nếu valid
- Gateway battery

**2. KIỂM TRA** `if (has_patient_event == 1)`

**Nếu TRUE:**
- Update Latest Patient Event
- Update HR/SpO2 nếu `vitals_valid`
- Update Node Battery
- Add Event History
- Update AI result
- Update event timestamp

**Nếu FALSE:**
- KHÔNG update Patient Event
- KHÔNG ghi thêm Event History
- KHÔNG coi HR/SpO2 cũ là realtime measurement

---

## X. Data Flow for QT6

```
MQTT / CLOUD
      |
      v
Complete_Packet
      |
      +----------------------------------+
      |                                  |
      v                                  v
Gate_Payload                      has_patient_event ?
      |                                  |
      |                           +------+------+
      |                           |             |
      |                           0             1
      |                           |             |
      |                         Ignore          v
      |                         Patient   Patient_Event_Payload
      |                                         |
      v                                         v
Environment                              Latest Patient Event
Network                                  Event History
Sensors                                  HR / SpO2
GPS                                      AI Result
Gateway Battery                          Node Battery
```

---

## XI. Main Dashboard Summary

```
DASHBOARD
├── Overview
│
├── Patient
│   ├── Latest Event
│   ├── AI Classification
│   ├── Confidence
│   ├── HR
│   ├── SpO2
│   ├── Audio Quality
│   └── Node Battery
│
├── Environment
│   ├── Temperature
│   ├── Humidity
│   ├── Pressure
│   ├── TVOC
│   └── eCO2
│
├── Gateway
│   ├── Gateway ID
│   ├── Operating Mode
│   ├── Gateway Battery
│   └── Sensor Health
│
├── Network
│   ├── Uplink
│   ├── Wi-Fi
│   ├── Wi-Fi RSSI
│   ├── LTE
│   ├── LTE RSSI
│   └── MQTT
│
├── Location
│   ├── GPS Status
│   ├── Map
│   └── Last GPS Update
│
└── History
    ├── Patient Events
    └── Environment History
```

---

## Final Design Principle

- **`Gate_Payload_t`** = periodic/current telemetry
- **`Patient_Event_Payload_t`** = event-based patient measurement
- **`Complete_Packet_t`** = transport/data model kết hợp hai loại trên
- **`has_patient_event`** = điều kiện để Qt6 biết packet hiện tại có chứa một Patient Event MỚI hay không