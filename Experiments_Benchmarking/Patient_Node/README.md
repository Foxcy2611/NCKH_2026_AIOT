# Node - Thí nghiệm và đánh giá

## 1. Mục tiêu

Thư mục `Node` dùng để đánh giá các quyết định kỹ thuật của Patient Node trước khi chốt số liệu đưa vào báo cáo NCKH.

Patient Node hiện đã có pipeline chính:

```text
Âm thanh
  ↓
Kiểm tra chất lượng
  ↓
Lọc Butterworth
  ↓
Pre-emphasis
  ↓
Mel-Spectrogram
  ↓
DS-CNN
  ↓
Kết quả TinyML
  ↓
Hiển thị / gửi Gateway
```

Các thí nghiệm trong thư mục này không nhằm viết lại toàn bộ hệ thống, mà dùng để kiểm tra xem những lựa chọn hiện tại có hợp lý hay không.

---

## 2. Cấu hình chuẩn để đối chiếu

Khi một thí nghiệm không thay đổi trực tiếp một tham số nào đó, giữ cấu hình chuẩn hiện tại:

| Thành phần | Cấu hình chuẩn |
|---|---|
| Tần số lấy mẫu | 16 kHz |
| Độ dài mẫu | 5 giây |
| Bộ lọc | Butterworth band-pass 100-2000 Hz |
| Bậc Butterworth | 5 |
| Pre-emphasis | 0.97 |
| Đặc trưng | Mel-Spectrogram 64 × 129 |
| Mô hình | DS-CNN |
| Lượng tử hóa cuối | INT8 |
| Ngưỡng phân lớp | 0.5 |
| Voting | 3 lần |
| Thiết bị đích | ESP32-S3 |

Cấu hình này là mốc để so sánh, không có nghĩa mọi tham số trên đều đã được chứng minh là tối ưu.

---

# 3. Các nhóm thí nghiệm

## 3.1. Lượng tử hóa mô hình

Thư mục đề xuất:

```text
AI/
└── quantization/
```

So sánh:

- INT8;
- INT16 × INT8 nếu pipeline hỗ trợ ổn định.

INT4 chỉ nên xem như hướng khảo sát thêm nếu công cụ và runtime hỗ trợ phù hợp.

Các chỉ số cần lưu:

- Accuracy;
- Precision;
- Recall;
- F1-score;
- kích thước model;
- bộ nhớ cần dùng;
- thời gian suy luận trên ESP32-S3;
- thời gian toàn pipeline nếu có.

Mục tiêu:

> Xác định mức lượng tử hóa phù hợp giữa độ chính xác và tài nguyên phần cứng.

---

## 3.2. Bậc bộ lọc Butterworth

Thư mục đề xuất:

```text
DSP/
└── butterworth_order/
```

Các bản thử:

```text
Không lọc
Bậc 3
Bậc 5
Bậc 7
```

Các yếu tố khác giữ nguyên.

Cần so sánh:

- Accuracy;
- Recall;
- F1-score;
- thời gian xử lý DSP;
- ảnh hưởng trên các mẫu nhiễu.

Mục tiêu:

> Kiểm tra xem Butterworth bậc 5 hiện tại có thực sự hợp lý so với các lựa chọn đơn giản hoặc phức tạp hơn.

---

## 3.3. Dải tần band-pass

Thư mục đề xuất:

```text
DSP/
└── bandpass_range/
```

Có thể thử:

```text
50-2000 Hz
100-2000 Hz
100-2500 Hz
100-4000 Hz
```

Không cần mở rộng quá nhiều nếu các kết quả đầu tiên đã cho thấy xu hướng rõ.

Cần đánh giá:

- Accuracy;
- Recall;
- F1-score;
- khả năng chống nhiễu;
- thời gian xử lý.

Mục tiêu:

> Xác định dải tần phù hợp nhất với dữ liệu âm thanh hô hấp đang sử dụng.

---

## 3.4. Pre-emphasis

Thư mục đề xuất:

```text
DSP/
└── pre_emphasis/
```

Các bản thử:

```text
Không dùng
0.95
0.97
```

Mục tiêu:

> Kiểm tra pre-emphasis có thực sự giúp mô hình hay chỉ làm pipeline phức tạp hơn.

Nếu kết quả gần như không thay đổi, có thể cân nhắc loại bỏ bước này.

---

## 3.5. Số lượng Mel band

Thư mục đề xuất:

```text
AI/
└── mel_bins/
```

Các bản thử:

```text
32
64
80
```

