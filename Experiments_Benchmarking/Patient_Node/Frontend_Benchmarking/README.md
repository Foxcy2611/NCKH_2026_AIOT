# Frontend Benchmarking - pipeline nghiên cứu A đến F

Thư mục này khảo sát Front-End âm thanh cho mô hình Asthma/Non-Asthma, huấn luyện checkpoint FP32, lượng tử hóa và kiểm chứng khả năng triển khai trên ESP32-S3.

Kết quả hiện tại của nghiên cứu:

- Front-End: **C4** - không pre-emphasis, 40 Mel, FFT 2048, hop 625, Butterworth 100-2000 Hz bậc 5.
- Kiến trúc: **V1 - Separable CNN + Flatten**.
- Checkpoint: `combo_pre0_mel40_fft2048__V1__s44`.
- Phương pháp triển khai được ưu tiên: **QAT INT8**.
- F0 và Pre0 đã được đối chiếu bổ sung trên **7 seed 40-46**.

Historical Test 159 WAV đã được sử dụng trong quá trình phân tích. Vì vậy, kết quả Test tại đây là hậu kiểm trong phạm vi nghiên cứu, không phải external untouched test và không phải bằng chứng chẩn đoán y khoa độc lập.

## 1. Luồng tổng thể

```mermaid
flowchart LR
    A[A - Cơ sở DSP và baseline F0] --> B[B - OFAT từng tham số]
    B --> C[C - 8 cấu hình x 3 seed]
    C --> D[D - PTQ/QAT và ESP32-S3]
    D --> E[E - Kiểm chứng cuối và chốt model]
    E --> F[F - Tổng hợp báo cáo nghiên cứu]
```

| Giai đoạn | Mục tiêu | Nguồn đầu ra chính |
|---|---|---|
| A | Giải thích Butterworth, pre-emphasis, STFT và Mel của F0 | Notebook A, `results/A_scientific_frontend_evidence/` |
| B | OFAT: mỗi lần thay một tham số so với F0 | `artifacts/features/`, `artifacts/models/`, `results/val_summary.csv` |
| C | Khảo sát factorial 8 cấu hình x seed 42/43/44 | 24 checkpoint FP32 và hai summary chuẩn |
| D | Lượng tử 24 checkpoint bằng ba phương pháp, đánh giá Val/Test và profiling tĩnh | `artifacts/D_Quantization/`, `results/D_Quantization/` |
| E | Ghép bằng chứng 7 seed, kiến trúc và log board để chốt nguyên mẫu | Notebook E |
| F | Tổng hợp kết quả A-E thành mạch lập luận cuối, giữ liên kết truy vết nguồn | Notebook F |

## 2. Script chính

Các bước preprocess, train và evaluate phải sử dụng script ở root thư mục này. Không cần runner PowerShell riêng.

| Script | Chức năng |
|---|---|
| `00_Analyze_Frontend.py` | Phân tích waveform, PSD, bandwidth và chi phí Front-End |
| `B0_Dataset_Audit.py` | Kiểm toán WAV nguồn, sample rate, nhãn và padding |
| `01_Build_Plan.py` | Đọc `configs/candidates.csv`, tạo `results/experiment_plan.csv` và config SHA |
| `B1_Preflight.py` | Kiểm tra candidate OFAT của mục B; không dùng để từ chối combination C1-C4 |
| `02_Preprocess.py` | Tạo tensor Train/Validation/Test theo từng `variant_id` |
| `03_Train.py` | Train checkpoint Keras theo kiến trúc, variant và seed |
| `04_Evaluate.py` | Đánh giá Validation/Test, tạo prediction, report và cập nhật summary |
| `B1_Domain_Validation.py` | Audit Validation theo nguồn/domain |
| `D0_Build_Quantization_Plan.py` | Khóa danh sách checkpoint và phương pháp lượng tử |
| `D1_Quantize.py` | Tạo PTQ INT8, PTQ INT16x8 và QAT INT8 |
| `D2_Evaluate_Quantized.py` | Đánh giá Keras/TFLite trên Validation và historical Test |
| `D3_Export_Deployment.py` | Xuất `.tflite` thành header C++ và deployment manifest |

