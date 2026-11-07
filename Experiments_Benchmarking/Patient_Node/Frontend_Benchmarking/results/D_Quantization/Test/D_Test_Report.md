# Báo cáo lượng tử hóa Frontend — Historical Test

- Plan SHA256: `8258e0c64948a6d2916f84089bd590f40c8b026b22f713e5bfe1845dabbe544d`
- Split đánh giá: **Historical Test**
- Test accessed: **true**
- Thứ tự checkpoint được bàn giao từ phân tích bước C.
- Cảnh báo: Test 159 WAV đã được xem ở bước C; đây không phải holdout mới hoàn toàn độc lập.

## Phạm vi checkpoint

| Ưu tiên | Vai trò | Trial | Variant | Input |
|---:|---|---|---|---|
| 1 | C_FULL_MATRIX | `F0__V1__s42` | `F0` | `64 × 129 × 1` |
| 2 | BASELINE | `F0__V1__s43` | `F0` | `64 × 129 × 1` |
| 3 | C_FULL_MATRIX | `F0__V1__s44` | `F0` | `64 × 129 × 1` |
| 4 | C_FULL_MATRIX | `pre_0__V1__s42` | `pre_0` | `64 × 129 × 1` |
| 5 | C_FULL_MATRIX | `pre_0__V1__s43` | `pre_0` | `64 × 129 × 1` |
| 6 | C_ADDITIONAL | `pre_0__V1__s44` | `pre_0` | `64 × 129 × 1` |
| 7 | C_FULL_MATRIX | `mel_40__V1__s42` | `mel_40` | `40 × 129 × 1` |
| 8 | TECHNICAL_CONTROL | `mel_40__V1__s43` | `mel_40` | `40 × 129 × 1` |
| 9 | C_FULL_MATRIX | `mel_40__V1__s44` | `mel_40` | `40 × 129 × 1` |
| 10 | C_FULL_MATRIX | `fft_2048__V1__s42` | `fft_2048` | `64 × 129 × 1` |
| 11 | C_FULL_MATRIX | `fft_2048__V1__s43` | `fft_2048` | `64 × 129 × 1` |
| 12 | C_FULL_MATRIX | `fft_2048__V1__s44` | `fft_2048` | `64 × 129 × 1` |
| 13 | C_FULL_MATRIX | `combo_pre0_mel40__V1__s42` | `combo_pre0_mel40` | `40 × 129 × 1` |
| 14 | PRIMARY | `combo_pre0_mel40__V1__s43` | `combo_pre0_mel40` | `40 × 129 × 1` |
| 15 | C_FULL_MATRIX | `combo_pre0_mel40__V1__s44` | `combo_pre0_mel40` | `40 × 129 × 1` |
| 16 | C_FULL_MATRIX | `combo_pre0_fft2048__V1__s42` | `combo_pre0_fft2048` | `64 × 129 × 1` |
| 17 | C_FULL_MATRIX | `combo_pre0_fft2048__V1__s43` | `combo_pre0_fft2048` | `64 × 129 × 1` |
| 18 | C_FULL_MATRIX | `combo_pre0_fft2048__V1__s44` | `combo_pre0_fft2048` | `64 × 129 × 1` |
| 19 | C_FULL_MATRIX | `combo_mel40_fft2048__V1__s42` | `combo_mel40_fft2048` | `40 × 129 × 1` |
| 20 | C_FULL_MATRIX | `combo_mel40_fft2048__V1__s43` | `combo_mel40_fft2048` | `40 × 129 × 1` |
| 21 | C_FULL_MATRIX | `combo_mel40_fft2048__V1__s44` | `combo_mel40_fft2048` | `40 × 129 × 1` |
| 22 | C_FULL_MATRIX | `combo_pre0_mel40_fft2048__V1__s42` | `combo_pre0_mel40_fft2048` | `40 × 129 × 1` |
| 23 | C_FULL_MATRIX | `combo_pre0_mel40_fft2048__V1__s43` | `combo_pre0_mel40_fft2048` | `40 × 129 × 1` |
| 24 | C_FULL_MATRIX | `combo_pre0_mel40_fft2048__V1__s44` | `combo_pre0_mel40_fft2048` | `40 × 129 × 1` |

## Kết quả Historical Test

