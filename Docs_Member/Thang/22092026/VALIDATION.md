# Kết quả kiểm tra

## Board — do người dùng thực hiện trước đóng gói
- Gateway(5) build/nạp thành công; environment gateway_synthetic.
- Node giả gửi 2049/2050/2051: ACK_ACCEPTED; bản gửi lại 2051: ACK_DUPLICATE.
- HiveMQ nhận patient/event và telemetry.
- Tắt router: Gateway nhận A/B/C = 2052/2053/2054, dirty=1 revision=6 latest=2054.
- Kết nối lại: transport_send_ok seq=2054 revision=6, dirty=0.
- Người dùng xác nhận PASS bài test chỉ gửi latest sau phục hồi.
- Ảnh không hiển thị ACK cuối của Node cho C; không ghi nhận riêng test ACK đó là pass.

## Host — chạy lại khi tích hợp
python Final_Project_NCKH/Gateway/test/native/run_tests.py
PASS: record missing/fresh/stale/boundary/future/partial/nonfinite/gas/64-bit-time/protocol.
PASS: JSON mode 0 và 2, telemetry/event/status/alert, null, metadata, buffer limits.
PASS: Wi-Fi mock timeout/backoff/channel mismatch/millis rollover.
Header Gateway và Node trong repo được đối chiếu byte: giống nhau.
Hai directional AES keys khớp; giá trị khóa không ghi trong log báo cáo.

Không có PlatformIO ở môi trường đóng gói nên không build/link ESP32 mới tại đây.
Source/header/platformio.ini/config từ Gateway(5) không thay đổi; vẫn cần build trên máy
người dùng ở vị trí repo mới để đáp ứng CONTRIBUTING.md trước push.
Host tests không thay thế test radio, TLS, LTE, GPS hay sensor thật.

## Chưa có kết quả xác nhận
LTE/failover, Wi-Fi còn liên kết nhưng mất Internet -> LTE, sensor/GPS thực,
TFT, test o bỏ ACK đầu, test t sửa tag, reset khi dirty, long-run/communication metrics,
Patient Node thật của nhóm. Không đánh dấu những mục này PASS.

## Kiểm tra cài vào repo ZIP
- Script apply chạy thành công trên bản sao repo đầu vào.
- Host tests và kiểm tra header chạy lại trong vị trí repo mới: PASS.
- Tất cả file ngoài Gateway giữ nguyên byte; chỉ thêm tài liệu M4.
- Tất cả source/header/platformio.ini của Gateway(5) giữ nguyên byte.
- Script từ chối target khác baseline: PASS.
