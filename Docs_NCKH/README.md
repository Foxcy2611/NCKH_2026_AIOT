# Docs_NCKH

Nơi chứa các tài liệu chính thức của đề tài: định nghĩa sản phẩm/kiến trúc đã chốt và kế hoạch triển khai.

## Nội dung

```text
Docs_NCKH/
├── README.md
├── NCKH_PRODUCT_DEFINITION_FINAL_REVISED.md
├── NCKH_PHAN_CONG_CONG_VIEC.md
├── Encrypt_AES-128-GCM_REVISED.md
├── GATE_PAYLOAD_COMPLETE_PACKET_DESIGN_REVISED.md
├── Data_On_Dashboard_REVISED.md
├── TONG_HOP_CAU_TRUC_GOI_TIN.md
└── Luong_phan_hoi_REVISED.txt
```

- **`NCKH_PRODUCT_DEFINITION_FINAL_REVISED.md`** — Product Definition + System Architecture đã gộp: sản phẩm là gì, kiến trúc 2 node ra sao, AI model, audio pipeline, state machine, data model, ESP-NOW, Gateway, network, UI, power, các tham số chưa khóa, roadmap kỹ thuật.
- **`NCKH_PHAN_CONG_CONG_VIEC.md`** — Kế hoạch triển khai: ai làm gì trong 5 thành viên, thứ tự làm, output bắt buộc từng bước.
- **`Encrypt_AES-128-GCM_REVISED.md`** — Đặc tả bảo mật liên kết ESP-NOW: payload hai chiều 16 byte, `Secure_Packet_t` 56 byte, AAD, nonce, tag, ACK/NACK và retry.
- **`GATE_PAYLOAD_COMPLETE_PACKET_DESIGN_REVISED.md`** — Thiết kế `Gateway_Payload_t`, trạng thái mới nhất tại Gateway và `Complete_Packet_t`.
- **`Data_On_Dashboard_REVISED.md`** — Quy tắc sử dụng `Complete_Packet_t` tại backend và Dashboard Qt6.
- **`TONG_HOP_CAU_TRUC_GOI_TIN.md`** — Bảng tổng hợp các struct, thành phần từng trường, kích thước và quan hệ dữ liệu từ Node đến Gateway, MQTT và Qt6.
- **`Luong_phan_hoi_REVISED.txt`** — Sơ đồ ngắn luồng Event bảo mật, phản hồi và retry để đối chiếu nhanh khi code hai phía.

## Cách dùng

Đây là tài liệu **đã chốt/tham chiếu**, không phải nơi ghi tư duy đang làm — phần đó nằm ở `Docs_Member/`. Khi triển khai phát sinh thay đổi, phải cập nhật đồng thời Product Definition và đặc tả AES-GCM để không lệch luồng giữa Node và Gateway.
