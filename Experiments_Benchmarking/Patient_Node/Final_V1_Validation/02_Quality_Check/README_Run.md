# Quality Gate V1 — bản gọn, chạy tái lập

Bộ này dành cho `Experiments_Benchmarking/Patient_Node/Final_V1_Validation/02_Quality_Check`.

## Các thay đổi

- `Quality_Gate_Selection.ipynb`: 14 cell (từ 29), giữ audit → phân bố → 432-candidate sweep/Playback retention → kiểm tra V1 → Freeze → Test → đối chứng bổ sung. Không chép các đoạn nhận xét dài và output cũ. Mặc định không tự freeze hoặc mở Test.
- `Extract_Quality_Metrics.py`: khi tạo Test, xuất thêm `test_metrics_provenance.json`. File này gắn SHA-256 của Test CSV, JSON FROZEN, manifest, calibration và các WAV nguồn của Test. Không ghi đè output cũ.
- `quality_utils.py`: các hàm sinh và kiểm chứng provenance. **Không thay đổi công thức RMS, block MAV, clipping hay thứ tự quyết định.**
- `test_quality_utils.py`: 11 unit tests, thêm các ngưỡng biên và chống cache Test bị sửa.

## Chạy trên Windows (PowerShell)

1. Sao lưu `results/` **cũ** ra ngoài thư mục thí nghiệm (bao gồm `final_quality_gate.json` và mọi output Test); tùy chọn sao lưu `figures/`. Nếu lưu vào trong dự án, đặt trong thư mục archive riêng. Không ghi đè kết quả đã freeze.
2. Copy 4 file từ gói này vào `02_Quality_Check`, thay thế file cùng tên. Xác nhận có đúng `AI_Training_Model`, `Experiments_Benchmarking`, `Final_Project_NCKH` trong repository root.
3. Mở PowerShell **trong `02_Quality_Check`**, chạy:

```powershell
py -3.11 -m unittest -v test_quality_utils.py
py -3.11 .\Extract_Quality_Metrics.py plan --windows-per-session 2 --with-playback
py -3.11 .\Extract_Quality_Metrics.py calibrate
```

4. Mở `Quality_Gate_Selection.ipynb`, chọn kernel Python 3.11 và chạy lần lượt đến cell *Xác nhận V1 trên Calibration*. So sánh số cửa sổ và trường hợp `AUDIO_INACTIVE` với hồ sơ cũ.
5. **Nếu dữ liệu và cách chia tập giữ nguyên**, trong cell Freeze đặt `FREEZE_NOW=True`, chạy riêng cell này để tạo `results/final_quality_gate.json` mới. Notebook cố định ngưỡng V1 cũ (`20,20,1%,1%`) để tái lập; **không dùng Test trước đây để chọn lại ngưỡng**.
6. Trong cell Held-out Test đặt `RUN_HELDOUT_TEST=True`. Script xuất `results/test_metrics.csv` **và** `results/test_metrics_provenance.json`; notebook từ chối cache thiếu/sai SHA.
7. Muốn đối chứng thêm: chép `vad_silence_session_01.wav` vào `extra_validation/` (hoặc khai báo `SILENCE_NEW_PATH`), đặt `RUN_SUPPLEMENTAL=True` và chạy riêng cell cuối. Kết quả nằm ở `results/supplemental_validation/`.

**Không chạy ngay `Run All` với `FREEZE_NOW=True` và `RUN_HELDOUT_TEST=True` khi chưa xem Calibration.**

## Dữ liệu đầu vào

- Script đòi WAV **PCM16 LE mono 16 kHz** và cửa sổ **5 giây**.
- Split 33 Environment V2 phải đúng file `environment_session_split.csv` do Phase 1 xuất; không tự chia lại.
- Chưa có dataset/WAV, manifest hay firmware trong gói. Do vậy các thống kê thực nghiệm cần chạy trên máy bạn.
- Các mốc lịch sử dùng đối chiếu: Calibration 207/208 `AUDIO_OK`; Test 21/22 `AUDIO_OK`; Playback 144/144 Calibration, 16/16 Test. Nếu kết quả mới khác, kiểm tra input và code trước khi kết luận.
- Test cũ đã được xem ở phiên trước. Chạy lại Test với cùng ngưỡng là **tái lập kỹ thuật**, không tạo một Test độc lập mới.
- Unit tests đã PASS trên Python với tín hiệu giả lập, nhưng chưa thể khẳng định parity với C++/ESP32 vì chưa có firmware và log board trong gói.
