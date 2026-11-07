# Final AI Model - Patient Node

Thư mục này lưu lõi AI chính thức và bằng chứng truy vết model đang được triển khai trên Patient Node.

## Model đã chốt

| Thuộc tính | Giá trị |
|---|---|
| Trial | `combo_pre0_mel40_fft2048__V1__s44` |
| Tên ngắn | `C4 V1 s44` |
| Architecture | `V1 - SepConv2D + Flatten` |
| Seed | `44` |
| Quantization | `QAT Full INT8` |
| Input | `[1, 40, 129, 1]`, `int8` |
| Output | `[1, 1]`, `int8` (`p_non_asthma`) |
| Model size | `347,968 bytes` |
| TFLite SHA-256 | `d081c1cfcd873c4e2182f9d9e0f8aff07a69ea0b041cf0d6d845d3222efc46b9` |
| Header SHA-256 | `bb26264a77ef0c382e3b127fb3b3345a563e42d5a610796a67738a2b197851d1` |
| Status | `FINAL - chờ nghiệm thu lại threshold/phần cứng` |

## Cấu hình frontend bắt buộc

```text
PCM16, 16 kHz, 5 giây
  -> peak normalization
  -> Butterworth band-pass 100-2000 Hz, order 5
  -> không pre-emphasis (coefficient = 0)
  -> Mel-Spectrogram: n_fft=2048, hop_length=625, n_mels=40
  -> power-to-dB, top_db=80
  -> min-max theo Train: [-80, 0] -> float32 [0, 1]
  -> lượng tử input INT8
```

| Tensor | Dtype | Scale | Zero point |
|---|---|---:|---:|
| Input | `int8` | `0.003921568859368563` | `-128` |
| Output | `int8` | `0.00390625` | `-128` |

## Kết quả phần mềm của QAT INT8

| Split | Accuracy | Asthma precision | Asthma recall | Asthma F1 | Confusion matrix |
|---|---:|---:|---:|---:|---|
| Validation (154) | 97.40% | 92.50% | 97.37% | 94.87% | `[[37, 1], [3, 113]]` |
| Test (159) | 95.60% | 89.74% | 92.11% | 90.91% | `[[35, 3], [4, 117]]` |

Các metric trên dùng ngưỡng nhị phân `0.5` để kiểm tra model. Hai ngưỡng ba trạng thái `ASTHMA/UNSURE/NON-ASTHMA` phải được nghiệm thu lại trong `Final_V1_Validation`; không tái sử dụng ngưỡng của F0 cũ.

## Cấu trúc artifact

```text
AI_Model/
├── Asthma_Model.h
├── deployment_manifest.json
├── README.md
├── C4_V1_s44_QAT_INT8/
│   ├── C4_V1_s44_QAT_INT8.tflite
│   ├── deployment_manifest.json
│   ├── conversion_metadata.json
│   ├── training_metadata.json
│   ├── val_classification_report.txt
│   ├── val_metrics.json
│   ├── test_classification_report.txt
│   └── test_metrics.json
```

Thư mục này chỉ giữ artifact **C4 V1 s44 QAT INT8** đang triển khai. Artifact
F0 lịch sử đã được loại khỏi `Final_Project_NCKH/AI_Model`; các kết quả nghiên
cứu cũ vẫn thuộc khu vực `Experiments_Benchmarking`.

## Vị trí header đã đồng bộ

Các file sau phải có cùng SHA-256 `bb26264a...851d1`:

1. `Final_Project_NCKH/AI_Model/Asthma_Model.h`
2. `Final_Project_NCKH/Patient_Node/include/Model_AI/Asthma_Model.h`
3. `Deploy_Model/2_Test_Model_LiveMic/include/Model_AI/Asthma_Model.h`
4. `Deploy_Model/3_Model_Complete/include/Model_AI/Asthma_Model.h`
5. `ESP32_Standalone_Modules_Test/Asthma_Playback_Calibration/include/Model_AI/Asthma_Model.h`

Nguồn chuẩn được export tại:

```text
Experiments_Benchmarking/Patient_Node/Frontend_Benchmarking/
  artifacts/D_Deployment/combo_pre0_mel40_fft2048__V1__s44/QAT_INT8/
```

`Deploy_Model/1_Test_Model_Static_Profiling` vẫn giữ nhiều model để đối chứng, nhưng nhánh mặc định đã chuyển sang C4 QAT INT8.

## Nghiệm thu còn lại

- chạy lại Classification Threshold cho C4;
- xác nhận Python-C++ parity với frontend `40 x 129`;
- đo lại Tensor Arena/RAM/PSRAM và thời gian `Invoke()`;
- nghiệm thu Quality Gate, VAD, CHECK/MONITOR và packet end-to-end.
