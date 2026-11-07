# Frontend Benchmarking Results

`results/` chứa kế hoạch, summary và báo cáo cấp thí nghiệm. Tensor và model dung lượng lớn nằm trong `../artifacts/`.

| Đường dẫn | Nguồn tạo chính | Chức năng |
|---|---|---|
| `experiment_plan.csv` | `01_Build_Plan.py` | Kế hoạch thí nghiệm, variant và config hash |
| `plan_manifest.json` | `01_Build_Plan.py` | Metadata của kế hoạch |
| `val_summary.csv` | `04_Evaluate.py` | Summary Validation dùng chung cho B/C |
| `test_summary.csv` | `04_Evaluate.py` | Summary Test hậu kiểm dùng chung cho C |
| `A_scientific_frontend_evidence/` | `00_Analyze_Frontend.py`, notebook A | Bằng chứng tín hiệu và hình vẽ |
| `B0_dataset_audit/` | `B0_Dataset_Audit.py` | Audit dataset, nguồn WAV và sample rate |
| `B1_domain_audit/` | `B1_Domain_Validation.py` | Audit Validation theo domain |
| `D_Quantization/` | D0-D2 và notebook D | Plan, report Val/Test và bảng handoff lượng tử |

`C_Sync_24_Checkpoints.py` có thể kiểm tra và đồng bộ hai summary sau khi 24 checkpoint đã tồn tại, nhưng không phải nguồn train model. Luồng chuẩn vẫn là `03_Train.py` rồi `04_Evaluate.py`.

## Kết quả notebook D hiện hành

Notebook `Notebook/05_Quantization_Deployment/D_Quantization_ESP32S3_ThreeLogs_Final.ipynb` đọc kết quả 24 checkpoint FP32, 72 model lượng tử và ba log ESP32-S3 để tạo bảng/hình tổng hợp trong `D_Quantization/`.

Các thư mục như `Full_24_Analysis/` hoặc `Notebook_Analysis/` là output phân tích của những phiên notebook tương ứng. Chỉ dùng chúng khi SHA và trial ID còn khớp với artifact hiện tại.

## Dữ liệu lịch sử

- `C1_before_run_snapshots/` và `C2_C4_before_run_snapshots/`: snapshot tạo bởi runner PowerShell cũ; giữ để truy vết, không còn là bước chạy bắt buộc.
- `D_locked_20/` và `C_D_8x3_analysis/`: output của quy trình cũ; không phải nguồn chuẩn cho notebook hiện hành.

Hai file `val_summary.csv` và `test_summary.csv` là nguồn chuẩn cho notebook C. Không tạo summary song song trong thư mục notebook.

Không sửa thủ công hash, metric hoặc prediction. Nếu model/config thay đổi, phải đánh giá lại bằng script nguồn. Xem luồng hiện hành tại [`../Roadmap_Frontend_A_to_E.md`](../Roadmap_Frontend_A_to_E.md).
