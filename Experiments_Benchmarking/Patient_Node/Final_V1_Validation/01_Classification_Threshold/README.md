# 01 — Classification Threshold

## Mục tiêu

Chọn và freeze vùng hậu xử lý cho Patient Node FINAL V1:

```text
p_non_asthma <= LOW       -> ASTHMA
LOW < p_non_asthma < HIGH -> UNSURE
p_non_asthma >= HIGH      -> NON-ASTHMA
```

Model vẫn là binary `0=Asthma`, `1=Non-Asthma`; `UNSURE` chỉ được tạo sau
inference.

## Baseline cố định

- Dataset: Dataset V2 và split hiện hành.
- Feature: `Phase2_Preprocess_&_Traning/Output_Preprocess/`.
- Architecture: V1 SepConv2D + Flatten.
- Quantization: PTQ Full INT8.
- Model: `V1_PTQ_INT8.tflite`.
- Normalization: `TRAIN_MIN/TRAIN_MAX` của V1.
- Không train lại và không preprocess lại WAV.

## Thành phần

| File | Vai trò |
|---|---|
| `Generate_Predictions.py` | Normalize, quantize, invoke V1 PTQ INT8 và xuất prediction từng sample. |
| `threshold_utils.py` | Áp dụng LOW/HIGH, tính metric, sweep và export config. |
| `Threshold_Selection.ipynb` | Điều phối thí nghiệm và ghi kết luận. |
| `results/` | CSV/JSON sinh ra khi chạy. |
| `figures/` | Biểu đồ phân tích Validation. |

## Luồng của `Generate_Predictions.py`

Script đọc trực tiếp `X_val_mel.npy` hoặc `X_test_mel.npy` đã được tạo ở Phase
2. Nó không đọc lại WAV và không chạy lại preprocessing:

```text
X_<split>_mel.npy
-> normalize theo TRAIN_MIN/TRAIN_MAX của V1
-> quantize theo input scale/zero-point của V1 PTQ INT8
-> invoke V1_PTQ_INT8.tflite
-> dequantize output INT8
-> p_non_asthma từng sample
-> ghép với Y_<split>_mel.npy và Files_<split>.npy
-> prediction CSV + metadata JSON
```

## Kỷ luật Validation/Test

```text
Validation
-> so sánh candidate
-> grid sweep
-> chọn duy nhất LOW/HIGH
-> export final_threshold.json với status=FROZEN
-> Test đúng một lượt cuối
```

`Generate_Predictions.py --split test` sẽ từ chối chạy nếu chưa có
`results/final_threshold.json` ở trạng thái `FROZEN`.

## Cách chạy chi tiết

Không chạy trực tiếp `threshold_utils.py`. Đây là thư viện hàm để notebook
import. Luồng sử dụng chính gồm năm bước dưới đây.

### Bước 0 — Kiểm tra Python

Máy hiện tại có Python 3.14 và Python 3.11. TensorFlow nằm trong Python 3.11,
vì vậy phải ghi rõ `py -3.11`; lệnh `py` không ghi version sẽ gọi Python 3.14
và báo `No module named 'tensorflow'`.

Từ thư mục gốc repository, kiểm tra một lần:

```powershell
py -3.11 -c "import sys, tensorflow as tf; print(sys.executable); print(tf.__version__)"
```

Kết quả phải chỉ tới:

```text
C:\Users\nguye\AppData\Local\Programs\Python\Python311\python.exe
```

Khi mở notebook cũng phải chọn đúng Python 3.11 làm kernel.

Cell Setup dùng `os.getcwd()` rồi dò ngược qua các thư mục cha để tìm folder
`01_Classification_Threshold`. Vì notebook không có biến `__file__`, đây là cách
linh động khi VS Code/Jupyter đặt working directory ở repo root, một folder trung
gian hoặc ngay tại folder experiment.

### Bước 1 — Sinh prediction cho Validation

Chạy:

```powershell
py -3.11 "Experiments_Benchmarking/Patient_Node/Final_V1_Validation/01_Classification_Threshold/Generate_Predictions.py" --split val
```

Tác dụng:

1. Đọc `X_val_mel.npy`, `Y_val_mel.npy` và `Files_val.npy`.
2. Kiểm tra đúng 38 Asthma + 116 Non-Asthma = 154 mẫu.
3. Normalize bằng tham số của V1.
4. Quantize và chạy `V1_PTQ_INT8.tflite`.
5. Lưu xác suất của từng sample.

Sau bước này phải có:

```text
results/validation_predictions.csv
results/validation_predictions_metadata.json
```

Metadata lưu model SHA-256, normalization và quantization parameters để truy
vết đúng baseline. Chạy lại cùng artifact sẽ ghi lại hai file này một cách
reproducible.

> Có thể bỏ qua command trên và chạy cell 0–1 của notebook; cell 1 sẽ tự gọi
> `generate_predictions("val")` nếu chưa có CSV. Chạy command trước giúp tách rõ
> bước inference khỏi bước phân tích.

