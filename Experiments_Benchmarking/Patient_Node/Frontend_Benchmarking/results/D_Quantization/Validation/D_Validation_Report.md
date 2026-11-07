# Báo cáo lượng tử hóa Frontend — Validation

- Plan SHA256: `8258e0c64948a6d2916f84089bd590f40c8b026b22f713e5bfe1845dabbe544d`
- Split đánh giá: **Validation**
- Test accessed: **false**
- Thứ tự checkpoint được bàn giao từ phân tích bước C.

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

## Kết quả Validation

| Ưu tiên | Trial | Method | Accuracy | Macro F1 | Asthma Recall | Non-Asthma Recall | Đổi nhãn so với FP32 | Kích thước (byte) | I/O |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | `F0__V1__s42` | `KERAS_FP32` | 0.9416 | 0.9258 | 0.9737 | 0.9310 | 0 | 6402662 | float32 → float32 |
| 1 | `F0__V1__s42` | `PTQ_INT8` | 0.9545 | 0.9404 | 0.9474 | 0.9569 | 4 | 543976 | int8 → int8 |
| 1 | `F0__V1__s42` | `QAT_INT8` | 0.9545 | 0.9414 | 0.9737 | 0.9483 | 2 | 544568 | int8 → int8 |
| 1 | `F0__V1__s42` | `PTQ_INT16x8` | 0.9416 | 0.9258 | 0.9737 | 0.9310 | 0 | 547744 | int16 → int16 |
| 2 | `F0__V1__s43` | `KERAS_FP32` | 0.9740 | 0.9657 | 0.9737 | 0.9741 | 0 | 6402662 | float32 → float32 |
| 2 | `F0__V1__s43` | `PTQ_INT8` | 0.9610 | 0.9476 | 0.9211 | 0.9741 | 2 | 543976 | int8 → int8 |
| 2 | `F0__V1__s43` | `QAT_INT8` | 0.9610 | 0.9476 | 0.9211 | 0.9741 | 6 | 544568 | int8 → int8 |
| 2 | `F0__V1__s43` | `PTQ_INT16x8` | 0.9740 | 0.9657 | 0.9737 | 0.9741 | 0 | 547744 | int16 → int16 |
| 3 | `F0__V1__s44` | `KERAS_FP32` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0 | 6402662 | float32 → float32 |
| 3 | `F0__V1__s44` | `PTQ_INT8` | 0.9805 | 0.9736 | 0.9474 | 0.9914 | 3 | 543976 | int8 → int8 |
| 3 | `F0__V1__s44` | `QAT_INT8` | 0.9870 | 0.9828 | 1.0000 | 0.9828 | 2 | 544568 | int8 → int8 |
| 3 | `F0__V1__s44` | `PTQ_INT16x8` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0 | 547744 | int16 → int16 |
| 4 | `pre_0__V1__s42` | `KERAS_FP32` | 0.9610 | 0.9501 | 1.0000 | 0.9483 | 0 | 6402662 | float32 → float32 |
| 4 | `pre_0__V1__s42` | `PTQ_INT8` | 0.8961 | 0.8422 | 0.6316 | 0.9828 | 20 | 543976 | int8 → int8 |
| 4 | `pre_0__V1__s42` | `QAT_INT8` | 0.9675 | 0.9581 | 1.0000 | 0.9569 | 5 | 544568 | int8 → int8 |
| 4 | `pre_0__V1__s42` | `PTQ_INT16x8` | 0.9675 | 0.9581 | 1.0000 | 0.9569 | 1 | 547744 | int16 → int16 |
| 5 | `pre_0__V1__s43` | `KERAS_FP32` | 0.9610 | 0.9485 | 0.9474 | 0.9655 | 0 | 6402662 | float32 → float32 |
| 5 | `pre_0__V1__s43` | `PTQ_INT8` | 0.9416 | 0.9221 | 0.8947 | 0.9569 | 5 | 543976 | int8 → int8 |
| 5 | `pre_0__V1__s43` | `QAT_INT8` | 0.9740 | 0.9651 | 0.9474 | 0.9828 | 4 | 544568 | int8 → int8 |
| 5 | `pre_0__V1__s43` | `PTQ_INT16x8` | 0.9610 | 0.9485 | 0.9474 | 0.9655 | 0 | 547744 | int16 → int16 |
| 6 | `pre_0__V1__s44` | `KERAS_FP32` | 0.9935 | 0.9913 | 1.0000 | 0.9914 | 0 | 6402662 | float32 → float32 |
| 6 | `pre_0__V1__s44` | `PTQ_INT8` | 0.9935 | 0.9913 | 1.0000 | 0.9914 | 2 | 543976 | int8 → int8 |
| 6 | `pre_0__V1__s44` | `QAT_INT8` | 0.9870 | 0.9828 | 1.0000 | 0.9828 | 3 | 544568 | int8 → int8 |
| 6 | `pre_0__V1__s44` | `PTQ_INT16x8` | 0.9935 | 0.9913 | 1.0000 | 0.9914 | 0 | 547744 | int16 → int16 |
| 7 | `mel_40__V1__s42` | `KERAS_FP32` | 0.9805 | 0.9745 | 1.0000 | 0.9741 | 0 | 4043366 | float32 → float32 |
| 7 | `mel_40__V1__s42` | `PTQ_INT8` | 0.9221 | 0.8891 | 0.7632 | 0.9741 | 11 | 347368 | int8 → int8 |
| 7 | `mel_40__V1__s42` | `QAT_INT8` | 0.9675 | 0.9581 | 1.0000 | 0.9569 | 2 | 347960 | int8 → int8 |
| 7 | `mel_40__V1__s42` | `PTQ_INT16x8` | 0.9805 | 0.9745 | 1.0000 | 0.9741 | 0 | 351136 | int16 → int16 |
| 8 | `mel_40__V1__s43` | `KERAS_FP32` | 0.9610 | 0.9501 | 1.0000 | 0.9483 | 0 | 4043366 | float32 → float32 |
| 8 | `mel_40__V1__s43` | `PTQ_INT8` | 0.9805 | 0.9740 | 0.9737 | 0.9828 | 7 | 347368 | int8 → int8 |
| 8 | `mel_40__V1__s43` | `QAT_INT8` | 0.9675 | 0.9581 | 1.0000 | 0.9569 | 5 | 347960 | int8 → int8 |
| 8 | `mel_40__V1__s43` | `PTQ_INT16x8` | 0.9610 | 0.9501 | 1.0000 | 0.9483 | 0 | 351136 | int16 → int16 |
| 9 | `mel_40__V1__s44` | `KERAS_FP32` | 0.9545 | 0.9404 | 0.9474 | 0.9569 | 0 | 4043366 | float32 → float32 |
| 9 | `mel_40__V1__s44` | `PTQ_INT8` | 0.9805 | 0.9731 | 0.9211 | 1.0000 | 6 | 347368 | int8 → int8 |
| 9 | `mel_40__V1__s44` | `QAT_INT8` | 0.9870 | 0.9828 | 1.0000 | 0.9828 | 5 | 347960 | int8 → int8 |
| 9 | `mel_40__V1__s44` | `PTQ_INT16x8` | 0.9481 | 0.9313 | 0.9211 | 0.9569 | 1 | 351136 | int16 → int16 |
| 10 | `fft_2048__V1__s42` | `KERAS_FP32` | 0.9675 | 0.9567 | 0.9474 | 0.9741 | 0 | 6402662 | float32 → float32 |
| 10 | `fft_2048__V1__s42` | `PTQ_INT8` | 0.9416 | 0.9160 | 0.7895 | 0.9914 | 10 | 543976 | int8 → int8 |
| 10 | `fft_2048__V1__s42` | `QAT_INT8` | 0.9545 | 0.9383 | 0.8947 | 0.9741 | 4 | 544576 | int8 → int8 |
| 10 | `fft_2048__V1__s42` | `PTQ_INT16x8` | 0.9675 | 0.9567 | 0.9474 | 0.9741 | 0 | 547744 | int16 → int16 |
| 11 | `fft_2048__V1__s43` | `KERAS_FP32` | 0.9675 | 0.9581 | 1.0000 | 0.9569 | 0 | 6402662 | float32 → float32 |
| 11 | `fft_2048__V1__s43` | `PTQ_INT8` | 0.9610 | 0.9485 | 0.9474 | 0.9655 | 5 | 543976 | int8 → int8 |
| 11 | `fft_2048__V1__s43` | `QAT_INT8` | 0.9805 | 0.9745 | 1.0000 | 0.9741 | 2 | 544576 | int8 → int8 |
| 11 | `fft_2048__V1__s43` | `PTQ_INT16x8` | 0.9740 | 0.9662 | 1.0000 | 0.9655 | 1 | 547744 | int16 → int16 |
| 12 | `fft_2048__V1__s44` | `KERAS_FP32` | 0.9740 | 0.9662 | 1.0000 | 0.9655 | 0 | 6402662 | float32 → float32 |
| 12 | `fft_2048__V1__s44` | `PTQ_INT8` | 0.9805 | 0.9745 | 1.0000 | 0.9741 | 5 | 543976 | int8 → int8 |
| 12 | `fft_2048__V1__s44` | `QAT_INT8` | 0.9740 | 0.9662 | 1.0000 | 0.9655 | 4 | 544576 | int8 → int8 |
| 12 | `fft_2048__V1__s44` | `PTQ_INT16x8` | 0.9740 | 0.9662 | 1.0000 | 0.9655 | 0 | 547744 | int16 → int16 |
| 13 | `combo_pre0_mel40__V1__s42` | `KERAS_FP32` | 0.9675 | 0.9581 | 1.0000 | 0.9569 | 0 | 4043366 | float32 → float32 |
| 13 | `combo_pre0_mel40__V1__s42` | `PTQ_INT8` | 0.8896 | 0.8444 | 0.7105 | 0.9483 | 16 | 347368 | int8 → int8 |
| 13 | `combo_pre0_mel40__V1__s42` | `QAT_INT8` | 0.9805 | 0.9745 | 1.0000 | 0.9741 | 6 | 347968 | int8 → int8 |
| 13 | `combo_pre0_mel40__V1__s42` | `PTQ_INT16x8` | 0.9675 | 0.9581 | 1.0000 | 0.9569 | 0 | 351136 | int16 → int16 |
| 14 | `combo_pre0_mel40__V1__s43` | `KERAS_FP32` | 0.9870 | 0.9828 | 1.0000 | 0.9828 | 0 | 4043366 | float32 → float32 |
| 14 | `combo_pre0_mel40__V1__s43` | `PTQ_INT8` | 0.9740 | 0.9651 | 0.9474 | 0.9828 | 4 | 347368 | int8 → int8 |
| 14 | `combo_pre0_mel40__V1__s43` | `QAT_INT8` | 0.9675 | 0.9574 | 0.9737 | 0.9655 | 5 | 347968 | int8 → int8 |
| 14 | `combo_pre0_mel40__V1__s43` | `PTQ_INT16x8` | 0.9870 | 0.9828 | 1.0000 | 0.9828 | 0 | 351136 | int16 → int16 |
| 15 | `combo_pre0_mel40__V1__s44` | `KERAS_FP32` | 0.9935 | 0.9913 | 1.0000 | 0.9914 | 0 | 4043366 | float32 → float32 |
| 15 | `combo_pre0_mel40__V1__s44` | `PTQ_INT8` | 0.9610 | 0.9466 | 0.8947 | 0.9828 | 5 | 347368 | int8 → int8 |
| 15 | `combo_pre0_mel40__V1__s44` | `QAT_INT8` | 0.9805 | 0.9740 | 0.9737 | 0.9828 | 4 | 347968 | int8 → int8 |
| 15 | `combo_pre0_mel40__V1__s44` | `PTQ_INT16x8` | 0.9935 | 0.9913 | 1.0000 | 0.9914 | 0 | 351136 | int16 → int16 |
| 16 | `combo_pre0_fft2048__V1__s42` | `KERAS_FP32` | 0.9740 | 0.9657 | 0.9737 | 0.9741 | 0 | 6402662 | float32 → float32 |
| 16 | `combo_pre0_fft2048__V1__s42` | `PTQ_INT8` | 0.9156 | 0.8733 | 0.6842 | 0.9914 | 13 | 543976 | int8 → int8 |
| 16 | `combo_pre0_fft2048__V1__s42` | `QAT_INT8` | 0.9675 | 0.9567 | 0.9474 | 0.9741 | 3 | 544576 | int8 → int8 |
| 16 | `combo_pre0_fft2048__V1__s42` | `PTQ_INT16x8` | 0.9675 | 0.9574 | 0.9737 | 0.9655 | 1 | 547744 | int16 → int16 |
| 17 | `combo_pre0_fft2048__V1__s43` | `KERAS_FP32` | 0.9805 | 0.9745 | 1.0000 | 0.9741 | 0 | 6402662 | float32 → float32 |
| 17 | `combo_pre0_fft2048__V1__s43` | `PTQ_INT8` | 0.9610 | 0.9493 | 0.9737 | 0.9569 | 7 | 543976 | int8 → int8 |
| 17 | `combo_pre0_fft2048__V1__s43` | `QAT_INT8` | 0.9610 | 0.9485 | 0.9474 | 0.9655 | 5 | 544576 | int8 → int8 |
| 17 | `combo_pre0_fft2048__V1__s43` | `PTQ_INT16x8` | 0.9805 | 0.9745 | 1.0000 | 0.9741 | 0 | 547744 | int16 → int16 |
| 18 | `combo_pre0_fft2048__V1__s44` | `KERAS_FP32` | 0.9675 | 0.9581 | 1.0000 | 0.9569 | 0 | 6402662 | float32 → float32 |
| 18 | `combo_pre0_fft2048__V1__s44` | `PTQ_INT8` | 0.9740 | 0.9662 | 1.0000 | 0.9655 | 3 | 543976 | int8 → int8 |
| 18 | `combo_pre0_fft2048__V1__s44` | `QAT_INT8` | 0.9870 | 0.9825 | 0.9737 | 0.9914 | 5 | 544576 | int8 → int8 |
| 18 | `combo_pre0_fft2048__V1__s44` | `PTQ_INT16x8` | 0.9740 | 0.9662 | 1.0000 | 0.9655 | 1 | 547744 | int16 → int16 |
| 19 | `combo_mel40_fft2048__V1__s42` | `KERAS_FP32` | 0.9610 | 0.9501 | 1.0000 | 0.9483 | 0 | 4043366 | float32 → float32 |
| 19 | `combo_mel40_fft2048__V1__s42` | `PTQ_INT8` | 0.9351 | 0.9036 | 0.7368 | 1.0000 | 16 | 347368 | int8 → int8 |
| 19 | `combo_mel40_fft2048__V1__s42` | `QAT_INT8` | 0.9545 | 0.9383 | 0.8947 | 0.9741 | 9 | 347968 | int8 → int8 |
| 19 | `combo_mel40_fft2048__V1__s42` | `PTQ_INT16x8` | 0.9610 | 0.9501 | 1.0000 | 0.9483 | 0 | 351136 | int16 → int16 |
| 20 | `combo_mel40_fft2048__V1__s43` | `KERAS_FP32` | 0.9740 | 0.9662 | 1.0000 | 0.9655 | 0 | 4043366 | float32 → float32 |
| 20 | `combo_mel40_fft2048__V1__s43` | `PTQ_INT8` | 0.9740 | 0.9651 | 0.9474 | 0.9828 | 4 | 347368 | int8 → int8 |
| 20 | `combo_mel40_fft2048__V1__s43` | `QAT_INT8` | 0.9870 | 0.9828 | 1.0000 | 0.9828 | 2 | 347968 | int8 → int8 |
| 20 | `combo_mel40_fft2048__V1__s43` | `PTQ_INT16x8` | 0.9740 | 0.9662 | 1.0000 | 0.9655 | 0 | 351136 | int16 → int16 |
| 21 | `combo_mel40_fft2048__V1__s44` | `KERAS_FP32` | 0.9805 | 0.9745 | 1.0000 | 0.9741 | 0 | 4043366 | float32 → float32 |
| 21 | `combo_mel40_fft2048__V1__s44` | `PTQ_INT8` | 0.9805 | 0.9740 | 0.9737 | 0.9828 | 2 | 347368 | int8 → int8 |
| 21 | `combo_mel40_fft2048__V1__s44` | `QAT_INT8` | 0.9805 | 0.9736 | 0.9474 | 0.9914 | 4 | 347968 | int8 → int8 |
| 21 | `combo_mel40_fft2048__V1__s44` | `PTQ_INT16x8` | 0.9805 | 0.9745 | 1.0000 | 0.9741 | 0 | 351136 | int16 → int16 |
| 22 | `combo_pre0_mel40_fft2048__V1__s42` | `KERAS_FP32` | 0.9740 | 0.9651 | 0.9474 | 0.9828 | 0 | 4043366 | float32 → float32 |
| 22 | `combo_pre0_mel40_fft2048__V1__s42` | `PTQ_INT8` | 0.9026 | 0.8569 | 0.6842 | 0.9741 | 13 | 347368 | int8 → int8 |
| 22 | `combo_pre0_mel40_fft2048__V1__s42` | `QAT_INT8` | 0.9675 | 0.9574 | 0.9737 | 0.9655 | 3 | 347968 | int8 → int8 |
| 22 | `combo_pre0_mel40_fft2048__V1__s42` | `PTQ_INT16x8` | 0.9740 | 0.9651 | 0.9474 | 0.9828 | 0 | 351136 | int16 → int16 |
| 23 | `combo_pre0_mel40_fft2048__V1__s43` | `KERAS_FP32` | 0.9805 | 0.9745 | 1.0000 | 0.9741 | 0 | 4043366 | float32 → float32 |
| 23 | `combo_pre0_mel40_fft2048__V1__s43` | `PTQ_INT8` | 0.9935 | 0.9913 | 1.0000 | 0.9914 | 2 | 347368 | int8 → int8 |
| 23 | `combo_pre0_mel40_fft2048__V1__s43` | `QAT_INT8` | 0.9675 | 0.9581 | 1.0000 | 0.9569 | 4 | 347968 | int8 → int8 |
| 23 | `combo_pre0_mel40_fft2048__V1__s43` | `PTQ_INT16x8` | 0.9805 | 0.9745 | 1.0000 | 0.9741 | 0 | 351136 | int16 → int16 |
| 24 | `combo_pre0_mel40_fft2048__V1__s44` | `KERAS_FP32` | 0.9870 | 0.9828 | 1.0000 | 0.9828 | 0 | 4043366 | float32 → float32 |
| 24 | `combo_pre0_mel40_fft2048__V1__s44` | `PTQ_INT8` | 0.9610 | 0.9445 | 0.8421 | 1.0000 | 8 | 347368 | int8 → int8 |
| 24 | `combo_pre0_mel40_fft2048__V1__s44` | `QAT_INT8` | 0.9740 | 0.9657 | 0.9737 | 0.9741 | 6 | 347968 | int8 → int8 |
| 24 | `combo_pre0_mel40_fft2048__V1__s44` | `PTQ_INT16x8` | 0.9870 | 0.9828 | 1.0000 | 0.9828 | 0 | 351136 | int16 → int16 |

