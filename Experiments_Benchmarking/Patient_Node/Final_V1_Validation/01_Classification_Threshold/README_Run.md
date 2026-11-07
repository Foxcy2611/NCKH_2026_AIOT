# C4/V1/s44 QAT INT8 — Classification Threshold

## Vị trí cài đặt

Chép bốn file `.py`/`.ipynb` trong gói này vào:

`Experiments_Benchmarking/Patient_Node/Final_V1_Validation/01_Classification_Threshold/`

Đừng đổi tên file Python (`Generate_Predictions.py`, `threshold_utils.py`, `Prepare_Playback_Calibration.py`). Notebook tự tìm thư mục thí nghiệm từ working directory; hai script cũng tự dò root dự án qua `AI_Training_Model/` và `Experiments_Benchmarking/`, nên không còn phụ thuộc cứng vào số cấp thư mục cha.

Phụ thuộc: `numpy`, `pandas`, `matplotlib`, `tensorflow`, `ipykernel` (nếu chạy notebook). Python 3.11 là một lựa chọn tương thích với thiết kế hiện tại.

## Điều kiện trước khi chạy

Cần đủ artifact gốc theo đường dẫn cố định trong `Generate_Predictions.py`:

1. `Experiments_Benchmarking/Patient_Node/Frontend_Benchmarking/artifacts/features/combo_pre0_mel40_fft2048/{X_val,Y_val,Files_val}.npy`.
2. Cùng thư mục như trên cho split `test` (CHỈ dùng sau khi freeze).
3. `Experiments_Benchmarking/Patient_Node/Frontend_Benchmarking/artifacts/D_Quantization/combo_pre0_mel40_fft2048__V1__s44/methods/QAT_INT8/QAT_INT8.tflite`.
4. `conversion_metadata.json` đi kèm model, có đúng `trial_id`, `method_id`, normalization và SHA.

Script cố tình từ chối chạy nếu hash file `.tflite` khác `EXPECTED_MODEL_SHA256` trong `Generate_Predictions.py`. Không tự thay SHA để ép model khác chạy.

## Cách chạy trên Windows, từ root NCKH

```powershell
py -3.11 -m pip install numpy pandas matplotlib tensorflow ipykernel
py -3.11 "Experiments_Benchmarking/Patient_Node/Final_V1_Validation/01_Classification_Threshold/Generate_Predictions.py" --split val
```

Mở `Threshold_Selection.ipynb` trong VS Code/Jupyter và chọn kernel Python 3.11 có `tensorflow`.

1. Chạy các cell từ Setup đến hết mục **4** (Validation distribution, candidate và grid). Cell kiểm tra Playback-offset được mặc định tắt, vì không dùng chung kho feature phục vụ threshold.
2. Đọc bảng số mẫu lỗi/UNSURE và coverage; chọn một cặp LOW/HIGH chỉ theo Validation. `0.40 / 0.90` chỉ là **ứng viên lịch sử**, không phải ngưỡng đã xác minh trên bản upload này.
3. Tại mục **5** điền `FINAL_LOW`/`FINAL_HIGH` (đang `None` để không freeze tự động), nêu lý do ở `SELECTION_RATIONALE`, chạy cell và kiểm tra metric.
4. Tại mục **6**, export `final_threshold.json` có `status=FROZEN`. Nếu đã freeze một cặp khác, code sẽ từ chối ghi đè.
5. Sau khi freeze mới chạy mục **7** để sinh Test prediction và đánh giá một lần. **Không quay về đổi LOW/HIGH theo Test**.

Outputs nằm trong `results/combo_pre0_mel40_fft2048__V1__s44_QAT_INT8/`; figure trong `figures/...`.

## So sánh ngưỡng float và raw INT8

`p_non_asthma` của model có scale/zero point từ TFLite. `final_threshold.json` ghi thêm hai trường:

- `low_output_int8_inclusive`
- `high_output_int8_inclusive`

Firmware nên kiểm tra `int(raw) <= low_raw` -> ASTHMA, `int(raw) >= high_raw` -> NON_ASTHMA; còn lại UNSURE.

Ví dụ **chỉ đúng với `output_scale=1/256`, `output_zero_point=-128`**: `LOW=.40` -> raw <= -26; `HIGH=.90` -> raw >= 103. Giá trị high 102 sẽ lệch quyết định float ở biên.

## Prepare_Playback_Calibration.py

**Không chạy ở giai đoạn chọn LOW/HIGH.** Script này chọn WAV biên độ đủ mạnh cho loa/INMP441 và kiểm thử trigger/VAD sau này. Nó hiện có thể chọn WAV từ Test, thậm chí ưu tiên mẫu model đoán đúng; vì vậy đây là bộ test chức năng có chọn lọc, **không phải tập đánh giá độ chính xác/VAD độc lập**. Nếu cần hiệu chỉnh VAD có ý nghĩa thống kê, dùng tập phát triển riêng (Validation/calibration hoặc WAV mới), để Test cho đánh giá cuối.

## Kiểm tra đường dẫn hiện tại

- Cú pháp cả ba script Python và toàn bộ cell notebook: hợp lệ.
- 256 mã output INT8: cùng quyết định float/raw cho các cặp ngưỡng thử (gồm 0.40/0.90).
- Kiểm thử khóa freeze: không cho đổi LOW/HIGH khi `final_threshold.json` đã đóng băng.
- Đã xác nhận feature Val/Test, model `QAT_INT8.tflite`, `conversion_metadata.json`, prediction Test của Frontend và manifest PCM16 Phase 4 đều tồn tại tại đúng đường dẫn.
- Việc kiểm tra liên kết không tự chạy lại inference hoặc thay đổi kết quả nghiệm thu; hãy chạy theo thứ tự Validation -> freeze -> Test ở trên.
