# Frontend Benchmarking Artifacts

```text
02_Preprocess.py                            -> features/
03_Train.py + 04_Evaluate.py               -> models/
D1_Quantize.py + D2_Evaluate_Quantized.py  -> D_Quantization/
D3_Export_Deployment.py                    -> D_Deployment/
```

| Thư mục | Chức năng |
|---|---|
| `features/` | Log-Mel Train/Validation/Test theo frontend candidate; một cấu hình feature có thể được dùng lại cho nhiều seed train |
| `models/` | Checkpoint Keras, history, metadata và prediction Val/Test |
| `D_Quantization/` | TFLite PTQ/QAT, conversion metadata và đánh giá |
| `D_Deployment/` | Header C++ và deployment manifest |

Tên trial giữ dạng `<variant>__<architecture>__s<seed>`, ví dụ `F0__V1__s43`. Không đổi dấu `__` vì script dùng chuỗi này để truy checkpoint.

Các file `.npy`, `.keras`, `.tflite` có thể bị `.gitignore` chặn do dung lượng. Luôn đối chiếu `trial_id`, config hash, model hash và dataset fingerprint trước khi dùng artifact. Model đưa vào firmware phải đi qua D1, D2, notebook D và D3.

Luồng tạo artifact chuẩn dùng các script tại root `Frontend_Benchmarking`: `02_Preprocess.py` -> `03_Train.py` -> `04_Evaluate.py` -> D0-D3. Không cần runner PowerShell riêng cho từng seed hoặc combo.
