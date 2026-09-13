# THIẾT KẾ `Gate_Payload_t` VÀ `Complete_Packet_t`

## 1. Mục tiêu

Tài liệu này chốt mô hình dữ liệu phía **Gateway** sau khi hệ thống đã có:

- `Patient_Event_Payload_t`: dữ liệu sự kiện bệnh nhân được tạo tại Patient Node, mã hóa bằng AES-128-GCM, truyền qua ESP-NOW và chỉ được sử dụng tại Gateway sau khi xác thực/giải mã thành công.
- `Gate_Payload_t`: dữ liệu định kỳ do chính Gateway tạo ra từ cảm biến môi trường, trạng thái mạng, trạng thái MQTT và GPS.
- `Complete_Packet_t`: cấu trúc tổng hợp dùng làm dữ liệu đầu vào cho tầng publish/cloud.

Gateway phải hỗ trợ hai trường hợp:

1. **Không có Patient Event**: Gateway vẫn gửi telemetry định kỳ của riêng nó lên cloud.
2. **Có Patient Event**: Gateway ghép `Patient_Event_Payload_t` vừa nhận với `Gate_Payload_t` gần thời điểm đó nhất rồi gửi đồng thời lên cloud.

```text
CASE 1 — Không có Patient Event

Gate_Payload_t
      |
      v
Complete_Packet_t
has_patient_event = 0
      |
      v
Cloud / Qt6


CASE 2 — Có Patient Event

Patient_Event_Payload_t
          +
Gate_Payload_t
          |
          v
Complete_Packet_t
has_patient_event = 1
          |
          v
Cloud / Qt6
```

---

## 2. Trạng thái hoạt động của Gateway

```cpp
typedef enum : uint8_t {
    GATE_MODE_HOME = 0,
    GATE_MODE_OFFLINE,
    GATE_MODE_MOBILE
} Gate_Operating_Mode_t;
```

- `GATE_MODE_HOME`: Gateway ở nhà, thường dùng Wi-Fi làm uplink chính; GPS không cần cập nhật liên tục.
- `GATE_MODE_OFFLINE`: hiện không có uplink Internet khả dụng; Gateway vẫn đọc sensor và có thể lưu local.
- `GATE_MODE_MOBILE`: Gateway và Patient Node được mang ra ngoài; LTE là uplink chính và GPS được cập nhật thường xuyên hơn.

`operating_mode` mô tả **kịch bản vận hành**, không phải đường truyền hiện tại.

```cpp
typedef enum : uint8_t {
    GATE_UPLINK_NONE = 0,
    GATE_UPLINK_WIFI,
    GATE_UPLINK_LTE
} Gate_Uplink_Type_t;
```

- `GATE_UPLINK_NONE`: chưa có uplink Internet.
- `GATE_UPLINK_WIFI`: dữ liệu đang đi qua Wi-Fi.
- `GATE_UPLINK_LTE`: dữ liệu đang đi qua LTE.

Ví dụ Gateway vẫn có thể ở `GATE_MODE_HOME` nhưng `uplink_type = GATE_UPLINK_LTE` nếu Wi-Fi lỗi và LTE đang fallback.

---

## 3. Sensor Valid Mask

```cpp
typedef enum : uint8_t {
    SENSOR_DHT22_VALID  = 1 << 0,
    SENSOR_BMP280_VALID = 1 << 1,
    SENSOR_SGP30_VALID  = 1 << 2,
    SENSOR_GPS_VALID    = 1 << 3
} Gate_Sensor_Valid_Bit_t;
```

| Bit | Mask | Module |
|---:|---:|---|
| 0 | `0x01` | DHT22 |
| 1 | `0x02` | BMP280 |
| 2 | `0x04` | SGP30 |
| 3 | `0x08` | GPS / NEO-M8N |

Ví dụ `sensor_valid_mask = 0x07` nghĩa là DHT22, BMP280, SGP30 hợp lệ; GPS chưa hợp lệ hoặc đang không dùng.

