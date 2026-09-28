# Patient Node — đặc tả cấu hình FINAL hiện hành

## 1. Vai trò của tài liệu

Tài liệu này mô tả cấu hình Patient Node đang được dùng trong source FINAL.
Đây là nguồn đối chiếu khi kiểm tra firmware, lập báo cáo và xây dựng các thí
nghiệm trong `Experiments_Benchmarking/Patient_Node`.

Một số ngưỡng đang chạy ổn nhưng chưa được chứng minh là tối ưu. Chúng được
đánh dấu `FINAL - cần kiểm chứng`; giá trị hiện hành vẫn được giữ cố định làm
mốc cho đến khi có thí nghiệm chính thức đủ bằng chứng để thay thế.

Pipeline hiện hành:

```text
INMP441
  ↓
Thu 5 giây / VAD và bộ đệm trước kích hoạt
  ↓
Quality Gate
  ↓
Chuẩn hóa biên độ
  ↓
Butterworth band-pass
  ↓
Pre-emphasis
  ↓
Mel-Spectrogram dB
  ↓
Chuẩn hóa và lượng tử INT8
  ↓
DS-CNN
  ↓
Phân lớp / voting
  ↓
Hiển thị và gửi Gateway
```

---

## 2. Quy ước trạng thái

| Trạng thái | Ý nghĩa |
|---|---|
| `FINAL` | Đã khớp với source hiện hành và được đóng băng |
| `FINAL - cần kiểm chứng` | Đang được dùng chính thức nhưng cần thí nghiệm để chứng minh hoặc thay thế |
| `Đo theo từng lần chạy` | Không phải hằng số; phải ghi trong log phép thử |

`FINAL` ở đây có nghĩa là cấu hình sản phẩm hiện hành, không phải tuyên bố tối
ưu tuyệt đối cho mọi bệnh nhân và mọi môi trường.

---

## 3. Phần cứng và cấu hình biên dịch

| Thành phần | Giá trị FINAL | Trạng thái |
|---|---:|---|
| Bo mạch | ESP32-S3, profile `esp32-s3-n16r8v` | FINAL |
| Framework | Arduino trên PlatformIO | FINAL |
| PSRAM | Bật, chế độ `qio_opi` | FINAL |
| Tối ưu biên dịch | `-O3` | FINAL |
| Serial monitor | 115200 baud | FINAL |
| Micro | INMP441 | FINAL |
| I2S BCLK/SCK | GPIO 14 | FINAL |
| I2S WS | GPIO 15 | FINAL |
| I2S SD | GPIO 16 | FINAL |
| I2C SCL | GPIO 7 | FINAL |
| I2C SDA | GPIO 8 | FINAL |
| MAX30102 INT | GPIO 9 | FINAL |
| Nút SLEEP/CHECK/MONITOR | GPIO 6 / 4 / 5 | FINAL |
| OLED | SSD1306, 128 × 64, địa chỉ `0x3C` | FINAL |

Thư viện firmware đang khai báo:

- `TensorFlowLite_ESP32` phiên bản `^1.0.0`;
- `arduinoFFT` phiên bản `^2.0.4`.

Mỗi báo cáo phần cứng vẫn phải ghi phiên bản thực tế mà PlatformIO đã giải
quyết tại thời điểm build.

---

## 4. Thu âm

| Thông số | Giá trị FINAL | Trạng thái |
|---|---:|---|
| Tần số lấy mẫu | 16.000 Hz | FINAL |
| Số kênh | Mono, kênh I2S phải | FINAL |
| Dữ liệu I2S nhận | 32 bit/mẫu | FINAL |
| Chuyển về PCM | Dịch phải 16 bit, giới hạn về `int16_t` | FINAL |
| Hệ số khuếch đại phần mềm | 1 | FINAL |
| Kích thước một chunk | 256 mẫu, khoảng 16 ms | FINAL |
| Số DMA buffer | 8 | FINAL |
| Độ dài một đoạn | 5 giây | FINAL |
| Tổng số mẫu | 80.000 | FINAL |

CHECK thu thẳng một đoạn 5 giây, không dùng VAD và không dùng bộ đệm trước
kích hoạt. MONITOR dùng VAD và bộ đệm trước kích hoạt như mục 11.

---

## 5. Tiền xử lý âm thanh

### 5.1. Chuẩn hóa và lọc

