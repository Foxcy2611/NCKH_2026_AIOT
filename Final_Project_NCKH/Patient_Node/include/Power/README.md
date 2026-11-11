# Đọc mức pin của Patient Node

Module này đo điện áp pin qua ADC của ESP32-S3, quy đổi sang phần trăm và ghi kết quả vào `Node_Payload_t::battery_node` trước khi packet được mã hóa và gửi sang Gateway.

## 1. Các file liên quan

| File | Chức năng |
|---|---|
| `include/Power/Node_Battery.h` | Kiểu dữ liệu và API đọc pin |
| `src/Node_Battery.cpp` | Lấy mẫu ADC, lọc và quy đổi phần trăm |
| `common/inc/Node_Battery_Config.h` | Tham số điện áp, ADC và bật/tắt module |
| `shared/Board_Pinout.h` | Khai báo GPIO dùng chung của bo mạch |

## 2. Cấu hình phần cứng hiện tại

- Bo mạch: ESP32-S3 DevKitC-1.
- Chân đọc pin: `GPIO12`, tương ứng `ADC2_CH1`.
- Điện áp tham chiếu phía pin: `8,39 V`.
- Điện áp đo tại ADC ứng với mức trên: `2,56 V`.
- Mức đầy: `8,39 V`.
- Mức cạn tạm thời: `6,40 V`.
- Suy hao ADC: `ADC_11db`.
- Khoảng ADC được chấp nhận: `150-3000 mV`.

`GPIO12` hiện không xung đột với I2C (`GPIO8/9`), MAX30102 INT (`GPIO10`), I2S (`GPIO14/15/16`) hoặc ba nút (`GPIO4/5/6`).

> Không nối trực tiếp pin 2S vào GPIO12. Điện áp pin phải đi qua đúng cầu chia áp của mạch Node. Cần so sánh `adcMv` và `voltage` của firmware với đồng hồ đo trước khi chốt hệ số hiệu chuẩn.

## 3. Luồng hoạt động

1. `setup()` gọi `NodeBattery_Begin()` để cấu hình GPIO12 và attenuation.
2. Khi state machine dựng event payload, `NodeBattery_Read()` lấy 8 mẫu ADC.
3. Module bỏ mẫu nhỏ nhất và lớn nhất, sau đó lấy trung bình 6 mẫu còn lại.
4. Giá trị ADC được đổi sang điện áp pin bằng tỷ lệ `8,39 / 2,56`.
5. Điện áp được lọc EMA với hệ số `0,25` rồi nội suy tuyến tính về `0-100%`.
6. `battery_node` được ghi một lần vào plaintext trước khi mã hóa. Khi ESP-NOW retry, Node gửi lại packet đã tạo và không đọc pin lần nữa.
7. Sau Light Sleep, `NodeBattery_ResetFilter()` xóa lịch sử EMA để phiên tiếp theo dùng dữ liệu mới.

Nếu module không sẵn sàng hoặc mẫu ADC không hợp lệ, `battery_node = 255`. Gateway và Dashboard hiểu `255` là không có dữ liệu và hiển thị `N/A`.

## 4. Lưu ý nghiệm thu

Phần trăm pin hiện là ước lượng tuyến tính theo điện áp, không phải phép đo dung lượng thực. Trước khi chốt cần kiểm tra ít nhất ba mức pin:

| Mức thử | Cần đối chiếu |
|---|---|
| Gần đầy | Điện áp đồng hồ, `adcMv`, điện áp quy đổi và phần trăm |
| Trung bình | Độ ổn định giữa nhiều packet |
| Gần cạn | Mốc `6,40 V` có phù hợp với phần cứng hay không |

Ngoài ra cần thử tháo đường đo hoặc tạo giá trị ADC ngoài khoảng để xác nhận Node gửi `255` và Dashboard hiển thị `N/A`.
