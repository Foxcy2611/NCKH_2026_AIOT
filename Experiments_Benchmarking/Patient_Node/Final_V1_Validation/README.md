# Patient Node — Final V1 Validation

Thư mục này chứa toàn bộ phép kiểm chứng cần thiết trước khi đóng băng:

```text
Patient Node Firmware: FINAL V1
```

Đây **không phải nhánh nghiên cứu mở rộng**.

Mục tiêu của thư mục này là chứng minh rằng các tham số và luồng hiện hành đã được kiểm tra đủ để dùng làm baseline chính thức.

Checklist tổng:

- [Step_Done_V1.md](/Docs_Member/Chien/Step_Done_V1.md)

Nhánh nghiên cứu sau baseline:

- [Extension](../Extension/README.md)

---

## 1. Nguyên tắc

Final V1 Validation dùng baseline hiện hành làm mốc:

```text
Dataset V2
→ V1 DS-CNN
→ C4 frontend (pre=0, Mel 40, FFT 2048)
→ QAT Full INT8, seed 44
→ Patient Node firmware
→ Gateway
→ Cloud / MQTT
→ Qt6
```

Không retrain model trong chuỗi chốt V1 chỉ vì một threshold runtime chưa phù hợp.

Các phần cần chốt ở đây chủ yếu là:

- post-processing;
- Quality Gate;
- VAD;
- điều kiện sử dụng thực tế;
- sensor;
- communication;
- stability.

Chỉ quay lại AI training nếu kiểm thử phần cứng cho thấy lỗi có nguyên nhân rõ ràng từ model hoặc preprocessing.

---

## 2. Cấu trúc

```text
Final_V1_Validation/
├── README.md
├── 01_Classification_Threshold/
├── 02_Quality_Gate/
├── 03_VAD_Distance/
├── 04_MAX30102/
├── 05_End_to_End/
└── 06_Long_Term_Stability/
```

Sau khi sáu bước trên đạt yêu cầu, cập nhật:

```text
../Step_Done_V1.md
```

và thực hiện bước đóng băng source / config / tài liệu.

---

## 3. Bước 1 — Classification Threshold

Mục tiêu:

```text
p_non_asthma <= LOW     → ASTHMA
LOW < p_non_asthma < HIGH
                         → UNSURE
p_non_asthma >= HIGH    → NON-ASTHMA
```

Model vẫn là binary:

```text
0 = Asthma
1 = Non-Asthma
```

`UNSURE` chỉ là post-processing.

### Dataset dùng để chốt

Dùng đúng split của Final AI Model hiện hành:

```text
Validation: 154
├── Asthma      : 38
└── Non-Asthma  : 116

Test: 159
├── Asthma      : 38
└── Non-Asthma  : 121
```

Nguyên tắc:

```text
154 Validation
→ chọn LOW/HIGH
→ freeze
→ 159 Test chạy đúng một lượt cuối
```

Không dùng Test để quay lại chọn threshold.

Folder dự kiến:

```text
01_Classification_Threshold/
├── Generate_Predictions.py
├── threshold_utils.py
├── Threshold_Selection.ipynb
├── README.md
└── results/
    ├── validation_predictions.csv
    ├── threshold_comparison.csv
    ├── final_threshold.json
    └── final_test_result.csv
```

---

## 4. Bước 2 — Quality Gate

Chốt các ngưỡng hiện hành:

```text
RMS minimum
MAV active threshold
Active ratio
Clipping threshold
Clipped ratio
```

Mục tiêu:

- âm hợp lệ không bị loại quá nhiều;
- silence / âm quá yếu vẫn bị chặn;
- clipping vẫn được phát hiện;
- MONITOR bỏ sample lỗi mà không tăng vote;
- không treo state machine.

Folder:

```text
02_Quality_Gate/
├── README.md
├── quality_gate_test.*
├── results/
├── logs/
└── figures/
```

Có thể dùng `.csv` để lưu mỗi lần thử:

```text
scenario
distance
rms
mav
active_ratio
clipped_ratio
expected
actual
pass
```

---

## 5. Bước 3 — VAD và khoảng cách

Chốt:

```text
VAD threshold
consecutive chunks
pre-trigger buffer
distance
environment condition
```

Cần thử nhiều khoảng cách và điều kiện môi trường.

Kết quả cuối phải trả lời được:

```text
Patient Node V1 được bảo đảm trong điều kiện nào?
```

Không ghi một khoảng cách Final chỉ dựa trên cảm giác hoặc một lần thử.

---

## 6. Bước 4 — MAX30102

Kiểm tra trên module thật:

- I2C;
- có/không có ngón tay;
- timeout;
- `vitals_valid`;
- Heart Rate;
- SpO2;
- ảnh hưởng chuyển động;
- so sánh với thiết bị tham chiếu nếu có.

Mục tiêu là xác nhận tính hợp lý ở mức prototype nghiên cứu, không phải kiểm định thiết bị y tế.

---

## 7. Bước 5 — End-to-End

Chạy toàn chuỗi:

```text
Node CHECK / MONITOR
→ ESP-NOW
→ Gateway
→ ACK
→ Complete_Packet
→ MQTT / Cloud
→ Qt6
```

Phải lưu cùng một lượt:

```text
Node log
Gateway log
MQTT packet
Qt6 result
```

Cần kiểm tra cả:

```text
has_patient_event = true
has_patient_event = false
```

và các tình huống retry / reconnect.

---

## 8. Bước 6 — Long-Term Stability

Node:

```text
MONITOR liên tục 2–4 giờ
```

Toàn hệ thống:

```text
Node + Gateway + MQTT + Qt6
8–12 giờ
```

nếu có điều kiện có thể kéo dài hơn.

Theo dõi:

- reset;
- watchdog;
- heap;
- I2S;
- OLED;
- state machine;
- pending ACK;
- reconnect;
- duplicate / lost event;
- memory drift.

---

## 9. Evidence bắt buộc

Mỗi bước phải để lại bằng chứng trong repo hoặc thư mục lưu trữ experiment:

```text
README / conclusion
CSV / JSON
log
figure
firmware version
model version
config
```

Không chốt một tham số chỉ bằng lời mô tả.

---

## 10. Điều kiện đóng FINAL V1

Chỉ freeze khi:

```text
01 Classification Threshold    DONE
02 Quality Gate                DONE
03 VAD / Distance              DONE
04 MAX30102                    DONE
05 End-to-End                  DONE
06 Long-Term Stability         DONE
```

Sau đó khóa:

- Patient Node source;
- `Asthma_Model.h`;
- model hash;
- threshold;
- Quality Gate;
- VAD;
- vote;
- MAX30102 config;
- pin map;
- packet schema;
- ESP-NOW config;
- PlatformIO config;
- library versions.

Commit/tag khuyến nghị:

```text
patient-node-final-v1
```

Sau khi freeze, thay đổi tiếp theo phải thuộc:

```text
V1.1
hoặc
V2
```

không sửa âm thầm baseline Final V1.
