# Roadmap Frontend Benchmarking A đến F

Tài liệu này tóm tắt thứ tự thực hiện. Hướng dẫn lệnh đầy đủ nằm tại [`README.md`](README.md).

## Luồng nghiên cứu

```text
A: cơ sở DSP/F0
-> B: OFAT từng tham số
-> C: factorial 8 cấu hình x 3 seed
-> D: lượng tử hóa và profiling ESP32-S3
-> E: kiểm chứng cuối, chốt model
-> F: tổng hợp báo cáo nghiên cứu
```

## A - Cơ sở DSP

Chạy phân tích nguồn khi cần tái tạo bảng/hình:

```powershell
py -3.11 .\00_Analyze_Frontend.py
```

Notebook:

```text
Notebook/01_Baseline_DSP/A_F0_s42_Baseline_DSP_Foundation.ipynb
```

## B - OFAT

```powershell
py -3.11 .\B0_Dataset_Audit.py
py -3.11 .\01_Build_Plan.py
py -3.11 .\B1_Preflight.py
py -3.11 .\02_Preprocess.py
py -3.11 .\03_Train.py --architecture V1 --seed 42 --epochs 100 --batch-size 32
py -3.11 .\04_Evaluate.py --architecture V1 --seed 42 --split val
py -3.11 .\B1_Domain_Validation.py --architecture V1
```

Notebook:

```text
Notebook/02_Dataset_Audit/B0_SampleRate_Source_Audit.ipynb
Notebook/03_OFAT_Exploration/B_F0_OFAT_9Trials_Conclusion.ipynb
```

## C - 24 checkpoint FP32

Sau khi bật đúng tám candidate C trong `configs/candidates.csv`:

```powershell
py -3.11 .\01_Build_Plan.py
py -3.11 .\02_Preprocess.py
py -3.11 .\03_Train.py --architecture V1 --seed 42 --epochs 100 --batch-size 32
py -3.11 .\03_Train.py --architecture V1 --seed 43 --epochs 100 --batch-size 32
py -3.11 .\03_Train.py --architecture V1 --seed 44 --epochs 100 --batch-size 32
```

Validation và Test dùng `04_Evaluate.py`; Test luôn chỉ rõ trial:

```powershell
py -3.11 .\04_Evaluate.py --trial-id combo_pre0_mel40_fft2048__V1__s44 --split val
py -3.11 .\02_Preprocess.py --include-test
py -3.11 .\04_Evaluate.py --trial-id combo_pre0_mel40_fft2048__V1__s44 --split test
```

`--include-test` chỉ tạo tensor Test sau khi checkpoint/candidate cần hậu kiểm đã được xác định; không dùng kết quả này để tối ưu ngược bước B/C.

Audit tùy chọn sau khi đủ C24:

```powershell
py -3.11 .\Notebook\04_Fontend_Selection\C_Sync_24_Checkpoints.py --fingerprint-only
```

Notebook:

```text
Notebook/04_Fontend_Selection/C_Factorial_8x3_C4_Selection.ipynb
```

## D - Quantization

```powershell
py -3.11 .\D0_Build_Quantization_Plan.py --all-c-checkpoints --force-plan
py -3.11 .\D1_Quantize.py
py -3.11 .\D2_Evaluate_Quantized.py --split both
```

Notebook:

```text
Notebook/05_Quantization_Deployment/D_Quantization_ESP32S3_ThreeLogs_Final.ipynb
```

Xuất model được chọn:

```powershell
py -3.11 .\D3_Export_Deployment.py --trial-id combo_pre0_mel40_fft2048__V1__s44 --method QAT_INT8 --array-name asthma_model
```

## E - Verify

Notebook E đọc kết quả FP32, lượng tử và log profiling. F0/Pre0 được hậu kiểm trên seed 40-46; E không mở thêm vòng tìm kiếm hyperparameter.

```text
Notebook/06_Final_Verifycation/E_Final_Verification_and_Model_Selection.ipynb

Notebook tổng hợp cuối:

```text
Notebook/07_Research_Synthsis/F_NCKH_Final_Research_Synthesis.ipynb
```

Notebook F không tạo lại model hoặc metric. Nó tổng hợp kết luận và liên kết ngược về đúng notebook A-E để truy vết bằng chứng.
```

## Nguyên tắc

- Script root tạo artifact; notebook chỉ phân tích.
- Seed thay đổi quá trình train, không tạo tensor preprocess riêng.
- Không chỉnh metric/hash bằng tay.
- Không dùng Test để quay lại tối ưu candidate.
- `C_Sync_24_Checkpoints.py` là audit tùy chọn, không phải script train.
- Các runner PowerShell theo đợt đã được loại bỏ; dùng trực tiếp `01` đến `04` để tái lập.
