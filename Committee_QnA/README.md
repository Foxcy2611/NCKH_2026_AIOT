# Committee Q&A — Ngân hàng câu hỏi vấn đáp NCKH

**Dự án:** Nghiên cứu, thiết kế và chế tạo hệ thống IoT ứng dụng TinyML hỗ trợ theo dõi và cảnh báo sớm cho bệnh nhân hen suyễn  
**Phạm vi ôn tập:** AI Model → Patient Node → IoT Gateway → Dashboard → Tích hợp toàn hệ thống.

> **Quy ước:** Có **58 câu hỏi**. Các câu đánh dấu ⭐ là câu nên ưu tiên ôn kỹ. Mỗi liên kết `[Qxx]` là **đường dẫn dự kiến (placeholder)** tới file trả lời tương ứng trong thư mục `Answers/`; các file này chưa cần tồn tại. Nếu chọn trả lời bằng Jupyter Notebook, đổi đuôi `.md` thành `.ipynb` khi tạo file.

## I. AI Model — Huấn luyện, DSP và triển khai TinyML (Q01–Q16)

### 1. Dataset và tiền xử lý

1. **[Q01](./Answers/Q01.md)** ⭐ — Dataset V2 của nhóm được tổ chức như thế nào? Cụ thể cách chia dữ liệu Core theo Patient ID, Playback theo WAV nguồn và Environment theo Session ID?
2. **[Q02](./Answers/Q02.md)** — Nhóm sử dụng những phương pháp Data Augmentation nào? Vì sao chỉ áp dụng cho tập Training?
3. **[Q03](./Answers/Q03.md)** ⭐ — Pipeline xử lý âm thanh từ WAV/PCM16 đến tensor Log-Mel Spectrogram `40 × 129 × 1` gồm những bước nào?
4. **[Q04](./Answers/Q04.md)** — Vì sao chọn tần số lấy mẫu 16 kHz, cửa sổ 5 giây, bộ lọc Butterworth bậc 5 trong dải 100–2000 Hz?
5. **[Q05](./Answers/Q05.md)** — Các thông số FFT Size = 2048, Hop Length = 625, 40 Mel bins có tác dụng gì? Nếu thay đổi sẽ ảnh hưởng thế nào đến dữ liệu đầu vào?
6. **[Q06](./Answers/Q06.md)** ⭐ — Vì sao chọn Log-Mel Spectrogram thay vì MFCC, Mel Spectrogram hoặc đưa trực tiếp tín hiệu PCM vào mạng?
7. **[Q07](./Answers/Q07.md)** — Frontend C4 có những đặc điểm gì? Vì sao nhóm lựa chọn C4 thay vì các cấu hình Frontend khác?

### 2. Kiến trúc và huấn luyện mô hình

8. **[Q08](./Answers/Q08.md)** ⭐ — Kiến trúc DS-CNN V1 cụ thể gồm những layer nào? Tensor thay đổi kích thước ra sao qua từng khối?
9. **[Q09](./Answers/Q09.md)** — Vì sao sử dụng SeparableConv2D thay vì Conv2D thông thường? Sự khác biệt về số tham số và chi phí tính toán?
10. **[Q10](./Answers/Q10.md)** — Vì sao nhóm sử dụng Flatten + Dense thay vì Global Average Pooling (GAP)?
11. **[Q11](./Answers/Q11.md)** — Những hyperparameter chính khi huấn luyện là gì: Optimizer, Learning Rate, Batch Size, Epoch, Loss và các Callback?
12. **[Q12](./Answers/Q12.md)** ⭐ — Nhóm dựa vào những chỉ số nào để lựa chọn mô hình tốt nhất? Vì sao chú trọng Asthma Recall thay vì chỉ Accuracy?

### 3. Lượng tử hóa và kết quả

13. **[Q13](./Answers/Q13.md)** ⭐ — Quy trình QAT INT8 của nhóm thực hiện như thế nào? Vì sao chọn QAT thay vì PTQ?
14. **[Q14](./Answers/Q14.md)** — Vì sao sau QAT INT8, Accuracy tăng từ 90,57% lên 95,60%? Có phải lượng tử hóa luôn làm mô hình tốt hơn không?
15. **[Q15](./Answers/Q15.md)** ⭐ — Mô hình sau lượng tử hóa có 331.386 tham số, kích thước khoảng 339,8 KB và tensor đầu vào INT8. Các thông số này ảnh hưởng gì đến việc triển khai trên ESP32-S3?
16. **[Q16](./Answers/Q16.md)** — Nhóm kiểm thử và đối chiếu kết quả suy luận giữa Python/TFLite và ESP32-S3 như thế nào để bảo đảm tính nhất quán?

## II. Patient Node — ESP32-S3, cảm biến và suy luận (Q17–Q31)

### 1. Phần cứng và giao tiếp

