# AI Result Visualizations

Thư mục này chứa các script Python **chỉ đọc artifact/kết quả đã có và vẽ hình** phục vụ
báo cáo, slide hoặc vấn đáp. Các script tại đây không tiền xử lý lại dataset, không train,
không lượng tử hóa và không thay đổi checkpoint/model.

Nhóm này được tách khỏi `Audio_Visualizations`:

- `Audio_Visualizations`: waveform, phổ, Log-Mel và Butterworth trên tín hiệu âm thanh;
- `AI_Result_Visualizations`: accuracy, recall, false negative và confusion matrix của model.

## Thành phần

| Script | Nguồn dữ liệu | Ảnh đầu ra | Mục đích |
|---|---|---|---|
| `Compare_C4_FP32_vs_QAT_INT8.py` | `Frontend_Benchmarking/results/D_Quantization/Test/test_summary.csv` | `C4_V1_s44_FP32_vs_QAT_INT8.png` | So sánh Accuracy, Asthma Recall và số ca Asthma bị bỏ sót của FP32 với QAT INT8 trên tập Test. |
| `Visualize_V2_V3_Confusion_Matrices.py` | `Phase2_Preprocess_&_Traning/Output_Comparison_V2_1_vs_V3_1/metrics_summary.csv` | `V2_V3_Confusion_Matrices_Comparison.png` | Vẽ bốn ma trận nhầm lẫn cho Common RAW và Playback-only của V2.1/V3.1. |

Hai ảnh PNG đi kèm là kết quả đã sinh từ dữ liệu hiện có. Có thể chạy lại script để cập
nhật ảnh khi các CSV nguồn thay đổi.

## Cách chạy

Mở PowerShell tại root repository.

### So sánh FP32 và QAT INT8 của C4/V1/seed 44

```powershell
py -3.11 .\ESP32_Standalone_Modules_Test\AI_Result_Visualizations\Compare_C4_FP32_vs_QAT_INT8.py
```

Chọn trial hoặc đường dẫn ảnh khác:

```powershell
py -3.11 .\ESP32_Standalone_Modules_Test\AI_Result_Visualizations\Compare_C4_FP32_vs_QAT_INT8.py `
  --trial-id "combo_pre0_mel40_fft2048__V1__s44" `
  --output ".\temp\FP32_vs_QAT.png"
```

### So sánh confusion matrix V2.1 và V3.1

```powershell
py -3.11 .\ESP32_Standalone_Modules_Test\AI_Result_Visualizations\Visualize_V2_V3_Confusion_Matrices.py
```

Chọn CSV hoặc đường dẫn ảnh khác:

```powershell
py -3.11 .\ESP32_Standalone_Modules_Test\AI_Result_Visualizations\Visualize_V2_V3_Confusion_Matrices.py `
  --metrics ".\AI_Training_Model\Phase2_Preprocess_&_Traning\Output_Comparison_V2_1_vs_V3_1\metrics_summary.csv" `
  --output ".\temp\V2_V3_confusion.png"
```

## Phụ thuộc

```text
numpy
pandas
matplotlib
```

Đường dẫn mặc định được xác định từ root repository, vì vậy có thể chạy lệnh từ root mà
không cần sửa biến đường dẫn bên trong script.