## Confusion matrix và classification report

Quy ước: nhãn `0 = Asthma`, nhãn `1 = Non-Asthma`, hàng là nhãn thật và cột là nhãn dự đoán.

### 1. `F0__V1__s42` — `KERAS_FP32`

- Accuracy: **0.9416**
- Balanced accuracy: **0.9524**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 37 | 1 |
| Non-Asthma | 8 | 108 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8222 | 0.9737 | 0.8916 | 38 |
| Non-Asthma | 0.9908 | 0.9310 | 0.9600 | 116 |
| accuracy | — | — | 0.9416 | 154 |
| macro avg | 0.9065 | 0.9524 | 0.9258 | 154 |
| weighted avg | 0.9492 | 0.9416 | 0.9431 | 154 |

### 1. `F0__V1__s42` — `PTQ_INT8`

- Accuracy: **0.9545**
- Balanced accuracy: **0.9521**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 36 | 2 |
| Non-Asthma | 5 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8780 | 0.9474 | 0.9114 | 38 |
| Non-Asthma | 0.9823 | 0.9569 | 0.9694 | 116 |
| accuracy | — | — | 0.9545 | 154 |
| macro avg | 0.9302 | 0.9521 | 0.9404 | 154 |
| weighted avg | 0.9566 | 0.9545 | 0.9551 | 154 |

