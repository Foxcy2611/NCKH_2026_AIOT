# ĐẶC TẢ MÃ HÓA AES-128-GCM CHO ESP-NOW

> Phạm vi: liên kết cục bộ giữa **Patient Node** và **Gateway** trong dự án NCKH.
>
> Trạng thái: bản thiết kế dùng chung trước khi triển khai code hai phía.

---

## 1. Mục tiêu

Patient Node gửi kết quả âm thanh, chỉ số sinh hiệu và thông tin phiên đo qua ESP-NOW. Dữ liệu này không được gửi trực tiếp dưới dạng rõ.

Thiết kế sử dụng:

- ESP-NOW làm phương tiện truyền dữ liệu.
- `peer.encrypt = false` tại tầng ESP-NOW.
- AES-128-GCM tại tầng ứng dụng để mã hóa và xác thực packet.
- ACK/NACK riêng để Patient Node biết Gateway đã thực sự xử lý packet.
- Retry sử dụng lại đúng packet mã hóa cũ, không tạo packet mới.

AES-GCM đồng thời cung cấp:

1. **Tính bí mật:** người nghe lén không đọc được nội dung sự kiện.
2. **Tính toàn vẹn:** dữ liệu bị sửa sẽ làm kiểm tra `authentication_tag` thất bại.
3. **Tính xác thực:** chỉ thiết bị có đúng khóa mới tạo được packet hợp lệ.

Do `authentication_tag` đã đảm nhiệm kiểm tra toàn vẹn và xác thực, packet AES-GCM **không dùng CRC32**.

---

## 2. Nguyên tắc kiến trúc

Chỉ có **một loại packet vật lý** được truyền qua ESP-NOW ở cả hai chiều:

```text
Secure_EspNow_Packet_t
```

Packet này có thể chứa một trong hai loại dữ liệu logic:

```text
MSG_PATIENT_EVENT       -> Patient_Event_Payload_t
MSG_GATEWAY_RESPONSE    -> Gateway_Response_Payload_t
```

Hai payload chỉ là dữ liệu tạm trước mã hóa hoặc sau giải mã. Chúng không được gửi trực tiếp.

```text
Patient_Session_t
        |
        v
Patient_Event_Payload_t (plaintext tạm)
        |
        | AES-128-GCM
        v
Secure_EspNow_Packet_t (ciphertext + tag)
        |
        | ESP-NOW
        v
Gateway xác thực tag và giải mã
        |
        v
Patient_Event_Payload_t
```

Chiều phản hồi hoạt động tương tự:

```text
Gateway_Response_Payload_t
        |
        | AES-128-GCM
        v
Secure_EspNow_Packet_t
        |
        | ESP-NOW
        v
Patient Node xác thực và giải mã ACK/NACK
```

Quy ước tên của dự án: `Secure_EspNow_Packet_t` là **khung truyền bảo mật dùng chung** cho cả Patient Event và Gateway Response. Tên này giúp phân biệt rõ packet đã mã hóa với hai payload plaintext.

| Chiều truyền | `message_type` | Plaintext trước mã hóa | Khóa sử dụng |
|---|---|---|---|
| Node → Gateway | `MSG_PATIENT_EVENT` | `Patient_Event_Payload_t` | `KEY_NODE_TO_GATEWAY` |
| Gateway → Node | `MSG_GATEWAY_RESPONSE` | `Gateway_Response_Payload_t` | `KEY_GATEWAY_TO_NODE` |

Hai chiều có cùng kích thước và cùng cách phân vùng packet. Sự khác nhau nằm ở nội dung plaintext, loại message, khóa, nonce và tag.

---

## 3. Phân vùng packet

Một packet bảo mật gồm bốn vùng:

```text
+------------------+----------+------------------+--------------------+
| HEADER / AAD     | NONCE    | CIPHERTEXT       | AUTHENTICATION TAG |
| 12 byte          | 12 byte  | 24 byte          | 16 byte            |
+------------------+----------+------------------+--------------------+
                         Tổng: 64 byte
```

### 3.1. HEADER / AAD

Vùng này không mã hóa vì bên nhận cần đọc trước khi chọn khóa và giải mã.

```text
magic             2 byte
protocol_version  1 byte
message_type      1 byte
device_id         4 byte
sequence          4 byte
```