| Ưu tiên | Trial | Method | Accuracy | Macro F1 | Asthma Recall | Non-Asthma Recall | Đổi nhãn so với FP32 | Kích thước (byte) | I/O |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | `F0__V1__s42` | `KERAS_FP32` | 0.8931 | 0.8655 | 0.9211 | 0.8843 | 0 | 6402662 | float32 → float32 |
| 1 | `F0__V1__s42` | `PTQ_INT8` | 0.9371 | 0.9165 | 0.9211 | 0.9421 | 7 | 543976 | int8 → int8 |
| 1 | `F0__V1__s42` | `QAT_INT8` | 0.8868 | 0.8586 | 0.9211 | 0.8760 | 5 | 544568 | int8 → int8 |
| 1 | `F0__V1__s42` | `PTQ_INT16x8` | 0.8931 | 0.8655 | 0.9211 | 0.8843 | 0 | 547744 | int16 → int16 |
| 2 | `F0__V1__s43` | `KERAS_FP32` | 0.9434 | 0.9242 | 0.9211 | 0.9504 | 0 | 6402662 | float32 → float32 |
| 2 | `F0__V1__s43` | `PTQ_INT8` | 0.9434 | 0.9229 | 0.8947 | 0.9587 | 4 | 543976 | int8 → int8 |
| 2 | `F0__V1__s43` | `QAT_INT8` | 0.9434 | 0.9229 | 0.8947 | 0.9587 | 4 | 544568 | int8 → int8 |
| 2 | `F0__V1__s43` | `PTQ_INT16x8` | 0.9434 | 0.9242 | 0.9211 | 0.9504 | 0 | 547744 | int16 → int16 |
| 3 | `F0__V1__s44` | `KERAS_FP32` | 0.9119 | 0.8868 | 0.9211 | 0.9091 | 0 | 6402662 | float32 → float32 |
| 3 | `F0__V1__s44` | `PTQ_INT8` | 0.9245 | 0.8963 | 0.8421 | 0.9504 | 10 | 543976 | int8 → int8 |
| 3 | `F0__V1__s44` | `QAT_INT8` | 0.9119 | 0.8850 | 0.8947 | 0.9174 | 4 | 544568 | int8 → int8 |
| 3 | `F0__V1__s44` | `PTQ_INT16x8` | 0.9119 | 0.8868 | 0.9211 | 0.9091 | 0 | 547744 | int16 → int16 |
| 4 | `pre_0__V1__s42` | `KERAS_FP32` | 0.9119 | 0.8868 | 0.9211 | 0.9091 | 0 | 6402662 | float32 → float32 |
| 4 | `pre_0__V1__s42` | `PTQ_INT8` | 0.8616 | 0.7796 | 0.5263 | 0.9669 | 24 | 543976 | int8 → int8 |
| 4 | `pre_0__V1__s42` | `QAT_INT8` | 0.9245 | 0.9014 | 0.9211 | 0.9256 | 4 | 544568 | int8 → int8 |
| 4 | `pre_0__V1__s42` | `PTQ_INT16x8` | 0.9119 | 0.8868 | 0.9211 | 0.9091 | 0 | 547744 | int16 → int16 |
| 5 | `pre_0__V1__s43` | `KERAS_FP32` | 0.9119 | 0.8868 | 0.9211 | 0.9091 | 0 | 6402662 | float32 → float32 |
| 5 | `pre_0__V1__s43` | `PTQ_INT8` | 0.9308 | 0.9057 | 0.8684 | 0.9504 | 11 | 543976 | int8 → int8 |
| 5 | `pre_0__V1__s43` | `QAT_INT8` | 0.9182 | 0.8940 | 0.9211 | 0.9174 | 3 | 544568 | int8 → int8 |
| 5 | `pre_0__V1__s43` | `PTQ_INT16x8` | 0.9182 | 0.8940 | 0.9211 | 0.9174 | 1 | 547744 | int16 → int16 |
| 6 | `pre_0__V1__s44` | `KERAS_FP32` | 0.9182 | 0.8923 | 0.8947 | 0.9256 | 0 | 6402662 | float32 → float32 |
| 6 | `pre_0__V1__s44` | `PTQ_INT8` | 0.9497 | 0.9308 | 0.8947 | 0.9669 | 7 | 543976 | int8 → int8 |
| 6 | `pre_0__V1__s44` | `QAT_INT8` | 0.9182 | 0.8905 | 0.8684 | 0.9339 | 2 | 544568 | int8 → int8 |
| 6 | `pre_0__V1__s44` | `PTQ_INT16x8` | 0.9182 | 0.8923 | 0.8947 | 0.9256 | 0 | 547744 | int16 → int16 |
| 7 | `mel_40__V1__s42` | `KERAS_FP32` | 0.9119 | 0.8850 | 0.8947 | 0.9174 | 0 | 4043366 | float32 → float32 |
| 7 | `mel_40__V1__s42` | `PTQ_INT8` | 0.9119 | 0.8743 | 0.7632 | 0.9587 | 12 | 347368 | int8 → int8 |
| 7 | `mel_40__V1__s42` | `QAT_INT8` | 0.9182 | 0.8940 | 0.9211 | 0.9174 | 5 | 347960 | int8 → int8 |
| 7 | `mel_40__V1__s42` | `PTQ_INT16x8` | 0.9119 | 0.8850 | 0.8947 | 0.9174 | 0 | 351136 | int16 → int16 |
| 8 | `mel_40__V1__s43` | `KERAS_FP32` | 0.8868 | 0.8521 | 0.8421 | 0.9008 | 0 | 4043366 | float32 → float32 |
| 8 | `mel_40__V1__s43` | `PTQ_INT8` | 0.9119 | 0.8767 | 0.7895 | 0.9504 | 8 | 347368 | int8 → int8 |
| 8 | `mel_40__V1__s43` | `QAT_INT8` | 0.8931 | 0.8543 | 0.7895 | 0.9256 | 11 | 347960 | int8 → int8 |
| 8 | `mel_40__V1__s43` | `PTQ_INT16x8` | 0.8868 | 0.8521 | 0.8421 | 0.9008 | 0 | 351136 | int16 → int16 |
| 9 | `mel_40__V1__s44` | `KERAS_FP32` | 0.8302 | 0.7948 | 0.8684 | 0.8182 | 0 | 4043366 | float32 → float32 |
| 9 | `mel_40__V1__s44` | `PTQ_INT8` | 0.8868 | 0.8521 | 0.8421 | 0.9008 | 11 | 347368 | int8 → int8 |
| 9 | `mel_40__V1__s44` | `QAT_INT8` | 0.8679 | 0.8362 | 0.8947 | 0.8595 | 8 | 347960 | int8 → int8 |
| 9 | `mel_40__V1__s44` | `PTQ_INT16x8` | 0.8365 | 0.8012 | 0.8684 | 0.8264 | 1 | 351136 | int16 → int16 |
| 10 | `fft_2048__V1__s42` | `KERAS_FP32` | 0.8994 | 0.8706 | 0.8947 | 0.9008 | 0 | 6402662 | float32 → float32 |
| 10 | `fft_2048__V1__s42` | `PTQ_INT8` | 0.8994 | 0.8535 | 0.7105 | 0.9587 | 16 | 543976 | int8 → int8 |
| 10 | `fft_2048__V1__s42` | `QAT_INT8` | 0.8931 | 0.8568 | 0.8158 | 0.9174 | 11 | 544576 | int8 → int8 |
| 10 | `fft_2048__V1__s42` | `PTQ_INT16x8` | 0.9057 | 0.8796 | 0.9211 | 0.9008 | 1 | 547744 | int16 → int16 |
| 11 | `fft_2048__V1__s43` | `KERAS_FP32` | 0.9434 | 0.9242 | 0.9211 | 0.9504 | 0 | 6402662 | float32 → float32 |
| 11 | `fft_2048__V1__s43` | `PTQ_INT8` | 0.9434 | 0.9229 | 0.8947 | 0.9587 | 2 | 543976 | int8 → int8 |
| 11 | `fft_2048__V1__s43` | `QAT_INT8` | 0.9182 | 0.8923 | 0.8947 | 0.9256 | 6 | 544576 | int8 → int8 |
| 11 | `fft_2048__V1__s43` | `PTQ_INT16x8` | 0.9434 | 0.9242 | 0.9211 | 0.9504 | 0 | 547744 | int16 → int16 |
| 12 | `fft_2048__V1__s44` | `KERAS_FP32` | 0.9245 | 0.9014 | 0.9211 | 0.9256 | 0 | 6402662 | float32 → float32 |
| 12 | `fft_2048__V1__s44` | `PTQ_INT8` | 0.9245 | 0.9014 | 0.9211 | 0.9256 | 4 | 543976 | int8 → int8 |
| 12 | `fft_2048__V1__s44` | `QAT_INT8` | 0.9308 | 0.9089 | 0.9211 | 0.9339 | 1 | 544576 | int8 → int8 |
| 12 | `fft_2048__V1__s44` | `PTQ_INT16x8` | 0.9182 | 0.8940 | 0.9211 | 0.9174 | 1 | 547744 | int16 → int16 |
| 13 | `combo_pre0_mel40__V1__s42` | `KERAS_FP32` | 0.9057 | 0.8796 | 0.9211 | 0.9008 | 0 | 4043366 | float32 → float32 |
| 13 | `combo_pre0_mel40__V1__s42` | `PTQ_INT8` | 0.8931 | 0.8614 | 0.8684 | 0.9008 | 18 | 347368 | int8 → int8 |
| 13 | `combo_pre0_mel40__V1__s42` | `QAT_INT8` | 0.9182 | 0.8923 | 0.8947 | 0.9256 | 8 | 347968 | int8 → int8 |
| 13 | `combo_pre0_mel40__V1__s42` | `PTQ_INT16x8` | 0.9057 | 0.8796 | 0.9211 | 0.9008 | 0 | 351136 | int16 → int16 |
| 14 | `combo_pre0_mel40__V1__s43` | `KERAS_FP32` | 0.8868 | 0.8544 | 0.8684 | 0.8926 | 0 | 4043366 | float32 → float32 |
| 14 | `combo_pre0_mel40__V1__s43` | `PTQ_INT8` | 0.8994 | 0.8641 | 0.8158 | 0.9256 | 10 | 347368 | int8 → int8 |
| 14 | `combo_pre0_mel40__V1__s43` | `QAT_INT8` | 0.9057 | 0.8758 | 0.8684 | 0.9174 | 11 | 347968 | int8 → int8 |
| 14 | `combo_pre0_mel40__V1__s43` | `PTQ_INT16x8` | 0.8805 | 0.8475 | 0.8684 | 0.8843 | 1 | 351136 | int16 → int16 |
| 15 | `combo_pre0_mel40__V1__s44` | `KERAS_FP32` | 0.9119 | 0.8831 | 0.8684 | 0.9256 | 0 | 4043366 | float32 → float32 |
| 15 | `combo_pre0_mel40__V1__s44` | `PTQ_INT8` | 0.9119 | 0.8790 | 0.8158 | 0.9421 | 6 | 347368 | int8 → int8 |
| 15 | `combo_pre0_mel40__V1__s44` | `QAT_INT8` | 0.8994 | 0.8706 | 0.8947 | 0.9008 | 8 | 347968 | int8 → int8 |
| 15 | `combo_pre0_mel40__V1__s44` | `PTQ_INT16x8` | 0.9119 | 0.8831 | 0.8684 | 0.9256 | 0 | 351136 | int16 → int16 |
| 16 | `combo_pre0_fft2048__V1__s42` | `KERAS_FP32` | 0.8994 | 0.8706 | 0.8947 | 0.9008 | 0 | 6402662 | float32 → float32 |
| 16 | `combo_pre0_fft2048__V1__s42` | `PTQ_INT8` | 0.8616 | 0.7740 | 0.5000 | 0.9752 | 24 | 543976 | int8 → int8 |
| 16 | `combo_pre0_fft2048__V1__s42` | `QAT_INT8` | 0.8868 | 0.8471 | 0.7895 | 0.9174 | 12 | 544576 | int8 → int8 |
| 16 | `combo_pre0_fft2048__V1__s42` | `PTQ_INT16x8` | 0.8994 | 0.8706 | 0.8947 | 0.9008 | 0 | 547744 | int16 → int16 |
| 17 | `combo_pre0_fft2048__V1__s43` | `KERAS_FP32` | 0.9182 | 0.8940 | 0.9211 | 0.9174 | 0 | 6402662 | float32 → float32 |
| 17 | `combo_pre0_fft2048__V1__s43` | `PTQ_INT8` | 0.9371 | 0.9165 | 0.9211 | 0.9421 | 3 | 543976 | int8 → int8 |
| 17 | `combo_pre0_fft2048__V1__s43` | `QAT_INT8` | 0.9434 | 0.9242 | 0.9211 | 0.9504 | 4 | 544576 | int8 → int8 |
| 17 | `combo_pre0_fft2048__V1__s43` | `PTQ_INT16x8` | 0.9119 | 0.8868 | 0.9211 | 0.9091 | 1 | 547744 | int16 → int16 |
| 18 | `combo_pre0_fft2048__V1__s44` | `KERAS_FP32` | 0.8679 | 0.8384 | 0.9211 | 0.8512 | 0 | 6402662 | float32 → float32 |
| 18 | `combo_pre0_fft2048__V1__s44` | `PTQ_INT8` | 0.8931 | 0.8655 | 0.9211 | 0.8843 | 6 | 543976 | int8 → int8 |
| 18 | `combo_pre0_fft2048__V1__s44` | `QAT_INT8` | 0.9308 | 0.9089 | 0.9211 | 0.9339 | 12 | 544576 | int8 → int8 |
| 18 | `combo_pre0_fft2048__V1__s44` | `PTQ_INT16x8` | 0.8805 | 0.8518 | 0.9211 | 0.8678 | 2 | 547744 | int16 → int16 |
| 19 | `combo_mel40_fft2048__V1__s42` | `KERAS_FP32` | 0.8931 | 0.8635 | 0.8947 | 0.8926 | 0 | 4043366 | float32 → float32 |
| 19 | `combo_mel40_fft2048__V1__s42` | `PTQ_INT8` | 0.9119 | 0.8691 | 0.7105 | 0.9752 | 17 | 347368 | int8 → int8 |
| 19 | `combo_mel40_fft2048__V1__s42` | `QAT_INT8` | 0.9057 | 0.8777 | 0.8947 | 0.9091 | 6 | 347968 | int8 → int8 |
| 19 | `combo_mel40_fft2048__V1__s42` | `PTQ_INT16x8` | 0.8931 | 0.8635 | 0.8947 | 0.8926 | 0 | 351136 | int16 → int16 |
| 20 | `combo_mel40_fft2048__V1__s43` | `KERAS_FP32` | 0.9057 | 0.8777 | 0.8947 | 0.9091 | 0 | 4043366 | float32 → float32 |
| 20 | `combo_mel40_fft2048__V1__s43` | `PTQ_INT8` | 0.9182 | 0.8844 | 0.7895 | 0.9587 | 12 | 347368 | int8 → int8 |
| 20 | `combo_mel40_fft2048__V1__s43` | `QAT_INT8` | 0.9245 | 0.9014 | 0.9211 | 0.9256 | 11 | 347968 | int8 → int8 |
| 20 | `combo_mel40_fft2048__V1__s43` | `PTQ_INT16x8` | 0.9057 | 0.8777 | 0.8947 | 0.9091 | 0 | 351136 | int16 → int16 |
| 21 | `combo_mel40_fft2048__V1__s44` | `KERAS_FP32` | 0.9057 | 0.8758 | 0.8684 | 0.9174 | 0 | 4043366 | float32 → float32 |
| 21 | `combo_mel40_fft2048__V1__s44` | `PTQ_INT8` | 0.9057 | 0.8758 | 0.8684 | 0.9174 | 6 | 347368 | int8 → int8 |
| 21 | `combo_mel40_fft2048__V1__s44` | `QAT_INT8` | 0.9119 | 0.8831 | 0.8684 | 0.9256 | 5 | 347968 | int8 → int8 |
| 21 | `combo_mel40_fft2048__V1__s44` | `PTQ_INT16x8` | 0.9057 | 0.8758 | 0.8684 | 0.9174 | 0 | 351136 | int16 → int16 |
| 22 | `combo_pre0_mel40_fft2048__V1__s42` | `KERAS_FP32` | 0.9119 | 0.8831 | 0.8684 | 0.9256 | 0 | 4043366 | float32 → float32 |
| 22 | `combo_pre0_mel40_fft2048__V1__s42` | `PTQ_INT8` | 0.8616 | 0.7985 | 0.6316 | 0.9339 | 18 | 347368 | int8 → int8 |
| 22 | `combo_pre0_mel40_fft2048__V1__s42` | `QAT_INT8` | 0.9245 | 0.9014 | 0.9211 | 0.9256 | 6 | 347968 | int8 → int8 |
| 22 | `combo_pre0_mel40_fft2048__V1__s42` | `PTQ_INT16x8` | 0.9182 | 0.8923 | 0.8947 | 0.9256 | 1 | 351136 | int16 → int16 |
| 23 | `combo_pre0_mel40_fft2048__V1__s43` | `KERAS_FP32` | 0.9308 | 0.9089 | 0.9211 | 0.9339 | 0 | 4043366 | float32 → float32 |
| 23 | `combo_pre0_mel40_fft2048__V1__s43` | `PTQ_INT8` | 0.9245 | 0.8963 | 0.8421 | 0.9504 | 7 | 347368 | int8 → int8 |
| 23 | `combo_pre0_mel40_fft2048__V1__s43` | `QAT_INT8` | 0.9371 | 0.9151 | 0.8947 | 0.9504 | 7 | 347968 | int8 → int8 |
| 23 | `combo_pre0_mel40_fft2048__V1__s43` | `PTQ_INT16x8` | 0.9308 | 0.9089 | 0.9211 | 0.9339 | 0 | 351136 | int16 → int16 |
| 24 | `combo_pre0_mel40_fft2048__V1__s44` | `KERAS_FP32` | 0.9057 | 0.8691 | 0.7895 | 0.9421 | 0 | 4043366 | float32 → float32 |
| 24 | `combo_pre0_mel40_fft2048__V1__s44` | `PTQ_INT8` | 0.9245 | 0.8923 | 0.7895 | 0.9669 | 3 | 347368 | int8 → int8 |
| 24 | `combo_pre0_mel40_fft2048__V1__s44` | `QAT_INT8` | 0.9560 | 0.9400 | 0.9211 | 0.9669 | 10 | 347968 | int8 → int8 |
| 24 | `combo_pre0_mel40_fft2048__V1__s44` | `PTQ_INT16x8` | 0.9057 | 0.8691 | 0.7895 | 0.9421 | 0 | 351136 | int16 → int16 |

