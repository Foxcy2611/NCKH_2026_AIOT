# TỔNG HỢP CẤU TRÚC GÓI TIN VÀ MỐI QUAN HỆ DỮ LIỆU

## 1. Mục đích

Tài liệu này thống nhất tên, vai trò, thành phần và mối quan hệ giữa các cấu trúc dữ liệu được sử dụng trong hệ thống Patient Node, Gateway và Dashboard.

Quy ước trong tài liệu dựa trên thiết kế revised:

```text
Node_Payload_t             = 16 byte
Response_Payload_t = 16 byte
Secure_Packet_t            = 56 byte
```

Ba cấu trúc trên thuộc giao thức ESP-NOW và phải được định nghĩa từ cùng một header dùng chung cho Node và Gateway.

`Gateway_Payload_t` và `Complete_Packet_t` thuộc tầng Gateway/cloud. Hai cấu trúc này không được gửi trực tiếp dưới dạng binary qua ESP-NOW.

---

## 2. Sơ đồ quan hệ tổng thể

```text
PATIENT NODE

Patient_Session_t
      |
      | Chuyển dữ liệu phiên đo
      v
Node_Payload_t (16 byte plaintext)
      |
      | AES-128-GCM
      v
Secure_Packet_t (56 byte)
      |
      | ESP-NOW
      v
GATEWAY
      |
      | Xác thực tag + giải mã
      v
Node_Payload_t
      |
      v
current_node
      |
      +------------------------------+
                                     |
Gateway sensors/network/GPS          |
      |                              |
      v                              |
Gateway_Payload_t                    |
      |                              |
      v                              v
current_gate ---------------> Complete_Packet_t
                                     |
                                     | JSON / MQTT
                                     v
                              Backend / Qt6 Dashboard
```

Chiều phản hồi:

```text
GATEWAY

Response_Payload_t (16 byte plaintext)
      |
      | AES-128-GCM
      v
Secure_Packet_t (56 byte)
      |
      | ESP-NOW
      v
PATIENT NODE
      |
      | Xác thực tag + giải mã
      v
Response_Payload_t
      |
      +-- ACK_ACCEPTED / ACK_DUPLICATE -> kết thúc tx_inflight
      +-- NACK_BUSY                    -> chờ và retry packet cũ
      +-- Sai tag/sequence/session     -> bỏ phản hồi
```

---

## 3. `Patient_Session_t`

### Vai trò

Lưu trạng thái một phiên đo bên trong Patient Node. Đây không phải packet truyền thông và không được gửi trực tiếp qua ESP-NOW.

### Thành phần

| Trường | Kiểu | Ý nghĩa |
|---|---:|---|
| `session_id` | `uint32_t` | Định danh phiên CHECK hoặc MONITOR |
| `event_type` | `Event_Type_t` | Loại phiên đo |
| `audio_quality` | `Audio_Quality_t` | Kết quả kiểm tra chất lượng âm thanh |
| `classification` | `Interface_TinyML_t` | Kết quả mô hình |
| `model_score` | `float` | Điểm của lớp được chọn, khoảng `0.0–1.0` |
| `vitals_valid` | `bool` | Cho biết HR/SpO₂ có hợp lệ hay không |
| `heart_rate` | `uint16_t` | Nhịp tim BPM |
| `spo2` | `uint8_t` | Nồng độ SpO₂ theo phần trăm |

### Quan hệ

```text
Patient_Session_t
      |
      | Build payload khi phiên hoàn thành
      v
Node_Payload_t
```

`device_id`, `sequence`, nonce, tag, trạng thái retry và ACK không thuộc `Patient_Session_t`; chúng thuộc lớp truyền thông.

---

## 4. `Node_Payload_t`

### Vai trò

Là plaintext 16 byte chứa kết quả nghiệp vụ của Patient Node trước khi mã hóa. Gateway chỉ được sử dụng cấu trúc này sau khi AES-GCM xác thực và giải mã thành công.

### Cấu trúc

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

### Phân bố byte

| Trường | Kích thước | Ý nghĩa |
|---|---:|---|
| `session_id` | 4 byte | ID của phiên đo |
| `event_type` | 1 byte | Manual Check, Monitor Event hoặc loại sự kiện khác |
| `classification` | 1 byte | `ASTHMA_LIKE`, `NON_ASTHMA`, `UNSURE` |
| `model_score` | 4 byte | Điểm tin cậy của mô hình |
| `audio_quality` | 1 byte | `AUDIO_OK`, `TOO_WEAK`, `TOO_LOUD`, `INACTIVE` |
| `vitals_valid` | 1 byte | `1` nếu HR/SpO₂ hợp lệ, ngược lại là `0` |
| `heart_rate` | 2 byte | Nhịp tim BPM |
| `spo2` | 1 byte | SpO₂ theo phần trăm |
| `battery` | 1 byte | Pin Node: `0–100`; `255` nếu không khả dụng |
| **Tổng** | **16 byte** | Plaintext cố định của chiều Node → Gateway |

