# Các project thử nghiệm ESP32 độc lập

Thư mục này chứa các project nhỏ dùng để kiểm tra riêng phần cứng, đường thu âm và đường truyền trước khi đưa vào `Final_Project_NCKH/`. Mỗi project có cấu hình và mục tiêu riêng; mở đúng thư mục con khi chạy PlatformIO hoặc Qt.

## Chọn project theo việc cần làm

| Cần kiểm tra | Project | Việc thực hiện / kết quả cần xem |
|---|---|---|
| Thu âm qua INMP441 để tạo dataset | [ESP32_Read_INMP441](ESP32_Read_INMP441/README.md) | Đọc PCM16 16 kHz qua Serial; `Record_Audio.py` thu environment, `Record_Playback.py` phát WAV qua loa và thu lại, `Test_Audio.py` đo chất lượng WAV. |
| Vẽ waveform, Log-Mel và đáp ứng Butterworth | [Audio_Visualizations](Audio_Visualizations/README.md) | Tạo hình minh họa offline từ WAV core và đúng pipeline Phase 2; xuất PNG/SVG phục vụ báo cáo. |
| Vẽ kết quả Accuracy, Recall và confusion matrix | [AI_Result_Visualizations](AI_Result_Visualizations/README.md) | Đọc CSV/artifact đã có để tạo hình so sánh FP32-QAT và V2.1-V3.1; không train hoặc lượng tử hóa lại model. |
| Kiểm tra playback làm lệch kết quả AI | [Asthma_Playback_Calibration](Asthma_Playback_Calibration/README.md) | Thu đúng cửa sổ 5 giây qua INMP441, dump PCM, so `p_non_asthma` giữa Python và ESP32, đo offset và phân tích ảnh hưởng loa/phòng/mic. |
| Kiểm tra packet bảo mật Node → Gateway | [Patient_Node_Test](Patient_Node_Test/README.md) | Gửi event thủ công qua ESP-NOW/AES-GCM; thử packet mới, duplicate, replay và ciphertext sai tag bằng lệnh Serial. |
| Thử driver cảm biến và FreeRTOS | [AIOT_2026](AIOT_2026/README.md) | Đọc các cảm biến trên ESP32, kiểm tra bus I2C, tác vụ và dữ liệu trước khi tích hợp Gateway/Node. |
| Thử ESP32 → MQTT → Qt | [ESP32-Qt-Telemetry](ESP32-Qt-Telemetry/README.md) | Gửi dữ liệu nhiệt độ/độ ẩm qua MQTT và quan sát trong ứng dụng Qt. |
| Thử schema JSON cho Dashboard | [Test_JSON_to_Qt-6](Test_JSON_to_Qt-6/README.md) | Phát bản ghi giả lập Gateway-only/Asthma/Non-Asthma/Unsure để kiểm tra MQTT và cách Dashboard đọc JSON. |
| Lấy MAC phục vụ cấu hình ESP-NOW | [ESP_Get_MAC](ESP_Get_MAC/) | Hai project PlatformIO `WROM_Get_MAC` và `S3_Get_IP_MAC` in địa chỉ MAC qua Serial. |
| Thử bố cục ứng dụng Qt | [Test_Qt_Location](Test_Qt_Location/) | Project Qt/QML nhỏ để kiểm tra giao diện hoặc vị trí hiển thị. |

## Gắn với quy trình chính

```text
ESP32_Read_INMP441
  → tạo WAV trong Dataset_TuThu_v_Kaggle
  → Phase1 chia dữ liệu và Phase2 huấn luyện

Asthma_Playback_Calibration
  → đối chiếu Python / ESP32 và phân tích domain shift

AIOT_2026 + Patient_Node_Test + các project MQTT/Qt
  → kiểm tra từng module và hợp đồng truyền dữ liệu
  → Final_Project_NCKH/Patient_Node + Gateway + Dashboard_Qt6
```

Các project tại đây là môi trường thử nghiệm. Source tích hợp hiện hành nằm trong [Final_Project_NCKH](../Final_Project_NCKH/README.md); quy trình của toàn repository nằm tại [README gốc](../README.md). Một số project thử nghiệm lưu cấu hình, model, topic hoặc ngưỡng theo giai đoạn cũ; khi kiểm tra hệ thống cuối, đối chiếu lại với source và manifest của bản tích hợp.

## Cách bắt đầu

1. Chọn đúng project theo bảng trên và đọc README của nó nếu có.
2. Với firmware ESP32, mở thư mục chứa `platformio.ini` bằng PlatformIO; kiểm tra board, chân kết nối, cổng nạp và baud trước khi upload.
3. Với script Python, xem biến cấu hình đầu file và đường dẫn input/output trong README của project.
4. Với ứng dụng Qt, mở project chứa `CMakeLists.txt` bằng Qt Creator.

Không chạy hai chương trình cùng chiếm một cổng COM: đóng Serial Monitor trước khi script Python thu PCM từ ESP32.