Tổng cộng: `12 byte`.

Mặc dù không mã hóa, toàn bộ Header được đưa vào AAD của AES-GCM. Vì vậy, nếu một bit của Header bị thay đổi thì việc xác thực tag sẽ thất bại.

| Trường | Tác dụng |
|---|---|
| `magic` | Nhận biết đây là packet của đúng giao thức NCKH |
| `protocol_version` | Phát hiện Node và Gateway dùng cấu trúc không tương thích |
| `message_type` | Phân biệt Patient Event và Gateway Response |
| `device_id` | ID của thiết bị đang gửi packet và dùng để chọn đúng khóa AES |
| `sequence` | Ghép ACK với Event, phát hiện packet trùng và chống phát lại |

### 3.2. NONCE

- Kích thước: `12 byte`.
- Không cần giữ bí mật.
- Được truyền cùng packet.
- Phải khác nhau cho mỗi packet mới sử dụng cùng khóa.
- Retry phải dùng lại toàn bộ packet cũ, bao gồm nonce cũ.

Trong phạm vi nguyên mẫu NCKH, phương án đơn giản là:

```cpp
esp_fill_random(packet.nonce, sizeof(packet.nonce));
```

Nonce chỉ được tạo **một lần khi đóng gói message mới**. Không tạo nonce mới trong mỗi lần retry.

Nếu phát triển thành sản phẩm lâu dài, có thể thay bằng:

```text
device_id 4 byte + bộ đếm bền vững 8 byte
```

### 3.3. CIPHERTEXT

- Kích thước cố định: `24 byte`.
- Là kết quả mã hóa một payload logic 24 byte.
- Không được ép kiểu ciphertext thành payload trước khi xác thực và giải mã thành công.

### 3.4. AUTHENTICATION TAG

- Kích thước: `16 byte`.
- Được AES-GCM tạo trong lúc mã hóa.
- Bên nhận phải xác thực tag trước khi sử dụng plaintext.
- Nếu tag sai, bỏ packet và không dùng dữ liệu giải mã.

---

## 4. Các kiểu dữ liệu dùng chung

Các enum và struct giao thức phải nằm trong **một header dùng chung cho cả Patient Node và Gateway**. Không sao chép rồi sửa độc lập ở hai dự án vì rất dễ lệch kích thước.

Tên file đề xuất:

```text
Final_Project_NCKH/Common_Protocol/Secure_Protocol.h
```

### 4.1. Hằng số và loại message

```cpp
#ifndef NCKH_SECURE_PROTOCOL_H
#define NCKH_SECURE_PROTOCOL_H

#include <stddef.h>
#include <stdint.h>

constexpr uint16_t SECURE_PACKET_MAGIC = 0xA57A;
constexpr uint8_t SECURE_PROTOCOL_VERSION = 1;

constexpr size_t AES_128_KEY_SIZE = 16;
constexpr size_t AES_GCM_NONCE_SIZE = 12;
constexpr size_t AES_GCM_TAG_SIZE = 16;
constexpr size_t SECURE_PAYLOAD_SIZE = 24;

typedef enum : uint8_t {
    MSG_PATIENT_EVENT = 1,
    MSG_GATEWAY_RESPONSE = 2
} Secure_Message_Type_t;

typedef enum : uint8_t {
    RESPONSE_ACK_ACCEPTED = 0,
    RESPONSE_ACK_DUPLICATE,
    RESPONSE_NACK_BUSY,
    RESPONSE_NACK_UNSUPPORTED,
    RESPONSE_NACK_INTERNAL
} Gateway_Response_Code_t;
```

`ACK_DUPLICATE` có nghĩa Gateway đã nhận Event này trước đó. Gateway không lưu hoặc publish lại nhưng vẫn xác nhận thành công để Node xóa packet khỏi hàng đợi.

### 4.2. Payload Patient Event

```cpp
#pragma pack(push, 1)

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

    uint8_t battery;
} Patient_Event_Payload_t;

#pragma pack(pop)

static_assert(
    sizeof(Patient_Event_Payload_t) == SECURE_PAYLOAD_SIZE,
    "Sai kich thuoc Patient_Event_Payload_t"
);
```

Quy ước:

- `vitals_valid` dùng `uint8_t`, không dùng `bool` trong dữ liệu truyền.
- Enum được ép thành `uint8_t` trước khi gán vào payload.
- `model_score` vẫn dùng `float` vì hai thiết bị hiện đều là ESP32. Nếu sau này có thiết bị kiến trúc khác, nên đổi sang số nguyên có hệ số.
- Toàn bộ số nhiều byte hiện dùng thứ tự byte của ESP32. Nếu giao tiếp với thiết bị khác họ vi điều khiển, phải bổ sung quy tắc chuyển thứ tự byte.

### 4.3. Payload phản hồi Gateway

```cpp
#pragma pack(push, 1)

typedef struct {
    uint32_t target_device_id;     // Node được phản hồi
    uint32_t session_id;           // Session của Event đã nhận

    uint64_t gateway_timestamp;    // Unix time theo ms từ NTP/GPS

    uint8_t response_code;         // ACK_ACCEPTED, ACK_DUPLICATE...
    uint8_t time_valid;            // 1 nếu timestamp hợp lệ

    uint8_t reserved[6];           // Dành cho mở rộng sau này
} Gateway_Response_Payload_t;

#pragma pack(pop)

static_assert(
    sizeof(Gateway_Response_Payload_t) == 24,
    "Sai kich thuoc Gateway_Response_Payload_t"
);
```

### 4.4. Packet vật lý dùng cho cả hai chiều

```cpp
#pragma pack(push, 1)

typedef struct {
    // -------- HEADER / AAD: 12 byte --------
    uint16_t magic;
    uint8_t protocol_version;
    uint8_t message_type;
    uint32_t device_id;
    uint32_t sequence;

    // -------- AES-GCM NONCE: 12 byte --------
    uint8_t nonce[AES_GCM_NONCE_SIZE];

    // -------- ENCRYPTED PAYLOAD: 24 byte --------
    uint8_t ciphertext[SECURE_PAYLOAD_SIZE];

    // -------- AES-GCM TAG: 16 byte --------
    uint8_t authentication_tag[AES_GCM_TAG_SIZE];
} Secure_EspNow_Packet_t;

#pragma pack(pop)

constexpr size_t SECURE_AAD_SIZE =
    offsetof(Secure_EspNow_Packet_t, nonce);

static_assert(
    sizeof(Secure_EspNow_Packet_t) == 64,
    "Sai kich thuoc Secure_EspNow_Packet_t"
);

static_assert(
    SECURE_AAD_SIZE == 12,
    "Sai kich thuoc vung AAD"
);

#endif /* NCKH_SECURE_PROTOCOL_H */
```

Chỉ `Secure_EspNow_Packet_t` được đưa vào `esp_now_send()`.

---

## 5. Quản lý khóa

AES-128 dùng khóa đúng `16 byte`.

Nên dùng hai khóa khác nhau theo chiều truyền:

```text
KEY_NODE_TO_GATEWAY
KEY_GATEWAY_TO_NODE
```

Lợi ích:

- Tách biệt chiều Event và chiều Response.
- Giảm nguy cơ trùng nonce giữa hai thiết bị.
- Packet bắt được ở một chiều không thể được dùng lại nguyên trạng ở chiều ngược lại.

Nguyên tắc bắt buộc:

- Không in khóa ra Serial.
- Không ghi khóa thật vào tài liệu.
- Không đẩy khóa thật lên kho mã nguồn công khai.
- Node và Gateway phải được cấp đúng cặp khóa tương ứng.
- Nếu có nhiều Patient Node, nên cấp khóa riêng cho từng Node.
- Gateway chọn khóa dựa vào `device_id` kết hợp với MAC nguồn đã đăng ký.

Khóa viết trực tiếp trong firmware chỉ phù hợp nguyên mẫu. Nếu phát triển sản phẩm, cần cân nhắc Secure Boot, Flash Encryption và quy trình cấp khóa riêng.

---

## 6. Hàm mã hóa và giải mã dùng chung

ESP32 có thể sử dụng Mbed TLS qua:

```cpp
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <esp_system.h>
#include <mbedtls/gcm.h>
```

### 6.1. Mã hóa