### 1. `F0__V1__s42` — `QAT_INT8`

- Accuracy: **0.9545**
- Balanced accuracy: **0.9610**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 37 | 1 |
| Non-Asthma | 6 | 110 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8605 | 0.9737 | 0.9136 | 38 |
| Non-Asthma | 0.9910 | 0.9483 | 0.9692 | 116 |
| accuracy | — | — | 0.9545 | 154 |
| macro avg | 0.9257 | 0.9610 | 0.9414 | 154 |
| weighted avg | 0.9588 | 0.9545 | 0.9554 | 154 |

### 1. `F0__V1__s42` — `PTQ_INT16x8`

- Accuracy: **0.9416**
- Balanced accuracy: **0.9524**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 37 | 1 |
| Non-Asthma | 8 | 108 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8222 | 0.9737 | 0.8916 | 38 |
| Non-Asthma | 0.9908 | 0.9310 | 0.9600 | 116 |
| accuracy | — | — | 0.9416 | 154 |
| macro avg | 0.9065 | 0.9524 | 0.9258 | 154 |
| weighted avg | 0.9492 | 0.9416 | 0.9431 | 154 |

### 2. `F0__V1__s43` — `KERAS_FP32`

- Accuracy: **0.9740**
- Balanced accuracy: **0.9739**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 37 | 1 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9250 | 0.9737 | 0.9487 | 38 |
| Non-Asthma | 0.9912 | 0.9741 | 0.9826 | 116 |
| accuracy | — | — | 0.9740 | 154 |
| macro avg | 0.9581 | 0.9739 | 0.9657 | 154 |
| weighted avg | 0.9749 | 0.9740 | 0.9742 | 154 |

### 2. `F0__V1__s43` — `PTQ_INT8`

- Accuracy: **0.9610**
- Balanced accuracy: **0.9476**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9211 | 0.9211 | 0.9211 | 38 |
| Non-Asthma | 0.9741 | 0.9741 | 0.9741 | 116 |
| accuracy | — | — | 0.9610 | 154 |
| macro avg | 0.9476 | 0.9476 | 0.9476 | 154 |
| weighted avg | 0.9610 | 0.9610 | 0.9610 | 154 |

### 2. `F0__V1__s43` — `QAT_INT8`

- Accuracy: **0.9610**
- Balanced accuracy: **0.9476**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9211 | 0.9211 | 0.9211 | 38 |
| Non-Asthma | 0.9741 | 0.9741 | 0.9741 | 116 |
| accuracy | — | — | 0.9610 | 154 |
| macro avg | 0.9476 | 0.9476 | 0.9476 | 154 |
| weighted avg | 0.9610 | 0.9610 | 0.9610 | 154 |

### 2. `F0__V1__s43` — `PTQ_INT16x8`

- Accuracy: **0.9740**
- Balanced accuracy: **0.9739**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 37 | 1 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9250 | 0.9737 | 0.9487 | 38 |
| Non-Asthma | 0.9912 | 0.9741 | 0.9826 | 116 |
| accuracy | — | — | 0.9740 | 154 |
| macro avg | 0.9581 | 0.9739 | 0.9657 | 154 |
| weighted avg | 0.9749 | 0.9740 | 0.9742 | 154 |

### 3. `F0__V1__s44` — `KERAS_FP32`

- Accuracy: **1.0000**
- Balanced accuracy: **1.0000**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 0 | 116 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 1.0000 | 1.0000 | 1.0000 | 38 |
| Non-Asthma | 1.0000 | 1.0000 | 1.0000 | 116 |
| accuracy | — | — | 1.0000 | 154 |
| macro avg | 1.0000 | 1.0000 | 1.0000 | 154 |
| weighted avg | 1.0000 | 1.0000 | 1.0000 | 154 |

### 3. `F0__V1__s44` — `PTQ_INT8`

- Accuracy: **0.9805**
- Balanced accuracy: **0.9694**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 36 | 2 |
| Non-Asthma | 1 | 115 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9730 | 0.9474 | 0.9600 | 38 |
| Non-Asthma | 0.9829 | 0.9914 | 0.9871 | 116 |
| accuracy | — | — | 0.9805 | 154 |
| macro avg | 0.9779 | 0.9694 | 0.9736 | 154 |
| weighted avg | 0.9805 | 0.9805 | 0.9804 | 154 |

### 3. `F0__V1__s44` — `QAT_INT8`

- Accuracy: **0.9870**
- Balanced accuracy: **0.9914**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 2 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9500 | 1.0000 | 0.9744 | 38 |
| Non-Asthma | 1.0000 | 0.9828 | 0.9913 | 116 |
| accuracy | — | — | 0.9870 | 154 |
| macro avg | 0.9750 | 0.9914 | 0.9828 | 154 |
| weighted avg | 0.9877 | 0.9870 | 0.9871 | 154 |

### 3. `F0__V1__s44` — `PTQ_INT16x8`

- Accuracy: **1.0000**
- Balanced accuracy: **1.0000**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 0 | 116 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 1.0000 | 1.0000 | 1.0000 | 38 |
| Non-Asthma | 1.0000 | 1.0000 | 1.0000 | 116 |
| accuracy | — | — | 1.0000 | 154 |
| macro avg | 1.0000 | 1.0000 | 1.0000 | 154 |
| weighted avg | 1.0000 | 1.0000 | 1.0000 | 154 |

### 4. `pre_0__V1__s42` — `KERAS_FP32`

- Accuracy: **0.9610**
- Balanced accuracy: **0.9741**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 6 | 110 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8636 | 1.0000 | 0.9268 | 38 |
| Non-Asthma | 1.0000 | 0.9483 | 0.9735 | 116 |
| accuracy | — | — | 0.9610 | 154 |
| macro avg | 0.9318 | 0.9741 | 0.9501 | 154 |
| weighted avg | 0.9664 | 0.9610 | 0.9619 | 154 |

### 4. `pre_0__V1__s42` — `PTQ_INT8`

- Accuracy: **0.8961**
- Balanced accuracy: **0.8072**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 24 | 14 |
| Non-Asthma | 2 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9231 | 0.6316 | 0.7500 | 38 |
| Non-Asthma | 0.8906 | 0.9828 | 0.9344 | 116 |
| accuracy | — | — | 0.8961 | 154 |
| macro avg | 0.9069 | 0.8072 | 0.8422 | 154 |
| weighted avg | 0.8986 | 0.8961 | 0.8889 | 154 |

