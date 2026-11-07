# D Deployment Artifacts

Thư mục này được tạo bởi `D3_Export_Deployment.py` sau khi notebook D đã chọn một trial và method lượng tử phù hợp.

D3 không train, không lượng tử lại và không tự copy file vào firmware.

## Cấu trúc

```text
D_Deployment/
└── <trial_id>/
    └── <method>/
        ├── Asthma_Model.h
        └── deployment_manifest.json
```

## Các file

| File | Chức năng |
|---|---|
| `Asthma_Model.h` | Byte array của TFLite, căn hàng 4 byte, dùng để compile vào firmware |
| `deployment_manifest.json` | Trial/method, SHA-256, kích thước, frontend config, normalization và I/O quantization |

## Shortlist từ mục D13.2

Ba artifact dưới đây được xuất để đo đối chiếu trên ESP32-S3. Đây là ba model độc lập, không phải ba file được nhúng đồng thời vào một firmware.

| Vai trò | Trial | Phương pháp | Cấu hình frontend |
|---|---|---|---|
| Ứng viên chính | `combo_pre0_mel40_fft2048__V1__s44` | `QAT_INT8` | pre-emphasis `0.0`, Mel `40`, FFT `2048` |
| Baseline hiện tại | `F0__V1__s43` | `PTQ_INT8` | pre-emphasis `0.97`, Mel `64`, FFT `1024` |
| Đối chứng ablation | `combo_mel40_fft2048__V1__s44` | `QAT_INT8` | pre-emphasis `0.97`, Mel `40`, FFT `2048` |

Nguồn chốt shortlist là `results/D_Quantization/Full_24_Analysis/D3_ESP32S3_measure_shortlist.csv` do notebook D tạo.

## Cách xuất lại ba header

Mở PowerShell tại thư mục `Frontend_Benchmarking`. Firmware đang dùng symbol `model_data` và `model_data_len`, vì vậy phải truyền `--array-name model_data`:

```powershell
py -3.11 .\D3_Export_Deployment.py --trial-id combo_pre0_mel40_fft2048__V1__s44 --method QAT_INT8 --array-name model_data

py -3.11 .\D3_Export_Deployment.py --trial-id F0__V1__s43 --method PTQ_INT8 --array-name model_data

py -3.11 .\D3_Export_Deployment.py --trial-id combo_mel40_fft2048__V1__s44 --method QAT_INT8 --array-name model_data
```

`D3_Export_Deployment.py` chỉ chuyển byte của file `.tflite` đã lượng tử sang mảng C/C++; script không train, không lượng tử lại và không sửa firmware.

## Output D13.2

```text
D_Deployment/
├── combo_pre0_mel40_fft2048__V1__s44/
│   └── QAT_INT8/
│       ├── Asthma_Model.h
│       └── deployment_manifest.json
├── F0__V1__s43/
│   └── PTQ_INT8/
│       ├── Asthma_Model.h
│       └── deployment_manifest.json
└── combo_mel40_fft2048__V1__s44/
    └── QAT_INT8/
        ├── Asthma_Model.h
        └── deployment_manifest.json
```

Mỗi header đều dùng cùng symbol `model_data`. Khi benchmark, chỉ copy **một header mỗi lần build**. Đồng thời phải đặt DSP/frontend của firmware đúng theo `frontend_config` trong `deployment_manifest.json`; nếu chỉ thay model mà giữ sai Mel, FFT hoặc pre-emphasis thì kết quả không có giá trị đối chiếu.

## Kiểm tra trước khi bàn giao

1. `trial_id` và `method_id` đúng kết luận notebook D.
2. `source_tflite_sha256` khớp TFLite trong `D_Quantization`.
3. Input/output dtype phù hợp firmware.
4. Scale và zero point được firmware xử lý đúng.
5. Header đích sau khi copy có hash giống header do D3 tạo.
6. Chạy lại benchmark Tensor Arena, RAM/PSRAM, latency, operator compatibility và parity trên ESP32-S3.

Việc có `Asthma_Model.h` chưa đủ để kết luận model deploy thành công trên phần cứng.