| Bước | Giá trị FINAL | Trạng thái |
|---|---:|---|
| Sửa độ dài | Cắt hoặc đệm zero thành 80.000 mẫu | FINAL |
| Chuẩn hóa biên độ | Chia cho trị tuyệt đối lớn nhất của chính đoạn âm thanh, đưa về `[-1,1]` | FINAL |
| Butterworth | Band-pass 100–2000 Hz | FINAL |
| Bậc thiết kế gọi trong Python | 5 | FINAL |
| Bậc hàm truyền thực tế của band-pass | 10 | FINAL |
| Trạng thái lọc đầu đoạn | Toàn bộ bằng 0 | FINAL |
| Pre-emphasis | `y[n] = x[n] - 0,97 × x[n-1]` | FINAL |

Python nhận `order=5`, nhưng bộ lọc band-pass sinh ra có 11 hệ số và bậc hàm
truyền thực tế bằng 10. Khi so sánh bộ lọc phải ghi rõ cả hai thông tin này.

### 5.2. Mel-Spectrogram

| Thông số | Giá trị FINAL | Trạng thái |
|---|---:|---|
| FFT | 1024 điểm | FINAL |
| Độ dài cửa sổ | 1024 mẫu | FINAL |
| Bước dịch | 625 mẫu | FINAL |
| Cửa sổ | Hann tuần hoàn | FINAL |
| `center` | `true` | FINAL |
| Đệm biên | Zero | FINAL |
| Số bin phổ một phía | 513 | FINAL |
| Số dải Mel | 64 | FINAL |
| Số frame | 129 | FINAL |
| Dải Mel | 100–2000 Hz | FINAL |
| Công thức Mel | Slaney, không dùng HTK | FINAL |
| Chuẩn hóa filterbank | Slaney | FINAL |
| Đại lượng phổ | Power, số mũ 2 | FINAL |
| `amin` khi đổi dB | `1e-10` | FINAL |
| Mốc dB | Công suất lớn nhất của từng mẫu | FINAL |
| `top_db` | 80 dB | FINAL |
| Tensor đầu ra | `64 × 129 × 1`, `float32` | FINAL |

Kết quả Mel dB nằm trong khoảng `[-80,0]`. Trước khi đưa vào model, Python và
firmware cùng biến đổi:

```text
normalized = (mel_db - (-80)) / 80
normalized được giới hạn vào [0,1]
```

---

## 6. Dữ liệu huấn luyện

### 6.1. Quy tắc chia

- Seed cố định: `42`.
- Chia theo bệnh nhân trước khi tăng cường.
- Tất cả file của cùng một bệnh nhân chỉ xuất hiện trong một tập.
- Chỉ tăng cường Asthma thuộc train.
- Nhiễu dùng để trộn cho bản tăng cường cũng phải thuộc train.
- Validation và test chỉ giữ file gốc.
- Không chạy lại `train_test_split` trong bước tiền xử lý hoặc huấn luyện.
- Nhãn Python: `0 = Asthma`, `1 = Non-Asthma`.

### 6.2. Số lượng hiện hành

| Tập | Asthma | Non-Asthma | Tổng |
|---|---:|---:|---:|
| Train | 833 | 833 | 1.666 |
| Validation | 30 | 78 | 108 |
| Test | 30 | 83 | 113 |

Validation và test không được tăng cường chỉ để cân bằng số lượng. Nếu dữ liệu
được bổ sung hoặc chia lại thì phải coi đó là một thế hệ dữ liệu mới.

---

## 7. Huấn luyện DS-CNN

| Thành phần | Giá trị FINAL | Trạng thái |
|---|---:|---|
| Input | `64 × 129 × 1` | FINAL |
| Khối 1 | SeparableConv2D 16, kernel `3×3`, ReLU, same + BatchNorm + MaxPool `2×2` | FINAL |
| Khối 2 | SeparableConv2D 32, kernel `3×3`, ReLU, same + BatchNorm + MaxPool `2×2` | FINAL |
| Khối 3 | SeparableConv2D 64, kernel `3×3`, ReLU, same + BatchNorm + MaxPool `2×2` | FINAL |
| Phần cuối | Flatten + Dense 64 ReLU + Dropout 0,3 + Dense 1 Sigmoid | FINAL |
| Hàm lỗi | Binary cross-entropy | FINAL |
| Bộ tối ưu | Adam | FINAL |
| Epoch tối đa | 100 | FINAL |
| Batch size | 32 | FINAL |
| Trọng số lớp | Tính cân bằng từ tập train | FINAL |
| Chọn model | `val_loss` nhỏ nhất | FINAL |
| Dừng sớm | Patience 10, khôi phục trọng số tốt nhất | FINAL |
| Giảm learning rate | Hệ số 0,5; patience 5; nhỏ nhất `1e-6` | FINAL |
| Seed | 42 | FINAL |