## Confusion matrix và classification report

Quy ước: nhãn `0 = Asthma`, nhãn `1 = Non-Asthma`, hàng là nhãn thật và cột là nhãn dự đoán.

### 1. `F0__V1__s42` — `KERAS_FP32`

- Accuracy: **0.8931**
- Balanced accuracy: **0.9027**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 14 | 107 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7143 | 0.9211 | 0.8046 | 38 |
| Non-Asthma | 0.9727 | 0.8843 | 0.9264 | 121 |
| accuracy | — | — | 0.8931 | 159 |
| macro avg | 0.8435 | 0.9027 | 0.8655 | 159 |
| weighted avg | 0.9110 | 0.8931 | 0.8973 | 159 |

### 1. `F0__V1__s42` — `PTQ_INT8`

- Accuracy: **0.9371**
- Balanced accuracy: **0.9316**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 7 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8333 | 0.9211 | 0.8750 | 38 |
| Non-Asthma | 0.9744 | 0.9421 | 0.9580 | 121 |
| accuracy | — | — | 0.9371 | 159 |
| macro avg | 0.9038 | 0.9316 | 0.9165 | 159 |
| weighted avg | 0.9407 | 0.9371 | 0.9382 | 159 |

### 1. `F0__V1__s42` — `QAT_INT8`

- Accuracy: **0.8868**
- Balanced accuracy: **0.8985**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 15 | 106 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7000 | 0.9211 | 0.7955 | 38 |
| Non-Asthma | 0.9725 | 0.8760 | 0.9217 | 121 |
| accuracy | — | — | 0.8868 | 159 |
| macro avg | 0.8362 | 0.8985 | 0.8586 | 159 |
| weighted avg | 0.9074 | 0.8868 | 0.8916 | 159 |

### 1. `F0__V1__s42` — `PTQ_INT16x8`

- Accuracy: **0.8931**
- Balanced accuracy: **0.9027**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 14 | 107 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7143 | 0.9211 | 0.8046 | 38 |
| Non-Asthma | 0.9727 | 0.8843 | 0.9264 | 121 |
| accuracy | — | — | 0.8931 | 159 |
| macro avg | 0.8435 | 0.9027 | 0.8655 | 159 |
| weighted avg | 0.9110 | 0.8931 | 0.8973 | 159 |

### 2. `F0__V1__s43` — `KERAS_FP32`

- Accuracy: **0.9434**
- Balanced accuracy: **0.9357**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 6 | 115 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8537 | 0.9211 | 0.8861 | 38 |
| Non-Asthma | 0.9746 | 0.9504 | 0.9623 | 121 |
| accuracy | — | — | 0.9434 | 159 |
| macro avg | 0.9141 | 0.9357 | 0.9242 | 159 |
| weighted avg | 0.9457 | 0.9434 | 0.9441 | 159 |

### 2. `F0__V1__s43` — `PTQ_INT8`

- Accuracy: **0.9434**
- Balanced accuracy: **0.9267**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 5 | 116 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8718 | 0.8947 | 0.8831 | 38 |
| Non-Asthma | 0.9667 | 0.9587 | 0.9627 | 121 |
| accuracy | — | — | 0.9434 | 159 |
| macro avg | 0.9192 | 0.9267 | 0.9229 | 159 |
| weighted avg | 0.9440 | 0.9434 | 0.9436 | 159 |

### 2. `F0__V1__s43` — `QAT_INT8`

- Accuracy: **0.9434**
- Balanced accuracy: **0.9267**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 5 | 116 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8718 | 0.8947 | 0.8831 | 38 |
| Non-Asthma | 0.9667 | 0.9587 | 0.9627 | 121 |
| accuracy | — | — | 0.9434 | 159 |
| macro avg | 0.9192 | 0.9267 | 0.9229 | 159 |
| weighted avg | 0.9440 | 0.9434 | 0.9436 | 159 |

### 2. `F0__V1__s43` — `PTQ_INT16x8`

- Accuracy: **0.9434**
- Balanced accuracy: **0.9357**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 6 | 115 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8537 | 0.9211 | 0.8861 | 38 |
| Non-Asthma | 0.9746 | 0.9504 | 0.9623 | 121 |
| accuracy | — | — | 0.9434 | 159 |
| macro avg | 0.9141 | 0.9357 | 0.9242 | 159 |
| weighted avg | 0.9457 | 0.9434 | 0.9441 | 159 |

### 3. `F0__V1__s44` — `KERAS_FP32`

- Accuracy: **0.9119**
- Balanced accuracy: **0.9151**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 11 | 110 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7609 | 0.9211 | 0.8333 | 38 |
| Non-Asthma | 0.9735 | 0.9091 | 0.9402 | 121 |
| accuracy | — | — | 0.9119 | 159 |
| macro avg | 0.8672 | 0.9151 | 0.8868 | 159 |
| weighted avg | 0.9226 | 0.9119 | 0.9146 | 159 |

### 3. `F0__V1__s44` — `PTQ_INT8`

- Accuracy: **0.9245**
- Balanced accuracy: **0.8963**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 32 | 6 |
| Non-Asthma | 6 | 115 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8421 | 0.8421 | 0.8421 | 38 |
| Non-Asthma | 0.9504 | 0.9504 | 0.9504 | 121 |
| accuracy | — | — | 0.9245 | 159 |
| macro avg | 0.8963 | 0.8963 | 0.8963 | 159 |
| weighted avg | 0.9245 | 0.9245 | 0.9245 | 159 |