### 4. `pre_0__V1__s42` — `QAT_INT8`

- Accuracy: **0.9675**
- Balanced accuracy: **0.9784**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 5 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8837 | 1.0000 | 0.9383 | 38 |
| Non-Asthma | 1.0000 | 0.9569 | 0.9780 | 116 |
| accuracy | — | — | 0.9675 | 154 |
| macro avg | 0.9419 | 0.9784 | 0.9581 | 154 |
| weighted avg | 0.9713 | 0.9675 | 0.9682 | 154 |

### 4. `pre_0__V1__s42` — `PTQ_INT16x8`

- Accuracy: **0.9675**
- Balanced accuracy: **0.9784**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 5 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8837 | 1.0000 | 0.9383 | 38 |
| Non-Asthma | 1.0000 | 0.9569 | 0.9780 | 116 |
| accuracy | — | — | 0.9675 | 154 |
| macro avg | 0.9419 | 0.9784 | 0.9581 | 154 |
| weighted avg | 0.9713 | 0.9675 | 0.9682 | 154 |

### 5. `pre_0__V1__s43` — `KERAS_FP32`

- Accuracy: **0.9610**
- Balanced accuracy: **0.9564**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 36 | 2 |
| Non-Asthma | 4 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9000 | 0.9474 | 0.9231 | 38 |
| Non-Asthma | 0.9825 | 0.9655 | 0.9739 | 116 |
| accuracy | — | — | 0.9610 | 154 |
| macro avg | 0.9412 | 0.9564 | 0.9485 | 154 |
| weighted avg | 0.9621 | 0.9610 | 0.9614 | 154 |

### 5. `pre_0__V1__s43` — `PTQ_INT8`

- Accuracy: **0.9416**
- Balanced accuracy: **0.9258**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 5 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8718 | 0.8947 | 0.8831 | 38 |
| Non-Asthma | 0.9652 | 0.9569 | 0.9610 | 116 |
| accuracy | — | — | 0.9416 | 154 |
| macro avg | 0.9185 | 0.9258 | 0.9221 | 154 |
| weighted avg | 0.9422 | 0.9416 | 0.9418 | 154 |

### 5. `pre_0__V1__s43` — `QAT_INT8`

- Accuracy: **0.9740**
- Balanced accuracy: **0.9651**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 36 | 2 |
| Non-Asthma | 2 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9474 | 0.9474 | 0.9474 | 38 |
| Non-Asthma | 0.9828 | 0.9828 | 0.9828 | 116 |
| accuracy | — | — | 0.9740 | 154 |
| macro avg | 0.9651 | 0.9651 | 0.9651 | 154 |
| weighted avg | 0.9740 | 0.9740 | 0.9740 | 154 |

### 5. `pre_0__V1__s43` — `PTQ_INT16x8`

- Accuracy: **0.9610**
- Balanced accuracy: **0.9564**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 36 | 2 |
| Non-Asthma | 4 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9000 | 0.9474 | 0.9231 | 38 |
| Non-Asthma | 0.9825 | 0.9655 | 0.9739 | 116 |
| accuracy | — | — | 0.9610 | 154 |
| macro avg | 0.9412 | 0.9564 | 0.9485 | 154 |
| weighted avg | 0.9621 | 0.9610 | 0.9614 | 154 |

### 6. `pre_0__V1__s44` — `KERAS_FP32`

- Accuracy: **0.9935**
- Balanced accuracy: **0.9957**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 1 | 115 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9744 | 1.0000 | 0.9870 | 38 |
| Non-Asthma | 1.0000 | 0.9914 | 0.9957 | 116 |
| accuracy | — | — | 0.9935 | 154 |
| macro avg | 0.9872 | 0.9957 | 0.9913 | 154 |
| weighted avg | 0.9937 | 0.9935 | 0.9935 | 154 |

### 6. `pre_0__V1__s44` — `PTQ_INT8`

- Accuracy: **0.9935**
- Balanced accuracy: **0.9957**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 1 | 115 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9744 | 1.0000 | 0.9870 | 38 |
| Non-Asthma | 1.0000 | 0.9914 | 0.9957 | 116 |
| accuracy | — | — | 0.9935 | 154 |
| macro avg | 0.9872 | 0.9957 | 0.9913 | 154 |
| weighted avg | 0.9937 | 0.9935 | 0.9935 | 154 |

### 6. `pre_0__V1__s44` — `QAT_INT8`

- Accuracy: **0.9870**
- Balanced accuracy: **0.9914**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 2 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9500 | 1.0000 | 0.9744 | 38 |
| Non-Asthma | 1.0000 | 0.9828 | 0.9913 | 116 |
| accuracy | — | — | 0.9870 | 154 |
| macro avg | 0.9750 | 0.9914 | 0.9828 | 154 |
| weighted avg | 0.9877 | 0.9870 | 0.9871 | 154 |

### 6. `pre_0__V1__s44` — `PTQ_INT16x8`

- Accuracy: **0.9935**
- Balanced accuracy: **0.9957**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 1 | 115 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9744 | 1.0000 | 0.9870 | 38 |
| Non-Asthma | 1.0000 | 0.9914 | 0.9957 | 116 |
| accuracy | — | — | 0.9935 | 154 |
| macro avg | 0.9872 | 0.9957 | 0.9913 | 154 |
| weighted avg | 0.9937 | 0.9935 | 0.9935 | 154 |

### 7. `mel_40__V1__s42` — `KERAS_FP32`

- Accuracy: **0.9805**
- Balanced accuracy: **0.9871**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9268 | 1.0000 | 0.9620 | 38 |
| Non-Asthma | 1.0000 | 0.9741 | 0.9869 | 116 |
| accuracy | — | — | 0.9805 | 154 |
| macro avg | 0.9634 | 0.9871 | 0.9745 | 154 |
| weighted avg | 0.9819 | 0.9805 | 0.9808 | 154 |

### 7. `mel_40__V1__s42` — `PTQ_INT8`

- Accuracy: **0.9221**
- Balanced accuracy: **0.8686**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 29 | 9 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9062 | 0.7632 | 0.8286 | 38 |
| Non-Asthma | 0.9262 | 0.9741 | 0.9496 | 116 |
| accuracy | — | — | 0.9221 | 154 |
| macro avg | 0.9162 | 0.8686 | 0.8891 | 154 |
| weighted avg | 0.9213 | 0.9221 | 0.9197 | 154 |

### 7. `mel_40__V1__s42` — `QAT_INT8`

- Accuracy: **0.9675**
- Balanced accuracy: **0.9784**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 5 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8837 | 1.0000 | 0.9383 | 38 |
| Non-Asthma | 1.0000 | 0.9569 | 0.9780 | 116 |
| accuracy | — | — | 0.9675 | 154 |
| macro avg | 0.9419 | 0.9784 | 0.9581 | 154 |
| weighted avg | 0.9713 | 0.9675 | 0.9682 | 154 |

### 7. `mel_40__V1__s42` — `PTQ_INT16x8`

- Accuracy: **0.9805**
- Balanced accuracy: **0.9871**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9268 | 1.0000 | 0.9620 | 38 |
| Non-Asthma | 1.0000 | 0.9741 | 0.9869 | 116 |
| accuracy | — | — | 0.9805 | 154 |
| macro avg | 0.9634 | 0.9871 | 0.9745 | 154 |
| weighted avg | 0.9819 | 0.9805 | 0.9808 | 154 |

### 8. `mel_40__V1__s43` — `KERAS_FP32`

- Accuracy: **0.9610**
- Balanced accuracy: **0.9741**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 6 | 110 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8636 | 1.0000 | 0.9268 | 38 |
| Non-Asthma | 1.0000 | 0.9483 | 0.9735 | 116 |
| accuracy | — | — | 0.9610 | 154 |
| macro avg | 0.9318 | 0.9741 | 0.9501 | 154 |
| weighted avg | 0.9664 | 0.9610 | 0.9619 | 154 |

### 8. `mel_40__V1__s43` — `PTQ_INT8`

- Accuracy: **0.9805**
- Balanced accuracy: **0.9782**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 37 | 1 |
| Non-Asthma | 2 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9487 | 0.9737 | 0.9610 | 38 |
| Non-Asthma | 0.9913 | 0.9828 | 0.9870 | 116 |
| accuracy | — | — | 0.9805 | 154 |
| macro avg | 0.9700 | 0.9782 | 0.9740 | 154 |
| weighted avg | 0.9808 | 0.9805 | 0.9806 | 154 |

### 8. `mel_40__V1__s43` — `QAT_INT8`

- Accuracy: **0.9675**
- Balanced accuracy: **0.9784**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 5 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8837 | 1.0000 | 0.9383 | 38 |
| Non-Asthma | 1.0000 | 0.9569 | 0.9780 | 116 |
| accuracy | — | — | 0.9675 | 154 |
| macro avg | 0.9419 | 0.9784 | 0.9581 | 154 |
| weighted avg | 0.9713 | 0.9675 | 0.9682 | 154 |

### 8. `mel_40__V1__s43` — `PTQ_INT16x8`