Min/max chuẩn hóa chỉ được lấy từ train:

```text
TRAIN_MIN = -80.0
TRAIN_MAX = 0.0
```

---

## 8. Lượng tử hóa và model

| Thành phần | Giá trị FINAL | Trạng thái |
|---|---:|---|
| Kiểu model triển khai | TFLite INT8 toàn phần | FINAL |
| Dữ liệu đại diện | 100 mẫu train, 50 mẫu mỗi lớp | FINAL |
| Input shape | `[1,64,129,1]` | FINAL |
| Input scale | `0.003921568859368563` | FINAL |
| Input zero point | `-128` | FINAL |
| Output shape | `[1,1]` | FINAL |
| Output scale | `0.00390625` | FINAL |
| Output zero point | `-128` | FINAL |
| Kích thước `.tflite` | 543.976 byte | FINAL |
| Tensor Arena | 270 KiB, cấp phát trong PSRAM | FINAL |

Model triển khai:

```text
AI_Training_Model/P3_Quantize_Model/Output_Quantize/Asthma_Model_Int8.tflite
```

SHA-256:

```text
189304263B624C9B1E2A91B050E29535C0256CF0D8CB91BEC9D70549BCF0EF63
```

Nếu hash thay đổi thì phải coi đó là model khác, dù tên file vẫn giống nhau.

---

## 9. Luật phân lớp hiện hành

Đầu sigmoid biểu diễn xác suất của lớp `Non-Asthma`:

```text
p_non_asthma = output sigmoid
p_asthma     = 1 - p_non_asthma
```

Ngưỡng `0,5` chỉ dùng cho báo cáo nhị phân Keras/INT8:

```text
p_non_asthma < 0,5  → Asthma
p_non_asthma ≥ 0,5  → Non-Asthma
```

Firmware sử dụng ba vùng:

| Điều kiện | Kết quả | Mã |
|---|---|---:|
| `p_non_asthma ≤ 0,45` | ASTHMA | 0 |
| `0,45 < p_non_asthma < 0,65` | UNSURE | 2 |
| `p_non_asthma ≥ 0,65` | NON-ASTHMA | 1 |

Hai biên `0,45` và `0,65` có trạng thái **FINAL - cần kiểm chứng**. Thay hai
biên này là xử lý sau suy luận, không bắt buộc huấn luyện lại model.

`UNSURE` không phải lớp thứ ba được model huấn luyện. Giá trị `Unsure_Prob`
hiện tại không được diễn giải như xác suất độc lập của một lớp thứ ba.

---

## 10. Quality Gate hiện hành

| Thông số | Giá trị hiện hành | Trạng thái |
|---|---:|---|
| Kích thước block | 256 mẫu | FINAL |
| RMS tối thiểu | 150 | FINAL - cần kiểm chứng |
| MAV tối thiểu để block được coi là hoạt động | Lớn hơn 80 | FINAL - cần kiểm chứng |
| Tỷ lệ block hoạt động tối thiểu | 5% | FINAL - cần kiểm chứng |
| Mức xác định sample clip | Trị tuyệt đối lớn hơn 32.000 | FINAL - cần kiểm chứng |
| Tỷ lệ sample clip tối đa | 1% | FINAL - cần kiểm chứng |

Thứ tự quyết định:

```text
Active ratio < 5%          → AUDIO_INACTIVE
Clipped ratio > 1%         → AUDIO_TOO_LOUD
RMS < 150                  → AUDIO_TOO_WEAK
Còn lại                    → AUDIO_OK
```

CHECK đưa mẫu lỗi sang trạng thái lỗi và yêu cầu thực hiện lại. MONITOR bỏ mẫu
lỗi, không tăng vote và quay lại lắng nghe.

---

## 11. VAD và MONITOR hiện hành

| Thông số | Giá trị hiện hành | Trạng thái |
|---|---:|---|
| Đại lượng VAD | Trung bình trị tuyệt đối của chunk 256 mẫu | FINAL |
| Ngưỡng kích hoạt | Lớn hơn 75 | FINAL - cần kiểm chứng |
| Số chunk liên tiếp | 4, khoảng 64 ms | FINAL - cần kiểm chứng |
| Warm-up khi bật MONITOR | 100 chunk, khoảng 1,6 giây | FINAL |
| Bộ đệm trước kích hoạt | 16.000 mẫu, 1 giây | FINAL |
| Độ dài đoạn hoàn chỉnh | 80.000 mẫu, 5 giây | FINAL |
| Vote hợp lệ | Chỉ đoạn vượt Quality Gate và suy luận thành công | FINAL |
| Số vote | 3 | FINAL - cần kiểm chứng |

