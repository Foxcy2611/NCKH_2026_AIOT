# Thí nghiệm Dataset V3 - C4 s44 không có Playback

Thí nghiệm này dùng pipeline C4 đã chốt tại Frontend và chỉ thay dataset:

- baseline cũ: `Dataset_Chia_V2`, có playback;
- thí nghiệm này: `Dataset_Chia_V3`, bỏ toàn bộ 160 playback;
- Train V3 vẫn cân bằng `923 Asthma : 923 Non-Asthma`;
- kiến trúc `V1_SepConv2D_Flatten`, seed `44`.

Hợp đồng C4:

| Tham số | Giá trị |
|---|---:|
| Sample rate / cửa sổ | 16 kHz / 5 giây |
| Butterworth band-pass | 100-2000 Hz, order 5 |
| Pre-emphasis | `0.0` - không áp dụng |
| Mel bins | 40 |
| FFT / hop | 2048 / 625 |
| Tensor đầu vào | `40 x 129 x 1` |
| Frontend config SHA-256 | `5ae8a2c91c92b58653d899ddec056485787b6307db2cc0c350382b4ded2576f8` |

Mục tiêu là kiểm tra playback có làm giảm khả năng tổng quát của mô hình khi âm
thanh đi qua loa và INMP441 hay không. Không đổi kiến trúc, optimizer,
callback hoặc quy tắc chuẩn hóa để giữ phép so sánh công bằng.

> Output V3 cũ dùng 64 Mel, FFT 1024, pre-emphasis 0.97 hoặc seed 42 chỉ là
> artifact lịch sử. Muốn có kết quả C4 s44 phải chạy lại hai script bên dưới.

## Thứ tự chạy

Từ workspace root:

```powershell
py -3.11 "AI_Training_Model/Phase2_Preprocess_&_Traning/Preprocess_Audio_V3_No_Playback.py"
py -3.11 "AI_Training_Model/Phase2_Preprocess_&_Traning/Training_Model_V3_V1_No_Playback.py"
```

`Preprocess_Audio_V3_No_Playback.py` kiểm tra trước khi chạy:

- đúng `Dataset_Chia_V3`;
- không còn `__take01`/`__take02`;
- Train `923/923`, Val `30/108`, Test `30/113`.
- tensor đúng `40 x 129 x 1` và ghi `Preprocess_Metadata.json`.

Feature V3 được lưu tách biệt trong:

```text
Output_Preprocess_V3_No_Playback/
```

`Training_Model_V3_V1_No_Playback.py` kiểm tra metadata C4, config SHA-256,
X/Y/Files và count trước epoch đầu tiên. Model
tốt nhất cùng log, normalization và báo cáo test được lưu trong:

```text
Output_Train_V3_V1_No_Playback/
```

Model Keras:

```text
Output_Train_V3_V1_No_Playback/Model_Asthma_V3_V1_No_Playback.keras
```

## So sánh V2_1 và V3_1

Sau khi cả hai model đã tồn tại, chạy:

```powershell
py -3.11 "AI_Training_Model/Phase2_Preprocess_&_Traning/Compare_V2_1_vs_V3_1.py"
```

Script chạy hai phép đánh giá khóa:

1. Common Raw Test: toàn bộ 143 mẫu Test V3, gồm 30 Asthma và 113 Non-Asthma.
2. Playback-only Test: đúng 16 file thuộc Test V2 nhưng không còn trong V3,
   gồm 8 Asthma và 8 Non-Asthma.

Kết quả nằm trong `Output_Comparison_V2_1_vs_V3_1/`, gồm metrics, confusion
matrix, biểu đồ và `p_non_asthma` của từng file cho cả hai model.

> Các output V2 gốc (`Output_Preprocess` và
> `Output_Train_V1_SepConv2D_Flatten`) không bị ghi đè bởi nhánh thí nghiệm này.