### Quy tắc

- Không dùng `bool` hoặc enum có kích thước phụ thuộc trình biên dịch trong packet.
- Nếu `vitals_valid == 0`, `heart_rate` và `spo2` phải bằng `0` và bên nhận phải bỏ qua hai trường này.
- Payload revised không chứa timestamp.
- Payload không được gửi trực tiếp qua `esp_now_send()`.

---

## 5. `Response_Payload_t`

### Vai trò

Là plaintext 16 byte do Gateway tạo để phản hồi một Event đã nhận. Phản hồi cũng phải được mã hóa bằng AES-128-GCM.

### Cấu trúc

```cpp
#pragma pack(push, 1)
typedef struct {
    uint32_t target_device_id;
    uint32_t session_id;
    uint8_t response_code;
    uint8_t reserved[7];
} Response_Payload_t;
#pragma pack(pop)

static_assert(sizeof(Response_Payload_t) == 16);
```

### Phân bố byte

| Trường | Kích thước | Ý nghĩa |
|---|---:|---|
| `target_device_id` | 4 byte | Node được nhận phản hồi |
| `session_id` | 4 byte | Phiên đo mà Gateway đang phản hồi |
| `response_code` | 1 byte | ACK/NACK nghiệp vụ |
| `reserved` | 7 byte | Giữ payload đủ 16 byte và dành cho mở rộng |
| **Tổng** | **16 byte** | Plaintext cố định của chiều Gateway → Node |

### Các mã phản hồi

| Mã | Ý nghĩa | Node xử lý |
|---|---|---|
| `RESPONSE_ACK_ACCEPTED` | Event mới đã được Gateway tiếp nhận | Xóa `tx_inflight` |
| `RESPONSE_ACK_DUPLICATE` | Event đã được nhận trước đó | Xóa `tx_inflight` |
| `RESPONSE_NACK_BUSY` | Gateway tạm thời chưa thể nhận | Chờ và retry packet cũ |
| `RESPONSE_NACK_UNSUPPORTED` | Loại Event không được hỗ trợ | Dừng gửi hoặc báo lỗi |
| `RESPONSE_NACK_INTERNAL` | Gateway gặp lỗi nội bộ | Retry theo giới hạn |

Payload revised không chứa timestamp và không thực hiện đồng bộ thời gian cho Node.

---

## 6. `Secure_Packet_t`

### Vai trò

Đây là packet vật lý duy nhất được truyền trực tiếp qua ESP-NOW ở cả hai chiều.

```text
MSG_PATIENT_EVENT
    ciphertext chứa Node_Payload_t

MSG_GATEWAY_RESPONSE
    ciphertext chứa Response_Payload_t
```

### Cấu trúc

```cpp
#pragma pack(push, 1)
typedef struct {
    // HEADER / AAD: 12 byte
    uint16_t magic;
    uint8_t protocol_version;
    uint8_t message_type;
    uint32_t device_id;
    uint32_t sequence;

    // AES-GCM
    uint8_t nonce[12];
    uint8_t ciphertext[16];
    uint8_t authentication_tag[16];
} Secure_Packet_t;
#pragma pack(pop)

static_assert(sizeof(Secure_Packet_t) == 56);
```

### Phân vùng

| Vùng | Kích thước | Có mã hóa? | Có được GCM xác thực? |
|---|---:|---:|---:|
| Header/AAD | 12 byte | Không | Có |
| Nonce | 12 byte | Không | Dùng cho GCM |
| Ciphertext | 16 byte | Có | Có |
| Authentication tag | 16 byte | Không | Là kết quả xác thực |
| **Tổng** | **56 byte** |  |  |

### Thành phần Header/AAD

| Trường | Kích thước | Ý nghĩa |
|---|---:|---|
| `magic` | 2 byte | Nhận diện đúng giao thức NCKH |
| `protocol_version` | 1 byte | Phiên bản cấu trúc packet |
| `message_type` | 1 byte | Phân biệt Event và Response |
| `device_id` | 4 byte | Thiết bị gửi packet |
| `sequence` | 4 byte | Ghép phản hồi, chống trùng và phát lại |

### Quy tắc bắt buộc

- Node → Gateway và Gateway → Node sử dụng hai khóa AES khác nhau.
- Mỗi message mới phải có nonce mới.
- Retry phải gửi lại nguyên `Secure_Packet_t`; không mã hóa lại, không đổi nonce và không tăng sequence.
- Bên nhận không được đọc plaintext nếu xác thực tag thất bại.
- GCM tag thay CRC32 trong giao thức này.
- Packet sai kích thước, MAC, magic, phiên bản hoặc tag phải bị loại bỏ.

---

## 7. `Gateway_Payload_t`

### Vai trò

Là snapshot mới nhất về Gateway, môi trường, mạng và GPS. Cấu trúc này thuộc tầng Gateway/cloud, không thuộc packet ESP-NOW 56 byte.

### Thành phần

