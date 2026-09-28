# CÁC BƯỚC CHỐT PATIENT NODE FINAL V1

## 1. Mục tiêu

Tài liệu này là checklist các công việc còn lại để Patient Node được công nhận là
`FINAL V1`. Việc firmware đã chạy được chưa đồng nghĩa mọi ngưỡng đã tối ưu hoặc
đã có đủ bằng chứng thực nghiệm.

Luồng tổng thể đã thử thành công:

```text
Node CHECK/MONITOR
    → mã hóa và gửi ESP-NOW
    → Gateway giải mã
    → Gateway phản hồi ACK cho Node
    → Gateway định kỳ tạo Complete_Packet
    → MQTT/Cloud
    → Qt6 nhận JSON và cập nhật dashboard
```

Gateway vẫn phải được nạp lại bản source mới nhất trước lượt kiểm tra toàn chuỗi
chính thức.

Các trạng thái sử dụng trong tài liệu:

- `[ ]`: chưa hoàn thành;
- `[~]`: đã chạy được nhưng chưa có đủ phép thử hoặc bằng chứng;
- `[x]`: đã kiểm tra, lưu kết quả và được chấp nhận cho Final V1.

---

## 2. Bước 1 — Chốt vùng phân lớp

### 2.1. Mục tiêu

Kiểm chứng hai biên phân lớp hiện hành:

```text
p_non_asthma <= 0,45         → ASTHMA     (mã 0)
0,45 < p_non_asthma < 0,65  → UNSURE     (mã 2)
p_non_asthma >= 0,65         → NON-ASTHMA (mã 1)
```

Model chỉ được huấn luyện hai lớp. `UNSURE` là vùng xử lý sau suy luận, không
phải lớp thứ ba của model.

### 2.2. Cách thực hiện

1. Dùng đúng 108 mẫu validation, gồm 30 Asthma và 78 Non-Asthma.
2. Chạy model TFLite INT8 và lưu `p_non_asthma`, nhãn thật và kết quả của từng
   mẫu.
3. So sánh tối thiểu các cặp biên:

```text
0,40 / 0,60
0,45 / 0,65
0,45 / 0,70
0,50 / 0,65
```

4. Với mỗi cặp biên, thống kê:

   - số Asthma được phát hiện đúng;
   - số Asthma bị nhầm thẳng thành Non-Asthma;
   - số Non-Asthma bị cảnh báo nhầm thành Asthma;
   - số và tỷ lệ mẫu UNSURE;
   - Precision, Recall và F1 của Asthma;
   - ma trận nhầm lẫn có tính cả UNSURE.

5. Ưu tiên giảm trường hợp Asthma bị kết luận thành Non-Asthma, nhưng không để
   số cảnh báo sai hoặc tỷ lệ UNSURE tăng quá mức sử dụng được.
6. Chọn một cặp biên duy nhất bằng validation.
7. Sau khi đã chốt mới chạy đúng một lượt trên 113 mẫu test để báo cáo kết quả
   cuối. Không dùng tập test để quay lại lựa chọn ngưỡng.
8. Đối chiếu lại các phép thử phần cứng để bảo đảm Python/TFLite và firmware sử
   dụng đúng cùng hai biên.

### 2.3. Bằng chứng cần lưu

- File kết quả của 108 mẫu validation.
- Bảng so sánh các cặp biên.
- Kết quả cuối trên 113 mẫu test.
- Lý do chọn hai biên Final V1.

### 2.4. Điều kiện hoàn thành

- [ ] Hai biên được chọn bằng validation, không chọn bằng test.
- [ ] Source, tài liệu và kết quả thử dùng cùng một giá trị.
- [ ] Có báo cáo tỷ lệ UNSURE và số Asthma bị bỏ sót.
- [ ] Không cần huấn luyện lại model nếu chỉ thay hai biên này.

---

## 3. Bước 2 — Chốt Quality Gate

### 3.1. Mục tiêu

Quality Gate phải loại được âm thanh không dùng được nhưng không quá kén đến mức
loại nhầm nhiều lần nói, ho hoặc âm thanh hô hấp hợp lệ trong CHECK/MONITOR.

Ngưỡng hiện hành dùng làm mốc:

```text
RMS tối thiểu                    = 150
MAV để block hoạt động           > 80
Tỷ lệ block hoạt động tối thiểu  = 5%
Ngưỡng sample clipping           > 32000
Tỷ lệ clipping tối đa            = 1%
```

### 3.2. Chuẩn bị tình huống thử

Mỗi nhóm nên thực hiện tối thiểu 15–20 lần:

| Nhóm | Ví dụ | Kết quả mong đợi |
|---|---|---|
| Im lặng | Phòng yên | `AUDIO_INACTIVE` |
| Quá nhỏ | Nói/phát âm thanh quá xa | `AUDIO_INACTIVE` hoặc `AUDIO_TOO_WEAK` |
| Hợp lệ | Ho, thở, file thử ở khoảng cách quy định | `AUDIO_OK` |
| Quá lớn | La hoặc dí loa quá sát | `AUDIO_TOO_LOUD` nếu có clipping |
| Nhiễu | Quạt, xe, tiếng nói nền | Không được chấp nhận hàng loạt như âm hợp lệ |
| Va chạm | Gõ/chạm vào micro | Nên bị loại hoặc không tạo kết quả tin cậy |

### 3.3. Cách thực hiện

1. Giữ nguyên bộ ngưỡng hiện hành và chạy toàn bộ nhóm thử làm mốc.
2. Mỗi lần ghi:

```text
Tình huống
Khoảng cách
RMS
MAV trung bình
Active ratio
Clipped ratio
Kết luận Quality Gate
Kết quả mong đợi
Đúng/Sai
```

3. Tính:

   - tỷ lệ chấp nhận âm thanh hợp lệ;
   - tỷ lệ loại âm thanh không hợp lệ;
   - số âm hợp lệ bị loại nhầm;
   - số âm không hợp lệ lọt qua.

4. Nếu kết quả chưa đạt, chỉ thay đổi một nhóm tham số trong mỗi lượt:

   - trước tiên xem `MAV` và tỷ lệ block hoạt động nếu thường bị
     `AUDIO_INACTIVE`;
   - sau đó mới xem RMS nếu thường bị `AUDIO_TOO_WEAK`;
   - chỉ chỉnh clipping khi có bằng chứng âm thanh hợp lệ bị báo quá lớn.

5. Chạy lại cùng kịch bản và so sánh trực tiếp với cấu hình mốc.
6. Không chọn ngưỡng chỉ dựa trên một file hoặc một lần thử.

### 3.4. Điều kiện hoàn thành

- [ ] CHECK chấp nhận ổn định âm thanh hợp lệ trong điều kiện sử dụng đã quy định.
- [ ] Im lặng và âm quá yếu vẫn bị loại.
- [ ] Âm clipping vẫn bị phát hiện.
- [ ] MONITOR bỏ đoạn lỗi mà không tăng vote và không bị treo.
- [ ] Có bảng kết quả trước/sau khi chỉnh.
- [ ] Chốt một bộ ngưỡng duy nhất cho Final V1.

---

## 4. Bước 3 — Chốt VAD và điều kiện khoảng cách sử dụng

### 4.1. Mục tiêu

Chốt rõ thiết bị được sử dụng ở khoảng cách và môi trường nào. Không tuyên bố
Node hoạt động tốt ở mọi khoảng cách hoặc mọi mức nhiễu.

Thông số mốc hiện hành:

```text
Ngưỡng VAD              = 75
Số chunk liên tiếp      = 4, khoảng 64 ms
Warm-up                 = 100 chunk, khoảng 1,6 giây
Bộ đệm trước kích hoạt  = 1 giây
Đoạn hoàn chỉnh         = 5 giây
```

### 4.2. Ma trận kiểm tra

Thử tối thiểu các khoảng cách:

```text
3 cm
6 cm
10 cm
15 cm
```

Thử trong các môi trường:

- phòng yên;
- có tiếng quạt ổn định;
- có tiếng nói hoặc tiếng động nền nhẹ.

Nguồn âm thanh:

- ho/thở thực tế của người bình thường;
- file Asthma chưa dùng để huấn luyện nếu có;
- file Non-Asthma chưa dùng để huấn luyện;
- im lặng và chỉ có nhiễu nền.

Mỗi tổ hợp quan trọng nên lặp lại 10–20 lần.

### 4.3. Cách thực hiện

