# Patient Node — Steps to FINAL V1

## 1. Mục tiêu

Tài liệu này là checklist chính để đưa Patient Node từ trạng thái:

```text
firmware đã chạy được
```

tới:

```text
Patient Node — FINAL V1
```

Hai thư mục liên quan:

- [Final V1 Validation](./Final_V1_Validation/README.md)
- [Research Extensions](./Extension/README.md)

Quy ước trạng thái:

```text
[ ]  chưa hoàn thành
[~]  đã chạy được nhưng chưa đủ bằng chứng
[x]  đã kiểm tra, lưu artifact và chấp nhận cho FINAL V1
```

AI Model hiện hành:

```text
Architecture       : V1 — DS-CNN / SeparableConv2D
Quantization       : PTQ Full INT8
Decision benchmark : threshold 0.5
Input              : [1, 64, 129, 1] INT8
Tensor Arena target: 280,000 B
Status             : FROZEN
```

Trong chuỗi chốt Patient Node V1, **không retrain model** trừ khi kiểm thử cho thấy lỗi rõ ràng có nguồn gốc từ AI pipeline.

---

# 2. Bước 1 — Chốt vùng phân lớp

Folder:

```text
Final_V1_Validation/01_Classification_Threshold/
```

## 2.1. Mục tiêu

Chọn và freeze hai biên:

```text
p_non_asthma <= LOW       → ASTHMA
LOW < p_non_asthma < HIGH → UNSURE
p_non_asthma >= HIGH      → NON-ASTHMA
```

Model chỉ có hai lớp:

```text
0 = Asthma
1 = Non-Asthma
```

`UNSURE` là post-processing.

## 2.2. Dữ liệu

Dùng đúng split của Final AI Model hiện hành:

```text
Validation: 154
├── Asthma      : 38
└── Non-Asthma  : 116

Test: 159
├── Asthma      : 38
└── Non-Asthma  : 121
```

Không sử dụng lại số `108 Validation / 113 Test` của baseline cũ.

## 2.3. Cách thực hiện

1. Chạy V1 PTQ INT8 trên toàn bộ 154 Validation.
2. Lưu với từng sample:

```text
file_name
true_label
output_int8
p_non_asthma
binary_pred_0.5
```

3. So sánh tối thiểu:

```text
0.40 / 0.60
0.45 / 0.65
0.45 / 0.70
0.50 / 0.65
```

4. Có thể grid sweep rộng hơn trên Validation.
5. Với mỗi cặp biên tính:

```text
Asthma → Asthma
Asthma → Unsure
Asthma → Non-Asthma

Non-Asthma → Asthma
Non-Asthma → Unsure
Non-Asthma → Non-Asthma

Asthma Precision
Asthma Recall
Asthma F1
Unsure Rate
Asthma Miss Rate
Non-Asthma False Alarm Rate
```

6. Ưu tiên giảm:

```text
Asthma → Non-Asthma
```

nhưng không làm false alarm hoặc Unsure Rate tăng quá mức.

7. Chọn một cặp LOW/HIGH duy nhất bằng Validation.
8. Ghi vào `final_threshold.json`.
9. Freeze.
10. Chạy 159 Test đúng một lượt cuối.
11. Không quay lại chỉnh threshold bằng Test.

## 2.4. Điều kiện hoàn thành

- [ ] Có `validation_predictions.csv`.
- [ ] Có bảng so sánh threshold.
- [ ] LOW/HIGH được chọn chỉ bằng Validation.
- [ ] Có `final_threshold.json`.
- [ ] Có kết quả cuối trên 159 Test.
- [ ] Firmware / tài liệu / experiment dùng cùng LOW/HIGH.
- [ ] Có báo cáo Unsure Rate và Asthma Miss.

---

# 3. Bước 2 — Chốt Quality Gate

Folder:

```text
Final_V1_Validation/02_Quality_Gate/
```

Baseline hiện hành:

```text
RMS minimum                    = 150
MAV active threshold           > 80
Minimum active ratio           = 5%
Clipping sample threshold      > 32000
Maximum clipping ratio         = 1%
```

## 3.1. Nhóm thử

Mỗi nhóm nên lặp đủ số lần để có thống kê:

| Nhóm | Ví dụ | Kỳ vọng |
|---|---|---|
| Im lặng | phòng yên | `AUDIO_INACTIVE` |
| Quá nhỏ | nguồn âm xa | inactive / too weak |
| Hợp lệ | ho/thở/playback hợp lệ | `AUDIO_OK` |
| Quá lớn | nguồn sát mic / clipping | too loud |
| Nhiễu | quạt / speech nền | không lọt hàng loạt |
| Va chạm | chạm/gõ micro | nên bị loại hoặc không tạo inference tin cậy |

