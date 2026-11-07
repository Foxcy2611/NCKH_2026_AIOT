# So sanh Model A V2_1 va Model B V3_1

- Model A: `V2_1_With_Playback` - train V2 co playback
- Model B: `V3_1_No_Playback` - train V3 khong playback
- Binary threshold: `0.5` tren `p_non_asthma`
- Nhan: `0=Asthma`, `1=Non-Asthma`

## TEST 1 - COMMON RAW TEST (143 mau: 30/113)

| Metric | Model A | Model B |
|---|---:|---:|
| Accuracy | 0.923076923 | 0.902097902 |
| Asthma Precision | 0.787878788 | 0.722222222 |
| Asthma Recall | 0.866666667 | 0.866666667 |
| Asthma F1 | 0.825396825 | 0.787878788 |
| Non-Asthma Precision | 0.963636364 | 0.962616822 |
| Non-Asthma Recall | 0.938053097 | 0.911504425 |
| Non-Asthma F1 | 0.950672646 | 0.936363636 |

Confusion matrix dùng thứ tự hàng/cột `[Asthma, Non-Asthma]`.

- Model A: `[[26, 4], [7, 106]]`
- Model B: `[[26, 4], [10, 103]]`

## TEST 2 - PLAYBACK-ONLY TEST (16 mau: 8/8)

| Metric | Model A | Model B |
|---|---:|---:|
| Accuracy | 0.750000000 | 0.875000000 |
| Asthma Precision | 1.000000000 | 1.000000000 |
| Asthma Recall | 0.500000000 | 0.750000000 |
| Asthma F1 | 0.666666667 | 0.857142857 |
| Non-Asthma Precision | 0.666666667 | 0.800000000 |
| Non-Asthma Recall | 1.000000000 | 1.000000000 |
| Non-Asthma F1 | 0.800000000 | 0.888888889 |

Confusion matrix dùng thứ tự hàng/cột `[Asthma, Non-Asthma]`.

- Model A: `[[4, 4], [0, 8]]`
- Model B: `[[6, 2], [0, 8]]`

## File chi tiet

- `common_raw_predictions.csv`: p_non cua 143 raw cho ca hai model.
- `playback_only_predictions.csv`: p_non cua 16 playback cho ca hai model.
- `metrics_summary.csv`: metrics va confusion matrix dang bang.
- `confusion_matrices.png`: 4 confusion matrix.
- `p_non_comparison.png`: phan bo p_non theo tung test.

> Test chi de danh gia sau khi hai model da train xong; script khong
> dung test de chon threshold hoac thay doi model.
