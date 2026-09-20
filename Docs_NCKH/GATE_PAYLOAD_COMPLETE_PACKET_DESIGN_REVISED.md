# THIẾT KẾ `Gateway_Payload_t` VÀ `Complete_Packet_t` — REVISED

## 1. Mục tiêu

Gateway duy trì **latest state**, không duy trì hàng đợi lịch sử khi mất Internet.

Ba cấu trúc chính:

- `Node_Payload_t`: Event mới nhất nhận từ Patient Node sau khi AES-GCM xác thực/giải mã thành công. Payload này **không có timestamp**.
- `Gateway_Payload_t`: snapshot mới nhất của Gateway, environment, network và GPS. Timestamp của hệ thống chỉ được giữ tại đây.
- `Complete_Packet_t`: object tạm được dựng từ `current_node` + `current_gate` khi cần publish MQTT; không phải object được queue lâu dài.

```text
Patient Node --ESP-NOW--> current_node ----+
                                           +--> Complete_Packet_t --> MQTT
Gateway sensors/network --> current_gate --+
                         \--> TFT
```

---

## 2. Trạng thái vận hành và uplink

```cpp
typedef enum : uint8_t {
    GATE_MODE_HOME = 0,
    GATE_MODE_OFFLINE,
    GATE_MODE_MOBILE
} Gate_Operating_Mode_t;

typedef enum : uint8_t {
    GATE_UPLINK_NONE = 0,
    GATE_UPLINK_WIFI,
    GATE_UPLINK_LTE
} Gate_Uplink_Type_t;
```

- `operating_mode` mô tả chế độ vận hành sản phẩm.
- `uplink_type` mô tả đường Internet hiện tại.
- Khi Wi-Fi/LTE đều không khả dụng, `uplink_type = GATE_UPLINK_NONE`; Gateway vẫn đọc sensor, nhận ESP-NOW và cập nhật TFT/current state.

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

Không dùng giá trị `0` của sensor để biểu diễn lỗi; dùng `sensor_valid_mask`.

---

## 4. `Gateway_Payload_t`

```cpp
typedef struct {
    // Identity / time
    uint32_t gateway_id;
    uint64_t timestamp;          // thời điểm tạo current_gate

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

    uint8_t battery_gate;
} Gateway_Payload_t;
```

### Quy ước timestamp

- `Node_Payload_t`: **không có timestamp**.
- `Response_Payload_t`: **không có timestamp**.
- `Gateway_Payload_t.timestamp`: thời điểm Gateway tạo/cập nhật snapshot `current_gate`.
- `gps_timestamp`: thời điểm GPS fix gần nhất; vẫn là field thuộc `Gateway_Payload_t`.

`Gateway_Payload_t.timestamp` dùng cho `Last Gateway Update`/snapshot time trên backend. Không được diễn giải nó là thời điểm chính xác Patient Event xảy ra.

---

## 5. Current state trong Gateway

Gateway giữ đúng hai snapshot mới nhất:

```cpp
Node_Payload_t current_node{};
Gateway_Payload_t          current_gate{};

bool current_node_valid = false;
bool current_gate_valid = false;
bool node_dirty         = false;
```

Ý nghĩa:

- `current_node_valid`: Gateway đã từng nhận một Patient Event hợp lệ chưa.
- `current_gate_valid`: Gateway đã tạo được một Gate snapshot hợp lệ chưa.
- `node_dirty`: `current_node` hiện tại có phải Patient Event mới chưa được publish MQTT thành công hay không.

`valid` và `dirty` là hai khái niệm khác nhau:

```text
current_node_valid = true, node_dirty = false
```

nghĩa là Gateway vẫn có Latest Patient Event để TFT hiển thị, nhưng Event đó đã được cloud nhận.

### Khi nhận Patient Event hợp lệ

```cpp
current_node = decrypted_patient_event;
current_node_valid = true;
node_dirty = true;
```

Nếu Internet đang mất và Event mới khác đến, `current_node` bị overwrite. Hệ thống chủ ý chỉ giữ **latest event**, không đảm bảo phục hồi đầy đủ lịch sử trong thời gian mất Internet.

### Khi cập nhật sensor/network

```cpp
current_gate = new_gate_payload;
current_gate_valid = true;
```

