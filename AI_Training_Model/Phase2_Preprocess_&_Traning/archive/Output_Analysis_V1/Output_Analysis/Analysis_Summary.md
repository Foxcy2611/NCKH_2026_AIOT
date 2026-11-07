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
- Asthma đúng: `34`
- Asthma FN: `4`
- Non-Asthma FP: `5`
- Non-Asthma đúng: `111`

Ma trận theo thứ tự `[Asthma, Non-Asthma]`:

```text
[[ 34,   4],
 [  5, 111]]
```

Lỗi theo nhóm dữ liệu:

- `asthma_playback`: `4`
- `copd_core`: `3`
- `pneumonia_core`: `2`

## TEST

- Tổng mẫu: `159`
- Đúng: `139`
- Sai: `20`
- Accuracy: `0.8742`
- Asthma đúng: `32`
- Asthma FN: `6`
- Non-Asthma FP: `14`
- Non-Asthma đúng: `107`

Ma trận theo thứ tự `[Asthma, Non-Asthma]`:

```text
[[ 32,   6],
 [ 14, 107]]
```

Lỗi theo nhóm dữ liệu:

- `Environment_room_noise`: `6`
- `asthma_core`: `4`
- `asthma_playback`: `2`
- `bronchial_core`: `5`
- `copd_core`: `1`
- `pneumonia_core`: `2`

## Cách đọc hai loại lỗi

- `ASTHMA_FN`: bỏ sót Asthma, nhãn thật 0 nhưng dự đoán 1.
- `NON_ASTHMA_FP`: cảnh báo nhầm Asthma, nhãn thật 1 nhưng dự đoán 0.
