# Notebook Frontend Benchmarking A-F

Notebook là lớp **phân tích, trực quan hóa và lập luận nghiên cứu**. Chúng đọc artifact do các script tại root `Frontend_Benchmarking` tạo ra; notebook không thay thế preprocess, train, evaluate hoặc quantize.

## Thứ tự hiện hành

| Bước | Notebook | Nguồn chính | Vai trò |
|---|---|---|---|
| A | `01_Baseline_DSP/A_F0_s42_Baseline_DSP_Foundation.ipynb` | Cấu hình F0, archive Phase 2, mô phỏng DSP | Trình bày cơ sở Butterworth, pre-emphasis, STFT, Mel và kiến trúc V1 tham chiếu |
| B0 | `02_Dataset_Audit/B0_SampleRate_Source_Audit.ipynb` | Dataset và `results/B0_dataset_audit/` | Kiểm toán sample rate, nguồn WAV, nhãn và zero-padding |
| B | `03_OFAT_Exploration/B_F0_OFAT_9Trials_Conclusion.ipynb` | `results/val_summary.csv` và prediction OFAT | So sánh từng tham số với baseline F0 |
| C | `04_Fontend_Selection/C_Factorial_8x3_C4_Selection.ipynb` | 24 checkpoint và summary Val/Test | Phân tích 8 cấu hình x 3 seed và lựa chọn C4 |
| D | `05_Quantization_Deployment/D_Quantization_ESP32S3_ThreeLogs_Final.ipynb` | 24 FP32, 72 TFLite và log ESP32-S3 | So sánh lượng tử, lỗi lớp, kích thước và profiling tĩnh |
| E | `06_Final_Verifycation/E_Final_Verification_and_Model_Selection.ipynb` | Kết quả A-D, F0/Pre0 nhiều seed và log board | Kiểm chứng cuối và chốt model triển khai |
| F | `07_Research_Synthsis/F_NCKH_Final_Research_Synthesis.ipynb` | Kết quả A-E và hình Log-Mel C4 tái tạo từ Validation | Tổng hợp luận điểm nghiên cứu và hồ sơ model cuối |

```text
A -> B0/B -> C -> D -> E -> F
```

## Quy tắc chạy

1. Chạy script nguồn ở root `Frontend_Benchmarking` trước notebook.
2. Restart Kernel và chạy cell từ trên xuống dưới.
3. Kiểm tra cell setup đã tìm đúng thư mục `Frontend_Benchmarking`.
4. Nếu thiếu artifact hoặc sai SHA, quay lại script nguồn; không nhập metric thủ công.
5. Không dùng kết quả Test để sửa ngược candidate ở B hoặc C. Test chỉ dùng để hậu kiểm lựa chọn.

## Công cụ phụ của C

`04_Fontend_Selection/C_Sync_24_Checkpoints.py` chỉ dùng để audit/đồng bộ 24 checkpoint đã train:

```powershell
py -3.11 .\Notebook\04_Fontend_Selection\C_Sync_24_Checkpoints.py --fingerprint-only
```

Script này **không train model**. Việc train luôn sử dụng `03_Train.py`; evaluate sử dụng `04_Evaluate.py`.

## Log D và E

- `05_Quantization_Deployment/log/`: log profiling ba ứng viên dùng trong notebook D.
- `06_Final_Verifycation/log/`: log C4/QAT và V3/PTQ dùng cho kiểm chứng cuối.

Các log static profiling chỉ đo `Invoke()` trên tensor có sẵn; không bao gồm microphone, Butterworth, STFT hoặc Log-Mel.

## Hình C4 của F

`07_Research_Synthsis/Plot_C4_LogMel.py` đọc hai WAV bệnh core Validation
(Asthma và Non-Asthma/Bronchial), rồi gọi trực tiếp `frontend_core.py` để tái tạo
một hình Log-Mel hai panel theo đúng cấu hình C4. Script không lấy Playback,
augmentation hoặc environment:

```powershell
py -3.11 .\Notebook\07_Research_Synthsis\Plot_C4_LogMel.py
```

Ảnh được lưu trong `07_Research_Synthsis/figures/` và được liên kết tại mục 7
của notebook F. Script không train hoặc invoke model.

Notebook F chỉ tổng hợp và liên kết tới A-E; nguồn số liệu chuẩn vẫn là artifact/result của từng bước.

Xem lệnh đầy đủ tại:

- [`../README.md`](../README.md)
- [`../Roadmap_Frontend_A_to_E.md`](../Roadmap_Frontend_A_to_E.md)