### 3. `F0__V1__s44` — `QAT_INT8`

- Accuracy: **0.9119**
- Balanced accuracy: **0.9060**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 10 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7727 | 0.8947 | 0.8293 | 38 |
| Non-Asthma | 0.9652 | 0.9174 | 0.9407 | 121 |
| accuracy | — | — | 0.9119 | 159 |
| macro avg | 0.8690 | 0.9060 | 0.8850 | 159 |
| weighted avg | 0.9192 | 0.9119 | 0.9141 | 159 |

### 3. `F0__V1__s44` — `PTQ_INT16x8`

- Accuracy: **0.9119**
- Balanced accuracy: **0.9151**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 11 | 110 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7609 | 0.9211 | 0.8333 | 38 |
| Non-Asthma | 0.9735 | 0.9091 | 0.9402 | 121 |
| accuracy | — | — | 0.9119 | 159 |
| macro avg | 0.8672 | 0.9151 | 0.8868 | 159 |
| weighted avg | 0.9226 | 0.9119 | 0.9146 | 159 |

### 4. `pre_0__V1__s42` — `KERAS_FP32`

- Accuracy: **0.9119**
- Balanced accuracy: **0.9151**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 11 | 110 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7609 | 0.9211 | 0.8333 | 38 |
| Non-Asthma | 0.9735 | 0.9091 | 0.9402 | 121 |
| accuracy | — | — | 0.9119 | 159 |
| macro avg | 0.8672 | 0.9151 | 0.8868 | 159 |
| weighted avg | 0.9226 | 0.9119 | 0.9146 | 159 |

### 4. `pre_0__V1__s42` — `PTQ_INT8`

- Accuracy: **0.8616**
- Balanced accuracy: **0.7466**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 20 | 18 |
| Non-Asthma | 4 | 117 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8333 | 0.5263 | 0.6452 | 38 |
| Non-Asthma | 0.8667 | 0.9669 | 0.9141 | 121 |
| accuracy | — | — | 0.8616 | 159 |
| macro avg | 0.8500 | 0.7466 | 0.7796 | 159 |
| weighted avg | 0.8587 | 0.8616 | 0.8498 | 159 |

### 4. `pre_0__V1__s42` — `QAT_INT8`

- Accuracy: **0.9245**
- Balanced accuracy: **0.9233**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 9 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7955 | 0.9211 | 0.8537 | 38 |
| Non-Asthma | 0.9739 | 0.9256 | 0.9492 | 121 |
| accuracy | — | — | 0.9245 | 159 |
| macro avg | 0.8847 | 0.9233 | 0.9014 | 159 |
| weighted avg | 0.9313 | 0.9245 | 0.9263 | 159 |

### 4. `pre_0__V1__s42` — `PTQ_INT16x8`

- Accuracy: **0.9119**
- Balanced accuracy: **0.9151**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 11 | 110 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7609 | 0.9211 | 0.8333 | 38 |
| Non-Asthma | 0.9735 | 0.9091 | 0.9402 | 121 |
| accuracy | — | — | 0.9119 | 159 |
| macro avg | 0.8672 | 0.9151 | 0.8868 | 159 |
| weighted avg | 0.9226 | 0.9119 | 0.9146 | 159 |

### 5. `pre_0__V1__s43` — `KERAS_FP32`

- Accuracy: **0.9119**
- Balanced accuracy: **0.9151**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 11 | 110 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7609 | 0.9211 | 0.8333 | 38 |
| Non-Asthma | 0.9735 | 0.9091 | 0.9402 | 121 |
| accuracy | — | — | 0.9119 | 159 |
| macro avg | 0.8672 | 0.9151 | 0.8868 | 159 |
| weighted avg | 0.9226 | 0.9119 | 0.9146 | 159 |

### 5. `pre_0__V1__s43` — `PTQ_INT8`

- Accuracy: **0.9308**
- Balanced accuracy: **0.9094**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 33 | 5 |
| Non-Asthma | 6 | 115 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8462 | 0.8684 | 0.8571 | 38 |
| Non-Asthma | 0.9583 | 0.9504 | 0.9544 | 121 |
| accuracy | — | — | 0.9308 | 159 |
| macro avg | 0.9022 | 0.9094 | 0.9057 | 159 |
| weighted avg | 0.9315 | 0.9308 | 0.9311 | 159 |

### 5. `pre_0__V1__s43` — `QAT_INT8`

- Accuracy: **0.9182**
- Balanced accuracy: **0.9192**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 10 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7778 | 0.9211 | 0.8434 | 38 |
| Non-Asthma | 0.9737 | 0.9174 | 0.9447 | 121 |
| accuracy | — | — | 0.9182 | 159 |
| macro avg | 0.8757 | 0.9192 | 0.8940 | 159 |
| weighted avg | 0.9269 | 0.9182 | 0.9205 | 159 |

### 5. `pre_0__V1__s43` — `PTQ_INT16x8`

- Accuracy: **0.9182**
- Balanced accuracy: **0.9192**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 10 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7778 | 0.9211 | 0.8434 | 38 |
| Non-Asthma | 0.9737 | 0.9174 | 0.9447 | 121 |
| accuracy | — | — | 0.9182 | 159 |
| macro avg | 0.8757 | 0.9192 | 0.8940 | 159 |
| weighted avg | 0.9269 | 0.9182 | 0.9205 | 159 |

### 6. `pre_0__V1__s44` — `KERAS_FP32`

- Accuracy: **0.9182**
- Balanced accuracy: **0.9102**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 9 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7907 | 0.8947 | 0.8395 | 38 |
| Non-Asthma | 0.9655 | 0.9256 | 0.9451 | 121 |
| accuracy | — | — | 0.9182 | 159 |
| macro avg | 0.8781 | 0.9102 | 0.8923 | 159 |
| weighted avg | 0.9237 | 0.9182 | 0.9199 | 159 |

### 6. `pre_0__V1__s44` — `PTQ_INT8`

- Accuracy: **0.9497**
- Balanced accuracy: **0.9308**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 4 | 117 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8947 | 0.8947 | 0.8947 | 38 |
| Non-Asthma | 0.9669 | 0.9669 | 0.9669 | 121 |
| accuracy | — | — | 0.9497 | 159 |
| macro avg | 0.9308 | 0.9308 | 0.9308 | 159 |
| weighted avg | 0.9497 | 0.9497 | 0.9497 | 159 |

### 6. `pre_0__V1__s44` — `QAT_INT8`

- Accuracy: **0.9182**
- Balanced accuracy: **0.9012**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 33 | 5 |
| Non-Asthma | 8 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8049 | 0.8684 | 0.8354 | 38 |
| Non-Asthma | 0.9576 | 0.9339 | 0.9456 | 121 |
| accuracy | — | — | 0.9182 | 159 |
| macro avg | 0.8813 | 0.9012 | 0.8905 | 159 |
| weighted avg | 0.9211 | 0.9182 | 0.9193 | 159 |

### 6. `pre_0__V1__s44` — `PTQ_INT16x8`

- Accuracy: **0.9182**
- Balanced accuracy: **0.9102**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 9 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7907 | 0.8947 | 0.8395 | 38 |
| Non-Asthma | 0.9655 | 0.9256 | 0.9451 | 121 |
| accuracy | — | — | 0.9182 | 159 |
| macro avg | 0.8781 | 0.9102 | 0.8923 | 159 |
| weighted avg | 0.9237 | 0.9182 | 0.9199 | 159 |

### 7. `mel_40__V1__s42` — `KERAS_FP32`

- Accuracy: **0.9119**
- Balanced accuracy: **0.9060**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 10 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7727 | 0.8947 | 0.8293 | 38 |
| Non-Asthma | 0.9652 | 0.9174 | 0.9407 | 121 |
| accuracy | — | — | 0.9119 | 159 |
| macro avg | 0.8690 | 0.9060 | 0.8850 | 159 |
| weighted avg | 0.9192 | 0.9119 | 0.9141 | 159 |

### 7. `mel_40__V1__s42` — `PTQ_INT8`

- Accuracy: **0.9119**
- Balanced accuracy: **0.8609**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 29 | 9 |
| Non-Asthma | 5 | 116 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8529 | 0.7632 | 0.8056 | 38 |
| Non-Asthma | 0.9280 | 0.9587 | 0.9431 | 121 |
| accuracy | — | — | 0.9119 | 159 |
| macro avg | 0.8905 | 0.8609 | 0.8743 | 159 |
| weighted avg | 0.9101 | 0.9119 | 0.9102 | 159 |

### 7. `mel_40__V1__s42` — `QAT_INT8`

- Accuracy: **0.9182**
- Balanced accuracy: **0.9192**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 10 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7778 | 0.9211 | 0.8434 | 38 |
| Non-Asthma | 0.9737 | 0.9174 | 0.9447 | 121 |
| accuracy | — | — | 0.9182 | 159 |
| macro avg | 0.8757 | 0.9192 | 0.8940 | 159 |
| weighted avg | 0.9269 | 0.9182 | 0.9205 | 159 |

### 7. `mel_40__V1__s42` — `PTQ_INT16x8`

- Accuracy: **0.9119**
- Balanced accuracy: **0.9060**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 10 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7727 | 0.8947 | 0.8293 | 38 |
| Non-Asthma | 0.9652 | 0.9174 | 0.9407 | 121 |
| accuracy | — | — | 0.9119 | 159 |
| macro avg | 0.8690 | 0.9060 | 0.8850 | 159 |
| weighted avg | 0.9192 | 0.9119 | 0.9141 | 159 |

### 8. `mel_40__V1__s43` — `KERAS_FP32`