- Accuracy: **0.9610**
- Balanced accuracy: **0.9741**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 6 | 110 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8636 | 1.0000 | 0.9268 | 38 |
| Non-Asthma | 1.0000 | 0.9483 | 0.9735 | 116 |
| accuracy | — | — | 0.9610 | 154 |
| macro avg | 0.9318 | 0.9741 | 0.9501 | 154 |
| weighted avg | 0.9664 | 0.9610 | 0.9619 | 154 |

### 9. `mel_40__V1__s44` — `KERAS_FP32`

- Accuracy: **0.9545**
- Balanced accuracy: **0.9521**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 36 | 2 |
| Non-Asthma | 5 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8780 | 0.9474 | 0.9114 | 38 |
| Non-Asthma | 0.9823 | 0.9569 | 0.9694 | 116 |
| accuracy | — | — | 0.9545 | 154 |
| macro avg | 0.9302 | 0.9521 | 0.9404 | 154 |
| weighted avg | 0.9566 | 0.9545 | 0.9551 | 154 |

### 9. `mel_40__V1__s44` — `PTQ_INT8`

- Accuracy: **0.9805**
- Balanced accuracy: **0.9605**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 0 | 116 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 1.0000 | 0.9211 | 0.9589 | 38 |
| Non-Asthma | 0.9748 | 1.0000 | 0.9872 | 116 |
| accuracy | — | — | 0.9805 | 154 |
| macro avg | 0.9874 | 0.9605 | 0.9731 | 154 |
| weighted avg | 0.9810 | 0.9805 | 0.9802 | 154 |

### 9. `mel_40__V1__s44` — `QAT_INT8`

- Accuracy: **0.9870**
- Balanced accuracy: **0.9914**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 2 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9500 | 1.0000 | 0.9744 | 38 |
| Non-Asthma | 1.0000 | 0.9828 | 0.9913 | 116 |
| accuracy | — | — | 0.9870 | 154 |
| macro avg | 0.9750 | 0.9914 | 0.9828 | 154 |
| weighted avg | 0.9877 | 0.9870 | 0.9871 | 154 |

### 9. `mel_40__V1__s44` — `PTQ_INT16x8`

- Accuracy: **0.9481**
- Balanced accuracy: **0.9390**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 35 | 3 |
| Non-Asthma | 5 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8750 | 0.9211 | 0.8974 | 38 |
| Non-Asthma | 0.9737 | 0.9569 | 0.9652 | 116 |
| accuracy | — | — | 0.9481 | 154 |
| macro avg | 0.9243 | 0.9390 | 0.9313 | 154 |
| weighted avg | 0.9493 | 0.9481 | 0.9485 | 154 |

### 10. `fft_2048__V1__s42` — `KERAS_FP32`

- Accuracy: **0.9675**
- Balanced accuracy: **0.9608**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 36 | 2 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9231 | 0.9474 | 0.9351 | 38 |
| Non-Asthma | 0.9826 | 0.9741 | 0.9784 | 116 |
| accuracy | — | — | 0.9675 | 154 |
| macro avg | 0.9528 | 0.9608 | 0.9567 | 154 |
| weighted avg | 0.9679 | 0.9675 | 0.9677 | 154 |

### 10. `fft_2048__V1__s42` — `PTQ_INT8`

- Accuracy: **0.9416**
- Balanced accuracy: **0.8904**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 30 | 8 |
| Non-Asthma | 1 | 115 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9677 | 0.7895 | 0.8696 | 38 |
| Non-Asthma | 0.9350 | 0.9914 | 0.9623 | 116 |
| accuracy | — | — | 0.9416 | 154 |
| macro avg | 0.9514 | 0.8904 | 0.9160 | 154 |
| weighted avg | 0.9430 | 0.9416 | 0.9394 | 154 |

### 10. `fft_2048__V1__s42` — `QAT_INT8`

- Accuracy: **0.9545**
- Balanced accuracy: **0.9344**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9189 | 0.8947 | 0.9067 | 38 |
| Non-Asthma | 0.9658 | 0.9741 | 0.9700 | 116 |
| accuracy | — | — | 0.9545 | 154 |
| macro avg | 0.9424 | 0.9344 | 0.9383 | 154 |
| weighted avg | 0.9542 | 0.9545 | 0.9543 | 154 |

### 10. `fft_2048__V1__s42` — `PTQ_INT16x8`

- Accuracy: **0.9675**
- Balanced accuracy: **0.9608**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 36 | 2 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9231 | 0.9474 | 0.9351 | 38 |
| Non-Asthma | 0.9826 | 0.9741 | 0.9784 | 116 |
| accuracy | — | — | 0.9675 | 154 |
| macro avg | 0.9528 | 0.9608 | 0.9567 | 154 |
| weighted avg | 0.9679 | 0.9675 | 0.9677 | 154 |

### 11. `fft_2048__V1__s43` — `KERAS_FP32`

- Accuracy: **0.9675**
- Balanced accuracy: **0.9784**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 5 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8837 | 1.0000 | 0.9383 | 38 |
| Non-Asthma | 1.0000 | 0.9569 | 0.9780 | 116 |
| accuracy | — | — | 0.9675 | 154 |
| macro avg | 0.9419 | 0.9784 | 0.9581 | 154 |
| weighted avg | 0.9713 | 0.9675 | 0.9682 | 154 |

### 11. `fft_2048__V1__s43` — `PTQ_INT8`

- Accuracy: **0.9610**
- Balanced accuracy: **0.9564**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 36 | 2 |
| Non-Asthma | 4 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9000 | 0.9474 | 0.9231 | 38 |
| Non-Asthma | 0.9825 | 0.9655 | 0.9739 | 116 |
| accuracy | — | — | 0.9610 | 154 |
| macro avg | 0.9412 | 0.9564 | 0.9485 | 154 |
| weighted avg | 0.9621 | 0.9610 | 0.9614 | 154 |

### 11. `fft_2048__V1__s43` — `QAT_INT8`

- Accuracy: **0.9805**
- Balanced accuracy: **0.9871**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9268 | 1.0000 | 0.9620 | 38 |
| Non-Asthma | 1.0000 | 0.9741 | 0.9869 | 116 |
| accuracy | — | — | 0.9805 | 154 |
| macro avg | 0.9634 | 0.9871 | 0.9745 | 154 |
| weighted avg | 0.9819 | 0.9805 | 0.9808 | 154 |

### 11. `fft_2048__V1__s43` — `PTQ_INT16x8`

- Accuracy: **0.9740**
- Balanced accuracy: **0.9828**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 4 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9048 | 1.0000 | 0.9500 | 38 |
| Non-Asthma | 1.0000 | 0.9655 | 0.9825 | 116 |
| accuracy | — | — | 0.9740 | 154 |
| macro avg | 0.9524 | 0.9828 | 0.9662 | 154 |
| weighted avg | 0.9765 | 0.9740 | 0.9744 | 154 |

### 12. `fft_2048__V1__s44` — `KERAS_FP32`

- Accuracy: **0.9740**
- Balanced accuracy: **0.9828**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 4 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9048 | 1.0000 | 0.9500 | 38 |
| Non-Asthma | 1.0000 | 0.9655 | 0.9825 | 116 |
| accuracy | — | — | 0.9740 | 154 |
| macro avg | 0.9524 | 0.9828 | 0.9662 | 154 |
| weighted avg | 0.9765 | 0.9740 | 0.9744 | 154 |

### 12. `fft_2048__V1__s44` — `PTQ_INT8`

- Accuracy: **0.9805**
- Balanced accuracy: **0.9871**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9268 | 1.0000 | 0.9620 | 38 |
| Non-Asthma | 1.0000 | 0.9741 | 0.9869 | 116 |
| accuracy | — | — | 0.9805 | 154 |
| macro avg | 0.9634 | 0.9871 | 0.9745 | 154 |
| weighted avg | 0.9819 | 0.9805 | 0.9808 | 154 |

### 12. `fft_2048__V1__s44` — `QAT_INT8`

- Accuracy: **0.9740**
- Balanced accuracy: **0.9828**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 4 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9048 | 1.0000 | 0.9500 | 38 |
| Non-Asthma | 1.0000 | 0.9655 | 0.9825 | 116 |
| accuracy | — | — | 0.9740 | 154 |
| macro avg | 0.9524 | 0.9828 | 0.9662 | 154 |
| weighted avg | 0.9765 | 0.9740 | 0.9744 | 154 |

### 12. `fft_2048__V1__s44` — `PTQ_INT16x8`

- Accuracy: **0.9740**
- Balanced accuracy: **0.9828**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 4 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9048 | 1.0000 | 0.9500 | 38 |
| Non-Asthma | 1.0000 | 0.9655 | 0.9825 | 116 |
| accuracy | — | — | 0.9740 | 154 |
| macro avg | 0.9524 | 0.9828 | 0.9662 | 154 |
| weighted avg | 0.9765 | 0.9740 | 0.9744 | 154 |

### 13. `combo_pre0_mel40__V1__s42` — `KERAS_FP32`

