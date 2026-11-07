# Calibration Results và phân tích playback domain

Tài liệu này mô tả output của dự án `Asthma_Playback_Calibration` và tổng hợp kết luận
từ hai phép thử:

1. calibration vật lý `WAV -> loa -> phòng -> INMP441 -> ESP32/Python`;
2. đối chứng model V2_1 có playback với V3_1 không playback.

## 1. Phạm vi dữ liệu

Calibration vật lý gồm:

- 3 WAV Asthma và 3 WAV Non-Asthma;
- mỗi WAV được phát lại 3 lần;
- tổng cộng 18 capture, mỗi capture 5 giây, mono PCM16 16 kHz;
- model đánh giá: V1 PTQ INT8;
- ba trạng thái: Asthma khi `p_non <= 0.20`, Non-Asthma khi `p_non >= 0.95`, còn lại
  là Unsure.

Danh sách WAV nguồn nằm trong
`Experiments_Benchmarking/Patient_Node/Final_V1_Validation/01_Classification_Threshold/Playback_Calibration/`.

## 2. Cấu trúc output

```text
calibration_results/
├── playback_calibration_results.csv
├── captures/
│   ├── Asthma/                      9 WAV capture
│   └── Non_Asthma/                  9 WAV capture
└── offset_analysis/
    └── <source_stem>/
        ├── capture_offset_results.csv
        ├── waveform_alignment.png
        ├── cross_correlation.png
        ├── summary.md
        └── shift_vs_capture/
            ├── shift_vs_capture_results.csv
            ├── shift_vs_capture_probability.png
            ├── shifted_original_crops/
            └── summary.md
```

### `playback_calibration_results.csv`

| Cột | Ý nghĩa |
|---|---|
| `file` | Đường dẫn tương đối của WAV nguồn calibration |
| `true_class` | `Asthma` hoặc `Non_Asthma` |
| `trial` | Lần phát 1, 2 hoặc 3 |
| `p_non_original_python` | Xác suất Non-Asthma của WAV gốc trên Python V1 PTQ |
| `p_non_capture_python` | Xác suất của capture loa -> INMP441 trên Python |
| `p_non_esp32` | Xác suất do ESP32 tính trên đúng capture đó |
| `pcm_rms` | RMS PCM16 của capture |
| `pcm_peak` | Peak tuyệt đối PCM16 của capture |
| `capture_file` | WAV capture tương ứng |

### `capture_offset_results.csv`

Lưu offset raw/capture theo sample, giây và mili giây; NCC; `p_non` Python/ESP32 và
đường dẫn capture. Quy ước offset là vị trí trong WAV gốc tương ứng với mẫu đầu tiên
của capture.

### `shift_vs_capture_results.csv`

Lưu kết quả tách nguyên nhân bằng cách so WAV gốc crop tại đúng offset với capture thật.
Hai cột quan trọng:

- `delta_shifted_minus_original`: ảnh hưởng của dịch cửa sổ;
- `delta_capture_minus_shifted`: phần chênh còn lại sau đường loa/phòng/micro.

## 3. Kết quả calibration vật lý

### Tổng hợp theo file

| File | Class | Mean `p_non` capture | Khoảng 3 trial | Mean `p_non` ESP32 | Mean PCM RMS |
|---|---|---:|---:|---:|---:|
| `01__P47WheezingRS_232.wav` | Asthma | 0.743490 | 0.582031-0.957031 | 0.725260 | 1605.071 |
| `02__P17WheezingIE_85.wav` | Asthma | 0.688802 | 0.539062-0.906250 | 0.664063 | 965.059 |
| `03__P47WheezingRL_235.wav` | Asthma | 0.095052 | 0.039063-0.187500 | 0.110677 | 498.417 |
| `01__P47COPDMc_372.wav` | Non-Asthma | 0.996094 | 0.996094-0.996094 | 0.996094 | 1953.251 |
| `02__P47COPDPr_371.wav` | Non-Asthma | 0.996094 | 0.996094-0.996094 | 0.996094 | 903.916 |
| `03__P8Pneumonia28V.wav` | Non-Asthma | 0.985677 | 0.976563-0.996094 | 0.979167 | 446.308 |