- Accuracy: **0.8868**
- Balanced accuracy: **0.8715**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 32 | 6 |
| Non-Asthma | 12 | 109 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7273 | 0.8421 | 0.7805 | 38 |
| Non-Asthma | 0.9478 | 0.9008 | 0.9237 | 121 |
| accuracy | — | — | 0.8868 | 159 |
| macro avg | 0.8375 | 0.8715 | 0.8521 | 159 |
| weighted avg | 0.8951 | 0.8868 | 0.8895 | 159 |

### 8. `mel_40__V1__s43` — `PTQ_INT8`

- Accuracy: **0.9119**
- Balanced accuracy: **0.8699**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 30 | 8 |
| Non-Asthma | 6 | 115 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8333 | 0.7895 | 0.8108 | 38 |
| Non-Asthma | 0.9350 | 0.9504 | 0.9426 | 121 |
| accuracy | — | — | 0.9119 | 159 |
| macro avg | 0.8841 | 0.8699 | 0.8767 | 159 |
| weighted avg | 0.9107 | 0.9119 | 0.9111 | 159 |

### 8. `mel_40__V1__s43` — `QAT_INT8`

- Accuracy: **0.8931**
- Balanced accuracy: **0.8575**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 30 | 8 |
| Non-Asthma | 9 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7692 | 0.7895 | 0.7792 | 38 |
| Non-Asthma | 0.9333 | 0.9256 | 0.9295 | 121 |
| accuracy | — | — | 0.8931 | 159 |
| macro avg | 0.8513 | 0.8575 | 0.8543 | 159 |
| weighted avg | 0.8941 | 0.8931 | 0.8936 | 159 |

### 8. `mel_40__V1__s43` — `PTQ_INT16x8`

- Accuracy: **0.8868**
- Balanced accuracy: **0.8715**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 32 | 6 |
| Non-Asthma | 12 | 109 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7273 | 0.8421 | 0.7805 | 38 |
| Non-Asthma | 0.9478 | 0.9008 | 0.9237 | 121 |
| accuracy | — | — | 0.8868 | 159 |
| macro avg | 0.8375 | 0.8715 | 0.8521 | 159 |
| weighted avg | 0.8951 | 0.8868 | 0.8895 | 159 |

### 9. `mel_40__V1__s44` — `KERAS_FP32`

- Accuracy: **0.8302**
- Balanced accuracy: **0.8433**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 33 | 5 |
| Non-Asthma | 22 | 99 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.6000 | 0.8684 | 0.7097 | 38 |
| Non-Asthma | 0.9519 | 0.8182 | 0.8800 | 121 |
| accuracy | — | — | 0.8302 | 159 |
| macro avg | 0.7760 | 0.8433 | 0.7948 | 159 |
| weighted avg | 0.8678 | 0.8302 | 0.8393 | 159 |

### 9. `mel_40__V1__s44` — `PTQ_INT8`

- Accuracy: **0.8868**
- Balanced accuracy: **0.8715**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 32 | 6 |
| Non-Asthma | 12 | 109 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7273 | 0.8421 | 0.7805 | 38 |
| Non-Asthma | 0.9478 | 0.9008 | 0.9237 | 121 |
| accuracy | — | — | 0.8868 | 159 |
| macro avg | 0.8375 | 0.8715 | 0.8521 | 159 |
| weighted avg | 0.8951 | 0.8868 | 0.8895 | 159 |

### 9. `mel_40__V1__s44` — `QAT_INT8`

- Accuracy: **0.8679**
- Balanced accuracy: **0.8771**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 17 | 104 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.6667 | 0.8947 | 0.7640 | 38 |
| Non-Asthma | 0.9630 | 0.8595 | 0.9083 | 121 |
| accuracy | — | — | 0.8679 | 159 |
| macro avg | 0.8148 | 0.8771 | 0.8362 | 159 |
| weighted avg | 0.8922 | 0.8679 | 0.8738 | 159 |

### 9. `mel_40__V1__s44` — `PTQ_INT16x8`

- Accuracy: **0.8365**
- Balanced accuracy: **0.8474**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 33 | 5 |
| Non-Asthma | 21 | 100 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.6111 | 0.8684 | 0.7174 | 38 |
| Non-Asthma | 0.9524 | 0.8264 | 0.8850 | 121 |
| accuracy | — | — | 0.8365 | 159 |
| macro avg | 0.7817 | 0.8474 | 0.8012 | 159 |
| weighted avg | 0.8708 | 0.8365 | 0.8449 | 159 |

### 10. `fft_2048__V1__s42` — `KERAS_FP32`

- Accuracy: **0.8994**
- Balanced accuracy: **0.8978**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 12 | 109 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7391 | 0.8947 | 0.8095 | 38 |
| Non-Asthma | 0.9646 | 0.9008 | 0.9316 | 121 |
| accuracy | — | — | 0.8994 | 159 |
| macro avg | 0.8519 | 0.8978 | 0.8706 | 159 |
| weighted avg | 0.9107 | 0.8994 | 0.9024 | 159 |

### 10. `fft_2048__V1__s42` — `PTQ_INT8`

- Accuracy: **0.8994**
- Balanced accuracy: **0.8346**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 27 | 11 |
| Non-Asthma | 5 | 116 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8438 | 0.7105 | 0.7714 | 38 |
| Non-Asthma | 0.9134 | 0.9587 | 0.9355 | 121 |
| accuracy | — | — | 0.8994 | 159 |
| macro avg | 0.8786 | 0.8346 | 0.8535 | 159 |
| weighted avg | 0.8967 | 0.8994 | 0.8963 | 159 |

### 10. `fft_2048__V1__s42` — `QAT_INT8`

- Accuracy: **0.8931**
- Balanced accuracy: **0.8666**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 31 | 7 |
| Non-Asthma | 10 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7561 | 0.8158 | 0.7848 | 38 |
| Non-Asthma | 0.9407 | 0.9174 | 0.9289 | 121 |
| accuracy | — | — | 0.8931 | 159 |
| macro avg | 0.8484 | 0.8666 | 0.8568 | 159 |
| weighted avg | 0.8966 | 0.8931 | 0.8944 | 159 |

### 10. `fft_2048__V1__s42` — `PTQ_INT16x8`

- Accuracy: **0.9057**
- Balanced accuracy: **0.9109**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 12 | 109 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7447 | 0.9211 | 0.8235 | 38 |
| Non-Asthma | 0.9732 | 0.9008 | 0.9356 | 121 |
| accuracy | — | — | 0.9057 | 159 |
| macro avg | 0.8589 | 0.9109 | 0.8796 | 159 |
| weighted avg | 0.9186 | 0.9057 | 0.9088 | 159 |

### 11. `fft_2048__V1__s43` — `KERAS_FP32`

- Accuracy: **0.9434**
- Balanced accuracy: **0.9357**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 6 | 115 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8537 | 0.9211 | 0.8861 | 38 |
| Non-Asthma | 0.9746 | 0.9504 | 0.9623 | 121 |
| accuracy | — | — | 0.9434 | 159 |
| macro avg | 0.9141 | 0.9357 | 0.9242 | 159 |
| weighted avg | 0.9457 | 0.9434 | 0.9441 | 159 |

### 11. `fft_2048__V1__s43` — `PTQ_INT8`

- Accuracy: **0.9434**
- Balanced accuracy: **0.9267**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 5 | 116 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8718 | 0.8947 | 0.8831 | 38 |
| Non-Asthma | 0.9667 | 0.9587 | 0.9627 | 121 |
| accuracy | — | — | 0.9434 | 159 |
| macro avg | 0.9192 | 0.9267 | 0.9229 | 159 |
| weighted avg | 0.9440 | 0.9434 | 0.9436 | 159 |

### 11. `fft_2048__V1__s43` — `QAT_INT8`

- Accuracy: **0.9182**
- Balanced accuracy: **0.9102**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 9 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7907 | 0.8947 | 0.8395 | 38 |
| Non-Asthma | 0.9655 | 0.9256 | 0.9451 | 121 |
| accuracy | — | — | 0.9182 | 159 |
| macro avg | 0.8781 | 0.9102 | 0.8923 | 159 |
| weighted avg | 0.9237 | 0.9182 | 0.9199 | 159 |

### 11. `fft_2048__V1__s43` — `PTQ_INT16x8`

- Accuracy: **0.9434**
- Balanced accuracy: **0.9357**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 6 | 115 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8537 | 0.9211 | 0.8861 | 38 |
| Non-Asthma | 0.9746 | 0.9504 | 0.9623 | 121 |
| accuracy | — | — | 0.9434 | 159 |
| macro avg | 0.9141 | 0.9357 | 0.9242 | 159 |
| weighted avg | 0.9457 | 0.9434 | 0.9441 | 159 |

### 12. `fft_2048__V1__s44` — `KERAS_FP32`

- Accuracy: **0.9245**
- Balanced accuracy: **0.9233**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 9 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7955 | 0.9211 | 0.8537 | 38 |
| Non-Asthma | 0.9739 | 0.9256 | 0.9492 | 121 |
| accuracy | — | — | 0.9245 | 159 |
| macro avg | 0.8847 | 0.9233 | 0.9014 | 159 |
| weighted avg | 0.9313 | 0.9245 | 0.9263 | 159 |

### 12. `fft_2048__V1__s44` — `PTQ_INT8`

