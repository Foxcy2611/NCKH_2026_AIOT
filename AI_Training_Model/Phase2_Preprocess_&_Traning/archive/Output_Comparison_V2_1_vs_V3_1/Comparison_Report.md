# So sanh Model A V2_1 va Model B V3_1

- Model A: `V2_1_With_Playback` - train Dataset_V2 có playback
- Model B: `V3_1_No_Playback` - train Dataset_V3 không playback
- Kiến trúc chung: `V1_SepConv2D_Flatten`
- Binary threshold: `0.5` tren `p_non_asthma`
- Nhan: `0=Asthma`, `1=Non-Asthma`

## TEST 1 - COMMON RAW TEST (143 mau: 30/113)

| Metric | Model A | Model B |
|---|---:|---:|
| Accuracy | 0.881118881 | 0.923076923 |
| Asthma Precision | 0.658536585 | 0.771428571 |
| Asthma Recall | 0.900000000 | 0.900000000 |
| Asthma F1 | 0.760563380 | 0.830769231 |
| Non-Asthma Precision | 0.970588235 | 0.972222222 |
| Non-Asthma Recall | 0.876106195 | 0.929203540 |
| Non-Asthma F1 | 0.920930233 | 0.950226244 |

Confusion matrix dùng thứ tự hàng/cột `[Asthma, Non-Asthma]`.

- Model A: `[[27, 3], [14, 99]]`
- Model B: `[[27, 3], [8, 105]]`

## TEST 2 - PLAYBACK-ONLY TEST (16 mau: 8/8)

| Metric | Model A | Model B |
|---|---:|---:|
| Accuracy | 1.000000000 | 0.750000000 |
| Asthma Precision | 1.000000000 | 1.000000000 |
| Asthma Recall | 1.000000000 | 0.500000000 |
| Asthma F1 | 1.000000000 | 0.666666667 |
| Non-Asthma Precision | 1.000000000 | 0.666666667 |
| Non-Asthma Recall | 1.000000000 | 1.000000000 |
| Non-Asthma F1 | 1.000000000 | 0.800000000 |

Confusion matrix dùng thứ tự hàng/cột `[Asthma, Non-Asthma]`.

- Model A: `[[8, 0], [0, 8]]`
- Model B: `[[4, 4], [0, 8]]`

## File chi tiet

- `common_raw_predictions.csv`: p_non cua 143 raw cho ca hai model.
- `playback_only_predictions.csv`: p_non cua 16 playback cho ca hai model.
- `metrics_summary.csv`: metrics va confusion matrix dang bang.
- `confusion_matrices.png`: 4 confusion matrix.
- `p_non_comparison.png`: phan bo p_non theo tung test.

> Test chi de danh gia sau khi hai model da train xong; script khong
> dung test de chon threshold hoac thay doi model.