| Nhóm | Trường |
|---|---|
| Định danh/thời gian | `gateway_id`, `timestamp` |
| Chế độ | `operating_mode`, `uplink_type` |
| Môi trường | `temperature`, `humidity`, `pressure`, `tvoc`, `eco2` |
| Tình trạng cảm biến | `sensor_valid_mask` |
| Wi-Fi | `wifi_connected`, `wifi_rssi_dbm` |
| LTE | `lte_registered`, `lte_rssi_dbm` |
| MQTT | `mqtt_connected` |
| GPS | `latitude`, `longitude`, `gps_timestamp` |
| Nguồn | `battery_gate` |

### Quy tắc

- `timestamp` là thời điểm Gateway tạo/cập nhật snapshot, không phải thời điểm chính xác Patient Event xảy ra.
- Lỗi cảm biến được thể hiện bằng `sensor_valid_mask`, không dùng giá trị `0` làm dấu hiệu lỗi.
- `Gateway_Payload_t` được cập nhật định kỳ và có thể ghi đè snapshot cũ.
- Không gửi raw binary của struct này lên MQTT; cần chuyển thành JSON hoặc schema rõ ràng.
- Không khóa kích thước binary của struct vì đây không phải packet RF cố định và trình biên dịch có thể chèn padding.

---

## 8. `Complete_Packet_t`

### Vai trò

Là cấu trúc tổng hợp tạm thời do Gateway dựng khi chuẩn bị publish MQTT/cloud.

### Cấu trúc

```cpp
typedef struct {
    uint8_t has_patient_event;
    Gateway_Payload_t gateway;
    Node_Payload_t node;
} Complete_Packet_t;
```

Tên field thực tế có thể là `gate` và `patient_event`, nhưng kiểu dữ liệu phải thống nhất là `Gateway_Payload_t` và `Node_Payload_t`.

### Thành phần

| Trường | Vai trò |
|---|---|
| `has_patient_event` | Cho biết packet có chứa Event mới cần cập nhật hay không |
| `Gateway_Payload_t` | Snapshot Gateway hiện tại |
| `Node_Payload_t` | Patient Event mới nhất |

### Quy tắc Dashboard

```text
has_patient_event == 0
    -> luôn cập nhật Gateway/environment/network
    -> bỏ qua phần Node trong packet
    -> không thêm Patient Event History

has_patient_event == 1
    -> cập nhật Gateway/environment/network
    -> cập nhật Latest Patient Event
    -> thêm Event History
    -> chỉ dùng HR/SpO₂ khi vitals_valid == 1
```

`Complete_Packet_t` không phải packet ESP-NOW, không chứa nonce/ciphertext/tag/khóa và không được xem là hàng đợi lưu lịch sử.

---

## 9. Trạng thái dữ liệu phía Gateway

Gateway duy trì:

```cpp
Node_Payload_t    current_node{};
Gateway_Payload_t current_gateway{};

bool current_node_valid = false;
bool current_gateway_valid = false;
bool node_dirty = false;
```

### Khi nhận Node Event hợp lệ

```text
current_node = Node Event vừa giải mã
current_node_valid = true
node_dirty = true
```

### Khi MQTT publish thành công Event

```text
node_dirty = false
```

Không xóa `current_node` vì Gateway TFT vẫn có thể cần hiển thị Event gần nhất.

Nếu Internet mất và Event mới đến, Event mới được phép ghi đè Event cũ. Kiến trúc revised không giữ offline queue đầy đủ.

---

## 10. Bảng tổng hợp cuối cùng

| Struct | Nơi tạo | Nơi sử dụng | Kích thước cố định | Có truyền trực tiếp? |
|---|---|---|---:|---|
| `Patient_Session_t` | Patient Node | State Machine Node | Không khóa | Không |
| `Node_Payload_t` | Patient Node | AES-GCM/Gateway | 16 byte | Không, phải mã hóa |
| `Response_Payload_t` | Gateway | AES-GCM/Patient Node | 16 byte | Không, phải mã hóa |
| `Secure_Packet_t` | Node hoặc Gateway | ESP-NOW hai chiều | 56 byte | Có, qua ESP-NOW |
| `Gateway_Payload_t` | Gateway | Gateway/TFT/cloud | Không khóa binary | Không qua ESP-NOW |
| `Complete_Packet_t` | Gateway | MQTT/backend/Qt6 | Không khóa binary | Chuyển thành JSON |

---

## 11. Quy tắc đặt tên đã chốt

```text
Node_Payload_t             // Dữ liệu nghiệp vụ từ Patient Node
Response_Payload_t // Phản hồi nghiệp vụ từ Gateway
Secure_Packet_t            // Packet AES-GCM thật sự truyền ESP-NOW
Gateway_Payload_t          // Snapshot Gateway/environment/network/GPS
Complete_Packet_t          // Gateway + Node data cho cloud/dashboard
```

Không sử dụng lại các tên cũ:

```text
Patient_Event_Payload_t
Secure_EspNow_Packet_t
Gate_Payload_t
```