Mỗi lần ghi:

```text
scenario
distance
RMS
MAV
active_ratio
clipped_ratio
expected
actual
pass
```

## 3.2. Điều kiện hoàn thành

- [ ] Âm hợp lệ được chấp nhận ổn định.
- [ ] Silence / âm quá yếu bị loại.
- [ ] Clipping được phát hiện.
- [ ] MONITOR bỏ sample lỗi mà không tăng vote.
- [ ] Không treo state machine.
- [ ] Có bảng trước/sau nếu thay threshold.
- [ ] Freeze một bộ Quality Gate cho V1.

---

# 4. Bước 3 — Chốt VAD và khoảng cách

Folder:

```text
Final_V1_Validation/03_VAD_Distance/
```

Baseline:

```text
VAD threshold          = 75
Consecutive chunks     = 4
Warm-up                = 100 chunks
Pre-trigger buffer     = 1 s
Clip                    = 5 s
```

## 4.1. Khoảng cách cần kiểm tra

Tối thiểu:

```text
3 cm
6 cm
10 cm
15 cm
```

Môi trường:

```text
phòng yên
quạt ổn định
nhiễu nền nhẹ
```

Theo dõi:

```text
trigger / miss
false trigger
reaction time
Quality Gate result
pre-trigger correctness
inference / vote
```

MONITOR nên chạy thêm 30–60 phút chỉ với background để đo false trigger.

Nếu baseline chưa phù hợp, thử có kiểm soát:

```text
VAD threshold: 60 / 75 / 90
chunks       : 2 / 4 / 6
```

Không đổi đồng thời cả hai biến trong vòng so sánh đầu.

## 4.2. Điều kiện hoàn thành

- [ ] Freeze VAD threshold.
- [ ] Freeze số chunk.
- [ ] Xác nhận pre-trigger 1 s.
- [ ] Chốt khoảng cách sử dụng tối đa.
- [ ] Ghi rõ điều kiện môi trường.
- [ ] Có trigger/miss/false-trigger statistics.

---

# 5. Bước 4 — Kiểm tra MAX30102

Folder:

```text
Final_V1_Validation/04_MAX30102/
```

Kiểm tra:

```text
I2C 0x57
finger detection
timeout
Heart Rate
SpO2
vitals_valid
motion
ambient light
```

Nếu có thiết bị tham chiếu:

```text
ít nhất 3 người
~5 lượt/người
đo khi nghỉ
```

Kết quả chỉ dùng ở mức prototype nghiên cứu.

Không diễn giải thành kiểm định y tế.

Thiết kế firmware hiện hành cần được xác nhận bằng test phần cứng:

```text
boot: xác minh/cấu hình MAX30102 rồi shutdown
→ bắt đầu CHECK: wake SpO2
→ vào VITAL_CHECK
→ reset buffer/cache và flush FIFO
→ chờ kết quả trong deadline chung 10 giây
→ có HR + SpO2 hợp lệ: vitals_valid=1
→ không ngón tay / FIFO-I2C lỗi / kết quả invalid: vitals_valid=0, HR=0, SpO2=0
→ luôn đi tiếp SESSION_READY, không chờ vô hạn
→ shutdown MAX30102 khi CHECK hoàn tất/hủy/lỗi
```

MAX30102 không còn duy trì SpO2 ngoài CHECK. Bộ đệm trượt 75/25 không được tái sử dụng qua
ranh giới hai phiên CHECK. Các checkbox bên dưới chỉ được đánh dấu sau khi đã chạy module thật;
việc đã sửa source chưa được tính là hoàn thành validation.

## Điều kiện hoàn thành

- [ ] Có/không có ngón tay được xử lý đúng.
- [ ] Timeout không treo hệ thống.
- [ ] `vitals_valid` đúng.
- [ ] Packet không chứa dữ liệu invalid dưới dạng hợp lệ.
- [ ] LED RED/IR tắt tại STANDBY và MONITOR, bật đúng khi CHECK bắt đầu.
- [ ] Sensor trở lại shutdown sau complete/abort/timeout/error.
- [ ] Có bảng so sánh tham chiếu nếu thực hiện được.
- [ ] Giới hạn được ghi rõ.

---

# 6. Bước 5 — End-to-End

Folder:

```text
Final_V1_Validation/05_End_to_End/
```

Luồng CHECK:

```text
CHECK
→ audio 5 s
→ Quality Gate
→ DSP
→ V1 PTQ INT8
→ post-processing
→ MAX30102
→ Node_Payload
→ AES-128-GCM
→ ESP-NOW
→ Gateway ACK
→ Complete_Packet
→ MQTT
→ Qt6
```

