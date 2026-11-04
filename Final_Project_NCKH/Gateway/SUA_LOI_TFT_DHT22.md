# TFT DHT22

Code cũ ép float humidity sang int kể cả khi humidity=NAN. Phép chuyển đổi
này không có kết quả hợp lệ theo C++, có thể cho số rất lớn trên ESP32.
TFT cũng vẽ nhiệt độ NAN bằng String(temp,1) thay vì hiển thị N/A.
Các chuỗi dài tràn hai cột ENV chỉ rộng khoảng 33 pixel.

Đã giữ humidity kiểu float tới hàm vẽ, kiểm tra finite/phạm vi và bit DHT22
ở cả đường packet lẫn snapshot. Khởi động/chưa đọc được hiển thị N/A.
Chuỗi hợp lệ dùng font 1 để cả -40.0 và 100% nằm gọn trong cột.
Không thay đổi cache latest DHT22/SpO2 và MQTT.

Nếu N/A vẫn kéo dài, xem Serial Monitor 115200:
- [Sensor] mode=1: chế độ cảm biến thật (mặc định).
- [Sensor] DHT OK: lần đọc hợp lệ, cache sẽ có giá trị.
- DHT LOI 1: timeout; DHT LOI 2: checksum; DHT LOI Pham vi: số ngoài miền.
GPIO cấu hình DHT22 hiện là 25. Không thể kết luận lỗi đọc từ ảnh màn hình.
Gửi log khởi động và các dòng DHT nếu chưa có DHT OK.

Kiểm thử host formatter/các đường dữ liệu đã đạt; chưa nạp hoặc kiểm tra
hiển thị trên ESP32 thật. Cần build/nạp lại project, không dùng firmware cũ.
