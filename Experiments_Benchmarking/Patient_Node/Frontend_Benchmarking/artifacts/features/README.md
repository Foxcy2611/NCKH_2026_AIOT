# Features

Thư mục này được tạo bởi `02_Preprocess.py`.

## Chức năng

Mỗi thư mục con tương ứng với một frontend candidate trong `results/experiment_plan.csv`. Script đọc WAV từ Dataset V2, áp dụng crop/DSP/Log-Mel theo cấu hình candidate rồi lưu tensor Train/Validation; tensor Test chỉ được tạo khi gọi rõ `--include-test`.

```text
features/
└── <variant>/
    ├── X_train.npy
    ├── Y_train.npy
    ├── Files_train.npy
    ├── train_metadata.json
    ├── X_val.npy
    ├── Y_val.npy
    ├── Files_val.npy
    ├── val_metadata.json
    ├── X_test.npy              # chỉ có sau --include-test
    ├── Y_test.npy
    ├── Files_test.npy
    └── test_metadata.json
```

## Ý nghĩa các file

| File | Nội dung | Được dùng bởi |
|---|---|---|
| `X_<split>.npy` | Tensor Log-Mel chưa normalize toàn cục, shape phụ thuộc frontend | `03_Train.py`, bước D |
| `Y_<split>.npy` | Nhãn `0=Asthma`, `1=Non-Asthma` | Train/evaluate |
| `Files_<split>.npy` | Tên WAV theo đúng thứ tự tensor | Prediction và audit |
| `<split>_metadata.json` | Config hash, dataset root/fingerprint, shape, dtype và protocol | Kiểm tra tính tái lập |

## Cách tạo

Tất cả candidate đang `enabled=1`:

```powershell
py -3.11 .\02_Preprocess.py
```

Một candidate:

```powershell
py -3.11 .\02_Preprocess.py --variant F0
```

Sau khi đã xác định checkpoint cần hậu kiểm, tạo Test cho các candidate đang bật:

```powershell
py -3.11 .\02_Preprocess.py --include-test
```

Train/Validation phục vụ xây dựng và lựa chọn candidate. Historical Test chỉ dùng để hậu kiểm; không dùng kết quả Test để thay đổi ngược cấu hình ở B/C.

Không sửa tensor bằng tay. Nếu thay cấu hình hoặc dataset, hãy tạo lại plan rồi chạy lại preprocess có kiểm soát.