### Bước 2 — Phân tích và so sánh threshold bằng notebook

Mở `Threshold_Selection.ipynb`, chọn kernel Python 3.11 rồi chạy tuần tự:

| Mục | Tác dụng | Artifact |
|---|---|---|
| `0. Experiment Setup` | Khai báo đường dẫn và import hai module Python. | Không |
| `1. Load Validation Predictions` | Đọc CSV/metadata Validation. | Không |
| `2. Distribution Analysis` | Vẽ phân bố `p_non_asthma` của hai lớp. | `figures/validation_probability_distribution.png` |
| `3. Candidate Threshold Comparison` | So sánh các cặp LOW/HIGH được đề xuất. | `results/candidate_threshold_comparison.csv` |
| `4. Threshold Grid Sweep` | Quét lưới threshold chỉ trên Validation và xếp hạng. | `results/threshold_grid_sweep.csv` |

Không bấm `Run All` ngay. Notebook cố ý đặt `FINAL_LOW = None` và
`FINAL_HIGH = None` để dừng trước khi tự động freeze một cấu hình chưa được xem
xét.

Ở bảng kết quả, ưu tiên đọc:

```text
asthma_miss_rate
asthma_unsure_rate
non_asthma_false_alarm_rate
overall_unsure_rate
asthma_recall
asthma_f1
accepted_accuracy
```

`duplicate_decision_pattern=true` nghĩa là cặp threshold đó tạo cùng quyết định
với một cặp đã có do output INT8 chỉ có số mức xác suất hữu hạn.

### Bước 3 — Chọn và kiểm tra LOW/HIGH cuối trên Validation

Tại mục `5. Final Threshold Selection`, điền cặp đã chọn và lý do. Ví dụ định
dạng, không phải giá trị bắt buộc:

```python
FINAL_LOW = 0.45
FINAL_HIGH = 0.65
SELECTION_NOTE = "Giảm Asthma miss nhưng vẫn giữ Unsure và false alarm ở mức chấp nhận được."
```

Chạy cell và xem:

- metric Validation của đúng cặp vừa nhập;
- các sample `WRONG`;
- các sample `UNSURE`.

Nếu chưa chấp nhận, thay LOW/HIGH và chạy lại mục 5. Chưa chạy mục 6 trong lúc
còn cân nhắc.

### Bước 4 — Freeze cấu hình

Khi đã chốt bằng Validation, chạy mục `6. Export FINAL Config`.

Notebook tạo:

```text
results/validation_predictions_final.csv
results/final_threshold.json
```

`final_threshold.json` có `status=FROZEN`, model hash, LOW/HIGH, output
scale/zero-point, metric Validation và lý do lựa chọn. Từ thời điểm này không
đổi threshold dựa trên Test.

### Bước 5 — Đánh giá Test đúng một lần

Cách khuyến nghị: chạy mục `7. Final Test Evaluation` trong notebook. Cell này
sẽ tự động:

1. Kiểm tra `final_threshold.json` đã `FROZEN`.
2. Sinh prediction Test nếu chưa có.
3. Kiểm tra đúng 38 Asthma + 121 Non-Asthma = 159 mẫu.
4. Áp dụng đúng LOW/HIGH đã freeze.
5. Xuất kết quả cuối.

Kết quả:

```text
results/test_predictions.csv
results/test_predictions_metadata.json
results/final_test_result.csv
results/final_test_metrics.csv
results/final_test_metrics.json
```

Nếu chỉ muốn sinh prediction Test bằng terminal sau khi đã freeze:

```powershell
py -3.11 "Experiments_Benchmarking/Patient_Node/Final_V1_Validation/01_Classification_Threshold/Generate_Predictions.py" --split test
```

Lệnh terminal chỉ sinh prediction. Sau đó vẫn phải chạy mục 7 trong notebook để
áp dụng LOW/HIGH và xuất metric cuối.

Cuối cùng sửa phần Markdown `8. Conclusion` để ghi LOW/HIGH, metric Validation,
metric Test, quyết định chấp nhận và giới hạn đã biết.

## Artifact dự kiến

```text
results/
|-- validation_predictions.csv
|-- validation_predictions_metadata.json
|-- candidate_threshold_comparison.csv
|-- threshold_grid_sweep.csv
|-- validation_predictions_final.csv
|-- final_threshold.json
|-- test_predictions.csv
|-- test_predictions_metadata.json
|-- final_test_result.csv
|-- final_test_metrics.csv
`-- final_test_metrics.json
```

## Metric bắt buộc

- Asthma Precision, Recall và F1.
- `Asthma -> Non-Asthma` miss rate.
- `Asthma -> Unsure` rate.
- `Non-Asthma -> Asthma` false-alarm rate.
- Overall Unsure Rate.
- Coverage và accuracy trên các mẫu không Unsure.

Không chọn LOW/HIGH chỉ bằng accuracy tổng.
