# Dataset_Chia_V2

Đây là bộ dữ liệu nhị phân dùng cho pipeline V2, gồm hai lớp
`Asthma` và `Non_Asthma_Disease`; mỗi lớp được chia thành `train`, `val` và
`test`.

## Cách chia dữ liệu

### 1. Chia WAV Core theo bệnh nhân

- WAV Core được lấy từ các nhóm `asthma`, `Bronchial`, `copd`, `healthy` và
  `pneumonia` trong `Dataset_TuThu_v_Kaggle`.
- Mã bệnh nhân `P<number>` ở đầu tên file được dùng làm `patient_id`.
- Với Asthma, `group_id` chính là mã bệnh nhân. Với Non-Asthma, `group_id`
  có thêm loại bệnh, ví dụ `COPD_P12`, để tránh nhầm các ID giống nhau giữa
  các nguồn bệnh.
- Các `group_id` được xáo trộn bằng seed `42` và chia gần tỷ lệ `80/10/10`.
- **Toàn bộ WAV của cùng một `group_id` chỉ thuộc một split**. Không chia
  riêng từng WAV, nhờ đó tránh để cùng bệnh nhân xuất hiện ở cả Train và
  Validation/Test.
- Trước khi chia, các WAV trùng hoàn toàn được phát hiện bằng SHA-256; một
  WAV trùng nội dung nhưng mang hai nhãn khác nhau sẽ làm script dừng.

Kết quả Core:

| Lớp | Train | Validation | Test |
|---|---:|---:|---:|
| Asthma Core | 228 | 30 | 30 |
| Non-Asthma Core | 653 | 78 | 83 |

### 2. Ánh xạ Playback theo WAV nguồn

Playback không được chia lại ngẫu nhiên. Mỗi file `take01/take02` kế thừa
split của WAV Core đã được dùng để phát:

```text
Core Train -> Playback Train
Core Validation -> Playback Validation
Core Test -> Playback Test
```

Quy tắc này giữ WAV gốc và các bản thu lại qua loa - INMP441 trong cùng một
split, tránh quan hệ nguồn - bản sao bị rò rỉ sang tập đánh giá.

### 3. Chia âm thanh môi trường theo session

- Có 33 session môi trường chính, được khóa theo tỷ lệ `27/3/3`.
- Validation: 1 Podcast, 1 Fan và 1 Clap.
- Test: 1 Knock, 1 Room noise và 1 Speech.
- 27 session còn lại thuộc Train.
- Mỗi session được chia trước, sau đó mới cắt thành 10 clip, mỗi clip 5 giây.
  Vì vậy, mọi clip sinh từ cùng một session luôn nằm trong cùng một split.
- Các clip này mang nhãn `Non_Asthma_Disease`.

### 4. Tăng cường chỉ trên Asthma Train

- Chỉ 228 Asthma Core Train được dùng làm file cha.
- Không tăng cường Playback, Validation hoặc Test.
- Sinh 695 WAV bằng năm phương pháp: trộn môi trường, time shift, white
  noise, time stretch và pitch shift.
- Nguồn môi trường dùng để trộn chỉ lấy từ Train.

Sau bước này, hai lớp Train được cân bằng ở mức 987 WAV mỗi lớp.

## Quy mô Dataset V2 hoàn chỉnh

| Split | Asthma | Non-Asthma | Tổng |
|---|---:|---:|---:|
| Train | 987 | 987 | 1.974 |
| Validation | 38 | 116 | 154 |
| Test | 38 | 121 | 159 |

Validation và Test được giữ theo phân bố thực tế, không nhân bản hoặc tăng
cường chỉ để cân bằng nhãn.

## Nguồn truy vết

Các quyết định chia không được suy ra từ vị trí file hiện tại mà được lưu tại:

- `Phase1_Split_Data/Output/00_Core_Split/core_split_manifest.csv`;
- `Phase1_Split_Data/Output/00_Core_Split/core_group_split.csv`;
- `Phase1_Split_Data/Output/02_Map_Playback/playback_map_manifest.csv`;
- `Phase1_Split_Data/Output/03_Cut_Environment/environment_session_split.csv`;
- `Phase1_Split_Data/Output/04_Build_Dataset/environment_clip_manifest.csv`;
- `Phase1_Split_Data/Output/05_Argument_Asthma/asthma_augmentation_manifest.csv`.

Quy trình đầy đủ và thứ tự chạy script được mô tả tại
[`Phase1_Split_Data/README.md`](../Phase1_Split_Data/README.md).