- Accuracy: **0.9245**
- Balanced accuracy: **0.9233**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 9 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7955 | 0.9211 | 0.8537 | 38 |
| Non-Asthma | 0.9739 | 0.9256 | 0.9492 | 121 |
| accuracy | — | — | 0.9245 | 159 |
| macro avg | 0.8847 | 0.9233 | 0.9014 | 159 |
| weighted avg | 0.9313 | 0.9245 | 0.9263 | 159 |

### 12. `fft_2048__V1__s44` — `QAT_INT8`

- Accuracy: **0.9308**
- Balanced accuracy: **0.9275**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 8 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8140 | 0.9211 | 0.8642 | 38 |
| Non-Asthma | 0.9741 | 0.9339 | 0.9536 | 121 |
| accuracy | — | — | 0.9308 | 159 |
| macro avg | 0.8940 | 0.9275 | 0.9089 | 159 |
| weighted avg | 0.9359 | 0.9308 | 0.9322 | 159 |

### 12. `fft_2048__V1__s44` — `PTQ_INT16x8`

- Accuracy: **0.9182**
- Balanced accuracy: **0.9192**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 10 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7778 | 0.9211 | 0.8434 | 38 |
| Non-Asthma | 0.9737 | 0.9174 | 0.9447 | 121 |
| accuracy | — | — | 0.9182 | 159 |
| macro avg | 0.8757 | 0.9192 | 0.8940 | 159 |
| weighted avg | 0.9269 | 0.9182 | 0.9205 | 159 |

### 13. `combo_pre0_mel40__V1__s42` — `KERAS_FP32`

- Accuracy: **0.9057**
- Balanced accuracy: **0.9109**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 12 | 109 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7447 | 0.9211 | 0.8235 | 38 |
| Non-Asthma | 0.9732 | 0.9008 | 0.9356 | 121 |
| accuracy | — | — | 0.9057 | 159 |
| macro avg | 0.8589 | 0.9109 | 0.8796 | 159 |
| weighted avg | 0.9186 | 0.9057 | 0.9088 | 159 |

### 13. `combo_pre0_mel40__V1__s42` — `PTQ_INT8`

- Accuracy: **0.8931**
- Balanced accuracy: **0.8846**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 33 | 5 |
| Non-Asthma | 12 | 109 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7333 | 0.8684 | 0.7952 | 38 |
| Non-Asthma | 0.9561 | 0.9008 | 0.9277 | 121 |
| accuracy | — | — | 0.8931 | 159 |
| macro avg | 0.8447 | 0.8846 | 0.8614 | 159 |
| weighted avg | 0.9029 | 0.8931 | 0.8960 | 159 |

### 13. `combo_pre0_mel40__V1__s42` — `QAT_INT8`

- Accuracy: **0.9182**
- Balanced accuracy: **0.9102**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 9 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7907 | 0.8947 | 0.8395 | 38 |
| Non-Asthma | 0.9655 | 0.9256 | 0.9451 | 121 |
| accuracy | — | — | 0.9182 | 159 |
| macro avg | 0.8781 | 0.9102 | 0.8923 | 159 |
| weighted avg | 0.9237 | 0.9182 | 0.9199 | 159 |

### 13. `combo_pre0_mel40__V1__s42` — `PTQ_INT16x8`

- Accuracy: **0.9057**
- Balanced accuracy: **0.9109**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 12 | 109 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7447 | 0.9211 | 0.8235 | 38 |
| Non-Asthma | 0.9732 | 0.9008 | 0.9356 | 121 |
| accuracy | — | — | 0.9057 | 159 |
| macro avg | 0.8589 | 0.9109 | 0.8796 | 159 |
| weighted avg | 0.9186 | 0.9057 | 0.9088 | 159 |

### 14. `combo_pre0_mel40__V1__s43` — `KERAS_FP32`

- Accuracy: **0.8868**
- Balanced accuracy: **0.8805**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 33 | 5 |
| Non-Asthma | 13 | 108 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7174 | 0.8684 | 0.7857 | 38 |
| Non-Asthma | 0.9558 | 0.8926 | 0.9231 | 121 |
| accuracy | — | — | 0.8868 | 159 |
| macro avg | 0.8366 | 0.8805 | 0.8544 | 159 |
| weighted avg | 0.8988 | 0.8868 | 0.8902 | 159 |

### 14. `combo_pre0_mel40__V1__s43` — `PTQ_INT8`

- Accuracy: **0.8994**
- Balanced accuracy: **0.8707**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 31 | 7 |
| Non-Asthma | 9 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7750 | 0.8158 | 0.7949 | 38 |
| Non-Asthma | 0.9412 | 0.9256 | 0.9333 | 121 |
| accuracy | — | — | 0.8994 | 159 |
| macro avg | 0.8581 | 0.8707 | 0.8641 | 159 |
| weighted avg | 0.9015 | 0.8994 | 0.9002 | 159 |

### 14. `combo_pre0_mel40__V1__s43` — `QAT_INT8`

- Accuracy: **0.9057**
- Balanced accuracy: **0.8929**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 33 | 5 |
| Non-Asthma | 10 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7674 | 0.8684 | 0.8148 | 38 |
| Non-Asthma | 0.9569 | 0.9174 | 0.9367 | 121 |
| accuracy | — | — | 0.9057 | 159 |
| macro avg | 0.8622 | 0.8929 | 0.8758 | 159 |
| weighted avg | 0.9116 | 0.9057 | 0.9076 | 159 |

### 14. `combo_pre0_mel40__V1__s43` — `PTQ_INT16x8`

- Accuracy: **0.8805**
- Balanced accuracy: **0.8764**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 33 | 5 |
| Non-Asthma | 14 | 107 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7021 | 0.8684 | 0.7765 | 38 |
| Non-Asthma | 0.9554 | 0.8843 | 0.9185 | 121 |
| accuracy | — | — | 0.8805 | 159 |
| macro avg | 0.8287 | 0.8764 | 0.8475 | 159 |
| weighted avg | 0.8948 | 0.8805 | 0.8845 | 159 |

### 15. `combo_pre0_mel40__V1__s44` — `KERAS_FP32`

- Accuracy: **0.9119**
- Balanced accuracy: **0.8970**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 33 | 5 |
| Non-Asthma | 9 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7857 | 0.8684 | 0.8250 | 38 |
| Non-Asthma | 0.9573 | 0.9256 | 0.9412 | 121 |
| accuracy | — | — | 0.9119 | 159 |
| macro avg | 0.8715 | 0.8970 | 0.8831 | 159 |
| weighted avg | 0.9163 | 0.9119 | 0.9134 | 159 |

### 15. `combo_pre0_mel40__V1__s44` — `PTQ_INT8`

- Accuracy: **0.9119**
- Balanced accuracy: **0.8790**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 31 | 7 |
| Non-Asthma | 7 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8158 | 0.8158 | 0.8158 | 38 |
| Non-Asthma | 0.9421 | 0.9421 | 0.9421 | 121 |
| accuracy | — | — | 0.9119 | 159 |
| macro avg | 0.8790 | 0.8790 | 0.8790 | 159 |
| weighted avg | 0.9119 | 0.9119 | 0.9119 | 159 |

### 15. `combo_pre0_mel40__V1__s44` — `QAT_INT8`

- Accuracy: **0.8994**
- Balanced accuracy: **0.8978**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 12 | 109 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7391 | 0.8947 | 0.8095 | 38 |
| Non-Asthma | 0.9646 | 0.9008 | 0.9316 | 121 |
| accuracy | — | — | 0.8994 | 159 |
| macro avg | 0.8519 | 0.8978 | 0.8706 | 159 |
| weighted avg | 0.9107 | 0.8994 | 0.9024 | 159 |

### 15. `combo_pre0_mel40__V1__s44` — `PTQ_INT16x8`

- Accuracy: **0.9119**
- Balanced accuracy: **0.8970**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 33 | 5 |
| Non-Asthma | 9 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7857 | 0.8684 | 0.8250 | 38 |
| Non-Asthma | 0.9573 | 0.9256 | 0.9412 | 121 |
| accuracy | — | — | 0.9119 | 159 |
| macro avg | 0.8715 | 0.8970 | 0.8831 | 159 |
| weighted avg | 0.9163 | 0.9119 | 0.9134 | 159 |

### 16. `combo_pre0_fft2048__V1__s42` — `KERAS_FP32`

- Accuracy: **0.8994**
- Balanced accuracy: **0.8978**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 12 | 109 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7391 | 0.8947 | 0.8095 | 38 |
| Non-Asthma | 0.9646 | 0.9008 | 0.9316 | 121 |
| accuracy | — | — | 0.8994 | 159 |
| macro avg | 0.8519 | 0.8978 | 0.8706 | 159 |
| weighted avg | 0.9107 | 0.8994 | 0.9024 | 159 |

### 16. `combo_pre0_fft2048__V1__s42` — `PTQ_INT8`

- Accuracy: **0.8616**
- Balanced accuracy: **0.7376**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 19 | 19 |
| Non-Asthma | 3 | 118 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8636 | 0.5000 | 0.6333 | 38 |
| Non-Asthma | 0.8613 | 0.9752 | 0.9147 | 121 |
| accuracy | — | — | 0.8616 | 159 |
| macro avg | 0.8625 | 0.7376 | 0.7740 | 159 |
| weighted avg | 0.8619 | 0.8616 | 0.8475 | 159 |

### 16. `combo_pre0_fft2048__V1__s42` — `QAT_INT8`

- Accuracy: **0.8868**
- Balanced accuracy: **0.8534**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 30 | 8 |
| Non-Asthma | 10 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7500 | 0.7895 | 0.7692 | 38 |
| Non-Asthma | 0.9328 | 0.9174 | 0.9250 | 121 |
| accuracy | — | — | 0.8868 | 159 |
| macro avg | 0.8414 | 0.8534 | 0.8471 | 159 |
| weighted avg | 0.8891 | 0.8868 | 0.8878 | 159 |

