# Combined Evaluation

Thư mục này được tổng hợp bởi `D2_Evaluate_Quantized.py` sau khi các trial/method đã có kết quả đánh giá hợp lệ.

## Các file

| File | Nội dung |
|---|---|
| `Validation_All_Models_Predictions.csv` | Prediction Validation của toàn bộ FP32 và quantized model, có cột trial/method để phân biệt |
| `Test_All_Models_Predictions.csv` | Prediction historical Test của toàn bộ model |
| `Validation_All_Models_Report.txt` | Classification report và confusion matrix Validation ghép theo từng model |
| `Test_All_Models_Report.txt` | Classification report và confusion matrix historical Test ghép theo từng model |

## Cách tạo lại

Chạy inference đầy đủ:

```powershell
py -3.11 .\D2_Evaluate_Quantized.py --split both
```

Chỉ dựng lại report/CSV tổng hợp từ các metrics đã có, không inference:

```powershell
py -3.11 .\D2_Evaluate_Quantized.py --report-only --split both
```

Notebook D đọc các file tại đây để so sánh đồng nhất giữa Keras FP32, PTQ INT8, QAT INT8 và PTQ INT16x8.