`current_gate` luôn được overwrite bằng snapshot mới nhất và dùng trực tiếp cho TFT.

---

## 6. `Complete_Packet_t`

```cpp
typedef struct {
    uint8_t has_patient_event;
    Gateway_Payload_t gate;
    Node_Payload_t patient_event;
} Complete_Packet_t;
```

`Complete_Packet_t` chỉ được dựng khi cần publish/cloud transport.

### Gate-only telemetry

```cpp
Complete_Packet_t packet{};
packet.has_patient_event = 0;
packet.gate = current_gate;
```

### Có Patient Event mới chưa publish

```cpp
Complete_Packet_t packet{};
packet.gate = current_gate;

if (current_node_valid && node_dirty) {
    packet.has_patient_event = 1;
    packet.patient_event = current_node;
} else {
    packet.has_patient_event = 0;
}
```

Sau khi MQTT publish thành công packet có Patient Event:

```cpp
node_dirty = false;
```

Không xóa `current_node` và không đổi `current_node_valid`, vì TFT vẫn cần Latest Patient Event.

---

## 7. Khi Internet lỗi

```text
ESP-NOW OK + Wi-Fi/LTE ERROR

Patient Event -> current_node
Sensors       -> current_gate
TFT           -> đọc current_node/current_gate
MQTT          -> chưa publish được
node_dirty    -> giữ true nếu có Event mới
```

Gateway **không tạo offline queue** và không lưu nhiều `Complete_Packet_t`.

Nếu có nhiều Patient Event trong thời gian Internet lỗi:

```text
Event #25 -> current_node = #25
Event #26 -> current_node = #26  (overwrite #25)
Event #27 -> current_node = #27  (overwrite #26)
```

Khi Internet trở lại, Gateway ghép `current_node #27` với `current_gate` mới nhất thành `Complete_Packet_t` và publish. Đây là chính sách latest-state có chủ ý.

---

## 8. Backend / Dashboard rule

Backend luôn cập nhật Gate data từ mọi packet.

```cpp
updateGatewayTelemetry(packet.gate);
```

Chỉ coi Patient Event là mới khi:

```cpp
packet.has_patient_event == 1
```

Không lấy `patient_event` của packet có `has_patient_event == 0` để giả làm dữ liệu mới.

Patient Event không có timestamp riêng. Dashboard nên hiển thị:

- `Last Gateway Update` từ `packet.gate.timestamp`.
- `Latest Patient Event` theo `session_id`, classification, score, quality, HR/SpO2 và battery.
- Nếu cần lịch sử backend, thời gian record có thể dùng thời gian nhận tại backend hoặc `gate.timestamp` với nhãn rõ là **Gateway snapshot time**, không phải Patient event time chính xác.

---

## 9. Luồng chốt

```text
                         GATEWAY
                            |
          +-----------------+------------------+
          |                                    |
          v                                    v
Environment / Network                 ESP-NOW Patient Event
          |                                    |
          v                                    v
     current_gate                    verify/decrypt
 current_gate_valid=true                    |
          |                                  v
          |                            current_node
          |                       current_node_valid=true
          |                            node_dirty=true
          +------------------+---------------+
                             |
                      +------v------+
                      |     TFT     |
                      +-------------+
                             |
                      Build Complete
                             |
                     Internet available?
                       /            \
                     no             yes
                     |               |
                 giữ state         MQTT
                                     |
                         success + event?
                                     |
                              node_dirty=false
```

---

## 10. Struct Patient Event tham chiếu

```cpp
#pragma pack(push, 1)
typedef struct {
    uint32_t session_id;
    uint8_t event_type;
    uint8_t classification;
    float model_score;
    uint8_t audio_quality;
    uint8_t vitals_valid;
    uint16_t heart_rate;
    uint8_t spo2;
    uint8_t battery;
} Node_Payload_t;
#pragma pack(pop)

static_assert(sizeof(Node_Payload_t) == 16);
```

`Complete_Packet_t` là internal Gateway/cloud data model. Khi gửi MQTT nên serialize thành JSON hoặc schema rõ ràng; không gửi raw C++ binary layout và không đưa nonce/ciphertext/tag/khóa lên MQTT.