Cần so sánh:

- Accuracy;
- F1-score;
- kích thước tensor đầu vào;
- thời gian tạo đặc trưng;
- bộ nhớ.

Mục tiêu:

> Kiểm tra 64 Mel band có đạt cân bằng tốt giữa thông tin đặc trưng và tài nguyên hay không.

---

## 3.6. Tần số lấy mẫu

Thư mục đề xuất:

```text
AI/
└── sample_rate/
```

Các bản thử chính:

```text
8 kHz
16 kHz
```

Cần đo:

- Accuracy;
- F1-score;
- thời gian xử lý;
- kích thước buffer;
- mức sử dụng RAM.

Mục tiêu:

> Kiểm tra 16 kHz có mang lại lợi ích đủ lớn so với cấu hình nhẹ hơn.

---

## 3.7. Độ dài đoạn âm thanh

Thư mục đề xuất:

```text
AI/
└── segment_length/
```

Có thể thử:

```text
3 giây
5 giây
7 giây
```

Cần xem:

- khả năng chứa đủ mẫu âm thanh hô hấp;
- Accuracy/F1;
- thời gian xử lý;
- RAM;
- độ trễ từ lúc bắt đầu đo đến khi có kết quả.

Thí nghiệm này chỉ nên thực hiện nếu còn đủ thời gian vì có thể kéo theo việc tạo lại dữ liệu đầu vào và huấn luyện lại.

---

## 3.8. Kiểm tra chất lượng âm thanh

Thư mục đề xuất:

```text
Firmware_System/
└── quality_gate/
```

So sánh:

```text
Không dùng Quality Gate
Có Quality Gate
```

Tập đánh giá nên có nhiều tình huống:

- im lặng;
- tín hiệu quá nhỏ;
- tín hiệu hợp lệ;
- clipping;
- va chạm ngắn;
- nhiễu môi trường.

Cần đo:

- tỷ lệ chấp nhận audio hợp lệ;
- tỷ lệ loại audio không hợp lệ;
- false accept;
- false reject;
- ảnh hưởng đến kết quả TinyML.

Đây là một trong các thí nghiệm quan trọng vì Quality Gate là một phần của hệ thống, không chỉ là model.

---

## 3.9. Voting

Thư mục đề xuất:

```text
Firmware_System/
└── voting/
```

Các bản thử:

```text
1 lần
3 lần
5 lần
```

Cần so sánh:

- Accuracy/F1;
- độ ổn định kết quả;
- tổng thời gian xử lý;
- tài nguyên;
- năng lượng nếu có điều kiện đo.

Mục tiêu:

> Kiểm tra 3 lần voting hiện tại có đáng với chi phí xử lý tăng thêm hay không.

---

## 3.10. VAD

Thư mục đề xuất:

```text
Firmware_System/
└── vad/
```

Có thể đánh giá:

- số block liên tiếp để xác nhận trigger;
- ngưỡng năng lượng;
- false trigger;
- missed trigger;
- thời gian phản ứng.

Ví dụ thử:

```text
2 block
4 block
6 block
```

Không cần thử quá nhiều tham số cùng lúc.

---

## 3.11. Ngưỡng phân lớp

Thư mục đề xuất:

```text
AI/
└── classification_threshold/
```

Có thể thử trên tập validation:

```text
0.40
0.45
0.50
0.55
0.60
```

Theo dõi:

- Precision;
- Recall;
- F1;
- confusion matrix.

Không chọn ngưỡng bằng tập test cuối.

---

## 3.12. Độ ổn định trên phần cứng thực tế

Thư mục đề xuất:

```text
Firmware_System/
└── hardware_robustness/
```

Đây là nhóm thí nghiệm rất quan trọng đối với Patient Node.

Có thể kiểm thử theo:

### Khoảng cách microphone

```text
gần
trung bình
xa hơn
```

Khoảng cách cụ thể chỉ chốt sau khi có enclosure và cách sử dụng cuối.

### Môi trường

Ví dụ:

- phòng yên;
- có quạt;
- có tiếng nói;
- có TV;
- có tiếng động nền.

### Mức tín hiệu

- nhỏ;
- trung bình;
- lớn;
- clipping.

Theo dõi đồng thời:

- VAD;
- Quality Gate;
- kết quả TinyML;
- thời gian xử lý;
- lỗi runtime nếu có.

Mục tiêu:

> Xác định giới hạn hoạt động thực tế của Patient Node thay vì chỉ đánh giá trên file âm thanh sạch.

---

