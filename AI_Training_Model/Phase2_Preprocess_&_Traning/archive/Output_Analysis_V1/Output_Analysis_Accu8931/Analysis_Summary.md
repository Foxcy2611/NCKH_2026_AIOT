# Phân tích lỗi Model Asthma V2

Script chỉ thực hiện suy luận, không huấn luyện lại mô hình.

- Model: `Model_Asthma.keras`
- Ngưỡng phân lớp: `0.5`
- TRAIN_MIN: `-80.0`
- TRAIN_MAX: `0.0`
- Nhãn `0 = Asthma`, `1 = Non-Asthma`.
- Xác suất đầu ra là xác suất `Non-Asthma`.

## VAL

- Tổng mẫu: `154`
- Đúng: `145`
- Sai: `9`
- Accuracy: `0.9416`
- Asthma đúng: `37`
- Asthma FN: `1`
- Non-Asthma FP: `8`
- Non-Asthma đúng: `108`

Ma trận theo thứ tự `[Asthma, Non-Asthma]`:

```text
[[ 37,   1],
 [  8, 108]]
```

Lỗi theo nhóm dữ liệu:

- `asthma_playback`: `1`
- `copd_core`: `3`
- `copd_playback`: `2`
- `pneumonia_core`: `3`

## TEST

- Tổng mẫu: `159`
- Đúng: `142`
- Sai: `17`
- Accuracy: `0.8931`
- Asthma đúng: `35`
- Asthma FN: `3`
- Non-Asthma FP: `14`
- Non-Asthma đúng: `107`

Ma trận theo thứ tự `[Asthma, Non-Asthma]`:

```text
[[ 35,   3],
 [ 14, 107]]
```

Lỗi theo nhóm dữ liệu:

- `Environment_room_noise`: `4`
- `asthma_core`: `3`
- `bronchial_core`: `6`
- `healthy_core`: `1`
- `pneumonia_core`: `3`

## Cách đọc hai loại lỗi

- `ASTHMA_FN`: bỏ sót Asthma, nhãn thật 0 nhưng dự đoán 1.
- `NON_ASTHMA_FP`: cảnh báo nhầm Asthma, nhãn thật 1 nhưng dự đoán 0.