- Accuracy: **0.9675**
- Balanced accuracy: **0.9784**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 5 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8837 | 1.0000 | 0.9383 | 38 |
| Non-Asthma | 1.0000 | 0.9569 | 0.9780 | 116 |
| accuracy | — | — | 0.9675 | 154 |
| macro avg | 0.9419 | 0.9784 | 0.9581 | 154 |
| weighted avg | 0.9713 | 0.9675 | 0.9682 | 154 |

### 13. `combo_pre0_mel40__V1__s42` — `PTQ_INT8`

- Accuracy: **0.8896**
- Balanced accuracy: **0.8294**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 27 | 11 |
| Non-Asthma | 6 | 110 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8182 | 0.7105 | 0.7606 | 38 |
| Non-Asthma | 0.9091 | 0.9483 | 0.9283 | 116 |
| accuracy | — | — | 0.8896 | 154 |
| macro avg | 0.8636 | 0.8294 | 0.8444 | 154 |
| weighted avg | 0.8867 | 0.8896 | 0.8869 | 154 |

### 13. `combo_pre0_mel40__V1__s42` — `QAT_INT8`

- Accuracy: **0.9805**
- Balanced accuracy: **0.9871**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9268 | 1.0000 | 0.9620 | 38 |
| Non-Asthma | 1.0000 | 0.9741 | 0.9869 | 116 |
| accuracy | — | — | 0.9805 | 154 |
| macro avg | 0.9634 | 0.9871 | 0.9745 | 154 |
| weighted avg | 0.9819 | 0.9805 | 0.9808 | 154 |

### 13. `combo_pre0_mel40__V1__s42` — `PTQ_INT16x8`

- Accuracy: **0.9675**
- Balanced accuracy: **0.9784**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 5 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8837 | 1.0000 | 0.9383 | 38 |
| Non-Asthma | 1.0000 | 0.9569 | 0.9780 | 116 |
| accuracy | — | — | 0.9675 | 154 |
| macro avg | 0.9419 | 0.9784 | 0.9581 | 154 |
| weighted avg | 0.9713 | 0.9675 | 0.9682 | 154 |

### 14. `combo_pre0_mel40__V1__s43` — `KERAS_FP32`

- Accuracy: **0.9870**
- Balanced accuracy: **0.9914**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 2 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9500 | 1.0000 | 0.9744 | 38 |
| Non-Asthma | 1.0000 | 0.9828 | 0.9913 | 116 |
| accuracy | — | — | 0.9870 | 154 |
| macro avg | 0.9750 | 0.9914 | 0.9828 | 154 |
| weighted avg | 0.9877 | 0.9870 | 0.9871 | 154 |

### 14. `combo_pre0_mel40__V1__s43` — `PTQ_INT8`

- Accuracy: **0.9740**
- Balanced accuracy: **0.9651**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 36 | 2 |
| Non-Asthma | 2 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9474 | 0.9474 | 0.9474 | 38 |
| Non-Asthma | 0.9828 | 0.9828 | 0.9828 | 116 |
| accuracy | — | — | 0.9740 | 154 |
| macro avg | 0.9651 | 0.9651 | 0.9651 | 154 |
| weighted avg | 0.9740 | 0.9740 | 0.9740 | 154 |

### 14. `combo_pre0_mel40__V1__s43` — `QAT_INT8`

- Accuracy: **0.9675**
- Balanced accuracy: **0.9696**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 37 | 1 |
| Non-Asthma | 4 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9024 | 0.9737 | 0.9367 | 38 |
| Non-Asthma | 0.9912 | 0.9655 | 0.9782 | 116 |
| accuracy | — | — | 0.9675 | 154 |
| macro avg | 0.9468 | 0.9696 | 0.9574 | 154 |
| weighted avg | 0.9693 | 0.9675 | 0.9679 | 154 |

### 14. `combo_pre0_mel40__V1__s43` — `PTQ_INT16x8`

- Accuracy: **0.9870**
- Balanced accuracy: **0.9914**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 2 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9500 | 1.0000 | 0.9744 | 38 |
| Non-Asthma | 1.0000 | 0.9828 | 0.9913 | 116 |
| accuracy | — | — | 0.9870 | 154 |
| macro avg | 0.9750 | 0.9914 | 0.9828 | 154 |
| weighted avg | 0.9877 | 0.9870 | 0.9871 | 154 |

### 15. `combo_pre0_mel40__V1__s44` — `KERAS_FP32`

- Accuracy: **0.9935**
- Balanced accuracy: **0.9957**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 1 | 115 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9744 | 1.0000 | 0.9870 | 38 |
| Non-Asthma | 1.0000 | 0.9914 | 0.9957 | 116 |
| accuracy | — | — | 0.9935 | 154 |
| macro avg | 0.9872 | 0.9957 | 0.9913 | 154 |
| weighted avg | 0.9937 | 0.9935 | 0.9935 | 154 |

### 15. `combo_pre0_mel40__V1__s44` — `PTQ_INT8`

- Accuracy: **0.9610**
- Balanced accuracy: **0.9387**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 2 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9444 | 0.8947 | 0.9189 | 38 |
| Non-Asthma | 0.9661 | 0.9828 | 0.9744 | 116 |
| accuracy | — | — | 0.9610 | 154 |
| macro avg | 0.9553 | 0.9387 | 0.9466 | 154 |
| weighted avg | 0.9608 | 0.9610 | 0.9607 | 154 |

### 15. `combo_pre0_mel40__V1__s44` — `QAT_INT8`

- Accuracy: **0.9805**
- Balanced accuracy: **0.9782**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 37 | 1 |
| Non-Asthma | 2 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9487 | 0.9737 | 0.9610 | 38 |
| Non-Asthma | 0.9913 | 0.9828 | 0.9870 | 116 |
| accuracy | — | — | 0.9805 | 154 |
| macro avg | 0.9700 | 0.9782 | 0.9740 | 154 |
| weighted avg | 0.9808 | 0.9805 | 0.9806 | 154 |

### 15. `combo_pre0_mel40__V1__s44` — `PTQ_INT16x8`

- Accuracy: **0.9935**
- Balanced accuracy: **0.9957**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 1 | 115 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9744 | 1.0000 | 0.9870 | 38 |
| Non-Asthma | 1.0000 | 0.9914 | 0.9957 | 116 |
| accuracy | — | — | 0.9935 | 154 |
| macro avg | 0.9872 | 0.9957 | 0.9913 | 154 |
| weighted avg | 0.9937 | 0.9935 | 0.9935 | 154 |

### 16. `combo_pre0_fft2048__V1__s42` — `KERAS_FP32`

- Accuracy: **0.9740**
- Balanced accuracy: **0.9739**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 37 | 1 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9250 | 0.9737 | 0.9487 | 38 |
| Non-Asthma | 0.9912 | 0.9741 | 0.9826 | 116 |
| accuracy | — | — | 0.9740 | 154 |
| macro avg | 0.9581 | 0.9739 | 0.9657 | 154 |
| weighted avg | 0.9749 | 0.9740 | 0.9742 | 154 |

### 16. `combo_pre0_fft2048__V1__s42` — `PTQ_INT8`

- Accuracy: **0.9156**
- Balanced accuracy: **0.8378**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 26 | 12 |
| Non-Asthma | 1 | 115 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9630 | 0.6842 | 0.8000 | 38 |
| Non-Asthma | 0.9055 | 0.9914 | 0.9465 | 116 |
| accuracy | — | — | 0.9156 | 154 |
| macro avg | 0.9342 | 0.8378 | 0.8733 | 154 |
| weighted avg | 0.9197 | 0.9156 | 0.9104 | 154 |

### 16. `combo_pre0_fft2048__V1__s42` — `QAT_INT8`

- Accuracy: **0.9675**
- Balanced accuracy: **0.9608**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 36 | 2 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9231 | 0.9474 | 0.9351 | 38 |
| Non-Asthma | 0.9826 | 0.9741 | 0.9784 | 116 |
| accuracy | — | — | 0.9675 | 154 |
| macro avg | 0.9528 | 0.9608 | 0.9567 | 154 |
| weighted avg | 0.9679 | 0.9675 | 0.9677 | 154 |

### 16. `combo_pre0_fft2048__V1__s42` — `PTQ_INT16x8`

- Accuracy: **0.9675**
- Balanced accuracy: **0.9696**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 37 | 1 |
| Non-Asthma | 4 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9024 | 0.9737 | 0.9367 | 38 |
| Non-Asthma | 0.9912 | 0.9655 | 0.9782 | 116 |
| accuracy | — | — | 0.9675 | 154 |
| macro avg | 0.9468 | 0.9696 | 0.9574 | 154 |
| weighted avg | 0.9693 | 0.9675 | 0.9679 | 154 |

### 17. `combo_pre0_fft2048__V1__s43` — `KERAS_FP32`

- Accuracy: **0.9805**
- Balanced accuracy: **0.9871**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9268 | 1.0000 | 0.9620 | 38 |
| Non-Asthma | 1.0000 | 0.9741 | 0.9869 | 116 |
| accuracy | — | — | 0.9805 | 154 |
| macro avg | 0.9634 | 0.9871 | 0.9745 | 154 |
| weighted avg | 0.9819 | 0.9805 | 0.9808 | 154 |