Nếu DHT22 lỗi nhưng BMP280 còn tốt thì có thể:
- `humidity` -> `N/A` / `ERROR`
- `temperature` -> fallback sang BMP280
- `pressure` -> vẫn hợp lệ
- `tvoc`, `eco2` -> vẫn hợp lệ nếu SGP30 còn tốt

Không dùng giá trị `0` để biểu diễn sensor lỗi vì `0` có thể là dữ liệu đo hợp lệ.

---

## 4. `Gate_Payload_t`

```cpp
typedef struct {
    // Identity / time
    uint32_t gateway_id;
    uint64_t timestamp;

    // Operating state
    uint8_t operating_mode;
    uint8_t uplink_type;

    // Environment
    float temperature;
    float humidity;
    float pressure;
    uint16_t tvoc;
    uint16_t eco2;

    // Sensor health
    uint8_t sensor_valid_mask;

    // Network status
    uint8_t wifi_connected;
    int16_t wifi_rssi_dbm;

    uint8_t lte_registered;
    int16_t lte_rssi_dbm;

    uint8_t mqtt_connected;

    // Location
    double latitude;
    double longitude;
    uint64_t gps_timestamp;

} Gate_Payload_t;
```

### `gateway_id`

ID logic của Gateway. Dùng để phân biệt Gateway trong database, liên kết telemetry với đúng thiết bị và giúp backend biết record thuộc thiết bị nào.

### `timestamp`

Dấu thời gian của `Gate_Payload_t` hiện tại, tức thời điểm Gateway tạo/snapshot bộ dữ liệu môi trường và trạng thái hệ thống.

### `operating_mode`

Kịch bản vận hành hiện tại: Home, Offline hoặc Mobile.

### `uplink_type`

Đường truyền hiện tại Gateway đang dùng để lên cloud: None, Wi-Fi hoặc LTE.

### `temperature`

Nhiệt độ cuối cùng sau logic fusion/fallback giữa DHT22 và BMP280.

Logic đề xuất:

```cpp
if (DHT22 valid && BMP280 valid) {
    temperature =
        (dht22_temperature + corrected_bmp280_temperature) / 2.0f;
}
else if (DHT22 valid) {
    temperature = dht22_temperature;
}
else if (BMP280 valid) {
    temperature = corrected_bmp280_temperature;
}
else {
    temperature = NAN;
}
```

`corrected_bmp280_temperature` có thể áp dụng offset calibration sau khi test trên enclosure thực tế. Nếu cả hai sensor lỗi, không dùng `0.0f`; nên dùng `NAN` hoặc để backend dựa vào bitmask mà hiển thị `ERROR`.

### `humidity`

Độ ẩm tương đối từ DHT22. Chỉ có ý nghĩa nếu bit `SENSOR_DHT22_VALID` đang bật.

### `pressure`

Áp suất khí quyển từ BMP280. Chỉ có ý nghĩa nếu bit `SENSOR_BMP280_VALID` đang bật.

Project hiện tại không cần altitude nên không có field độ cao.

### `tvoc`

TVOC từ SGP30. Chỉ dùng khi `SENSOR_SGP30_VALID` hợp lệ.

### `eco2`

eCO2 / CO2-equivalent từ SGP30. Đây không phải phép đo CO2 trực tiếp.

### `sensor_valid_mask`

Bitmask cho biết module sensor nào có dữ liệu hợp lệ. Backend Qt6 có thể dùng trực tiếp để hiển thị `OK`, `ERROR`, `N/A` và chọn logic fallback.

### `wifi_connected`

`0` = Wi-Fi chưa kết nối.  
`1` = Wi-Fi đang kết nối.

Field này độc lập với trạng thái MQTT.

### `wifi_rssi_dbm`

Cường độ tín hiệu Wi-Fi theo dBm, dùng để hiển thị chất lượng kết nối trên Dashboard.

