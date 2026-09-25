# Đối chiếu yêu cầu và quyết định tích hợp

| Yêu cầu | Trạng thái bản này |
|---|---|
| Latest current_node/current_gate trong RAM | Đã triển khai, bài test mất Wi-Fi được người dùng xác nhận PASS |
| Không backlog/NVS Event Gateway | Đã bỏ storage và queue nghiệp vụ; raw RX queue và cache dedup vẫn cần |
| Dựng Complete_Packet khi publish, telemetry mới | Đã triển khai |
| Revision bảo vệ dirty khi có event mới | Đã triển khai |
| AES-GCM hai chiều, ACK/dedup | Đã triển khai; valid/duplicate đã quan sát trên board |
| Wire revised 16/16/56, bỏ timestamp Node/Response | CHƯA chuyển: Node và Gateway repo thực tế cùng 24/24/64 |
| Tên Gateway_Payload_t | Code vẫn dùng Gate_Payload_t, chưa đồng bộ tên revised |
| battery_gate và battery unavailable=255 | battery_gate chưa có; validator Node hiện không chấp nhận battery_node=255 |
| Temperature fusion/fallback DHT22 + BMP280 | Chưa có: temperature từ DHT22, BMP280 chỉ dùng pressure |
| HOME/MOBILE là policy độc lập uplink | Chưa có: mode hiện suy từ uplink/MQTT |
| Wi-Fi connected nhưng Internet/broker lỗi -> LTE | Chưa có: failover hiện theo mất liên kết Wi-Fi >15s |
| GPS HOME cache / MOBILE cập nhật | Chưa có policy riêng; GPS bật bằng build flag |
| Timestamp Gateway | uptime_ms có nhãn rõ; chưa đồng bộ UTC cho gate.timestamp |
| Backend ACK lưu dữ liệu | Chưa có, dirty sạch theo kết quả publish của adapter |
| TFT local | Chưa có module TFT trong Gateway này; API snapshot sẵn để tích hợp |
| LTE, GPS và sensor thực trên bản tích hợp | Chưa kiểm thử phần cứng trong phiên này |

## Mâu thuẫn trong tài liệu nhóm
Docs_NCKH/README.md và Encrypt_AES-128-GCM_REVISED.md khóa 16/16/56,
không timestamp ở Node/Response. NCKH_PHAN_CONG_CONG_VIEC.md vẫn mô tả
24/24/64 và một số luồng queue cũ; header thật của Patient_Node còn 24/24/64.
Không chuyển riêng Gateway sang 56 byte vì sẽ mất tương thích với Node hiện tại.
M1/M4 cần chốt và chuyển đồng thời Node, Gateway, Node test và tài liệu protocol.
Đây là điểm còn phải làm để tuyên bố đáp ứng đầy đủ revised, không phải đã được miễn.

## Giới hạn mạng
Mất WAN khi AP còn chạy: bản Wi-Fi-only có thể giữ latest và thử MQTT lại;
không tự chuyển LTE dựa trên lỗi MQTT. LTE driver có sẵn không đồng nghĩa policy đã đủ.
Mất router: đã pass một lần trên board, chưa chứng minh tỷ lệ nhận khi quét/reconnect dài hạn.
Mất nguồn: latest và dedup mất theo RAM, đúng phạm vi bỏ lưu bền Event Gateway.
