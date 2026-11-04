# Đọc pin Gateway — GPIO34

## Cấu hình đã dùng

- Điện áp đo bằng đồng hồ: Vbat = 8,39 V; GPIO34 = 2,56 V.
- Hệ số thực đo: 8,39 / 2,56 = 3,27734375.
- Vbat = analogReadMilliVolts(GPIO34) / 1000 × 3,27734375.
- GPIO34 dùng ADC1, suy hao ADC_11db; không tắt hoặc đổi kênh Wi-Fi/ESP-NOW.
- Lấy 8 mẫu mỗi vòng TaskSensor (chu kỳ đặt 1 giây), bỏ mẫu nhỏ nhất/lớn nhất, lọc EMA 0,25. Không thêm delay hay task mới.
- Log Serial mỗi 10 giây, có log ngay lần đầu: `[Battery] GPIO34=...V Vbat=...V percent=... valid=...`.

## Phần trăm pin

Tạm giả định bộ pin Li-ion 2S. Mốc đầy 8,39 V và cạn 6,40 V được đặt trong `include/Config/gateway_config.h` qua GATEWAY_BATTERY_FULL_V / GATEWAY_BATTERY_EMPTY_V. Nội suy tuyến tính và giới hạn 0–100%. Hai điện áp người dùng cung cấp xác định hệ số chia áp, không đủ xác định dung lượng hoặc đường cong xả; phần trăm là ước lượng. Mốc 6,40 V chưa được người dùng xác nhận, không điều khiển ngắt nguồn/BMS.

## Tương thích

Chỉ cấp giá trị cho `gate.battery_gate` đã tồn tại. Không thêm khóa JSON, không sửa serializer, topic, lịch MQTT, Node, Dashboard, mã hóa, ACK/NACK hoặc cấu trúc ESP-NOW 56 byte. Trường pin trong EnvironmentSnapshot chỉ dùng nội bộ Gateway, sao chép qua khóa hiện có. Pin Node giữ nguyên.

Mẫu ADC ngoài 150–3000 mV hoặc không hữu hạn trả về 255 (JSON null); bộ lọc được reset để lần đo hợp lệ tiếp theo phục hồi ngay. Mẫu pin quá 5 giây cũng trả null. Điện áp hợp lệ thấp hơn mốc cạn hiển thị 0%. GPIO bị hở có thể trôi vào vùng hợp lệ; phần mềm không bảo đảm phát hiện dây bị hở. Chế độ không cảm biến/synthetic giữ pin là không khả dụng, không tạo giá trị giả.

## Sử dụng và đối chiếu thực tế

1. Giải nén và mở thư mục Gateway trong PlatformIO. Build/nạp môi trường esp32dev như dự án cũ.
2. Giữ nguyên mạch chia áp đang dùng vào GPIO34; không nối trực tiếp Vbat 8,39 V vào GPIO.
3. Mở Serial 115200. Khi đồng hồ đo GPIO34 = 2,56 V, kiểm tra log gần 2,560 V và Vbat gần 8,390 V. Hệ số thực đo không tự loại hết sai số ADC ESP32.
4. Nếu ADC lệch đồng hồ, ghi lại log và đồng hồ tại cùng thời điểm. Có thể hiệu chỉnh GATEWAY_BATTERY_ADC_REF bằng điện áp GPIO do firmware báo tại lúc đồng hồ đo Vbat đúng GATEWAY_BATTERY_VBAT_REF. Kiểm tra thêm điểm điện áp khác; hiệu chuẩn một điểm không sửa hết phi tuyến.
5. Dashboard tự hiện phần trăm qua battery_gate, không cần sửa Qt6. Không có trường Vbat mới; điện áp chỉ xem qua Serial.
6. Khi Node gửi event, kiểm tra giá trị nhịp tim/SpO2/phân loại, ACK và cập nhật Dashboard như trước. Thử Wi-Fi và LTE nếu sử dụng cả hai.

## Kiểm chứng

Bộ test native cũ và test pin kiểm tra hệ số 2,56 V → 8,39 V, mốc %, lọc, lỗi/phục hồi, mẫu cũ, và JSON giống từng byte sau khi bỏ khác biệt duy nhất battery_gate. Header giao thức Gateway/Node trùng nội dung sau chuẩn hóa xuống dòng.

Chạy lại: `python test/native/run_tests.py` và `python test/native/run_dashboard_tests.py` (cần g++ trên PATH). Chưa thử trực tiếp với Gateway/Node thật; cần đối chiếu log và đồng hồ khi nạp.

Tài liệu ADC Espressif: https://docs.espressif.com/projects/arduino-esp32/en/latest/api/adc.html

Build firmware chưa được xác nhận do trình biên dịch ESP32 trên máy báo lỗi Windows `Illegal System DLL Relocation`; chi tiết trong KET_QUA_KIEM_TRA.txt.
