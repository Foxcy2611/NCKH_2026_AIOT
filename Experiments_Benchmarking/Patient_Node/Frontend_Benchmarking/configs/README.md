# Cấu hình Frontend Benchmarking

Thư mục này chứa hai bảng cấu hình đầu vào của pipeline:

| File | Được đọc bởi | Chức năng |
|---|---|---|
| `candidates.csv` | `01_Build_Plan.py`, `B1_Preflight.py` | Khai báo frontend candidate cho mục B/C |
| `D_quantization_methods.csv` | `D0_Build_Quantization_Plan.py` | Khai báo method lượng tử hóa cho mục D |

Không sửa các artifact trong `results/` hoặc `artifacts/` để thay đổi cấu hình. Mọi thay đổi phải bắt đầu từ CSV tương ứng rồi tạo lại plan.

## 1. `candidates.csv`

Mỗi dòng là một frontend candidate. Baseline bất biến là `F0`:

```text
band-pass=100-2000 Hz
filter_order=5
pre_emphasis=0.97
n_mels=64
hop_length=625
n_fft=1024
```

### Các cột

| Cột | Ý nghĩa |
|---|---|
| `variant_id` | ID duy nhất, được dùng trong tên folder và trial |
| `group` | Nhóm ablation: baseline, bandpass, filter order, pre-emphasis, Mel, hop, FFT hoặc combination |
| `enabled` | `1`: đưa vào lịch mặc định; `0`: không chạy hàng loạt |
| `low_cut_hz`, `high_cut_hz` | Dải band-pass |
| `filter_order` | Bậc Butterworth; `0` biểu diễn bypass trong candidate tương ứng |
| `pre_emphasis` | Hệ số pre-emphasis |
| `n_mels` | Số Mel bins |
| `hop_length` | Bước nhảy STFT theo sample |
| `n_fft` | Kích thước FFT |
| `hypothesis` | Giả thuyết nghiên cứu của candidate |

### Quy tắc `enabled`

- Phải có ít nhất một dòng `enabled=1` khi chạy plan mặc định.
- `01_Build_Plan.py`, `02_Preprocess.py` và `03_Train.py` không có `--variant` sẽ xử lý các dòng đang bật.
- Có thể đặt `F0 enabled=0` nếu checkpoint F0 đã tồn tại và không muốn train lại.
- Nếu dòng F0 vẫn tồn tại thì các thông số của nó bắt buộc phải đúng baseline.
- `04_Evaluate.py --trial-id ...` vẫn có thể đánh giá checkpoint cụ thể dù candidate hiện đã tắt.

### OFAT và combination

Trong mục B, mỗi candidate ngoài F0 chỉ được thay đổi đúng một tham số. `B1_Preflight.py` kiểm tra quy tắc này.

Các candidate combination thuộc mục C và không chạy qua `B1_Preflight.py`:

| Mã nghiên cứu | `variant_id` | Thay đổi so với F0 |
|---|---|---|
| C1 | `combo_pre0_mel40` | `pre_emphasis=0`, `n_mels=40` |
| C2 | `combo_pre0_fft2048` | `pre_emphasis=0`, `n_fft=2048` |
| C3 | `combo_mel40_fft2048` | `n_mels=40`, `n_fft=2048` |
| C4 | `combo_pre0_mel40_fft2048` | `pre_emphasis=0`, `n_mels=40`, `n_fft=2048` |

Không dùng runner PowerShell riêng cho C1-C4. Bật các dòng cần khảo sát, tạo lại plan rồi dùng trực tiếp pipeline chính:

```powershell
py -3.11 .\01_Build_Plan.py
py -3.11 .\02_Preprocess.py
py -3.11 .\03_Train.py --architecture V1 --seed 42 --epochs 100 --batch-size 32
py -3.11 .\03_Train.py --architecture V1 --seed 43 --epochs 100 --batch-size 32
py -3.11 .\03_Train.py --architecture V1 --seed 44 --epochs 100 --batch-size 32
```

Nếu chỉ muốn chạy một combination đang `enabled=0`, truyền rõ `--variant`, ví dụ:

```powershell
py -3.11 .\02_Preprocess.py --variant combo_pre0_mel40_fft2048
py -3.11 .\03_Train.py --architecture V1 --variant combo_pre0_mel40_fft2048 --seed 44 --epochs 100 --batch-size 32
py -3.11 .\04_Evaluate.py --trial-id combo_pre0_mel40_fft2048__V1__s44 --split val
```

### Sau khi sửa candidate OFAT của mục B

```powershell
py -3.11 .\01_Build_Plan.py
py -3.11 .\B1_Preflight.py
py -3.11 .\02_Preprocess.py
py -3.11 .\03_Train.py --architecture V1 --seed 42 --epochs 100 --batch-size 32
py -3.11 .\04_Evaluate.py --architecture V1 --seed 42 --split val
```

Không chạy `B1_Preflight.py` cho C1-C4 vì preflight OFAT cố ý từ chối candidate thay đổi nhiều tham số. Các bước `01`, `02`, `03`, `04` vẫn là pipeline chuẩn cho combination.

Không bỏ qua `02_Preprocess.py`: `03_Train.py` chỉ đọc tensor đã được tạo đúng config hash.

## 2. `D_quantization_methods.csv`

Mỗi dòng là một phương pháp lượng tử hóa áp dụng cho các checkpoint đã đăng ký trong D0.

### Các cột

| Cột | Ý nghĩa |
|---|---|
| `method_id` | ID method được dùng trong đường dẫn artifact |
| `enabled` | `1`: đưa vào quantization plan; `0`: bỏ khỏi plan mới |
| `training_mode` | `PTQ` hoặc `QAT` |
| `integer_mode` | `INT8` hoặc `INT16x8` |
| `experimental` | Đánh dấu nhánh thử nghiệm |
| `description` | Mô tả ngắn method |

Các method hiện có:

| Method | Đặc điểm |
|---|---|
| `PTQ_INT8` | Full integer INT8 sau train; phù hợp firmware INT8 hiện tại |
| `QAT_INT8` | Fine-tune có nhận thức lượng tử rồi xuất INT8 |
| `PTQ_INT16x8` | Weight INT8, activation/I/O INT16; không phải drop-in replacement cho firmware INT8 |

### Sau khi sửa method

Tạo lại plan có kiểm soát:

```powershell
py -3.11 .\D0_Build_Quantization_Plan.py --force-plan
```

Sau đó mới chạy:

```powershell
py -3.11 .\D1_Quantize.py
py -3.11 .\D2_Evaluate_Quantized.py --split both
```

Không sửa CSV rồi chạy thẳng D1: D1 chỉ chấp nhận method đã được ghi trong `quantization_plan.json` hiện hành.

## 3. Nguyên tắc an toàn

- Không đổi config giữa preprocess, train và evaluate của cùng một trial.
- Không dùng Test để quay lại bật/tắt candidate.
- Không dùng `--force` hoặc `--force-plan` chỉ để bỏ qua lỗi hash.
- Luôn kiểm tra `experiment_plan.csv` hoặc `quantization_plan.csv` trước bước tốn thời gian.
- Tên trial phải giữ dạng `variant__architecture__seed`, ví dụ `F0__V1__s43`.