17. **[Q17](./Answers/Q17.md)** ⭐ — Vì sao sử dụng ESP32-S3-N16R8 thay vì ESP32 thông thường hoặc STM32? Nhóm tận dụng những tài nguyên phần cứng nào?
18. **[Q18](./Answers/Q18.md)** — Microphone INMP441 giao tiếp I2S với ESP32-S3 như thế nào? Tần số lấy mẫu, độ rộng dữ liệu và định dạng PCM được cấu hình ra sao?
19. **[Q19](./Answers/Q19.md)** — MAX30102 giao tiếp I2C và đo HR/SpO₂ như thế nào? Các điều kiện nào được dùng để xác định dữ liệu sinh hiệu hợp lệ?
20. **[Q20](./Answers/Q20.md)** — Các nút nhấn và OLED được điều khiển như thế nào? Làm sao tránh tình trạng thao tác nút gây xung đột khi thiết bị đang thu âm hoặc suy luận?

### 2. Firmware và pipeline TinyML

21. **[Q21](./Answers/Q21.md)** ⭐ — Hãy mô tả toàn bộ luồng xử lý của một phiên CHECK, từ nhấn nút đến hiển thị kết quả và truyền về Gateway.
22. **[Q22](./Answers/Q22.md)** — Chế độ MONITOR thực hiện ba vòng kiểm tra như thế nào? Kết quả cuối cùng được tổng hợp theo cơ chế gì?
23. **[Q23](./Answers/Q23.md)** ⭐ — Quality Check và VAD kiểm tra những thông số gì? Nếu âm thanh quá nhỏ, quá ồn hoặc không đạt điều kiện thì firmware xử lý ra sao?
24. **[Q24](./Answers/Q24.md)** — DSP trên ESP32-S3 được triển khai như thế nào để tạo được Log-Mel giống pipeline huấn luyện trên Python?
25. **[Q25](./Answers/Q25.md)** ⭐ — TensorFlow Lite Micro được khởi tạo và thực hiện suy luận như thế nào? Tensor Arena 192 KB được cấp phát và sử dụng ra sao?
26. **[Q26](./Answers/Q26.md)** — Firmware xử lý đầu ra INT8 của mô hình như thế nào? Cách Dequantize, áp dụng ngưỡng phân loại và hiển thị điểm dự đoán?
27. **[Q27](./Answers/Q27.md)** — Vì sao thời gian DSP khoảng 1984 ms, trong khi thời gian suy luận khoảng 1166 ms? Thành phần nào chiếm nhiều tài nguyên xử lý hơn?
28. **[Q28](./Answers/Q28.md)** ⭐ — FSM của Patient Node có những trạng thái chính nào? Chế độ Light Sleep được kích hoạt sau 15 giây bằng cơ chế gì và đánh thức ra sao?

### 3. Truyền thông Node → Gateway

29. **[Q29](./Answers/Q29.md)** ⭐ — Bản tin ESP-NOW mà Patient Node gửi có cấu trúc như thế nào? Những trường dữ liệu nào được truyền và kích thước gói tin là bao nhiêu?
30. **[Q30](./Answers/Q30.md)** — AES-128-GCM được thực hiện trên Node như thế nào? Nonce/IV, khóa bí mật và Authentication Tag được sử dụng ra sao?
31. **[Q31](./Answers/Q31.md)** ⭐ — Sau khi gửi bản tin, Node chờ ACK như thế nào? Timeout, Retry và xử lý trường hợp Gateway không phản hồi?

## III. IoT Gateway — FreeRTOS, truyền thông, cảm biến và LTE (Q32–Q48)

### 1. Firmware và FreeRTOS

32. **[Q32](./Answers/Q32.md)** ⭐ — Vì sao Gateway sử dụng FreeRTOS thay vì vòng lặp `loop()` thông thường? Firmware được chia thành những Task nào?
33. **[Q33](./Answers/Q33.md)** — Các TaskEspNow, TaskSensor, TaskConnManager, TaskSms, TaskMqttPublisher và TaskDisplayTFT được tổ chức và trao đổi dữ liệu như thế nào?
34. **[Q34](./Answers/Q34.md)** ⭐ — Queue, Mutex và Critical Section được sử dụng ở đâu trong Gateway? Chúng giải quyết những tình huống xung đột tài nguyên nào?
35. **[Q35](./Answers/Q35.md)** — Khi có nhiều sự kiện đồng thời, ví dụ nhận ESP-NOW, đọc GPS, cập nhật TFT và gửi MQTT, Gateway xử lý lịch thực thi như thế nào?

### 2. ESP-NOW và bảo mật

36. **[Q36](./Answers/Q36.md)** ⭐ — Gateway nhận gói ESP-NOW 56 byte như thế nào? Quy trình từ callback → Queue → xác thực → giải mã → xử lý sự kiện?
37. **[Q37](./Answers/Q37.md)** — ESP-NOW hoạt động trên kênh Wi-Fi 6 như thế nào? Vì sao phải đồng bộ kênh giữa Node và Gateway khi Gateway đồng thời sử dụng Wi-Fi?
38. **[Q38](./Answers/Q38.md)** ⭐ — Gateway kiểm tra Authentication Tag, Sequence và Session ID như thế nào để phát hiện gói không hợp lệ hoặc chống Replay Attack?
39. **[Q39](./Answers/Q39.md)** — ACK được mã hóa và gửi lại Patient Node như thế nào? Nếu Node gửi lại bản tin trùng thì Gateway xử lý ra sao?

