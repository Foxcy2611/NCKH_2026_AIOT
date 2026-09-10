# Edge AI & IoT hỗ trợ theo dõi hen suyễn

![ESP32](https://img.shields.io/badge/MCU-ESP32%20%7C%20ESP32--S3-red.svg)
![RTOS](https://img.shields.io/badge/Gateway-FreeRTOS-blue.svg)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![AI](https://img.shields.io/badge/AI-TensorFlow%20Lite%20Micro-orange.svg)
![C++](https://img.shields.io/badge/C++-00599C?style=for-the-badge&logo=c%2B%2B&logoColor=white)
![Qt](https://img.shields.io/badge/Qt-6-41CD52?style=for-the-badge&logo=qt&logoColor=white)
![Network](https://img.shields.io/badge/Network-ESP--NOW%20%7C%20WiFi%20%7C%204G%20LTE%20%7C%20MQTT-brightgreen.svg)


> **Đề tài NCKH:** Nghiên cứu, thiết kế và chế tạo hệ thống IoT ứng dụng
> TinyML hỗ trợ theo dõi và cảnh báo sớm cho bệnh nhân hen suyễn.

Dự án xây dựng một hệ thống theo dõi **edge-first**: Patient Node thu và xử lý
âm thanh hô hấp ngay trên ESP32-S3; Gateway bổ sung dữ liệu môi trường và kết
nối mạng; Dashboard trình bày phiên đo, sự kiện và lịch sử. Việc suy luận cốt
lõi không phụ thuộc Internet và raw audio không được truyền liên tục lên cloud.

> Đây là nguyên mẫu nghiên cứu hỗ trợ sàng lọc và cảnh báo kỹ thuật, không phải
> thiết bị chẩn đoán y khoa và không thay thế đánh giá của nhân viên y tế.

## Kiến trúc hệ thống

```text
                         ESP-NOW
┌──────────────────┐  PatientEvent  ┌──────────────────┐    MQTT  ┌─────────────────┐
│ Patient Edge Node│ ─────────────► │   IoT Gateway    │ ────────►│ Qt6 Dashboard   │
│ ESP32-S3         │                │ ESP32            │          │ sessions/history│
│ INMP441          │                │ environment      │          │ status/alerts   │
│ MAX30102 + OLED  │                │ Wi-Fi/LTE/GPS    │          └─────────────────┘
│ DSP + TinyML     │                │ aggregation      │
└──────────────────┘                └──────────────────┘
```

| Thành phần | Trách nhiệm chính | Không đảm nhiệm |
|---|---|---|
| **Patient Node** | Thu audio, Quality Gate, VAD, DSP, TinyML, HR/SpO₂ theo phiên, OLED và tạo `PatientEvent` | MQTT, LTE, GPS, cảm biến môi trường |
| **Gateway** | Nhận sự kiện, thu môi trường, ghép dữ liệu, lưu/chuyển tiếp và quản lý uplink | Chạy lại mô hình âm thanh thay Patient Node |
| **Dashboard** | Hiển thị phiên đo, lịch sử, trạng thái thiết bị và cảnh báo | Suy diễn chẩn đoán lâm sàng |

Kiến trúc tách trách nhiệm này giúp Patient Node vẫn đo và suy luận cục bộ khi
Gateway hoặc Internet tạm thời không khả dụng.

## Ba trường hợp sử dụng

Patient Node luôn là nơi thu dữ liệu bệnh nhân và chạy TinyML. Điểm khác nhau
giữa ba trường hợp là vị trí của Patient Node so với Gateway và đường truyền mà
Gateway dùng để đưa sự kiện lên hệ thống.

| Trường hợp | Patient Node ở đâu? | Gateway ở đâu? | Cơ chế hoạt động |
|---|---|---|---|
| **Theo dõi tại nhà** | Người dùng cầm, đặt trên bàn hoặc gần đầu giường, trong vùng ESP-NOW | Đặt cố định trong nhà, cấp nguồn liên tục | Patient Node xử lý tại edge → ESP-NOW → Gateway → Wi-Fi → MQTT |
| **Mang theo, không có Gateway** | Đi cùng người dùng, ngoài vùng ESP-NOW của nhà | Vẫn ở nhà hoặc không khả dụng | Patient Node tiếp tục đo, suy luận và hiển thị cục bộ; sự kiện chưa gửi được được đánh dấu chờ đồng bộ |
| **Mang theo và có kết nối** | Đi cùng người dùng | Cũng được mang theo và nằm trong vùng ESP-NOW của Patient Node | Patient Node → ESP-NOW → Gateway; Gateway dùng LTE làm uplink và có thể bật GPS khi cần vị trí |

### 1. Theo dõi tại nhà

```text
Patient Node trong nhà
  → xử lý audio và tạo PatientEvent
  → ESP-NOW
  → Gateway đặt cố định
  → Wi-Fi
  → MQTT / Dashboard
```

Gateway có thể đọc cảm biến môi trường định kỳ và ghép snapshot gần thời điểm
`PatientEvent`. Wi-Fi là uplink chính; LTE chỉ đóng vai trò dự phòng nếu được
bật trong cấu hình cuối. Patient Node không cần giữ kết nối Wi-Fi.

### 2. Mang theo, hoạt động độc lập

```text
Patient Node ngoài vùng Gateway
  → CHECK hoặc MONITOR
  → Quality Gate + TinyML
  → hiển thị kết quả trên OLED
  → lưu/đánh dấu PatientEvent chờ gửi
```

Trong trường hợp này không có dữ liệu môi trường từ Gateway tại thời điểm đo và
không có cập nhật realtime lên Dashboard. Khi Patient Node quay lại vùng
ESP-NOW, các sự kiện chờ có thể được gửi lại theo cơ chế sequence, ACK/retry và
chống trùng lặp.

### 3. Mang theo cả Patient Node và Gateway

```text
Patient Node mang theo
  → ESP-NOW cự ly gần
  → Gateway mang theo
  → LTE, tùy chọn GPS
  → MQTT / Dashboard
```

Gateway lúc này cung cấp uplink di động và có thể ghép dữ liệu môi trường tại
vị trí hiện tại. Chế độ này tiêu thụ năng lượng cao hơn do LTE/GPS, nên chỉ bật
các mô-đun cần thiết thay vì duy trì toàn bộ subsystem liên tục.

Trong cả ba trường hợp, raw audio vẫn ở Patient Node; Gateway chỉ nhận sự kiện
đã xử lý. Việc mất Gateway hoặc Internet không làm dừng chức năng TinyML cục
bộ, nhưng sẽ ảnh hưởng khả năng đồng bộ và hiển thị từ xa.

## Luồng hoạt động của Patient Node

Patient Node dùng ba nút riêng: `CHECK`, `MONITOR` và `SLEEP/STOP`.

### CHECK — kiểm tra chủ động

```text
CHECK
  → thu đúng 5 giây audio
  → kiểm tra chất lượng
  → DSP + DS-CNN INT8
  → hiển thị kết quả
  → tùy chọn đo HR/SpO₂ bằng MAX30102
  → hoàn tất PatientSession
```

HR/SpO₂ là phép đo theo phiên. Nếu người dùng bỏ qua bước đặt ngón tay,
`vitals_valid = false`; kết quả audio vẫn có thể hợp lệ.

### MONITOR — giám sát âm thanh tự động

```text
MONITOR
  → I2S chạy liên tục
  → bỏ 100 khối khởi động (~1,6 giây)
  → tạo bộ đệm vòng PSRAM 1 giây
  → VAD: 4 khối liên tiếp vượt ngưỡng
  → 1 giây pre-trigger + 4 giây post-trigger
  → kiểm tra chất lượng + DSP + TinyML
  → lặp ba chu kỳ capture/inference để bỏ phiếu
  → tạo PatientEvent
```

Bộ đệm pre-trigger giữ lại phần đầu của sự kiện trong lúc VAD đang chờ xác
nhận; nó không thay thế VAD và không phải noise baseline. Trong Monitor Mode,
MAX30102 mặc định không được giả định là đang có ngón tay trên cảm biến.

`SLEEP/STOP` có ưu tiên hủy luồng đang chạy, dừng ngoại vi cần thiết và đưa hệ
thống về trạng thái an toàn.

## Hợp đồng dữ liệu TinyML

| Thuộc tính | Giá trị hiện tại |
|---|---|
| Sample rate | 16 kHz, mono |
| Độ dài đoạn | 5 giây, 80.000 mẫu PCM16 |
| Tiền xử lý | Normalize → Butterworth 100–2.000 Hz → pre-emphasis 0,97 |
| Đặc trưng | Mel-Spectrogram `64 × 129`, Slaney, `top_db = 80` |
| Tensor đầu vào | INT8 `[1, 64, 129, 1]` |
| Model | DS-CNN full INT8 |
| Runtime | TensorFlow Lite Micro trên ESP32-S3 |
| Quy tắc lớp | `p(Non-Asthma) < 0,5` → lớp 0; ngược lại → lớp 1 |

Ở tầng ứng dụng, hai lớp nên được trình bày là `ASTHMA_LIKE` và
`NON_ASTHMA`. `NON_ASTHMA` không đồng nghĩa với “hoàn toàn bình thường”, vì
lớp này còn có thể chứa âm thanh hô hấp khác và âm thanh môi trường.

Pipeline C++ được kiểm chứng để **tương đương về thuật toán** với pipeline
Python. Dự án không tuyên bố bit-exact trên mọi nền tảng.

## Luồng dữ liệu dự kiến khi tích hợp hoàn chỉnh

```text
PatientSession
  → PatientEvent + sequence + CRC32
  → ESP-NOW + ACK/retry
  → EnvironmentSnapshot tại Gateway
  → CompleteRecord
  → Wi-Fi hoặc LTE
  → MQTT
  → Qt6/QML Dashboard
```

Raw PCM, Mel-Spectrogram và tensor nội bộ không thuộc payload vận hành bình
thường.

## Cấu trúc repository

```text
NCKH_2026_AIOT/
├── AI_Training_Model/        # dataset, train, quantize và đối chiếu Python/C++
├── Deploy_Model/             # các phase kiểm thử deployment trên ESP32-S3
│   ├── 1_Test_Model_Static_Profiling/
│   ├── 2_Test_Model_LiveMic/
│   └── 3_Model_Complete/
├── ESP32-Sensor_Suite/       # driver và prototype cảm biến tái sử dụng
├── ESP32-Qt-Telemetry/       # prototype telemetry MQTT ↔ Qt
├── ESP32_Pinout/             # tài liệu đấu nối phần cứng
├── Final_Project_NCKH/       # source tích hợp sản phẩm cuối
│   ├── AI_Model/
│   ├── Patient_Node/
│   ├── Gateway/
│   └── Dashboard_Qt6/
├── Docs_NCKH/                # đặc tả và phân công chính thức
└── Docs_Member/              # ghi chép làm việc theo thành viên
```

`AIOT_2026/` và các project telemetry/sensor cũ được giữ làm nguồn tham khảo;
đích tích hợp hiện tại là `Final_Project_NCKH/`.

## Tài liệu bắt đầu

- [Đặc tả sản phẩm đã chốt](./Docs_NCKH/NCKH_PRODUCT_DEFINITION_FINAL.md)
- [Phân công và kế hoạch công việc](./Docs_NCKH/NCKH_PHAN_CONG_CONG_VIEC.md)
- [Tổng quan Final Project](./Final_Project_NCKH/README.md)
- [Pipeline huấn luyện AI](./AI_Training_Model/README.md)
- [Các phase deployment](./Deploy_Model/README.md)
- [Phase 2: C++ + LiveMic](./Deploy_Model/2_Test_Model_LiveMic/README.md)
- [Bộ tài liệu kỹ thuật Phase 2](./Deploy_Model/2_Test_Model_LiveMic/doc/README.md)

## Nguyên tắc kỹ thuật

1. **Edge-first:** suy luận âm thanh chạy trên Patient Node.
2. **Quality before inference:** audio không đạt yêu cầu không bị ép phân lớp.
3. **Session/event based:** HR/SpO₂ không được mô tả như dữ liệu liên tục.
4. **Near-field:** INMP441 được đánh giá khi đặt gần nguồn âm hô hấp.
5. **No raw streaming:** chỉ truyền sự kiện đã xử lý trong vận hành bình thường.
6. **Evidence-based status:** chỉ gọi một phần là ổn định khi đã có phép kiểm thử tương ứng.
7. **No medical overclaim:** output là mẫu âm thanh gợi ý, không phải chẩn đoán.

## Phát triển

- AI: Python 3, TensorFlow/Keras, librosa, SciPy và NumPy.
- Firmware: PlatformIO, Arduino framework, ESP32/ESP32-S3 và TensorFlow Lite Micro.
- Dashboard: Qt 6, QML và MQTT.

Dự án được phát triển phục vụ nghiên cứu khoa học sinh viên tại Học viện Công
nghệ Bưu chính Viễn thông (PTIT), ARM Lab.