`Notebook/04_Fontend_Selection/C_Sync_24_Checkpoints.py` là công cụ **audit tùy chọn**, không train model. Nó kiểm tra đủ C24, prediction, config/model SHA và dataset fingerprint; chế độ đầy đủ chỉ gọi lại logic chuẩn của `02_Preprocess.py` và `04_Evaluate.py`.

`Legacy_D_Locked_Extended_Evaluate.py` thuộc quy trình D cũ, không nằm trong luồng chính.

## 3. Chuẩn bị môi trường

Mở PowerShell tại `Frontend_Benchmarking`:

```powershell
py -3.11 -m pip install -r .\requirements.txt
```

Dataset mặc định được tự tìm tại:

```text
AI_Training_Model/Dataset_Chia_V2
```

Cấu hình nghiên cứu nằm trong:

- `configs/candidates.csv`: Front-End candidate;
- `configs/D_quantization_methods.csv`: phương pháp lượng tử.

Sau khi thay đổi CSV, luôn tạo lại plan trước khi preprocess hoặc lượng tử.

## 4. Luồng preprocess - train - evaluate chuẩn

### 4.1. Tạo plan

Chỉnh cột `enabled` trong `configs/candidates.csv`, sau đó chạy:

```powershell
py -3.11 .\01_Build_Plan.py
```

Nếu đang làm OFAT ở B:

```powershell
py -3.11 .\B1_Preflight.py
```

Combination C1-C4 thay đổi nhiều tham số nên không thuộc kiểm tra OFAT này.

### 4.2. Preprocess

Preprocess toàn bộ variant đang `enabled=1`:

```powershell
py -3.11 .\02_Preprocess.py
```

Hoặc chỉ preprocess một variant:

```powershell
py -3.11 .\02_Preprocess.py --variant F0
```

Tensor của một variant được dùng chung giữa các seed. Seed chỉ ảnh hưởng quá trình train, không tạo một bản preprocess mới.

Chỉ sau khi đã xác định checkpoint cần hậu kiểm, tạo tensor Test bằng lệnh rõ ràng:

```powershell
py -3.11 .\02_Preprocess.py --include-test
```

Lệnh này chỉ tạo split Test cho các variant đang `enabled=1`; nó không train và không thay đổi trọng số model.

### 4.3. Train

Train tất cả variant đang bật ở một seed:

```powershell
py -3.11 .\03_Train.py --architecture V1 --seed 42 --epochs 100 --batch-size 32
```

Train một variant cụ thể, kể cả khi hiện đang `enabled=0`:

```powershell
py -3.11 .\03_Train.py --architecture V1 --variant F0 --seed 42 --epochs 100 --batch-size 32
```

Output:

```text
artifacts/models/F0__V1__s42/
```

Không dùng `--force` nếu chưa chủ động muốn archive trial cũ và train lại.

### 4.4. Evaluate

Validation:

```powershell
py -3.11 .\04_Evaluate.py --trial-id F0__V1__s42 --split val
```

Historical Test yêu cầu chỉ rõ trial và không cho ghi đè bằng `--force`:

```powershell
py -3.11 .\04_Evaluate.py --trial-id F0__V1__s42 --split test
```

Trước lệnh trên, variant tương ứng phải có `X_test.npy`, `Y_test.npy` và `Files_test.npy` được tạo bởi `02_Preprocess.py --include-test`.

Output chuẩn:

- `artifacts/models/<trial_id>/val_predictions.csv`;
- `artifacts/models/<trial_id>/test_predictions.csv`;
- `results/val_summary.csv`;
- `results/test_summary.csv`.

## 5. Tái lập ma trận C: 8 cấu hình x 3 seed

Tám variant:

```text
F0
pre_0
mel_40
fft_2048
combo_pre0_mel40
combo_pre0_fft2048
combo_mel40_fft2048
combo_pre0_mel40_fft2048
```

Sau khi bật đúng tám dòng, chạy `01_Build_Plan.py` và `02_Preprocess.py`. Train lần lượt bằng script chính:

```powershell
py -3.11 .\03_Train.py --architecture V1 --seed 42 --epochs 100 --batch-size 32
py -3.11 .\03_Train.py --architecture V1 --seed 43 --epochs 100 --batch-size 32
py -3.11 .\03_Train.py --architecture V1 --seed 44 --epochs 100 --batch-size 32
```

Đánh giá Validation theo từng seed bằng `04_Evaluate.py`. Khi đã đến bước hậu kiểm Test, chạy `02_Preprocess.py --include-test`, sau đó gọi `04_Evaluate.py --trial-id ... --split test` cho đúng checkpoint đã khóa.

Sau khi đủ 24 checkpoint, có thể audit mà không inference lại:

```powershell
py -3.11 .\Notebook\04_Fontend_Selection\C_Sync_24_Checkpoints.py --fingerprint-only
```

Chỉ khi cần sửa summary/prediction còn thiếu mới chạy chế độ đồng bộ đầy đủ:

```powershell
py -3.11 .\Notebook\04_Fontend_Selection\C_Sync_24_Checkpoints.py
```

## 6. Lượng tử hóa

Khóa full 24 checkpoint C:

```powershell
py -3.11 .\D0_Build_Quantization_Plan.py --all-c-checkpoints --force-plan
```

Lượng tử và đánh giá:

```powershell
py -3.11 .\D1_Quantize.py
py -3.11 .\D2_Evaluate_Quantized.py --split both
```

Xuất một model cho firmware:

```powershell
py -3.11 .\D3_Export_Deployment.py --trial-id combo_pre0_mel40_fft2048__V1__s44 --method QAT_INT8 --array-name asthma_model
```

Không dùng `--force-plan` hoặc `--force` để bỏ qua lỗi hash. Chỉ dùng khi chủ động thay đổi plan và chấp nhận tạo lại artifact liên quan.

## 7. Notebook hiện hành

Notebook chỉ phân tích artifact đã có; không thay thế script preprocess/train/evaluate.

| Bước | Notebook |
|---|---|
| A | `Notebook/01_Baseline_DSP/A_F0_s42_Baseline_DSP_Foundation.ipynb` |
| B0 | `Notebook/02_Dataset_Audit/B0_SampleRate_Source_Audit.ipynb` |
| B | `Notebook/03_OFAT_Exploration/B_F0_OFAT_9Trials_Conclusion.ipynb` |
| C | `Notebook/04_Fontend_Selection/C_Factorial_8x3_C4_Selection.ipynb` |
| D | `Notebook/05_Quantization_Deployment/D_Quantization_ESP32S3_ThreeLogs_Final.ipynb` |
| E | `Notebook/06_Final_Verifycation/E_Final_Verification_and_Model_Selection.ipynb` |
| F | `Notebook/07_Research_Synthsis/F_NCKH_Final_Research_Synthesis.ipynb` |

Thứ tự dùng:

1. Chạy script tạo artifact.
2. Mở notebook tương ứng.
3. Restart Kernel và Run All.
4. Nếu notebook báo thiếu file hoặc sai SHA, quay lại script nguồn; không điền metric thủ công.

Notebook F là tài liệu tổng hợp cuối, liên kết ngược về A-E và không thay thế các notebook nguồn.

## 8. Quy tắc provenance

- `config_sha256`: nhận diện đúng cấu hình Front-End.
- `model_sha256`: nhận diện đúng checkpoint Keras.
- `dataset_fingerprint`: nhận diện đúng tensor/split dữ liệu.
- Trial ID giữ dạng `<variant>__<architecture>__s<seed>`.
- Không đổi model sau khi đã xuất prediction mà không evaluate lại.
- Không dùng Test để quay lại điều chỉnh candidate ở B/C.

Tài liệu chi tiết theo từng thư mục:

- [`configs/README.md`](configs/README.md)
- [`Notebook/README.md`](Notebook/README.md)
- [`artifacts/README.md`](artifacts/README.md)
- [`results/README.md`](results/README.md)
- [`Roadmap_Frontend_A_to_E.md`](Roadmap_Frontend_A_to_E.md)
