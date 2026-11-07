# C - Factorial 8 cấu hình x 3 seed

Notebook hiện hành: `C_Factorial_8x3_C4_Selection.ipynb`.

## Phạm vi

- Baseline và biến đổi đơn lẻ: `F0`, `pre_0`, `mel_40`, `fft_2048`.
- Combo: C1 = pre0 + mel40; C2 = pre0 + fft2048; C3 = mel40 + fft2048; C4 = pre0 + mel40 + fft2048.
- Mỗi cấu hình được train độc lập với seed 42, 43 và 44, tạo tổng cộng 24 checkpoint FP32.
- Nguồn phân tích chuẩn là `results/val_summary.csv`, `results/test_summary.csv` và prediction trong `artifacts/models/<trial_id>/`.

Tập Test đã từng được tham khảo trong nghiên cứu, vì vậy kết quả Test ở đây là hậu kiểm lịch sử, không được mô tả như một holdout hoàn toàn chưa từng quan sát.

## Tạo 24 checkpoint bằng script chính

Mở PowerShell tại root `Frontend_Benchmarking`, sau đó chạy:

```powershell
py -3.11 .\01_Build_Plan.py
py -3.11 .\02_Preprocess.py

py -3.11 .\03_Train.py --architecture V1 --seed 42 --epochs 100 --batch-size 32
py -3.11 .\03_Train.py --architecture V1 --seed 43 --epochs 100 --batch-size 32
py -3.11 .\03_Train.py --architecture V1 --seed 44 --epochs 100 --batch-size 32

py -3.11 .\04_Evaluate.py --architecture V1 --seed 42 --split val
py -3.11 .\04_Evaluate.py --architecture V1 --seed 43 --split val
py -3.11 .\04_Evaluate.py --architecture V1 --seed 44 --split val
```

Sau khi khóa danh sách 24 checkpoint cần hậu kiểm, tạo tensor Test:

```powershell
py -3.11 .\02_Preprocess.py --include-test
```

Test bắt buộc gọi bằng trial ID cụ thể, ví dụ:

```powershell
py -3.11 .\04_Evaluate.py --trial-id F0__V1__s42 --split test
```

Lặp lệnh này cho từng trial cần hậu kiểm hoặc dùng `C_Sync_24_Checkpoints.py` để audit/đồng bộ đủ ma trận 24 trial.

`03_Train.py` chỉ train những variant đang có `enabled=1` trong `configs/candidates.csv`. Không cần runner PowerShell riêng cho C1-C4.

## Vai trò của `C_Sync_24_Checkpoints.py`

Đây là công cụ phụ để kiểm tra và đồng bộ artifact **sau khi train**, không phải script huấn luyện.

Chế độ đầy đủ có thể gọi lại preprocess/evaluate khi artifact còn thiếu:

```powershell
py -3.11 .\Notebook\04_Fontend_Selection\C_Sync_24_Checkpoints.py
```

Nếu prediction và metric đã đủ, chỉ cần kiểm tra SHA, nhãn, số mẫu và điền fingerprint:

```powershell
py -3.11 .\Notebook\04_Fontend_Selection\C_Sync_24_Checkpoints.py --fingerprint-only
```

Ưu tiên dùng trực tiếp `02_Preprocess.py`, `03_Train.py` và `04_Evaluate.py`. Chỉ chạy `C_Sync_24_Checkpoints.py` khi cần audit đủ 24 trial trước khi mở notebook C.

## Chạy notebook

1. Kiểm tra đủ 24 thư mục `artifacts/models/<trial_id>/`.
2. Kiểm tra mỗi trial có `val_predictions.csv` và `test_predictions.csv`.
3. Kiểm tra `results/val_summary.csv` và `results/test_summary.csv` có đủ 8 cấu hình x 3 seed.
4. Mở `C_Factorial_8x3_C4_Selection.ipynb`, Restart Kernel rồi chạy từ đầu xuống cuối.

Notebook chỉ đọc và phân tích artifact; không train, không inference và không tạo một bộ summary thay thế.

## Quy tắc provenance

- `config_sha256` nhận diện cấu hình tiền xử lý.
- `model_sha256` nhận diện đúng checkpoint đã đánh giá.
- `dataset_fingerprint` nhận diện danh sách WAV, nhãn và split.
- Một dòng metric chỉ hợp lệ khi các giá trị trên khớp với metadata tại thời điểm inference.
- Bước C làm việc với checkpoint FP32; lượng tử và handoff firmware nằm ở bước D.