Theo ngưỡng ba trạng thái:

- 9 trial Asthma: 3 Asthma, 5 Unsure, 1 Non-Asthma;
- 9 trial Non-Asthma: 9 Non-Asthma;
- mean `p_non` Asthma tăng từ `0.000000` ở WAV gốc lên `0.509115` ở capture;
- mean `p_non` Non-Asthma gần như giữ nguyên: `0.993490` -> `0.992622`.

Kết quả cho thấy domain shift không đối xứng trong mẫu calibration này: đường truyền
âm học làm hai source Asthma 01/02 thay đổi mạnh, trong khi source Asthma 03 và cả ba
source Non-Asthma ổn định hơn.

### Python và ESP32 có khớp không?

Trên cùng 18 capture:

- mean absolute error giữa `p_non_capture_python` và `p_non_esp32`: `0.022569`;
- riêng Asthma: `0.042969`;
- riêng Non-Asthma: `0.002170`;
- sai khác lớn nhất của một trial: `0.121094`.

Hai pipeline nhìn chung bám nhau, đặc biệt với Non-Asthma. Vì vậy hiện tượng
`p_non_asthma` tăng mạnh trên Asthma capture không chủ yếu do Python và C++ dùng hai
pipeline hoàn toàn khác nhau. Chênh nhỏ còn lại có thể đến từ sai số lượng tử và chi
tiết số học DSP.

## 4. Offset và tách nguyên nhân

| Asthma source | Offset mean | Std | Spread | NCC nhỏ nhất | Shifted mean | Capture mean | Nhận định |
|---|---:|---:|---:|---:|---:|---:|---|
| `01__P47WheezingRS_232` | 96.188 ms | 36.609 ms | 87.625 ms | 0.549337 | 0.000000 | 0.743490 | Acoustic path chiếm ưu thế |
| `02__P17WheezingIE_85` | 72.979 ms | 14.074 ms | 32.813 ms | 0.562397 | 0.005208 | 0.688802 | Acoustic path chiếm ưu thế |
| `03__P47WheezingRL_235` | 80.229 ms | 4.748 ms | 11.562 ms | 0.168340 | 0.001302 | 0.095052 | Chưa tách bạch hoàn toàn; source vẫn khá ổn định |

Với source 01 và 02, crop WAV gốc theo đúng offset vẫn được model nhận gần Asthma,
nhưng capture thật tăng `p_non` rất mạnh. Do đó lệch VAD/window không giải thích được
phần lớn lỗi; biến đổi do loa, đáp ứng tần số, khoảng cách, phòng và INMP441 là nguyên
nhân thực nghiệm nổi trội hơn.

Source 03 không bị flip mạnh. Hai trial có NCC thấp, nên không nên dùng riêng source
này để phủ định kết luận của source 01/02 hoặc để khẳng định quan hệ nhân quả.

## 5. Playback tạo thêm domain gì trong dataset?

Phép đối chứng sử dụng cùng kiến trúc V1:

- `V2_1_With_Playback`: train trên Dataset V2 có playback;
- `V3_1_No_Playback`: train trên Dataset V3 đã loại playback;
- Common Raw Test: 143 mẫu, gồm 30 Asthma và 113 Non-Asthma;
- Playback-only Test: 16 mẫu bị loại khỏi V3, gồm 8 Asthma và 8 Non-Asthma.

Nguồn số liệu:
[Output_Comparison_V2_1_vs_V3_1](../../../AI_Training_Model/Phase2_Preprocess_&_Traning/Output_Comparison_V2_1_vs_V3_1/Comparison_Report.md).

