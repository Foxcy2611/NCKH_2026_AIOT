# AI_Training_Model - Pipeline chuẩn từ dữ liệu đến triển khai

## Vai trò

`AI_Training_Model/` là pipeline chuẩn để chuẩn bị dữ liệu, tiền xử lý, huấn luyện,
lượng tử hóa và sinh artifact triển khai. Toàn bộ thí nghiệm, benchmark và lập luận
lựa chọn cấu hình được đặt tại
[`Frontend_Benchmarking`](../Experiments_Benchmarking/Patient_Node/Frontend_Benchmarking/README.md).

## Luồng sử dụng

```text
Dataset gốc
  -> Phase 1: chia theo bệnh nhân/session và tăng cường riêng Train
  -> Phase 2: WAV -> Log-Mel -> huấn luyện/đánh giá kiến trúc
  -> Phase 3: Keras -> TFLite FP32/PTQ INT8/QAT INT8/PTQ INT16x8
  -> Phase 4: sinh header và dữ liệu kiểm tra deployment
  -> Deploy_Model: đo Flash, RAM, Tensor Arena, latency và parity
```

| Phase | Nhiệm vụ | Entry point chính |
|---|---|---|
| Phase 1 | Chia dữ liệu, augmentation, dựng Dataset V2/V3 | `Phase1_Split_Data/README.md` |
| Phase 2 | Preprocess và huấn luyện V1-V6 | `Preprocess_Audio.py`, `Training_Model.py` |
| Phase 3 | Lượng tử hóa và đánh giá TFLite | `Quantize_Model.py` |
| Phase 4 | Sinh header và dữ liệu kiểm tra deployment | các script `Generate_*`/`Prepare_*` |

## Chạy pipeline chính

Từ root repository:

```powershell
py -3.11 "AI_Training_Model/Phase2_Preprocess_&_Traning/Preprocess_Audio.py"
py -3.11 "AI_Training_Model/Phase2_Preprocess_&_Traning/Training_Model.py"
py -3.11 "AI_Training_Model/Phase3_Quantization_Model/Quantize_Model.py"
```

`Preprocess_Audio.py` lưu cấu hình thực tế vào `Preprocess_Metadata.json`, nhưng
không so sánh với SHA bên ngoài. `Training_Model.py` tự lấy input shape từ tensor
`.npy`; seed mặc định là `42` và có thể đổi mà không sửa source:

```powershell
$env:TRAIN_SEED = "44"
py -3.11 "AI_Training_Model/Phase2_Preprocess_&_Traning/Training_Model.py"
```

Phase 3 mặc định lượng tử V1. Muốn đổi model có thể sửa `Config.py`, hoặc dùng
biến môi trường/batch runner được mô tả trong README của Phase 3.

## Cấu hình preprocess mặc định hiện tại

| Thông số | Giá trị |
|---|---:|
| Sample rate / duration | 16 kHz / 5 giây |
| Band-pass / order | 100-2.000 Hz / 5 |
| Mel / FFT / hop | 40 / 2048 / 625 |
| Tensor | `40 x 129 x 1` |
| Nhãn | `0=Asthma`, `1=Non-Asthma` |

Đây là giá trị mặc định có thể sửa ở đầu `Preprocess_Audio.py`, không phải cấu
hình bị khóa bằng SHA. Khi đổi tham số, cần preprocess và train/lượng tử lại để
model, normalization và tensor deployment cùng một pipeline.

## Tài liệu chi tiết

- [Phase 1](Phase1_Split_Data/README.md)
- [Phase 2](Phase2_Preprocess_&_Traning/README.md)
- [Phase 3](Phase3_Quantization_Model/README.md)
- [Phase 4](Phase4_Deployment_Artifacts/README.md)

> Model phục vụ nghiên cứu, không phải công cụ chẩn đoán y khoa độc lập.