```cpp
bool AES128GCM_Encrypt(
    const uint8_t key[AES_128_KEY_SIZE],
    const uint8_t nonce[AES_GCM_NONCE_SIZE],
    const uint8_t* aad,
    size_t aad_size,
    const uint8_t* plaintext,
    size_t plaintext_size,
    uint8_t* ciphertext,
    uint8_t tag[AES_GCM_TAG_SIZE]
) {
    if (key == nullptr || nonce == nullptr || aad == nullptr
        || plaintext == nullptr || ciphertext == nullptr || tag == nullptr) {
        return false;
    }

    mbedtls_gcm_context context;
    mbedtls_gcm_init(&context);

    int result = mbedtls_gcm_setkey(
        &context,
        MBEDTLS_CIPHER_ID_AES,
        key,
        128
    );

    if (result == 0) {
        result = mbedtls_gcm_crypt_and_tag(
            &context,
            MBEDTLS_GCM_ENCRYPT,
            plaintext_size,
            nonce,
            AES_GCM_NONCE_SIZE,
            aad,
            aad_size,
            plaintext,
            ciphertext,
            AES_GCM_TAG_SIZE,
            tag
        );
    }

    mbedtls_gcm_free(&context);
    return result == 0;
}
```

### 6.2. Xác thực và giải mã

```cpp
bool AES128GCM_Decrypt(
    const uint8_t key[AES_128_KEY_SIZE],
    const uint8_t nonce[AES_GCM_NONCE_SIZE],
    const uint8_t* aad,
    size_t aad_size,
    const uint8_t* ciphertext,
    size_t ciphertext_size,
    const uint8_t tag[AES_GCM_TAG_SIZE],
    uint8_t* plaintext
) {
    if (key == nullptr || nonce == nullptr || aad == nullptr
        || ciphertext == nullptr || tag == nullptr || plaintext == nullptr) {
        return false;
    }

    mbedtls_gcm_context context;
    mbedtls_gcm_init(&context);

    int result = mbedtls_gcm_setkey(
        &context,
        MBEDTLS_CIPHER_ID_AES,
        key,
        128
    );

    if (result == 0) {
        result = mbedtls_gcm_auth_decrypt(
            &context,
            ciphertext_size,
            nonce,
            AES_GCM_NONCE_SIZE,
            aad,
            aad_size,
            tag,
            AES_GCM_TAG_SIZE,
            ciphertext,
            plaintext
        );
    }

    mbedtls_gcm_free(&context);

    if (result != 0) {
        memset(plaintext, 0, ciphertext_size);
        return false;
    }

    return true;
}
```

Không được sử dụng nội dung `plaintext` nếu `AES128GCM_Decrypt()` trả về `false`.

---

## 7. Patient Node tạo Event packet

### 7.1. Chuyển Session thành payload

```cpp
Patient_Event_Payload_t payload{};

payload.session_id = session.session_id;
payload.timestamp = timestamp;
payload.event_type = static_cast<uint8_t>(session.event_type);
payload.classification = static_cast<uint8_t>(session.classification);
payload.model_score = session.model_score;
payload.audio_quality = static_cast<uint8_t>(session.audio_quality);
payload.vitals_valid = session.vitals_valid ? 1U : 0U;
payload.heart_rate = session.vitals_valid ? session.heart_rate : 0U;
payload.spo2 = session.vitals_valid ? session.spo2 : 0U;
payload.battery = battery_percent;
```

### 7.2. Tạo Header, nonce và mã hóa

```cpp
Secure_EspNow_Packet_t packet{};

packet.magic = SECURE_PACKET_MAGIC;
packet.protocol_version = SECURE_PROTOCOL_VERSION;
packet.message_type = MSG_PATIENT_EVENT;
packet.device_id = device_id;
packet.sequence = sequence;

// Chỉ gọi cho message mới, không gọi lại khi retry.
esp_fill_random(packet.nonce, sizeof(packet.nonce));

const bool encrypted = AES128GCM_Encrypt(
    KEY_NODE_TO_GATEWAY,
    packet.nonce,
    reinterpret_cast<const uint8_t*>(&packet),
    SECURE_AAD_SIZE,
    reinterpret_cast<const uint8_t*>(&payload),
    sizeof(payload),
    packet.ciphertext,
    packet.authentication_tag
);
```

Nếu mã hóa thất bại:

- Không gửi packet.
- Không đưa packet lỗi vào hàng đợi.
- Báo lỗi mã hóa cho tầng điều khiển.

Nếu thành công:

- Sao chép toàn bộ `Secure_EspNow_Packet_t` vào hàng đợi Pending.
- Gọi `esp_now_send()` với đúng 64 byte.
- Retry gửi lại đúng 64 byte đã lưu.

```cpp
esp_now_send(
    gateway_mac,
    reinterpret_cast<const uint8_t*>(&packet),
    sizeof(packet)
);
```

---

## 8. Gateway nhận, xác thực và giải mã Event

Callback nhận ESP-NOW không nên giải mã, ghi NVS hay publish MQTT. Callback chỉ:

1. Kiểm tra con trỏ và kích thước sơ bộ.
2. Sao chép MAC nguồn và đúng 64 byte packet vào hàng đợi RTOS.
3. Trả quyền xử lý càng sớm càng tốt.

Không giữ lại con trỏ `data` của callback vì vùng nhớ đó không còn bảo đảm hợp lệ sau khi callback kết thúc.

Trong `EspNowTask`, Gateway xử lý theo thứ tự:

```text
1. Kiểm tra received_length == sizeof(Secure_EspNow_Packet_t)
2. memcpy dữ liệu vào một biến Secure_EspNow_Packet_t cục bộ
3. Kiểm tra MAC nguồn có được đăng ký không
4. Kiểm tra magic
5. Kiểm tra protocol_version
6. Kiểm tra message_type == MSG_PATIENT_EVENT
7. Kiểm tra device_id khớp MAC/thiết bị đã đăng ký
8. Chọn KEY_NODE_TO_GATEWAY tương ứng
9. Xác thực tag và giải mã
10. Chỉ khi thành công mới đọc Patient_Event_Payload_t
11. Kiểm tra sequence trùng/cũ/mới
12. Đưa Event hợp lệ vào hàng đợi xử lý/MQTT
13. Tạo phản hồi bảo mật gửi về Node
```

Code giải mã khái quát:

```cpp
Patient_Event_Payload_t payload{};

const bool valid = AES128GCM_Decrypt(
    KEY_NODE_TO_GATEWAY,
    packet.nonce,
    reinterpret_cast<const uint8_t*>(&packet),
    SECURE_AAD_SIZE,
    packet.ciphertext,
    sizeof(packet.ciphertext),
    packet.authentication_tag,
    reinterpret_cast<uint8_t*>(&payload)
);

if (!valid) {
    // Tag sai: bỏ packet, không dùng payload, không phản hồi chi tiết.
    return;
}
```

Gateway chỉ gửi ACK/NACK sau khi Event đã vượt qua xác thực AES-GCM.

---

## 9. Gateway tạo ACK/NACK bảo mật

### 9.1. Khi nào phản hồi gì?

| Trường hợp | Hành động Gateway |
|---|---|
| Tag hợp lệ, Event mới và đã đưa vào hàng đợi | `RESPONSE_ACK_ACCEPTED` |
| Tag hợp lệ, Event trùng đã xử lý trước đó | `RESPONSE_ACK_DUPLICATE` |
| Tag hợp lệ nhưng hàng đợi Gateway đầy | `RESPONSE_NACK_BUSY` |
| Tag hợp lệ nhưng loại Event không hỗ trợ | `RESPONSE_NACK_UNSUPPORTED` |
| Tag hợp lệ nhưng có lỗi xử lý nội bộ | `RESPONSE_NACK_INTERNAL` |
| Sai kích thước, MAC lạ, magic sai hoặc tag sai | Im lặng và bỏ packet |

Packet tag sai không được nhận phản hồi chi tiết. Patient Node sẽ timeout và retry.

### 9.2. Tạo payload phản hồi

```cpp
Gateway_Response_Payload_t response{};

response.target_device_id = event_packet.device_id;
response.session_id = event_payload.session_id;
response.gateway_timestamp = gateway_timestamp_ms;
response.response_code = RESPONSE_ACK_ACCEPTED;
response.time_valid = gateway_time_is_valid ? 1U : 0U;
```

### 9.3. Mã hóa phản hồi