### 16. `combo_pre0_fft2048__V1__s42` — `PTQ_INT16x8`

- Accuracy: **0.8994**
- Balanced accuracy: **0.8978**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 12 | 109 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7391 | 0.8947 | 0.8095 | 38 |
| Non-Asthma | 0.9646 | 0.9008 | 0.9316 | 121 |
| accuracy | — | — | 0.8994 | 159 |
| macro avg | 0.8519 | 0.8978 | 0.8706 | 159 |
| weighted avg | 0.9107 | 0.8994 | 0.9024 | 159 |

### 17. `combo_pre0_fft2048__V1__s43` — `KERAS_FP32`

- Accuracy: **0.9182**
- Balanced accuracy: **0.9192**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 10 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7778 | 0.9211 | 0.8434 | 38 |
| Non-Asthma | 0.9737 | 0.9174 | 0.9447 | 121 |
| accuracy | — | — | 0.9182 | 159 |
| macro avg | 0.8757 | 0.9192 | 0.8940 | 159 |
| weighted avg | 0.9269 | 0.9182 | 0.9205 | 159 |

### 17. `combo_pre0_fft2048__V1__s43` — `PTQ_INT8`

- Accuracy: **0.9371**
- Balanced accuracy: **0.9316**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 7 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8333 | 0.9211 | 0.8750 | 38 |
| Non-Asthma | 0.9744 | 0.9421 | 0.9580 | 121 |
| accuracy | — | — | 0.9371 | 159 |
| macro avg | 0.9038 | 0.9316 | 0.9165 | 159 |
| weighted avg | 0.9407 | 0.9371 | 0.9382 | 159 |

### 17. `combo_pre0_fft2048__V1__s43` — `QAT_INT8`

- Accuracy: **0.9434**
- Balanced accuracy: **0.9357**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 6 | 115 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8537 | 0.9211 | 0.8861 | 38 |
| Non-Asthma | 0.9746 | 0.9504 | 0.9623 | 121 |
| accuracy | — | — | 0.9434 | 159 |
| macro avg | 0.9141 | 0.9357 | 0.9242 | 159 |
| weighted avg | 0.9457 | 0.9434 | 0.9441 | 159 |

### 17. `combo_pre0_fft2048__V1__s43` — `PTQ_INT16x8`

- Accuracy: **0.9119**
- Balanced accuracy: **0.9151**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 11 | 110 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7609 | 0.9211 | 0.8333 | 38 |
| Non-Asthma | 0.9735 | 0.9091 | 0.9402 | 121 |
| accuracy | — | — | 0.9119 | 159 |
| macro avg | 0.8672 | 0.9151 | 0.8868 | 159 |
| weighted avg | 0.9226 | 0.9119 | 0.9146 | 159 |

### 18. `combo_pre0_fft2048__V1__s44` — `KERAS_FP32`

- Accuracy: **0.8679**
- Balanced accuracy: **0.8861**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 18 | 103 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.6604 | 0.9211 | 0.7692 | 38 |
| Non-Asthma | 0.9717 | 0.8512 | 0.9075 | 121 |
| accuracy | — | — | 0.8679 | 159 |
| macro avg | 0.8160 | 0.8861 | 0.8384 | 159 |
| weighted avg | 0.8973 | 0.8679 | 0.8744 | 159 |

### 18. `combo_pre0_fft2048__V1__s44` — `PTQ_INT8`

- Accuracy: **0.8931**
- Balanced accuracy: **0.9027**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 14 | 107 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7143 | 0.9211 | 0.8046 | 38 |
| Non-Asthma | 0.9727 | 0.8843 | 0.9264 | 121 |
| accuracy | — | — | 0.8931 | 159 |
| macro avg | 0.8435 | 0.9027 | 0.8655 | 159 |
| weighted avg | 0.9110 | 0.8931 | 0.8973 | 159 |

### 18. `combo_pre0_fft2048__V1__s44` — `QAT_INT8`

- Accuracy: **0.9308**
- Balanced accuracy: **0.9275**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 8 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8140 | 0.9211 | 0.8642 | 38 |
| Non-Asthma | 0.9741 | 0.9339 | 0.9536 | 121 |
| accuracy | — | — | 0.9308 | 159 |
| macro avg | 0.8940 | 0.9275 | 0.9089 | 159 |
| weighted avg | 0.9359 | 0.9308 | 0.9322 | 159 |

### 18. `combo_pre0_fft2048__V1__s44` — `PTQ_INT16x8`

- Accuracy: **0.8805**
- Balanced accuracy: **0.8944**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 16 | 105 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.6863 | 0.9211 | 0.7865 | 38 |
| Non-Asthma | 0.9722 | 0.8678 | 0.9170 | 121 |
| accuracy | — | — | 0.8805 | 159 |
| macro avg | 0.8292 | 0.8944 | 0.8518 | 159 |
| weighted avg | 0.9039 | 0.8805 | 0.8858 | 159 |

### 19. `combo_mel40_fft2048__V1__s42` — `KERAS_FP32`

- Accuracy: **0.8931**
- Balanced accuracy: **0.8936**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 13 | 108 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7234 | 0.8947 | 0.8000 | 38 |
| Non-Asthma | 0.9643 | 0.8926 | 0.9270 | 121 |
| accuracy | — | — | 0.8931 | 159 |
| macro avg | 0.8438 | 0.8936 | 0.8635 | 159 |
| weighted avg | 0.9067 | 0.8931 | 0.8967 | 159 |

### 19. `combo_mel40_fft2048__V1__s42` — `PTQ_INT8`

- Accuracy: **0.9119**
- Balanced accuracy: **0.8429**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 27 | 11 |
| Non-Asthma | 3 | 118 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9000 | 0.7105 | 0.7941 | 38 |
| Non-Asthma | 0.9147 | 0.9752 | 0.9440 | 121 |
| accuracy | — | — | 0.9119 | 159 |
| macro avg | 0.9074 | 0.8429 | 0.8691 | 159 |
| weighted avg | 0.9112 | 0.9119 | 0.9082 | 159 |

### 19. `combo_mel40_fft2048__V1__s42` — `QAT_INT8`

- Accuracy: **0.9057**
- Balanced accuracy: **0.9019**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 11 | 110 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7556 | 0.8947 | 0.8193 | 38 |
| Non-Asthma | 0.9649 | 0.9091 | 0.9362 | 121 |
| accuracy | — | — | 0.9057 | 159 |
| macro avg | 0.8602 | 0.9019 | 0.8777 | 159 |
| weighted avg | 0.9149 | 0.9057 | 0.9082 | 159 |

### 19. `combo_mel40_fft2048__V1__s42` — `PTQ_INT16x8`

- Accuracy: **0.8931**
- Balanced accuracy: **0.8936**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 13 | 108 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7234 | 0.8947 | 0.8000 | 38 |
| Non-Asthma | 0.9643 | 0.8926 | 0.9270 | 121 |
| accuracy | — | — | 0.8931 | 159 |
| macro avg | 0.8438 | 0.8936 | 0.8635 | 159 |
| weighted avg | 0.9067 | 0.8931 | 0.8967 | 159 |

### 20. `combo_mel40_fft2048__V1__s43` — `KERAS_FP32`

- Accuracy: **0.9057**
- Balanced accuracy: **0.9019**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 11 | 110 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7556 | 0.8947 | 0.8193 | 38 |
| Non-Asthma | 0.9649 | 0.9091 | 0.9362 | 121 |
| accuracy | — | — | 0.9057 | 159 |
| macro avg | 0.8602 | 0.9019 | 0.8777 | 159 |
| weighted avg | 0.9149 | 0.9057 | 0.9082 | 159 |

### 20. `combo_mel40_fft2048__V1__s43` — `PTQ_INT8`

- Accuracy: **0.9182**
- Balanced accuracy: **0.8741**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 30 | 8 |
| Non-Asthma | 5 | 116 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8571 | 0.7895 | 0.8219 | 38 |
| Non-Asthma | 0.9355 | 0.9587 | 0.9469 | 121 |
| accuracy | — | — | 0.9182 | 159 |
| macro avg | 0.8963 | 0.8741 | 0.8844 | 159 |
| weighted avg | 0.9168 | 0.9182 | 0.9171 | 159 |

### 20. `combo_mel40_fft2048__V1__s43` — `QAT_INT8`

- Accuracy: **0.9245**
- Balanced accuracy: **0.9233**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 9 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7955 | 0.9211 | 0.8537 | 38 |
| Non-Asthma | 0.9739 | 0.9256 | 0.9492 | 121 |
| accuracy | — | — | 0.9245 | 159 |
| macro avg | 0.8847 | 0.9233 | 0.9014 | 159 |
| weighted avg | 0.9313 | 0.9245 | 0.9263 | 159 |

### 20. `combo_mel40_fft2048__V1__s43` — `PTQ_INT16x8`

- Accuracy: **0.9057**
- Balanced accuracy: **0.9019**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 11 | 110 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7556 | 0.8947 | 0.8193 | 38 |
| Non-Asthma | 0.9649 | 0.9091 | 0.9362 | 121 |
| accuracy | — | — | 0.9057 | 159 |
| macro avg | 0.8602 | 0.9019 | 0.8777 | 159 |
| weighted avg | 0.9149 | 0.9057 | 0.9082 | 159 |

### 21. `combo_mel40_fft2048__V1__s44` — `KERAS_FP32`