### 3. Cảm biến, GPS và hiển thị

40. **[Q40](./Answers/Q40.md)** — Gateway sử dụng DHT22 và BMP280 để đo những thông số gì? Vì sao một cảm biến dùng One-Wire-like, cảm biến còn lại dùng I2C?
41. **[Q41](./Answers/Q41.md)** — GPS NEO-M8N truyền dữ liệu NMEA qua UART như thế nào? Gateway kiểm tra dữ liệu GPS hợp lệ và cập nhật tọa độ ra sao?
42. **[Q42](./Answers/Q42.md)** ⭐ — Dữ liệu môi trường, GPS và sự kiện từ Patient Node được đồng bộ như thế nào? Cơ chế EnvironmentSnapshot và TTL có vai trò gì?
43. **[Q43](./Answers/Q43.md)** — TFT ST7735 giao tiếp SPI và được cập nhật bởi TaskDisplayTFT như thế nào? Làm sao tránh ảnh hưởng đến những tác vụ khác?

### 4. Wi-Fi, LTE, SMS và MQTT

44. **[Q44](./Answers/Q44.md)** ⭐ — Cơ chế Dual-Uplink Failover hoạt động như thế nào? Khi Wi-Fi mất trong 15 giây, Gateway thực hiện các bước gì để chuyển sang LTE?
45. **[Q45](./Answers/Q45.md)** — Vì sao sử dụng module A7680C? Gateway giao tiếp UART và điều khiển LTE bằng các nhóm lệnh AT nào?
46. **[Q46](./Answers/Q46.md)** ⭐ — Khi TaskSms và TaskConnManager cùng cần sử dụng A7680C, cơ chế Mutex/khóa tài nguyên giải quyết vấn đề ra sao?
47. **[Q47](./Answers/Q47.md)** — Gateway gửi SMS cảnh báo trong những điều kiện nào? Cơ chế cache 32 phiên ngăn gửi SMS trùng lặp như thế nào?
48. **[Q48](./Answers/Q48.md)** ⭐ — Gateway đóng gói JSON và xuất bản dữ liệu qua MQTT/TLS như thế nào? Vì sao chọn MQTT thay vì HTTP hoặc WebSocket?

## IV. Dashboard — Qt6/QML và giám sát (Q49–Q53)

49. **[Q49](./Answers/Q49.md)** ⭐ — Dashboard được xây dựng bằng Qt6/QML như thế nào? Vì sao chọn Qt6/QML thay vì Web Dashboard dùng React hoặc một framework khác?
50. **[Q50](./Answers/Q50.md)** ⭐ — Dashboard kết nối MQTT Broker, Subscribe Topic, nhận JSON và cập nhật các thông số AI, SpO₂, HR, môi trường và GPS ra sao?
51. **[Q51](./Answers/Q51.md)** — Các thành phần giao diện Overview, Patient, Environment, Gateway và Network lấy dữ liệu và cập nhật trạng thái như thế nào?
52. **[Q52](./Answers/Q52.md)** ⭐ — Khi mất MQTT, Gateway chuyển từ Wi-Fi sang LTE hoặc dữ liệu GPS không hợp lệ, Dashboard hiển thị và xử lý trạng thái như thế nào?
53. **[Q53](./Answers/Q53.md)** — Dashboard quản lý lịch sử các phiên đo như thế nào? Làm sao tránh một phiên bị hiển thị trùng khi dữ liệu được gửi lại?

## V. Tình huống tích hợp toàn hệ thống (Q54–Q58)

54. **[Q54](./Answers/Q54.md)** — Nếu Patient Node phân loại thành công nhưng Gateway đang tắt, kết quả sẽ được xử lý thế nào? Khi Gateway hoạt động trở lại có đồng bộ được sự kiện cũ không?
55. **[Q55](./Answers/Q55.md)** — Nếu ESP-NOW đã truyền thành công nhưng MQTT Broker mất kết nối, dữ liệu có bị mất hay không? Hệ thống có hàng đợi lưu sự kiện không?
56. **[Q56](./Answers/Q56.md)** — Nếu Wi-Fi bị mất khi Gateway đang gửi dữ liệu, việc chuyển sang 4G có làm gián đoạn ESP-NOW không?
57. **[Q57](./Answers/Q57.md)** — Nếu MAX30102 trả về SpO₂ hoặc HR không hợp lệ, kết quả AI có bị ảnh hưởng không? Dashboard thể hiện dữ liệu không hợp lệ như thế nào?
58. **[Q58](./Answers/Q58.md)** ⭐ — Trong thử nghiệm, tại sao hệ thống đạt 95,60% trên tập Test nhưng chỉ đạt 90% trên 20 lượt thử nghiệm tích hợp? Những yếu tố nào gây ra sai khác?

---

## Cấu trúc thư mục dự kiến

```text
Committee_QnA/
├── README.md
└── Answers/
    ├── Q01.md
    ├── Q02.md
    ├── ...
    └── Q58.md
```