### Common Raw Test

| Metric | V2 có playback | V3 không playback |
|---|---:|---:|
| Accuracy | 0.881119 | 0.923077 |
| Asthma Precision | 0.658537 | 0.771429 |
| Asthma Recall | 0.900000 | 0.900000 |
| Asthma F1 | 0.760563 | 0.830769 |
| Non-Asthma Recall | 0.876106 | 0.929204 |
| Confusion matrix | `[[27,3],[14,99]]` | `[[27,3],[8,105]]` |

Ở lần train hiện tại, bỏ playback giúp common raw accuracy tăng khoảng `4.20` điểm
phần trăm và giảm Non-Asthma bị nhầm thành Asthma từ 14 xuống 8, trong khi Asthma
recall giữ nguyên 0.90.

### Playback-only Test

| Metric | V2 có playback | V3 không playback |
|---|---:|---:|
| Accuracy | 1.000000 | 0.750000 |
| Asthma Recall | 1.000000 | 0.500000 |
| Asthma F1 | 1.000000 | 0.666667 |
| Non-Asthma Recall | 1.000000 | 1.000000 |
| Confusion matrix | `[[8,0],[0,8]]` | `[[4,4],[0,8]]` |

Playback trong Train tạo lợi ích rõ ràng trên playback-only cùng kiểu thu: model V2
nhận đủ 16/16, còn model V3 bỏ sót 4/8 Asthma playback.

### Kết luận về domain

Playback không chỉ là bản sao của raw. Nó tạo một domain mới bao gồm đặc tính của:

```text
source WAV + loa + âm lượng + khoảng cách + phòng + INMP441 + VAD/window
```

Dữ liệu hiện tại cho thấy một trade-off:

- thêm playback cải thiện mạnh in-domain playback;
- nhưng trong một lần train này, common raw generalization giảm;
- model có playback vẫn không bất biến với một phiên playback vật lý mới: hai trong
  ba source Asthma calibration bị đẩy phần lớn vào Unsure/Non-Asthma;
- vì vậy model có thể đang học một phần fingerprint của setup playback đã thu, không
  phải tính bất biến loa-micro tổng quát.

Nếu mục tiêu cuối là âm hô hấp thật thu trực tiếp bằng Patient Node, raw bệnh nhân và
recording thật qua đúng micro phải là domain chính. Playback nên được xem là domain
robustness/benchmark, không phải dữ liệu thay thế cho bệnh nhân thật.

Nếu tiếp tục đưa playback vào train, cần:

1. tách Train/Val/Test theo **capture session/setup**, không chỉ theo raw source;
2. để loa, phòng, khoảng cách hoặc thiết bị chưa thấy xuất hiện trong Val/Test;
3. không cho `take01/take02` cùng setup rơi sang nhiều split;
4. giới hạn tỷ trọng playback để không lấn át raw;
5. benchmark riêng raw, playback seen-domain và playback unseen-domain;
6. lặp lại nhiều seed trước khi kết luận playback chắc chắn làm giảm raw generalization.

## 6. Giới hạn của kết luận

- Playback-only Test chỉ có 16 mẫu.
- Calibration vật lý chỉ có 6 source và 18 trial, trong đó chỉ 3 source Asthma.
- Kết quả hiện tại đến từ một setup loa/phòng/micro và một lần train cho mỗi dataset.
- `p_non` INT8 có độ phân giải rời rạc; thay đổi nhỏ không nên được diễn giải quá mức.
- Cross-correlation đo alignment, không cô lập hoàn toàn đáp ứng tần số, gain, clipping,
  reverberation hoặc nhiễu nền.

Vì vậy các số liệu đủ để xác nhận có domain shift và định hướng thí nghiệm tiếp theo,
nhưng chưa đủ để khẳng định quan hệ nhân quả tuyệt đối hoặc thay thế đánh giá trên dữ
liệu người bệnh thật.