Sau khi VAD kích hoạt, một giây âm thanh trước kích hoạt được đưa vào đầu đoạn
5 giây. Hệ thống thu tiếp tới khi đủ 80.000 mẫu.

Sau mỗi vote hợp lệ, MONITOR tạo lại bộ đệm một giây nhưng không warm-up micro
lần nữa. Sau ba vote:

- lớp có số phiếu lớn nhất được chọn;
- điểm cuối là trung bình điểm của các vote thuộc lớp thắng;
- trường hợp `1-1-1` được kết luận `UNSURE`;
- CHECK không voting, chỉ suy luận một lần.

---

## 12. MAX30102 hiện hành

| Thông số | Giá trị FINAL | Trạng thái |
|---|---:|---|
| Địa chỉ I2C | `0x57` | FINAL |
| Chế độ | SpO2 | FINAL |
| Sample rate cấu hình cảm biến | 100 mẫu/giây | FINAL |
| Trung bình FIFO | 4 mẫu | FINAL |
| Độ rộng xung LED | 411 µs | FINAL |
| Dòng LED RED/IR | `0x24` | FINAL |
| Ngưỡng phát hiện ngón tay IR | 50.000 | FINAL - cần kiểm chứng phần cứng |
| Buffer thuật toán | 100 mẫu | FINAL |
| Mỗi lần cập nhật | 25 mẫu mới | FINAL |
| Tần số dùng trong thuật toán | 25 Hz | FINAL |
| Miền nhịp tim hợp lệ | 40–180 BPM | FINAL |
| Miền SpO2 hợp lệ | 70–100% | FINAL |
| Timeout mẫu | 6.000 ms | FINAL |

Phần MAX30102 phải được kiểm tra bằng module thật; source build thành công chưa
chứng minh độ chính xác sinh hiệu.

---

## 13. Truyền thông Patient Node hiện hành

| Thông số | Giá trị FINAL | Trạng thái |
|---|---:|---|
| ESP-NOW channel | 6 | FINAL |
| Mã hóa ứng dụng | AES-128-GCM | FINAL |
| ESP-NOW peer encryption | Tắt | FINAL |
| Nonce | 12 byte | FINAL |
| Authentication tag | 16 byte | FINAL |
| Secure packet | 56 byte | FINAL |
| Send callback timeout | 1.000 ms | FINAL |
| ACK timeout | 2.000 ms | FINAL |
| Retry delay | 1.000 ms | FINAL |
| Số lần retry tối đa | 3 | FINAL |
| Pending | Tối đa một sự kiện | FINAL |

Địa chỉ MAC, device ID và khóa AES lấy từ cấu hình ghép mạch. Không chép khóa
thật vào báo cáo hoặc log công khai.

---

## 14. Kết quả mốc hiện tại

### 14.1. Model trên tập test 113 mẫu

| Chỉ số | Keras | TFLite INT8 |
|---|---:|---:|
| Accuracy | 86,73% | 92,04% |
| Asthma đúng | 27/30 | 26/30 |
| Non-Asthma đúng | 71/83 | 78/83 |
| Macro F1 | 84,35% | 89,90% |
| Weighted F1 | 87,21% | 92,08% |

Đây là kết quả nhị phân với ngưỡng `0,5`, chưa phải báo cáo cho ba kết quả
ASTHMA/UNSURE/NON-ASTHMA của firmware.

### 14.2. Đối chiếu Python và C++ trên 20 mẫu

| Nội dung | Kết quả |
|---|---:|
| Cùng lớp dự đoán | 20/20 |
| ESP32 đúng nhãn thật | 19/20 |
| Tensor INT8 trùng toàn bộ | 14/20 |

Kết quả trên cho thấy pipeline C++ gần tương ứng Python trên tập đã kiểm. Nó
không chứng minh khả năng tổng quát trên bệnh nhân hoặc môi trường mới.

---

## 15. Quan hệ với kế hoạch kiểm thử

Các phép thử để kiểm chứng hoặc thay đổi cấu hình này nằm tại:

```text
Experiments_Benchmarking/Patient_Node/README.md
```

Khi một thí nghiệm được chấp nhận, phải cập nhật đồng thời:

1. source Patient Node;
2. tài liệu này;
3. kết luận và dữ liệu của thí nghiệm;
4. mã model hoặc SHA-256 nếu model thay đổi.