### 17. `combo_pre0_fft2048__V1__s43` — `PTQ_INT8`

- Accuracy: **0.9610**
- Balanced accuracy: **0.9653**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 37 | 1 |
| Non-Asthma | 5 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8810 | 0.9737 | 0.9250 | 38 |
| Non-Asthma | 0.9911 | 0.9569 | 0.9737 | 116 |
| accuracy | — | — | 0.9610 | 154 |
| macro avg | 0.9360 | 0.9653 | 0.9493 | 154 |
| weighted avg | 0.9639 | 0.9610 | 0.9617 | 154 |

### 17. `combo_pre0_fft2048__V1__s43` — `QAT_INT8`

- Accuracy: **0.9610**
- Balanced accuracy: **0.9564**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 36 | 2 |
| Non-Asthma | 4 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9000 | 0.9474 | 0.9231 | 38 |
| Non-Asthma | 0.9825 | 0.9655 | 0.9739 | 116 |
| accuracy | — | — | 0.9610 | 154 |
| macro avg | 0.9412 | 0.9564 | 0.9485 | 154 |
| weighted avg | 0.9621 | 0.9610 | 0.9614 | 154 |

### 17. `combo_pre0_fft2048__V1__s43` — `PTQ_INT16x8`

- Accuracy: **0.9805**
- Balanced accuracy: **0.9871**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9268 | 1.0000 | 0.9620 | 38 |
| Non-Asthma | 1.0000 | 0.9741 | 0.9869 | 116 |
| accuracy | — | — | 0.9805 | 154 |
| macro avg | 0.9634 | 0.9871 | 0.9745 | 154 |
| weighted avg | 0.9819 | 0.9805 | 0.9808 | 154 |

### 18. `combo_pre0_fft2048__V1__s44` — `KERAS_FP32`

- Accuracy: **0.9675**
- Balanced accuracy: **0.9784**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 5 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8837 | 1.0000 | 0.9383 | 38 |
| Non-Asthma | 1.0000 | 0.9569 | 0.9780 | 116 |
| accuracy | — | — | 0.9675 | 154 |
| macro avg | 0.9419 | 0.9784 | 0.9581 | 154 |
| weighted avg | 0.9713 | 0.9675 | 0.9682 | 154 |

### 18. `combo_pre0_fft2048__V1__s44` — `PTQ_INT8`

- Accuracy: **0.9740**
- Balanced accuracy: **0.9828**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 4 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9048 | 1.0000 | 0.9500 | 38 |
| Non-Asthma | 1.0000 | 0.9655 | 0.9825 | 116 |
| accuracy | — | — | 0.9740 | 154 |
| macro avg | 0.9524 | 0.9828 | 0.9662 | 154 |
| weighted avg | 0.9765 | 0.9740 | 0.9744 | 154 |

### 18. `combo_pre0_fft2048__V1__s44` — `QAT_INT8`

- Accuracy: **0.9870**
- Balanced accuracy: **0.9825**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 37 | 1 |
| Non-Asthma | 1 | 115 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9737 | 0.9737 | 0.9737 | 38 |
| Non-Asthma | 0.9914 | 0.9914 | 0.9914 | 116 |
| accuracy | — | — | 0.9870 | 154 |
| macro avg | 0.9825 | 0.9825 | 0.9825 | 154 |
| weighted avg | 0.9870 | 0.9870 | 0.9870 | 154 |

### 18. `combo_pre0_fft2048__V1__s44` — `PTQ_INT16x8`

- Accuracy: **0.9740**
- Balanced accuracy: **0.9828**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 4 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9048 | 1.0000 | 0.9500 | 38 |
| Non-Asthma | 1.0000 | 0.9655 | 0.9825 | 116 |
| accuracy | — | — | 0.9740 | 154 |
| macro avg | 0.9524 | 0.9828 | 0.9662 | 154 |
| weighted avg | 0.9765 | 0.9740 | 0.9744 | 154 |

### 19. `combo_mel40_fft2048__V1__s42` — `KERAS_FP32`

- Accuracy: **0.9610**
- Balanced accuracy: **0.9741**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 6 | 110 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8636 | 1.0000 | 0.9268 | 38 |
| Non-Asthma | 1.0000 | 0.9483 | 0.9735 | 116 |
| accuracy | — | — | 0.9610 | 154 |
| macro avg | 0.9318 | 0.9741 | 0.9501 | 154 |
| weighted avg | 0.9664 | 0.9610 | 0.9619 | 154 |

### 19. `combo_mel40_fft2048__V1__s42` — `PTQ_INT8`

- Accuracy: **0.9351**
- Balanced accuracy: **0.8684**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 28 | 10 |
| Non-Asthma | 0 | 116 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 1.0000 | 0.7368 | 0.8485 | 38 |
| Non-Asthma | 0.9206 | 1.0000 | 0.9587 | 116 |
| accuracy | — | — | 0.9351 | 154 |
| macro avg | 0.9603 | 0.8684 | 0.9036 | 154 |
| weighted avg | 0.9402 | 0.9351 | 0.9315 | 154 |

### 19. `combo_mel40_fft2048__V1__s42` — `QAT_INT8`

- Accuracy: **0.9545**
- Balanced accuracy: **0.9344**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 34 | 4 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9189 | 0.8947 | 0.9067 | 38 |
| Non-Asthma | 0.9658 | 0.9741 | 0.9700 | 116 |
| accuracy | — | — | 0.9545 | 154 |
| macro avg | 0.9424 | 0.9344 | 0.9383 | 154 |
| weighted avg | 0.9542 | 0.9545 | 0.9543 | 154 |

### 19. `combo_mel40_fft2048__V1__s42` — `PTQ_INT16x8`

- Accuracy: **0.9610**
- Balanced accuracy: **0.9741**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 6 | 110 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8636 | 1.0000 | 0.9268 | 38 |
| Non-Asthma | 1.0000 | 0.9483 | 0.9735 | 116 |
| accuracy | — | — | 0.9610 | 154 |
| macro avg | 0.9318 | 0.9741 | 0.9501 | 154 |
| weighted avg | 0.9664 | 0.9610 | 0.9619 | 154 |

### 20. `combo_mel40_fft2048__V1__s43` — `KERAS_FP32`

- Accuracy: **0.9740**
- Balanced accuracy: **0.9828**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 4 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9048 | 1.0000 | 0.9500 | 38 |
| Non-Asthma | 1.0000 | 0.9655 | 0.9825 | 116 |
| accuracy | — | — | 0.9740 | 154 |
| macro avg | 0.9524 | 0.9828 | 0.9662 | 154 |
| weighted avg | 0.9765 | 0.9740 | 0.9744 | 154 |

### 20. `combo_mel40_fft2048__V1__s43` — `PTQ_INT8`

- Accuracy: **0.9740**
- Balanced accuracy: **0.9651**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 36 | 2 |
| Non-Asthma | 2 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9474 | 0.9474 | 0.9474 | 38 |
| Non-Asthma | 0.9828 | 0.9828 | 0.9828 | 116 |
| accuracy | — | — | 0.9740 | 154 |
| macro avg | 0.9651 | 0.9651 | 0.9651 | 154 |
| weighted avg | 0.9740 | 0.9740 | 0.9740 | 154 |

### 20. `combo_mel40_fft2048__V1__s43` — `QAT_INT8`

- Accuracy: **0.9870**
- Balanced accuracy: **0.9914**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 2 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9500 | 1.0000 | 0.9744 | 38 |
| Non-Asthma | 1.0000 | 0.9828 | 0.9913 | 116 |
| accuracy | — | — | 0.9870 | 154 |
| macro avg | 0.9750 | 0.9914 | 0.9828 | 154 |
| weighted avg | 0.9877 | 0.9870 | 0.9871 | 154 |

### 20. `combo_mel40_fft2048__V1__s43` — `PTQ_INT16x8`

- Accuracy: **0.9740**
- Balanced accuracy: **0.9828**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 4 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9048 | 1.0000 | 0.9500 | 38 |
| Non-Asthma | 1.0000 | 0.9655 | 0.9825 | 116 |
| accuracy | — | — | 0.9740 | 154 |
| macro avg | 0.9524 | 0.9828 | 0.9662 | 154 |
| weighted avg | 0.9765 | 0.9740 | 0.9744 | 154 |

### 21. `combo_mel40_fft2048__V1__s44` — `KERAS_FP32`

- Accuracy: **0.9805**
- Balanced accuracy: **0.9871**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9268 | 1.0000 | 0.9620 | 38 |
| Non-Asthma | 1.0000 | 0.9741 | 0.9869 | 116 |
| accuracy | — | — | 0.9805 | 154 |
| macro avg | 0.9634 | 0.9871 | 0.9745 | 154 |
| weighted avg | 0.9819 | 0.9805 | 0.9808 | 154 |

### 21. `combo_mel40_fft2048__V1__s44` — `PTQ_INT8`