Luồng MONITOR:

```text
VAD
→ pre-trigger
→ Quality Gate
→ DSP + inference
→ 3 valid votes
→ final result
→ Node_Payload
→ Gateway
→ MQTT
→ Qt6
```

Phải thử:

1. CHECK thành công ngay lần đầu.
2. MONITOR đủ vote và chỉ gửi một kết luận cuối.
3. ESP-NOW fail một lần rồi retry thành công.
4. Gateway offline.
5. Gateway online lại.
6. Wi-Fi/MQTT mất và reconnect.
7. Không gửi lặp vô hạn.
8. sequence/session/event id đúng.
9. Qt6 hiển thị đúng state.

Phải lưu cùng lượt:

```text
Node log
Gateway log
MQTT payload
Qt6 evidence
```

## Điều kiện hoàn thành

- [ ] Gateway dùng source mới nhất.
- [ ] ACK/retry/timeout không kẹt.
- [ ] `has_patient_event=true` đúng.
- [ ] `has_patient_event=false` đúng.
- [ ] Qt6 giữ latest Node data đúng policy.
- [ ] Tên field / class code thống nhất toàn hệ thống.

---

# 7. Bước 6 — Long-Term Stability

Folder:

```text
Final_V1_Validation/06_Long_Term_Stability/
```

## 7.1. Node

Chạy:

```text
MONITOR 2–4 giờ
```

Theo dõi:

```text
unexpected reset
watchdog
OLED
I2S
heap
minimum free heap
state machine
stale vote
pending ACK
Light Sleep sau 15 giây STANDBY
wake bằng CHECK / MONITOR / SLEEP
I2S và ESP-NOW sau nhiều chu kỳ sleep/wake
```

## 7.2. Toàn hệ thống

Chạy:

```text
Node + Gateway + MQTT + Qt6
8–12 giờ
```

nếu có điều kiện có thể chạy 24 giờ.

Theo dõi:

```text
message count
ACK / retry
reconnect
JSON error
duplicate event
lost event
Qt6 update
memory drift
```

## Điều kiện hoàn thành

- [ ] Không reset ngoài dự kiến.
- [ ] Không deadlock / treo.
- [ ] Không có memory leak rõ.
- [ ] Pending ACK không kẹt.
- [ ] Reconnect hoạt động.
- [ ] CHECK/MONITOR vẫn chạy được sau test dài.
- [ ] Không tự sleep ngoài STANDBY.
- [ ] Không mất model/Tensor Arena sau Light Sleep.
- [ ] MAX30102 không sáng liên tục ngoài CHECK.

---

# 8. Bước 7 — Freeze Patient Node FINAL V1

Chỉ thực hiện khi Bước 1–6 đều `DONE`.

Freeze:

```text
Patient Node source
Asthma_Model.h
TFLite model
model SHA-256
classification LOW/HIGH
Quality Gate thresholds
VAD config
vote policy
MAX30102 config
Light Sleep timeout và wake-source
pin map
ESP-NOW channel
packet structure
schema version
cloud interval
platformio.ini
resolved library versions
```

Không commit:

```text
Wi-Fi password
MQTT secret
AES key
private credential
```

Artifact cuối cần có:

```text
threshold report
Quality Gate report
VAD report
MAX30102 result
end-to-end logs
long-term logs
demo evidence
firmware version
model hash
known limitations
```

Commit/tag khuyến nghị:

```text
patient-node-final-v1
```

Sau khi freeze:

```text
FINAL V1 không sửa trực tiếp
→ thay đổi mới = V1.1 hoặc V2
```

---

# 9. Trạng thái hiện tại

| Bước | Trạng thái | Hành động tiếp theo |
|---|---|---|
| 1. Classification Threshold | `Done` | chạy 154 Validation bằng V1 PTQ INT8 |
| 2. Quality Gate | `TODO` | test với mạch và nhiều tình huống |
| 3. VAD / Distance | `TODO` | lập ma trận khoảng cách |
| 4. MAX30102 | `Done` | kiểm tra module thật |
| 5. End-to-End | `[~]` | chạy lại bằng source/model mới nhất và lưu evidence |
| 6. Long-Term Stability | `[~]` | chạy Node và full system dài hạn |
| 7. Freeze | `TODO` | chỉ làm sau Bước 1–6 |

Thứ tự:

```text
1 Threshold
→ 2 Quality Gate
→ 3 VAD / Distance
→ 4 MAX30102
→ 5 End-to-End
→ 6 Long-Term
→ 7 Freeze FINAL V1
```