# 4. Các thí nghiệm ưu tiên

Nếu thời gian NCKH có giới hạn, ưu tiên thực hiện trước:

1. Lượng tử hóa;
2. Bậc Butterworth;
3. Dải band-pass;
4. Pre-emphasis;
5. Quality Gate;
6. Voting;
7. Độ ổn định trên phần cứng thực tế.

Các thí nghiệm còn lại được thực hiện khi có đủ thời gian hoặc khi cần làm rõ thêm một quyết định kỹ thuật.

---

# 5. Cấu trúc mỗi thí nghiệm

Ví dụ với Butterworth:

```text
butterworth_order/
├── butterworth_order.ipynb
│
├── outputs/
│   ├── no_filter/
│   ├── order_3/
│   ├── order_5/
│   └── order_7/
│
└── summary/
    ├── comparison.csv
    ├── metrics.json
    ├── f1_comparison.png
    ├── confusion_matrix.png
    └── README.md
```

### `outputs/`

Chứa kết quả riêng của từng cấu hình.

### `summary/`

Chứa kết quả so sánh cuối cùng giữa các cấu hình.

File `summary/README.md` nên trả lời ngắn gọn:

- đã thử những bản nào;
- kết quả chính;
- phương án nào được chọn;
- lý do chọn;
- giới hạn của phép thử.

---

# 6. Quy ước Notebook

Mỗi notebook nên có các phần:

```text
1. Mục tiêu thí nghiệm
2. Cấu hình giữ nguyên
3. Biến cần thay đổi
4. Tập dữ liệu sử dụng
5. Thực hiện
6. Đánh giá
7. Biểu đồ
8. Xuất summary
9. Kết luận
```

Notebook dùng để điều khiển thí nghiệm và trình bày kết quả.

Nếu một hàm xử lý đã có trong `AI_Training_Model` hoặc source dùng chung, nên gọi lại hàm đó thay vì sao chép code sang notebook.

---

# 7. Chỉ số đánh giá chung

Đối với các thí nghiệm AI nên ưu tiên:

```text
Accuracy
Precision
Recall
F1-score
Confusion Matrix
```

Đối với TinyML trên ESP32-S3 cần bổ sung khi phù hợp:

```text
Kích thước model
RAM
Tensor Arena
Thời gian DSP
Thời gian inference
Tổng thời gian pipeline
```

Đối với VAD/Quality Gate:

```text
False Trigger
Missed Trigger
False Accept
False Reject
Trigger Latency
```

Không phải thí nghiệm nào cũng cần dùng toàn bộ các chỉ số trên.

---

# 8. Nguyên tắc quan trọng khi so sánh

Tất cả các phiên bản AI dùng để so sánh phải sử dụng cùng cách chia dữ liệu:

```text
Train
Validation
Test
```

Không được random lại tập dữ liệu riêng cho từng phiên bản rồi so trực tiếp kết quả.

Nếu có augmentation:

- chỉ áp dụng cho Train;
- Validation và Test giữ nguyên theo quy tắc đánh giá đã chốt.

Mỗi lần chỉ nên thay đổi một nhóm tham số chính.

---

# 9. Kiến trúc model

Hiện tại không bắt buộc tạo thêm thí nghiệm lớn để so sánh nhiều kiến trúc mạng.

DS-CNN đã được chọn dựa trên tài liệu tham khảo trước đó và mục tiêu triển khai TinyML.

Trong báo cáo nên mô tả:

> DS-CNN là kiến trúc được lựa chọn cho hệ thống hiện tại, không tuyên bố đây là kiến trúc tốt nhất trong mọi trường hợp.

Nếu còn thời gian, so sánh kiến trúc model có thể được bổ sung như một thí nghiệm mở rộng, nhưng không phải ưu tiên của giai đoạn hiện tại.

---

# 10. Mục tiêu cuối cùng

Các kết quả trong `Node` phải giúp trả lời được:

> Vì sao Patient Node cuối cùng sử dụng cấu hình hiện tại?

Thay vì chỉ trình bày:

```text
Butterworth order 5
Pre-emphasis 0.97
Mel 64
INT8
Voting 3
```

báo cáo cần có cơ sở để nói:

```text
Đã khảo sát các phương án khác
        ↓
Đánh giá bằng cùng dữ liệu và điều kiện
        ↓
So sánh độ chính xác + tài nguyên + độ ổn định
        ↓
Chọn cấu hình cuối
```

Đây là mục tiêu chính của toàn bộ phần `Experiments_Benchmarking/Node`.
