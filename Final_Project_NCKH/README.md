# Final Project — thư mục tích hợp sản phẩm cuối

`Final_Project_NCKH/` là nơi tập trung **source tích hợp cuối cùng** của đề tài.
Các thư mục bên ngoài như `AI_Training_Model/`, `Deploy_Model/`,
`ESP32-Sensor_Suite/` và `ESP32-Qt-Telemetry/` phục vụ nghiên cứu, kiểm thử hoặc
làm prototype; những thành phần đã được lựa chọn mới được đưa vào đây để tạo
hệ thống hoàn chỉnh.

README này chỉ giới thiệu phạm vi và cách tổ chức thư mục. Kiến trúc, trường hợp
sử dụng và thông số kỹ thuật được duy trì ở tài liệu cấp repository để tránh
lặp lại nhiều nguồn dễ lệch nhau.

## Cấu trúc

```text
Final_Project_NCKH/
├── AI_Model/          # model artifact dùng cho bản tích hợp
├── Patient_Node/      # firmware ESP32-S3 phía người dùng
├── Gateway/           # firmware ESP32 gateway
├── Dashboard_Qt6/     # ứng dụng desktop Qt6/QML
└── README.md          # trang định hướng thư mục này
```

| Thư mục | Vai trò trong sản phẩm cuối |
|---|---|
| `AI_Model/` | Lưu model và artifact cần thiết để nhúng vào Patient Node |
| `Patient_Node/` | Thu dữ liệu bệnh nhân, xử lý DSP/TinyML, tạo `Patient_Event_Payload_t` và mã hóa thành packet AES-128-GCM |
| `Gateway/` | Xác thực/giải mã sự kiện, phản hồi bảo mật, thu context môi trường và quản lý kết nối mạng |
| `Dashboard_Qt6/` | Nhận dữ liệu qua MQTT và cung cấp giao diện theo dõi |

## Ranh giới với các thư mục thử nghiệm

```text
AI_Training_Model ─┐
Deploy_Model ──────┤
Sensor prototypes ─┼─► thành phần đã kiểm chứng ─► Final_Project_NCKH
Qt prototypes ─────┘
```

- Không dùng thư mục này để lưu dataset gốc, notebook thử nghiệm hoặc log tinh
  chỉnh pipeline.
- Không sao chép toàn bộ prototype vào đây; chỉ giữ code và tài nguyên thực sự
  thuộc phiên bản tích hợp.
- Thay đổi hợp đồng dùng chung như packet, MQTT topic hoặc pinout cần được cập
  nhật đồng bộ giữa các project liên quan.

## Quan hệ giữa các thành phần

```text
Patient_Node ── AES-GCM Patient Event / ESP-NOW ─► Gateway
Patient_Node ◄─ AES-GCM ACK/NACK / ESP-NOW ────── Gateway
Gateway      ── MQTT qua Wi-Fi/LTE ──────────────► Dashboard_Qt6
```

Patient Node chịu trách nhiệm xử lý tại edge. Gateway chịu trách nhiệm kết nối,
ghép context và chuyển dữ liệu. Dashboard chịu trách nhiệm hiển thị; không chạy
lại pipeline TinyML thay cho Patient Node.

## Tài liệu liên quan

- [README tổng thể](../README.md): mục tiêu, kiến trúc, ba trường hợp sử dụng và
  bản đồ repository.
- [Định nghĩa sản phẩm](../Docs_NCKH/NCKH_PRODUCT_DEFINITION_FINAL.md): phạm vi
  sản phẩm và các quyết định đã chốt.
- [Phân công công việc](../Docs_NCKH/NCKH_PHAN_CONG_CONG_VIEC.md): trách nhiệm
  và đầu ra của từng phần.
- [Đặc tả AES-128-GCM](../Docs_NCKH/Encrypt_AES-128-GCM.md): format packet,
  mã hóa Event, phản hồi ACK/NACK và retry.
- [Pipeline huấn luyện](../AI_Training_Model/README.md): dữ liệu, model và đánh
  giá phía Python.
- [Kiểm thử deployment](../Deploy_Model/README.md): quá trình xác minh C++,
  TensorFlow Lite Micro và micro thật.

Khi cần tìm code chạy cuối, bắt đầu tại project con tương ứng trong thư mục
này. Khi cần tìm lý do thiết kế hoặc kết quả thử nghiệm, đi theo các tài liệu
liên kết ở trên.
