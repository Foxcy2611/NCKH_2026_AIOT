# Bản chẩn đoán DHT22 timeout

Khoảng nghỉ đọc là ít nhất 3000 ms tính từ khi lần đọc trước hoàn thành.
Lần đầu cũng chờ ít nhất 3000 ms sau init. Task chạy mỗi 1000 ms nên khoảng
thực tế có thể dài hơn 3 giây. Không retry ngay khi lỗi.

Giữ latest DHT22/SpO2 và sửa TFT N/A. Chưa từng đọc thành công thì cache vẫn NA.
Giữ phương pháp đo xung hiện tại; chưa có phép đo chứng minh overhead timer là
nguyên nhân. Đây là bản tăng khoảng nghỉ và bổ sung chẩn đoán, không khẳng định
đã giải quyết lỗi phần cứng hoặc mọi lỗi timing.

Log từng lần đọc, không còn bỏ bớt theo bộ lọc 4 giây:
- attempts/ok/timeout/checksum: bộ đếm thực tế; không suy tỷ lệ từ ảnh chụp.
- cache=NA/available: đã có lần đo hợp lệ hay chưa.
- response_low_wait: không quan sát được pha LOW phản hồi trong thời hạn chờ.
- response_low_pulse: pha LOW không kết thúc trong thời hạn.
- response_high_wait/pulse: timeout ở pha HIGH phản hồi.
- data_low/data_high: timeout trong dữ liệu; bit=0…39 chỉ vị trí.

Các nhãn xác định nơi driver timeout, không tự chứng minh dây bị đứt, sai chân
hay ngắt tác động. GPIO hiện cấu hình 25. Gửi log mới với stage/bit/bộ đếm để
khoanh vùng. MQTT/topic/schema giữ nguyên.

Kiểm thử host chẩn đoán driver ở mức HIGH/LOW cố định và giải phóng critical
section, cache, TFT formatter và các kiểm thử trước đã chạy. Chưa đo xung hoặc
thử trên ESP32 thật. Build/nạp lại source bằng PlatformIO như trước.

Tham khảo giới hạn lấy mẫu DHT22 (không quá 0.5 Hz):
https://www.adafruit.com/product/393