```cpp
Secure_EspNow_Packet_t response_packet{};

response_packet.magic = SECURE_PACKET_MAGIC;
response_packet.protocol_version = SECURE_PROTOCOL_VERSION;
response_packet.message_type = MSG_GATEWAY_RESPONSE;
response_packet.device_id = gateway_id;

// Dùng sequence của Event để Node ghép phản hồi nhanh.
response_packet.sequence = event_packet.sequence;

// Mỗi phản hồi mới có nonce mới, kể cả phản hồi cho Event retry.
esp_fill_random(
    response_packet.nonce,
    sizeof(response_packet.nonce)
);

const bool encrypted = AES128GCM_Encrypt(
    KEY_GATEWAY_TO_NODE,
    response_packet.nonce,
    reinterpret_cast<const uint8_t*>(&response_packet),
    SECURE_AAD_SIZE,
    reinterpret_cast<const uint8_t*>(&response),
    sizeof(response),
    response_packet.ciphertext,
    response_packet.authentication_tag
);
```

Nếu mã hóa thành công, Gateway gửi `response_packet` về đúng MAC nguồn của Event.

ACK/NACK không cần một ACK khác. Nếu ACK bị mất, Node sẽ gửi lại Event; Gateway nhận diện Event trùng và gửi `ACK_DUPLICATE` mới.

---

## 10. Patient Node nhận và xử lý phản hồi

Callback nhận của Node cũng chỉ sao chép packet vào buffer/hàng đợi và đặt cờ. Việc xác thực, giải mã và đổi trạng thái diễn ra trong `EspNow_Process()` ở vòng lặp chính.

Thứ tự kiểm tra:

```text
1. MAC nguồn phải là Gateway đã đăng ký
2. Kích thước phải đúng 64 byte
3. magic và protocol_version phải đúng
4. message_type phải là MSG_GATEWAY_RESPONSE
5. device_id phải là Gateway ID dự kiến
6. sequence phải khớp packet Pending
7. Xác thực tag bằng KEY_GATEWAY_TO_NODE
8. Giải mã Gateway_Response_Payload_t
9. target_device_id phải là Device ID của Node
10. session_id phải khớp Pending Event; sequence đã được đối chiếu ở Header/AAD
11. Xử lý response_code
```

Nếu `time_valid == 1`, Node có thể dùng `gateway_timestamp` để cập nhật offset thời gian cục bộ. ACK/NACK không tạo `session_id` mới; Gateway luôn lặp lại `session_id` của Event đang phản hồi.

Xử lý kết quả:

```text
ACK_ACCEPTED hoặc ACK_DUPLICATE
    -> STATUS_ACK_CONFIRMED
    -> xóa Event khỏi Pending Queue
    -> đánh dấu synced = true

NACK_BUSY
    -> STATUS_RETRY_WAIT
    -> chờ rồi gửi lại packet mã hóa cũ

NACK_UNSUPPORTED hoặc NACK_INTERNAL
    -> lưu Event cục bộ
    -> synced = false
    -> không giữ Node kẹt vô hạn

Không có phản hồi hợp lệ trước timeout
    -> tăng retry_count
    -> gửi lại packet mã hóa cũ
    -> hết retry thì lưu local, synced = false
```

Không được xem callback gửi `ESP_NOW_SEND_SUCCESS` là ACK. Callback này chỉ xác nhận tầng MAC đã gửi được frame; ứng dụng vẫn phải chờ `MSG_GATEWAY_RESPONSE` hợp lệ.

---

## 11. Hàng đợi Pending và quy tắc retry

Hàng đợi phải lưu packet **sau mã hóa**:

```cpp
typedef struct {
    Event_Send_Status_t status;
    Secure_EspNow_Packet_t packet;

    uint8_t retry_count;
    uint32_t last_sent_millis;
} Pending_ACK_Entry_t;
```

Quy tắc bắt buộc:

- Không tăng `sequence` khi retry.
- Không tạo `session_id` mới khi retry.
- Không tạo nonce mới khi retry.
- Không mã hóa lại payload khi retry.
- Không thay đổi một byte nào trong packet Pending.
- Gateway không lưu hoặc publish lại Event trùng.
- Gateway vẫn ACK Event trùng để Node kết thúc retry.

Luồng:

```text
SESSION_READY
    |
    v
Tạo Payload -> Mã hóa -> Lưu Secure Packet vào Pending Queue
    |
    v
esp_now_send()
    |
    +-- callback SEND_FAIL --> RETRY_WAIT
    |
    +-- callback SEND_OK ----> ACK_PENDING
                                    |
                                    +-- ACK hợp lệ --> xóa Pending
                                    |
                                    +-- timeout ----> RETRY_WAIT
```

Giá trị timeout và số retry cụ thể cần đo thực nghiệm. Giá trị khởi đầu có thể dùng:

```text
ACK timeout: 1000 ms
Retry delay: 300-500 ms
Số lần retry thêm: 3
```

Nên cộng thêm một khoảng ngẫu nhiên nhỏ vào retry delay nếu có nhiều Node để tránh các thiết bị gửi lại cùng thời điểm.

---

## 12. Cấu hình ESP-NOW khi dùng AES-GCM ứng dụng

Peer không sử dụng mã hóa tích hợp của ESP-NOW:

```cpp
esp_now_peer_info_t peer_info{};

memcpy(peer_info.peer_addr, peer_mac, 6);
peer_info.channel = ESP_NOW_CHANNEL;
peer_info.ifidx = WIFI_IF_STA;
peer_info.encrypt = false;
```

Khi toàn bộ peer đều có `encrypt = false`, không cần:

```text
PMK
LMK
esp_now_set_pmk()
peer_info.lmk
```

Node và Gateway vẫn bắt buộc:

- Cùng kênh Wi-Fi.
- Biết MAC của nhau hoặc thêm peer động sau khi xác thực cấu hình.
- Đăng ký callback gửi và callback nhận.
- Kiểm tra giá trị trả về của mọi hàm ESP-NOW.

Gateway đang kết nối Wi-Fi để MQTT thì kênh ESP-NOW phải đi theo kênh của Access Point. Patient Node phải dùng đúng kênh đó.

---

## 13. Kiểm thử bắt buộc

### 13.1. Kiểm thử AES-GCM cục bộ

1. Cùng khóa + cùng nonce + đúng AAD: giải mã thành công và payload trùng tuyệt đối.
2. Sửa một bit ciphertext: giải mã thất bại.
3. Sửa một bit Header/AAD: giải mã thất bại.
4. Sửa một bit tag: giải mã thất bại.
5. Sửa một bit nonce: giải mã thất bại.
6. Dùng sai khóa: giải mã thất bại.

### 13.2. Kiểm thử Node ↔ Gateway

1. Event hợp lệ: Gateway nhận một lần, Node nhận `ACK_ACCEPTED`.
2. Làm mất ACK: Node retry cùng packet; Gateway không lưu trùng và trả `ACK_DUPLICATE`.
3. Gateway tắt: Node retry đủ số lần rồi lưu local.
4. Gateway queue đầy: trả `NACK_BUSY`, Node chờ rồi retry.
5. Giả ACK bằng dữ liệu tùy ý: Node phải loại vì GCM tag sai.
6. ACK cũ có sequence khác: Node phải loại.
7. Packet từ MAC không đăng ký: bên nhận phải loại.
8. Node reset: packet đã lưu local vẫn có thể gửi lại nguyên bản.

### 13.3. Điều kiện đạt

- `sizeof(Patient_Event_Payload_t) == 24` ở cả hai thiết bị.
- `sizeof(Gateway_Response_Payload_t) == 24` ở cả hai thiết bị.
- `sizeof(Secure_EspNow_Packet_t) == 64` ở cả hai thiết bị.
- Không còn CRC32 trong packet AES-GCM.
- Packet bị sửa không bao giờ được đưa vào MQTT hoặc xóa khỏi Pending Queue.
- Retry không tạo packet, nonce hoặc sequence mới.
- Event trùng không tạo bản ghi trùng ở Gateway.
- ACK giả hoặc ACK cũ không làm Node xóa Event Pending.

---

## 14. Thứ tự triển khai code