1. Chạy cấu hình `75` và 4 chunk làm mốc.
2. Mỗi lần ghi:

   - VAD có kích hoạt hay không;
   - có kích hoạt nhầm khi không có âm thanh mục tiêu hay không;
   - thời gian phản ứng;
   - Quality Gate có chấp nhận đoạn thu hay không;
   - phần âm thanh trước kích hoạt có nằm trong đoạn 5 giây hay không;
   - kết quả suy luận và vote.

3. Để MONITOR chạy 30–60 phút chỉ với nhiễu nền và đếm số lần kích hoạt nhầm.
4. Nếu ngưỡng hiện hành chưa phù hợp, thử lần lượt:

```text
Ngưỡng năng lượng: 60 / 75 / 90
Số chunk liên tiếp: 2 / 4 / 6
```

5. Không thay đồng thời ngưỡng và số chunk trong lượt so sánh đầu tiên.
6. Chọn khoảng cách lớn nhất vẫn có tỷ lệ kích hoạt và thu mẫu hợp lệ ổn định.
7. Viết rõ điều kiện sử dụng, ví dụ:

> Final V1 được sử dụng trong nhà, nhiễu nhẹ, nguồn âm cách INMP441 không quá
> 6 cm. Khoảng cách xa hơn không nằm trong phạm vi bảo đảm của nguyên mẫu.

Con số 6 cm chỉ được ghi Final sau khi kết quả đo xác nhận.

### 4.4. Điều kiện hoàn thành

- [ ] Chốt ngưỡng VAD và số chunk liên tiếp.
- [ ] Chốt khoảng cách sử dụng tối đa.
- [ ] Ghi rõ môi trường sử dụng và giới hạn của nguyên mẫu.
- [ ] Có thống kê kích hoạt đúng, bỏ sót và kích hoạt nhầm.
- [ ] Xác nhận bộ đệm một giây hoạt động đúng.

---

## 5. Bước 4 — Kiểm tra MAX30102 thật

### 5.1. Mục tiêu

Xác nhận module thật có thể phát hiện ngón tay, trả kết quả nhịp tim/SpO2 hợp lý
và đặt đúng cờ `vitals_valid`.

### 5.2. Cách thực hiện

1. Khởi động và xác nhận I2C tìm thấy địa chỉ `0x57`.
2. Không đặt ngón tay:

   - phải báo chưa có ngón tay hoặc hết thời gian;
   - `vitals_valid = false`;
   - packet không được biến giá trị lỗi thành dữ liệu hợp lệ.

3. Đặt ngón tay đúng vị trí:

   - chờ tín hiệu ổn định;
   - kiểm tra nhịp tim và SpO2;
   - `vitals_valid = true` khi cả hai giá trị hợp lệ.

4. Thử ngón tay đặt lệch, chuyển động và ánh sáng ngoài để xem hệ thống có loại
   phép đo kém hay không.
5. So sánh với máy đo SpO2 thương mại:

   - tối thiểu 3 người;
   - mỗi người khoảng 5 lượt;
   - đo khi ngồi nghỉ;
   - ghi đồng thời kết quả Node và thiết bị tham chiếu.

6. Mức sai lệch tham khảo cho nguyên mẫu:

```text
Nhịp tim: khoảng ±5 BPM
SpO2: khoảng ±2–3 điểm phần trăm
```

Đây không phải kiểm định thiết bị y tế. Nếu sai lệch lớn, kiểm tra vị trí ngón
tay, chuyển động, dòng LED, ánh sáng ngoài và thời gian chờ ổn định trước khi
đổi thuật toán.

### 5.3. Điều kiện hoàn thành

- [ ] Phát hiện đúng trường hợp có/không có ngón tay.
- [ ] Timeout không làm treo state machine.
- [ ] `vitals_valid` và dữ liệu trong packet đúng.
- [ ] Có bảng so sánh với thiết bị tham chiếu.
- [ ] Ghi rõ giới hạn: số liệu chỉ mang tính hỗ trợ nghiên cứu.

---

## 6. Bước 5 — Chạy toàn chuỗi Node → Gateway → Cloud → Qt6

### 6.1. Trạng thái hiện tại

Đã chạy thành công về chức năng:

- Node CHECK/MONITOR gửi được tới Gateway;
- Gateway phản hồi ACK;
- Gateway gửi định kỳ `Complete_Packet` lên Cloud;
- bản tin có thể chỉ chứa Gateway hoặc kèm `Node_Payload` mới;
- Qt6 nhận dữ liệu và cập nhật dashboard.

Trạng thái hiện tại là `[~]`: phải nạp Gateway từ source mới nhất và lưu lại log
của lượt kiểm tra chính thức.

### 6.2. Luồng CHECK cần xác nhận

```text
CHECK
→ thu 5 giây
→ Quality Gate
→ suy luận một lần
→ đo MAX30102
→ tạo Node_Payload_t
→ mã hóa AES-128-GCM
→ gửi ESP-NOW
→ Gateway xác thực/giải mã
→ Gateway phản hồi ACK
→ Gateway tạo Complete_Packet
→ MQTT
→ Qt6 cập nhật
```

### 6.3. Luồng MONITOR cần xác nhận

```text
VAD
→ bộ đệm trước kích hoạt
→ Quality Gate
→ DSP + suy luận
→ đủ 3 vote hợp lệ
→ kết luận cuối
→ Node_Payload_t
→ Gateway ACK
→ Complete_Packet
→ MQTT
→ Qt6
```

### 6.4. Quy tắc bản tin cần kiểm tra

Khi có sự kiện Node mới:

```text
message_type = "complete_packet"
schema_version = 1
has_patient_event = true
patient_event chứa Node_Payload mới
```

Sau khi sự kiện đó đã được publish thành công, bản tin định kỳ tiếp theo:

```text
message_type = "complete_packet"
schema_version = 1
has_patient_event = false
patient_event = null
```

Qt6 phải giữ dữ liệu Node gần nhất trên giao diện khi nhận packet không có sự
kiện Node mới.

### 6.5. Các trường hợp phải thử

1. CHECK gửi thành công ngay lần đầu.
2. MONITOR đủ ba vote rồi gửi đúng một kết luận cuối.
3. ESP-NOW lỗi một lần rồi retry thành công.
4. Gateway tắt: Node retry đủ số lần, bỏ sự kiện và không treo.
5. Gateway bật lại: phép đo mới tiếp tục gửi bình thường.
6. Wi-Fi/MQTT mất rồi kết nối lại được.
7. Không gửi lặp vô hạn cùng một sự kiện Node.
8. `sequence`, `session_id`, `event_id` và `record_id` thay đổi đúng vai trò.
9. Qt6 hiển thị đúng Asthma/Non-Asthma/Unsure, điểm model, sinh hiệu, môi
   trường, GPS và trạng thái mạng.

### 6.6. Điều kiện hoàn thành

- [ ] Nạp bản Gateway mới nhất.
- [ ] Lưu log Node, Gateway và bản tin MQTT cùng một lượt thử.
- [ ] Kiểm tra cả `has_patient_event=true` và `false`.
- [ ] ACK/retry/timeout không làm kẹt Node.
- [ ] Qt6 giữ đúng trạng thái Node gần nhất.
- [ ] Không có sai khác tên trường hoặc quy ước lớp giữa ba thành phần.

---

## 7. Bước 6 — Chạy thử ổn định dài hạn

### 7.1. Node riêng

Chạy MONITOR liên tục tối thiểu 2–4 giờ. Trong thời gian này:

- để một số khoảng chỉ có nhiễu nền;
- tạo nhiều lần kích hoạt hợp lệ;
- thực hiện CHECK nhiều lần;
- chuyển đổi CHECK/MONITOR/STANDBY;
- thử thoát và bắt đầu lại phiên mới.

Theo dõi:

```text
Reset ngoài dự kiến
Watchdog
Treo OLED
Treo I2S
Lỗi cấp phát bộ nhớ
Heap còn lại và heap nhỏ nhất
Vote còn sót từ phiên trước
Pending còn bị giữ
State machine không trở lại STANDBY
```

### 7.2. Toàn hệ thống

Chạy Node + Gateway + MQTT + Qt6 ít nhất 8–12 giờ; nếu có điều kiện thì chạy
24 giờ.

Theo dõi:

- số bản tin gửi và nhận;
- ACK và retry;
- chu kỳ MQTT 5 giây;
- mất/kết nối lại Wi-Fi, LTE và MQTT;
- lỗi JSON;
- trùng hoặc mất sự kiện;
- Qt6 ngừng cập nhật;
- bộ nhớ Node/Gateway có giảm dần hay không.