- Accuracy: **0.9805**
- Balanced accuracy: **0.9782**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 37 | 1 |
| Non-Asthma | 2 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9487 | 0.9737 | 0.9610 | 38 |
| Non-Asthma | 0.9913 | 0.9828 | 0.9870 | 116 |
| accuracy | — | — | 0.9805 | 154 |
| macro avg | 0.9700 | 0.9782 | 0.9740 | 154 |
| weighted avg | 0.9808 | 0.9805 | 0.9806 | 154 |

### 21. `combo_mel40_fft2048__V1__s44` — `QAT_INT8`

- Accuracy: **0.9805**
- Balanced accuracy: **0.9694**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 36 | 2 |
| Non-Asthma | 1 | 115 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9730 | 0.9474 | 0.9600 | 38 |
| Non-Asthma | 0.9829 | 0.9914 | 0.9871 | 116 |
| accuracy | — | — | 0.9805 | 154 |
| macro avg | 0.9779 | 0.9694 | 0.9736 | 154 |
| weighted avg | 0.9805 | 0.9805 | 0.9804 | 154 |

### 21. `combo_mel40_fft2048__V1__s44` — `PTQ_INT16x8`

- Accuracy: **0.9805**
- Balanced accuracy: **0.9871**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9268 | 1.0000 | 0.9620 | 38 |
| Non-Asthma | 1.0000 | 0.9741 | 0.9869 | 116 |
| accuracy | — | — | 0.9805 | 154 |
| macro avg | 0.9634 | 0.9871 | 0.9745 | 154 |
| weighted avg | 0.9819 | 0.9805 | 0.9808 | 154 |

### 22. `combo_pre0_mel40_fft2048__V1__s42` — `KERAS_FP32`

- Accuracy: **0.9740**
- Balanced accuracy: **0.9651**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 36 | 2 |
| Non-Asthma | 2 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9474 | 0.9474 | 0.9474 | 38 |
| Non-Asthma | 0.9828 | 0.9828 | 0.9828 | 116 |
| accuracy | — | — | 0.9740 | 154 |
| macro avg | 0.9651 | 0.9651 | 0.9651 | 154 |
| weighted avg | 0.9740 | 0.9740 | 0.9740 | 154 |

### 22. `combo_pre0_mel40_fft2048__V1__s42` — `PTQ_INT8`

- Accuracy: **0.9026**
- Balanced accuracy: **0.8292**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 26 | 12 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8966 | 0.6842 | 0.7761 | 38 |
| Non-Asthma | 0.9040 | 0.9741 | 0.9378 | 116 |
| accuracy | — | — | 0.9026 | 154 |
| macro avg | 0.9003 | 0.8292 | 0.8569 | 154 |
| weighted avg | 0.9022 | 0.9026 | 0.8979 | 154 |

### 22. `combo_pre0_mel40_fft2048__V1__s42` — `QAT_INT8`

- Accuracy: **0.9675**
- Balanced accuracy: **0.9696**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 37 | 1 |
| Non-Asthma | 4 | 112 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9024 | 0.9737 | 0.9367 | 38 |
| Non-Asthma | 0.9912 | 0.9655 | 0.9782 | 116 |
| accuracy | — | — | 0.9675 | 154 |
| macro avg | 0.9468 | 0.9696 | 0.9574 | 154 |
| weighted avg | 0.9693 | 0.9675 | 0.9679 | 154 |

### 22. `combo_pre0_mel40_fft2048__V1__s42` — `PTQ_INT16x8`

- Accuracy: **0.9740**
- Balanced accuracy: **0.9651**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 36 | 2 |
| Non-Asthma | 2 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9474 | 0.9474 | 0.9474 | 38 |
| Non-Asthma | 0.9828 | 0.9828 | 0.9828 | 116 |
| accuracy | — | — | 0.9740 | 154 |
| macro avg | 0.9651 | 0.9651 | 0.9651 | 154 |
| weighted avg | 0.9740 | 0.9740 | 0.9740 | 154 |

### 23. `combo_pre0_mel40_fft2048__V1__s43` — `KERAS_FP32`

- Accuracy: **0.9805**
- Balanced accuracy: **0.9871**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9268 | 1.0000 | 0.9620 | 38 |
| Non-Asthma | 1.0000 | 0.9741 | 0.9869 | 116 |
| accuracy | — | — | 0.9805 | 154 |
| macro avg | 0.9634 | 0.9871 | 0.9745 | 154 |
| weighted avg | 0.9819 | 0.9805 | 0.9808 | 154 |

### 23. `combo_pre0_mel40_fft2048__V1__s43` — `PTQ_INT8`

- Accuracy: **0.9935**
- Balanced accuracy: **0.9957**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 1 | 115 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9744 | 1.0000 | 0.9870 | 38 |
| Non-Asthma | 1.0000 | 0.9914 | 0.9957 | 116 |
| accuracy | — | — | 0.9935 | 154 |
| macro avg | 0.9872 | 0.9957 | 0.9913 | 154 |
| weighted avg | 0.9937 | 0.9935 | 0.9935 | 154 |

### 23. `combo_pre0_mel40_fft2048__V1__s43` — `QAT_INT8`

- Accuracy: **0.9675**
- Balanced accuracy: **0.9784**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 5 | 111 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.8837 | 1.0000 | 0.9383 | 38 |
| Non-Asthma | 1.0000 | 0.9569 | 0.9780 | 116 |
| accuracy | — | — | 0.9675 | 154 |
| macro avg | 0.9419 | 0.9784 | 0.9581 | 154 |
| weighted avg | 0.9713 | 0.9675 | 0.9682 | 154 |

### 23. `combo_pre0_mel40_fft2048__V1__s43` — `PTQ_INT16x8`

- Accuracy: **0.9805**
- Balanced accuracy: **0.9871**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9268 | 1.0000 | 0.9620 | 38 |
| Non-Asthma | 1.0000 | 0.9741 | 0.9869 | 116 |
| accuracy | — | — | 0.9805 | 154 |
| macro avg | 0.9634 | 0.9871 | 0.9745 | 154 |
| weighted avg | 0.9819 | 0.9805 | 0.9808 | 154 |

### 24. `combo_pre0_mel40_fft2048__V1__s44` — `KERAS_FP32`

- Accuracy: **0.9870**
- Balanced accuracy: **0.9914**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 2 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9500 | 1.0000 | 0.9744 | 38 |
| Non-Asthma | 1.0000 | 0.9828 | 0.9913 | 116 |
| accuracy | — | — | 0.9870 | 154 |
| macro avg | 0.9750 | 0.9914 | 0.9828 | 154 |
| weighted avg | 0.9877 | 0.9870 | 0.9871 | 154 |

### 24. `combo_pre0_mel40_fft2048__V1__s44` — `PTQ_INT8`

- Accuracy: **0.9610**
- Balanced accuracy: **0.9211**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 32 | 6 |
| Non-Asthma | 0 | 116 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 1.0000 | 0.8421 | 0.9143 | 38 |
| Non-Asthma | 0.9508 | 1.0000 | 0.9748 | 116 |
| accuracy | — | — | 0.9610 | 154 |
| macro avg | 0.9754 | 0.9211 | 0.9445 | 154 |
| weighted avg | 0.9630 | 0.9610 | 0.9599 | 154 |

### 24. `combo_pre0_mel40_fft2048__V1__s44` — `QAT_INT8`

- Accuracy: **0.9740**
- Balanced accuracy: **0.9739**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 37 | 1 |
| Non-Asthma | 3 | 113 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9250 | 0.9737 | 0.9487 | 38 |
| Non-Asthma | 0.9912 | 0.9741 | 0.9826 | 116 |
| accuracy | — | — | 0.9740 | 154 |
| macro avg | 0.9581 | 0.9739 | 0.9657 | 154 |
| weighted avg | 0.9749 | 0.9740 | 0.9742 | 154 |

### 24. `combo_pre0_mel40_fft2048__V1__s44` — `PTQ_INT16x8`

- Accuracy: **0.9870**
- Balanced accuracy: **0.9914**

| Actual \ Predicted | Asthma | Non-Asthma |
|---|---:|---:|
| Asthma | 38 | 0 |
| Non-Asthma | 2 | 114 |

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Asthma | 0.9500 | 1.0000 | 0.9744 | 38 |
| Non-Asthma | 1.0000 | 0.9828 | 0.9913 | 116 |
| accuracy | — | — | 0.9870 | 154 |
| macro avg | 0.9750 | 0.9914 | 0.9828 | 154 |
| weighted avg | 0.9877 | 0.9870 | 0.9871 | 154 |

## Trạng thái

- Đã có kết quả: **96/96** tổ hợp, bao gồm FP32 đối chứng.
- Báo cáo không tự thay đổi thứ tự ưu tiên checkpoint đã chuyển giao từ bước C.
- Validation có thể dùng để so sánh method lượng tử; historical Test chỉ dùng báo cáo sau khi phạm vi đã khóa.
- INT16x8 cần đường inference `int16_t`; không thay trực tiếp model INT8 hiện tại.