1. Tạo một header giao thức chung cho Node và Gateway.
2. Khai báo các payload và `Secure_EspNow_Packet_t` kèm `static_assert`.
3. Viết và kiểm thử `AES128GCM_Encrypt()` / `AES128GCM_Decrypt()` độc lập.
4. Patient Node: chuyển `Patient_Session_t` thành `Patient_Event_Payload_t`.
5. Patient Node: tạo secure packet và lưu vào Pending Queue.
6. Gateway: callback nhận chỉ đẩy raw packet vào RTOS Queue.
7. Gateway: Task xác thực, giải mã, chống trùng và tạo ACK/NACK.
8. Patient Node: callback nhận phản hồi và `EspNow_Process()` xử lý.
9. Kiểm thử timeout, retry, packet giả và mất Gateway.
10. Sau khi hai phía ổn định mới nối MQTT và lưu trữ lâu dài.

---

## 15. Các phần code cũ cần cập nhật khi bắt đầu triển khai

Tài liệu đã được chuyển sang thiết kế AES-GCM, nhưng code hiện tại vẫn đang ở trạng thái chuyển tiếp. Khi bắt đầu sửa code phải thực hiện đồng bộ theo danh sách sau:

- `[ĐÃ CHUẨN BỊ]` `Patient_Node/shared/system_state.h` đã có Patient Event payload và packet bảo mật; bước kế là đưa ba struct giao thức sang **một header dùng chung** cho cả Node và Gateway, bổ sung Gateway Response và `static_assert` kích thước.
- `[ĐÃ SỬA]` `Patient_Node/src/State_Machine.cpp`: chỉ tạo `Patient_Event_Payload_t`; đã bỏ truy cập trường packet rõ và bỏ tính/kiểm tra CRC32.
- `[ĐÃ SỬA]` `Patient_Node/include/Core_Logic/State_Machine.h`: API chỉ công bố payload sẵn sàng và chỉ kết thúc Session sau khi lớp truyền thông báo đã enqueue packet mã hóa thành công.
- `[CẦN SỬA]` `Patient_Node/src/EspNow_Client.cpp`: bỏ PMK/LMK, đặt `peer.encrypt = false`, nhận packet phản hồi và chuyển phần xác thực/giải mã ra ngoài callback.
- `[ĐÃ CHUẨN BỊ]` `Pending_ACK_Entry_t` lưu `Secure_EspNow_Packet_t`; khi triển khai phải bảo đảm retry không mã hóa lại.
- `[CẦN SỬA]` `Gateway/src/main_test_sender_espnow.cpp`: bỏ struct CRC32 cũ, dùng header giao thức chung.
- `[CẦN LÀM]` Gateway receiver: callback chỉ sao chép packet; Task xác thực tag trước khi đọc, lưu, ghép hoặc publish dữ liệu.
- `[ĐÃ CẬP NHẬT]` README tổng thể, Product Definition và bản phân công đã dùng luồng AES-GCM + ACK/NACK bảo mật.

Không nên sửa riêng từng struct ở Node và Gateway. Hai phía phải build từ cùng một định nghĩa giao thức.

---

## 16. Kết luận thiết kế

Thiết kế cuối cùng:

```text
Một Secure_EspNow_Packet_t cố định 64 byte
    |
    +-- MSG_PATIENT_EVENT
    |       chứa Patient_Event_Payload_t đã mã hóa
    |
    +-- MSG_GATEWAY_RESPONSE
            chứa Gateway_Response_Payload_t đã mã hóa
```

- Header được để rõ nhưng được xác thực bằng AAD.
- Nội dung nghiệp vụ nằm hoàn toàn trong ciphertext.
- Nonce dài 12 byte và chỉ sinh một lần cho message mới.
- Tag dài 16 byte thay thế CRC32.
- Hai chiều dùng khóa AES-128 riêng.
- ACK/NACK cũng được mã hóa và xác thực.
- Callback ESP-NOW chỉ sao chép dữ liệu; xử lý nặng diễn ra ngoài callback.
- Retry gửi lại nguyên secure packet cũ.
- Gateway chống trùng bằng `device_id + sequence` và ACK lại packet trùng.

Đây là phương án đủ gọn cho nguyên mẫu, dễ dùng chung giữa sender/receiver và không duy trì hai phiên bản Event packet song song.

---

## 17. Tài liệu tham khảo chính thức

- [ESP-IDF — ESP-NOW](https://docs.espressif.com/projects/esp-idf/en/v5.5/esp32/api-reference/network/esp_now.html)
- [ESP-IDF — Mbed TLS](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/protocols/mbedtls.html)
