# Thiết kế phần cứng

Thư mục này lưu ảnh thiết kế PCB, ảnh nguyên mẫu phần cứng và ảnh giao diện của hệ
thống hoàn chỉnh. Các tệp được dùng làm minh chứng trong báo cáo, slide thuyết trình
và hồ sơ nghiệm thu; chúng không thay thế schematic, Gerber hoặc mã nguồn firmware.

## 1. Danh mục hình ảnh

| Tệp | Nội dung |
|---|---|
| [Gateway_PCB.png](./Gateway_PCB.png) | Bố trí PCB của IoT Gateway. |
| [Patient Node PCB.png](<./Patient Node PCB.png>) | Bố trí PCB của Patient Node. |
| [Patient Node.png](<./Patient Node.png>) | Nguyên mẫu Patient Node hoàn chỉnh. |
| [Gateway.jpg](./Gateway.jpg) | Nguyên mẫu IoT Gateway hoàn chỉnh. |
| [Overview_Dashboard.png](./Overview_Dashboard.png) | Giao diện tổng quan của Dashboard Qt/QML. |
| [GPS_Map_Dashboard.png](./GPS_Map_Dashboard.png) | Giao diện bản đồ và thông tin vị trí trên Dashboard. |

## 2. Cấu hình Patient Node hiện hành

| Thành phần | Cấu hình đã chốt |
|---|---|
| Vi điều khiển | ESP32-S3-N16R8V, Flash 16 MB, PSRAM 8 MB |
| Micro INMP441 | I2S: SCK `GPIO14`, WS `GPIO15`, SD `GPIO16` |
| OLED SSD1306 | I2C: SDA `GPIO8`, SCL `GPIO9`, địa chỉ `0x3C` |
| MAX30102 | I2C dùng chung `GPIO8/9`, INT `GPIO10` |
| Nút CHECK / MONITOR / SLEEP | `GPIO4` / `GPIO5` / `GPIO6` |
| Đọc điện áp pin | `GPIO12`, `ADC2_CH1`, bắt buộc qua cầu chia áp |
| Tensor Arena bản cuối | 192 KiB trong PSRAM; mức profiling thực tế 169.380 byte |

> Không nối trực tiếp pin 2S vào GPIO12. Điện áp phải đi qua cầu chia áp và cần được
> hiệu chuẩn với đồng hồ đo trên đúng PCB trước khi chốt hệ số điện áp/phần trăm pin.

## 3. Nguồn cấu hình chuẩn

Để tránh một chân hoặc thông số được mô tả khác nhau ở nhiều nơi, khi có thay đổi hãy
ưu tiên đối chiếu theo thứ tự sau:

1. [Board_Pinout.h](../Final_Project_NCKH/Patient_Node/shared/Board_Pinout.h) - chân
   phần cứng của Patient Node.
2. [Node_Battery_Config.h](../Final_Project_NCKH/Patient_Node/common/inc/Node_Battery_Config.h)
   - cấu hình phép đo pin và cầu chia áp.
3. [Patient Node README](../Final_Project_NCKH/Patient_Node/README.md) - luồng firmware,
   bộ nhớ và trạng thái tích hợp.
4. [Danh sách mô-đun](../ESP32_Pinout/Danh_sach_Module.md) - danh sách phần cứng và
   chân giao tiếp của Patient Node/Gateway.
5. [Gateway source](../Final_Project_NCKH/Gateway/) - cấu hình chân và ngoại vi thực
   tế của Gateway.

Ngưỡng Quality Gate không được suy ra từ ảnh phần cứng. Nguồn đã chốt nằm tại
[Final V1 Quality Check](../Experiments_Benchmarking/Patient_Node/Final_V1_Validation/02_Quality_Check/)
và được hiện thực trong
[Quality_Check.cpp](../Final_Project_NCKH/Patient_Node/src/Quality_Check.cpp).

## 4. Quy tắc đóng băng phần cứng

Một bản phần cứng chỉ được coi là **frozen** khi đồng thời thỏa mãn:

- PCB/đấu nối thực tế trùng với `Board_Pinout.h` và cấu hình Gateway;
- phép đọc pin tại GPIO12 đã được hiệu chuẩn trên mạch thật;
- Patient Node, Gateway và Dashboard hoàn thành kiểm thử end-to-end;
- ảnh, source, model và tài liệu cùng chỉ tới một phiên bản phát hành/tag Git;
- các giới hạn còn lại của nguyên mẫu nghiên cứu được ghi rõ trong biên bản nghiệm thu.

Các ảnh trong thư mục này là snapshot minh chứng. Khi thay PCB hoặc chân kết nối,
phải cập nhật cả ảnh, source cấu hình và tài liệu liên quan trong cùng một thay đổi.