### `lte_registered`

`0` = modem LTE chưa đăng ký được vào mạng.  
`1` = modem LTE đã đăng ký mạng.

### `lte_rssi_dbm`

Cường độ tín hiệu LTE sau khi driver modem chuyển metric tương ứng sang dạng mà Gateway sử dụng.

### `mqtt_connected`

`0` = MQTT disconnected.  
`1` = MQTT connected.

Không suy ra trạng thái MQTT chỉ từ Wi-Fi/LTE.

### `latitude`

Vĩ độ từ NEO-M8N. Chỉ có ý nghĩa khi `SENSOR_GPS_VALID` bật.

### `longitude`

Kinh độ từ NEO-M8N. Chỉ có ý nghĩa khi `SENSOR_GPS_VALID` bật.

### `gps_timestamp`

Thời điểm GPS fix gần nhất. Field này giúp backend biết tọa độ đang mới hay chỉ là vị trí cache cũ.

Home Mode có thể lấy GPS một lần rồi cache. Mobile Mode có thể cập nhật GPS định kỳ/liên tục hơn.

LTE không tạo ra tọa độ GPS; NEO-M8N là nguồn vị trí, LTE chỉ là đường truyền để upload vị trí đó lên cloud.

---

## 5. `Complete_Packet_t`

Gateway phải hỗ trợ cả telemetry định kỳ và event-based patient data.

Thiết kế đề xuất:

```cpp
typedef struct {
    uint8_t has_patient_event;

    Gate_Payload_t gate;

    Patient_Event_Payload_t patient_event;

} Complete_Packet_t;
```

### `has_patient_event`

Biến này cho backend biết `Patient_Event_Payload_t` trong `Complete_Packet_t` có hợp lệ và có ý nghĩa hay không.

Quy ước:

```text
has_patient_event = 0
    -> Complete_Packet chỉ chứa Gate Payload hợp lệ
    -> patient_event phải bị bỏ qua

has_patient_event = 1
    -> Complete_Packet chứa:
       Gate Payload
       +
       Patient Event Payload
```

Nên dùng `uint8_t` thay vì `bool` để kích thước biểu diễn rõ ràng nếu sau này struct được serialize hoặc chia sẻ giữa nhiều thành phần.

---

## 6. Trường hợp Gate-only

Khi không có CHECK và không có Monitor Event, Gateway vẫn gửi telemetry định kỳ:

```cpp
Complete_Packet_t packet{};

packet.has_patient_event = 0;
packet.gate = current_gate_payload;
```

Backend luôn cập nhật phần Gateway/Environment nhưng không được đọc `packet.patient_event`.

Nếu serialize JSON, nên bỏ hẳn object `patient_event`:

```json
{
    "has_patient_event": false,
    "gate": {
        "gateway_id": 1,
        "temperature": 28.7,
        "humidity": 71.4,
        "pressure": 1008.2,
        "tvoc": 120,
        "eco2": 540,
        "operating_mode": "HOME",
        "uplink_type": "WIFI",
        "mqtt_connected": true
    }
}
```

---

## 7. Trường hợp Gate + Patient Event

Sau khi Gateway nhận `Secure_EspNow_Packet_t`, xác thực AES-GCM và giải mã thành công thành `Patient_Event_Payload_t`, Gateway lấy `Gate_Payload_t` gần thời điểm Event nhất rồi ghép:

```cpp
Complete_Packet_t packet{};

packet.has_patient_event = 1;
packet.gate = current_gate_payload;
packet.patient_event = decrypted_patient_event;
```

JSON tương ứng:

