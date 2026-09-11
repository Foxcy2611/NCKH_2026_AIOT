# Docs_NCKH

Nơi chứa các tài liệu chính thức của đề tài: định nghĩa sản phẩm/kiến trúc đã chốt và kế hoạch triển khai.

## Nội dung

```text
Docs_NCKH/
├── README.md
├── NCKH_PRODUCT_DEFINITION_FINAL.md
├── NCKH_PHAN_CONG_CONG_VIEC.md
├── Encrypt_AES-128-GCM.md
└── Luong_phan_hoi.txt
```

- **`NCKH_PRODUCT_DEFINITION_FINAL.md`** — Product Definition + System Architecture đã gộp: sản phẩm là gì, kiến trúc 2 node ra sao, AI model, audio pipeline, state machine, data model, ESP-NOW, Gateway, network, UI, power, các tham số chưa khóa, roadmap kỹ thuật.
- **`NCKH_PHAN_CONG_CONG_VIEC.md`** — Kế hoạch triển khai: ai làm gì trong 5 thành viên, thứ tự làm, output bắt buộc từng bước.
- **`Encrypt_AES-128-GCM.md`** — Đặc tả bảo mật liên kết ESP-NOW: packet chung 64 byte, payload hai chiều, AAD, nonce, tag, ACK/NACK và retry.
- **`Luong_phan_hoi.txt`** — Sơ đồ ngắn luồng Event bảo mật, phản hồi và retry để đối chiếu nhanh khi code hai phía.

## Cách dùng

Đây là tài liệu **đã chốt/tham chiếu**, không phải nơi ghi tư duy đang làm — phần đó nằm ở `Docs_Member/`. Khi triển khai phát sinh thay đổi, phải cập nhật đồng thời Product Definition và đặc tả AES-GCM để không lệch luồng giữa Node và Gateway.
