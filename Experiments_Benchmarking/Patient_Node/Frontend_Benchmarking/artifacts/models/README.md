# Models

Thư mục này chứa checkpoint và kết quả Validation/Test theo từng trial.

## Script tạo output

| Script | Output |
|---|---|
| `03_Train.py` | `Model_Asthma.keras`, `history.csv`, `training_metadata.json`, TensorBoard logs |
| `04_Evaluate.py --split val` | `val_predictions.csv`, `val_confusion.json`, `val_classification_report.txt` |
| `04_Evaluate.py --trial-id <trial> --split test` | `test_predictions.csv`, `test_confusion.json`, `test_classification_report.txt` |

## Cấu trúc một trial

```text
models/
└── <variant>__<architecture>__s<seed>/
    ├── Model_Asthma.keras
    ├── history.csv
    ├── training_metadata.json
    ├── val_predictions.csv
    ├── val_confusion.json
    ├── val_classification_report.txt
    ├── test_predictions.csv
    ├── test_confusion.json
    ├── test_classification_report.txt
    └── logs/
        ├── train/
        └── validation/
```

## Ý nghĩa các file

| File | Chức năng |
|---|---|
| `Model_Asthma.keras` | Best checkpoint Keras theo Validation loss |
| `history.csv` | Loss/metric theo từng epoch |
| `training_metadata.json` | Trial ID, seed, builder/config hash, recipe, dataset fingerprint, scaler và thời gian train |
| `val_predictions.csv` | `p_non_asthma`, nhãn thật và nhãn dự đoán theo từng WAV Validation |
| `val_confusion.json` | Ma trận nhầm lẫn Validation |
| `val_classification_report.txt` | Accuracy, precision, recall và F1 của Validation |
| `test_predictions.csv` | `p_non_asthma`, nhãn thật và nhãn dự đoán theo từng WAV historical Test |
| `test_confusion.json` | Ma trận nhầm lẫn historical Test |
| `test_classification_report.txt` | Accuracy, precision, recall và F1 của historical Test |
| `logs/` | Event TensorBoard do callback trong `03_Train.py` tạo |

## Vai trò trong pipeline

- Notebook B/C đọc kết quả Validation tại đây để phân tích candidate và seed.
- `04_Evaluate.py` chỉ cho đánh giá Test khi truyền `--trial-id` rõ ràng.
- `D0_Build_Quantization_Plan.py` kiểm toán checkpoint/hash trước khi lập kế hoạch lượng tử hóa.

Không dùng trực tiếp `Model_Asthma.keras` trong ESP32. Artifact firmware phải được xuất từ TFLite đã lượng tử ở mục D.