- Accuracy: **0.9057**
- Balanced accuracy: **0.8929**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 33 | 5 |
| Non-Asthma | 10 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7674 | 0.8684 | 0.8148 | 38 |
| Non-Asthma | 0.9569 | 0.9174 | 0.9367 | 121 |
| accuracy | — | — | 0.9057 | 159 |
| macro avg | 0.8622 | 0.8929 | 0.8758 | 159 |
| weighted avg | 0.9116 | 0.9057 | 0.9076 | 159 |

### 21. `combo_mel40_fft2048__V1__s44` — `PTQ_INT8`

- Accuracy: **0.9057**
- Balanced accuracy: **0.8929**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 33 | 5 |
| Non-Asthma | 10 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7674 | 0.8684 | 0.8148 | 38 |
| Non-Asthma | 0.9569 | 0.9174 | 0.9367 | 121 |
| accuracy | — | — | 0.9057 | 159 |
| macro avg | 0.8622 | 0.8929 | 0.8758 | 159 |
| weighted avg | 0.9116 | 0.9057 | 0.9076 | 159 |

### 21. `combo_mel40_fft2048__V1__s44` — `QAT_INT8`

- Accuracy: **0.9119**
- Balanced accuracy: **0.8970**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 33 | 5 |
| Non-Asthma | 9 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7857 | 0.8684 | 0.8250 | 38 |
| Non-Asthma | 0.9573 | 0.9256 | 0.9412 | 121 |
| accuracy | — | — | 0.9119 | 159 |
| macro avg | 0.8715 | 0.8970 | 0.8831 | 159 |
| weighted avg | 0.9163 | 0.9119 | 0.9134 | 159 |

### 21. `combo_mel40_fft2048__V1__s44` — `PTQ_INT16x8`

- Accuracy: **0.9057**
- Balanced accuracy: **0.8929**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 33 | 5 |
| Non-Asthma | 10 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7674 | 0.8684 | 0.8148 | 38 |
| Non-Asthma | 0.9569 | 0.9174 | 0.9367 | 121 |
| accuracy | — | — | 0.9057 | 159 |
| macro avg | 0.8622 | 0.8929 | 0.8758 | 159 |
| weighted avg | 0.9116 | 0.9057 | 0.9076 | 159 |

### 22. `combo_pre0_mel40_fft2048__V1__s42` — `KERAS_FP32`

- Accuracy: **0.9119**
- Balanced accuracy: **0.8970**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 33 | 5 |
| Non-Asthma | 9 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7857 | 0.8684 | 0.8250 | 38 |
| Non-Asthma | 0.9573 | 0.9256 | 0.9412 | 121 |
| accuracy | — | — | 0.9119 | 159 |
| macro avg | 0.8715 | 0.8970 | 0.8831 | 159 |
| weighted avg | 0.9163 | 0.9119 | 0.9134 | 159 |

### 22. `combo_pre0_mel40_fft2048__V1__s42` — `PTQ_INT8`

- Accuracy: **0.8616**
- Balanced accuracy: **0.7827**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 24 | 14 |
| Non-Asthma | 8 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7500 | 0.6316 | 0.6857 | 38 |
| Non-Asthma | 0.8898 | 0.9339 | 0.9113 | 121 |
| accuracy | — | — | 0.8616 | 159 |
| macro avg | 0.8199 | 0.7827 | 0.7985 | 159 |
| weighted avg | 0.8564 | 0.8616 | 0.8574 | 159 |

### 22. `combo_pre0_mel40_fft2048__V1__s42` — `QAT_INT8`

- Accuracy: **0.9245**
- Balanced accuracy: **0.9233**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 9 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7955 | 0.9211 | 0.8537 | 38 |
| Non-Asthma | 0.9739 | 0.9256 | 0.9492 | 121 |
| accuracy | — | — | 0.9245 | 159 |
| macro avg | 0.8847 | 0.9233 | 0.9014 | 159 |
| weighted avg | 0.9313 | 0.9245 | 0.9263 | 159 |

### 22. `combo_pre0_mel40_fft2048__V1__s42` — `PTQ_INT16x8`

- Accuracy: **0.9182**
- Balanced accuracy: **0.9102**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 9 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.7907 | 0.8947 | 0.8395 | 38 |
| Non-Asthma | 0.9655 | 0.9256 | 0.9451 | 121 |
| accuracy | — | — | 0.9182 | 159 |
| macro avg | 0.8781 | 0.9102 | 0.8923 | 159 |
| weighted avg | 0.9237 | 0.9182 | 0.9199 | 159 |

### 23. `combo_pre0_mel40_fft2048__V1__s43` — `KERAS_FP32`

- Accuracy: **0.9308**
- Balanced accuracy: **0.9275**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 8 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8140 | 0.9211 | 0.8642 | 38 |
| Non-Asthma | 0.9741 | 0.9339 | 0.9536 | 121 |
| accuracy | — | — | 0.9308 | 159 |
| macro avg | 0.8940 | 0.9275 | 0.9089 | 159 |
| weighted avg | 0.9359 | 0.9308 | 0.9322 | 159 |

### 23. `combo_pre0_mel40_fft2048__V1__s43` — `PTQ_INT8`

- Accuracy: **0.9245**
- Balanced accuracy: **0.8963**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 32 | 6 |
| Non-Asthma | 6 | 115 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8421 | 0.8421 | 0.8421 | 38 |
| Non-Asthma | 0.9504 | 0.9504 | 0.9504 | 121 |
| accuracy | — | — | 0.9245 | 159 |
| macro avg | 0.8963 | 0.8963 | 0.8963 | 159 |
| weighted avg | 0.9245 | 0.9245 | 0.9245 | 159 |

### 23. `combo_pre0_mel40_fft2048__V1__s43` — `QAT_INT8`

- Accuracy: **0.9371**
- Balanced accuracy: **0.9226**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 6 | 115 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8500 | 0.8947 | 0.8718 | 38 |
| Non-Asthma | 0.9664 | 0.9504 | 0.9583 | 121 |
| accuracy | — | — | 0.9371 | 159 |
| macro avg | 0.9082 | 0.9226 | 0.9151 | 159 |
| weighted avg | 0.9386 | 0.9371 | 0.9377 | 159 |

### 23. `combo_pre0_mel40_fft2048__V1__s43` — `PTQ_INT16x8`

- Accuracy: **0.9308**
- Balanced accuracy: **0.9275**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 8 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8140 | 0.9211 | 0.8642 | 38 |
| Non-Asthma | 0.9741 | 0.9339 | 0.9536 | 121 |
| accuracy | — | — | 0.9308 | 159 |
| macro avg | 0.8940 | 0.9275 | 0.9089 | 159 |
| weighted avg | 0.9359 | 0.9308 | 0.9322 | 159 |

### 24. `combo_pre0_mel40_fft2048__V1__s44` — `KERAS_FP32`

- Accuracy: **0.9057**
- Balanced accuracy: **0.8658**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 30 | 8 |
| Non-Asthma | 7 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8108 | 0.7895 | 0.8000 | 38 |
| Non-Asthma | 0.9344 | 0.9421 | 0.9383 | 121 |
| accuracy | — | — | 0.9057 | 159 |
| macro avg | 0.8726 | 0.8658 | 0.8691 | 159 |
| weighted avg | 0.9049 | 0.9057 | 0.9052 | 159 |

### 24. `combo_pre0_mel40_fft2048__V1__s44` — `PTQ_INT8`

- Accuracy: **0.9245**
- Balanced accuracy: **0.8782**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 30 | 8 |
| Non-Asthma | 4 | 117 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8824 | 0.7895 | 0.8333 | 38 |
| Non-Asthma | 0.9360 | 0.9669 | 0.9512 | 121 |
| accuracy | — | — | 0.9245 | 159 |
| macro avg | 0.9092 | 0.8782 | 0.8923 | 159 |
| weighted avg | 0.9232 | 0.9245 | 0.9230 | 159 |

### 24. `combo_pre0_mel40_fft2048__V1__s44` — `QAT_INT8`

- Accuracy: **0.9560**
- Balanced accuracy: **0.9440**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 4 | 117 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8974 | 0.9211 | 0.9091 | 38 |
| Non-Asthma | 0.9750 | 0.9669 | 0.9710 | 121 |
| accuracy | — | — | 0.9560 | 159 |
| macro avg | 0.9362 | 0.9440 | 0.9400 | 159 |
| weighted avg | 0.9565 | 0.9560 | 0.9562 | 159 |

### 24. `combo_pre0_mel40_fft2048__V1__s44` — `PTQ_INT16x8`

- Accuracy: **0.9057**
- Balanced accuracy: **0.8658**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 30 | 8 |
| Non-Asthma | 7 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8108 | 0.7895 | 0.8000 | 38 |
| Non-Asthma | 0.9344 | 0.9421 | 0.9383 | 121 |
| accuracy | — | — | 0.9057 | 159 |
| macro avg | 0.8726 | 0.8658 | 0.8691 | 159 |
| weighted avg | 0.9049 | 0.9057 | 0.9052 | 159 |

## Trạng thái

- Đã có kết quả: **96/96** tổ hợp, bao gồm FP32 đối chứng.
- Báo cáo không tự thay đổi thứ tự ưu tiên checkpoint đã chuyển giao từ bước C.
- Validation có thể dùng để so sánh method lượng tử; historical Test chỉ dùng báo cáo sau khi phạm vi đã khóa.
- INT16x8 cần đường inference `int16_t`; không thay trực tiếp model INT8 hiện tại.