```json
{
    "has_patient_event": true,

    "gate": {
        "gateway_id": 1,
        "temperature": 28.7,
        "humidity": 71.4,
        "pressure": 1008.2,
        "tvoc": 120,
        "eco2": 540,
        "operating_mode": "HOME",
        "uplink_type": "WIFI",
        "mqtt_connected": true
    },

    "patient_event": {
        "session_id": 25,
        "timestamp": 1789000000,
        "event_type": 1,
        "classification": 1,
        "model_score": 0.932,
        "audio_quality": 0,
        "vitals_valid": 1,
        "heart_rate": 82,
        "spo2": 97,
        "battery": 86
    }
}
```

---

## 8. Quy tắc Backend Qt6

Backend luôn xử lý Gate Payload:

```cpp
updateGatewayTelemetry(packet.gate);
```

Chỉ cập nhật Patient UI khi:

```cpp
if (packet.has_patient_event == 1) {
    updatePatientEvent(packet.patient_event);
}
```

Điều này tránh lỗi hiển thị Patient Event cũ như dữ liệu realtime.

Ví dụ:

```text
14:32 Patient Event:
HR = 82

14:33 Gate-only telemetry
14:34 Gate-only telemetry
14:35 Gate-only telemetry
```

Backend không được hiểu `HR = 82` là nhịp tim realtime ở 14:35.

Do đó Dashboard nên tách rõ:

```text
CURRENT ENVIRONMENT
    temperature
    humidity
    pressure
    TVOC
    eCO2

GATEWAY STATUS
    mode
    uplink
    Wi-Fi RSSI
    LTE RSSI
    MQTT
    sensor health
    GPS

LATEST PATIENT EVENT
    classification
    model score
    HR
    SpO2
    audio quality
    event time
```

`CURRENT ENVIRONMENT` và `GATEWAY STATUS` cập nhật từ mọi `Complete_Packet_t`.

`LATEST PATIENT EVENT` chỉ cập nhật khi:

```cpp
has_patient_event == 1
```

---

## 9. Thiết kế chốt

```text
                         GATEWAY
                            |
          +-----------------+------------------+
          |                                    |
          v                                    v
Environment / Network                 ESP-NOW Patient Event
          |                                    |
          v                                    v
   Gate_Payload_t                    AES-GCM verify/decrypt
          |                                    |
          |                                    v
          |                         Patient_Event_Payload_t
          |                                    |
          +----------------+-------------------+
                           |
                           v
                  Complete_Packet_t
                           |
                    has_patient_event
                      /           \
                     0             1
                    /               \
             Gate only        Gate + Patient
                    \               /
                     \             /
                           v
                      JSON / MQTT
                           |
                           v
                          Cloud
                           |
                           v
                       Qt6 Backend
```

### Struct chốt

```cpp
typedef struct {
    uint32_t session_id;
    uint64_t timestamp;  

    uint8_t event_type; 

    uint8_t classification;
    float model_score;    

    uint8_t audio_quality; 

    uint8_t vitals_valid;  
    uint16_t heart_rate;      
    uint8_t spo2;             

    uint8_t battery_node;      

} Patient_Event_Payload_t;

typedef struct {
    uint32_t gateway_id;
    uint64_t timestamp;

    uint8_t operating_mode;
    uint8_t uplink_type;

    float temperature;
    float humidity;
    float pressure;

    uint16_t tvoc;
    uint16_t eco2;

    uint8_t sensor_valid_mask;

    uint8_t wifi_connected;
    int16_t wifi_rssi_dbm;

    uint8_t lte_registered;
    int16_t lte_rssi_dbm;

    uint8_t mqtt_connected;

    double latitude;
    double longitude;
    uint64_t gps_timestamp;

    uint8_t battery_gate

} Gate_Payload_t;


typedef struct {
    uint8_t has_patient_event;

    Gate_Payload_t gate;

    Patient_Event_Payload_t patient_event;

} Complete_Packet_t;
```

`Complete_Packet_t` nên được xem là **internal Gateway/cloud data model**. Khi gửi qua MQTT, nên serialize thành JSON hoặc schema message rõ ràng thay vì gửi raw binary layout của C++ struct.
