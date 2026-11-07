# D Quantization Artifacts

Thư mục này chứa model lượng tử và kết quả đánh giá của bước D.

## Script tạo output

| Script | Nhiệm vụ |
|---|---|
| `D1_Quantize.py` | Tạo PTQ/QAT TFLite, QAT checkpoint/log và conversion metadata |
| `D2_Evaluate_Quantized.py` | Chạy Keras FP32 và các TFLite trên Validation/historical Test, xuất metric/report |

D0 tạo kế hoạch tại `results/D_Quantization/`; D3 đọc model từ đây nhưng ghi header sang `../D_Deployment/`.

## Cấu trúc theo trial

```text
D_Quantization/
├── <trial_id>/
│   ├── methods/
│   │   ├── PTQ_INT8/
│   │   ├── QAT_INT8/
│   │   └── PTQ_INT16x8/
│   ├── qat/
│   └── evaluation/
│       ├── KERAS_FP32/
│       ├── PTQ_INT8/
│       ├── QAT_INT8/
│       └── PTQ_INT16x8/
└── Combined_Evaluation/
```

## `methods/<method>/`

Được tạo bởi `D1_Quantize.py`.

| File | Chức năng |
|---|---|
| `<method>.tflite` | Model TFLite đã lượng tử |
| `conversion_metadata.json` | Method, model hash, plan hash, normalization, representative set và thông số I/O |

Các method hiện hành:

- `PTQ_INT8`: full integer INT8 sau train;
- `QAT_INT8`: fine-tune có nhận thức lượng tử rồi xuất full INT8;
- `PTQ_INT16x8`: INT8 weight với activation/I/O INT16, không thay thế trực tiếp firmware INT8.

## `qat/`

Chỉ được D1 tạo khi plan bật `QAT_INT8`.

| File | Chức năng |
|---|---|
| `QAT_Model.keras` | Checkpoint Keras sau QAT |
| `QAT_Training_Log.csv` | Lịch sử fine-tune QAT |
| `QAT_Metadata.json` | Cấu hình, bridge check và metadata QAT |

## `evaluation/<method>/`

Được tạo bởi `D2_Evaluate_Quantized.py`. `KERAS_FP32` là mốc đối chứng trước lượng tử.

Với mỗi split `val` hoặc `test` có:

| File | Chức năng |
|---|---|
| `<split>_predictions.csv` | Probability và prediction theo từng WAV |
| `<split>_metrics.json` | Metrics, confusion matrix, model hash và plan hash |
| `<split>_confusion_matrix.csv` | Ma trận nhầm lẫn hai lớp |
| `<split>_classification_report.csv` | Report dạng bảng cho xử lý tự động |
| `<split>_classification_report.txt` | Report dạng văn bản để đọc nhanh |

## `Combined_Evaluation/`

Đây là output gộp của D2 cho mọi trial/method. Xem [`Combined_Evaluation/README.md`](Combined_Evaluation/README.md).

Không chọn model chỉ bằng kích thước hoặc Accuracy. Notebook D phải xem đồng thời Asthma Recall/F1, confusion matrix, probability delta, kiểu I/O và khả năng triển khai phần cứng.

> Lưu ý tương thích: một số JSON/metadata đã sinh trước khi đổi tên workflow có
> thể còn lưu nhãn hoặc đường dẫn tuyệt đối bắt đầu bằng `E_`. Không sửa tay các
> file này vì chúng tham gia kiểm tra SHA. `D0_Build_Quantization_Plan.py` chỉ
> tái sử dụng chúng khi checkpoint, cấu hình, method và toàn bộ SHA nguồn vẫn
> trùng khớp; muốn làm sạch hoàn toàn metadata thì phải tạo plan D mới và chạy
> lại D1-D2.

