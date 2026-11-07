# Báo cáo cross-correlation delay của Asthma playback

## Phạm vi

- Chỉ phân tích `Train + Validation`; Test được giữ kín.
- Mỗi raw source được so với `take01` và `take02`.
- Không train model, không sửa WAV.
- `delay_seconds` ưu tiên normalized cross-correlation của RMS envelope; waveform correlation được dùng để đối chiếu/fallback.

## Thống kê delay đáng tin cậy

| Split | Tổng take | Reliable | Tỉ lệ | Median (s) | Std (s) | P10–P90 (s) |
|---|---:|---:|---:|---:|---:|---:|
| train | 64 | 64 | 1.0 | 1.02 | 0.02325 | 1.005–1.035 |
| val | 8 | 8 | 1.0 | 1.015 | 0.009922 | 1.005–1.028 |
| train_val | 72 | 72 | 1.0 | 1.02 | 0.022262 | 1.005–1.035 |

## Kiểm tra điều kiện fixed offset

- Reliable rate ≥ 0.80: **Đạt**
- Std ≤ 0.12 s: **Đạt**
- P90 − P10 ≤ 0.30 s: **Đạt**
- Median |take01 − take02| = 0.015 s, giới hạn 0.15 s: **Đạt**
- |Median Train − Median Val| = 0.005 s, giới hạn 0.20 s: **Đạt**

## Kết luận tự động

**Delay đủ ổn định: có thể dùng fixed offset.**

- Offset đề xuất (làm tròn theo bước 0.25 s): `1.0 s`.
- Trước khi rebuild dataset, vẫn cần xem các dòng `reliable = 0` và các outlier trong CSV chi tiết.

## File đầu ra

- `Playback_Delay_Per_Take.csv`: delay và confidence của từng take.
- `Playback_Delay_Take_Pairs.csv`: độ lệch giữa take01 và take02 cùng source.
- `Playback_Delay_Summary.csv`: thống kê Train/Val/Train+Val.