### 7.3. Điều kiện hoàn thành

- [ ] Không reset ngoài dự kiến.
- [ ] Không treo task, I2S, OLED hoặc state machine.
- [ ] Không có xu hướng mất dần bộ nhớ.
- [ ] Không kẹt pending ACK.
- [ ] Sau mất kết nối, hệ thống tiếp tục làm việc được.
- [ ] Node vẫn thực hiện được phiên CHECK/MONITOR mới sau khi chạy dài hạn.

---

## 8. Bước 7 — Đóng băng source, thông số và tài liệu FINAL V1

Chỉ thực hiện sau khi sáu bước trên đạt yêu cầu.

### 8.1. Thành phần phải đóng băng

- Source Patient Node.
- Model `.tflite` và `Asthma_Model.h`.
- SHA-256 của model.
- Hai biên phân lớp.
- Ngưỡng Quality Gate.
- VAD, số chunk và khoảng cách sử dụng.
- Số vote.
- Cấu hình MAX30102.
- Cấu hình chân phần cứng.
- Kênh ESP-NOW, cấu trúc packet và phiên bản schema.
- Chu kỳ gửi Cloud.
- `platformio.ini` và phiên bản thư viện thực tế.

Không đưa Wi-Fi, mật khẩu MQTT, khóa AES hoặc thông tin bí mật vào tài liệu công
khai.

### 8.2. Bằng chứng phải lưu

```text
Log kiểm thử ngưỡng
Bảng validation/test
Log Quality Gate và VAD
Kết quả MAX30102
Log toàn chuỗi
Log chạy dài hạn
Ảnh/video demo
Phiên bản firmware
Ngày chốt
Các giới hạn còn tồn tại
```

### 8.3. Quy tắc phiên bản

Ghi thống nhất:

```text
Patient Node Firmware: FINAL V1
Model: FINAL V1
Cloud schema_version: 1
message_type: complete_packet
```

Tạo commit/tag riêng, ví dụ:

```text
patient-node-final-v1
```

Sau khi đóng băng, không sửa trực tiếp Final V1. Mọi thay đổi tiếp theo phải tạo
V1.1 hoặc V2 để có thể đối chiếu lại kết quả.

### 8.4. Điều kiện hoàn thành

- [ ] Source build sạch từ một lần clean mới.
- [ ] Node và Gateway dùng đúng protocol đã chốt.
- [ ] Tài liệu khớp source.
- [ ] Model/hash khớp file triển khai.
- [ ] Không commit thông tin bí mật.
- [ ] Có commit/tag Final V1 và gói bằng chứng đi kèm.

---

## 9. Trạng thái và thứ tự thực hiện

| Bước | Trạng thái hiện tại | Hành động tiếp theo |
|---|---|---|
| 1. Vùng phân lớp | Chưa kiểm chứng chính thức | Chạy 108 validation và so sánh các cặp biên |
| 2. Quality Gate | CHECK còn loại nhầm | Ghi RMS/MAV/active/clipping theo từng tình huống |
| 3. VAD/khoảng cách | Khả quan dưới khoảng 6 cm | Lập ma trận khoảng cách và đo kích hoạt nhầm |
| 4. MAX30102 | Chờ module thật | So sánh với thiết bị tham chiếu |
| 5. Toàn chuỗi | Đã chạy được | Nạp Gateway mới và lưu log chính thức |
| 6. Chạy dài hạn | Chưa thực hiện | Chạy Node 2–4 giờ, toàn hệ thống 8–12 giờ |
| 7. Đóng băng | Chưa thực hiện | Chỉ làm sau khi bước 1–6 đạt |

Thứ tự đề xuất:

```text
Bước 1
→ Bước 2
→ Bước 3
→ Bước 4
→ nạp Gateway mới nhất
→ Bước 5
→ Bước 6
→ Bước 7
```

Không cần huấn luyện lại model trong chuỗi này, trừ khi các phép thử cho thấy
model thất bại rõ ràng. Phần việc chính còn lại là chốt xử lý sau suy luận,
ngưỡng âm thanh, phần cứng và độ ổn định của hệ thống.
