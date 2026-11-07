# Bổ sung nghiệm thu ba nguồn — Patient Node Final V1

## Tệp cần sử dụng

- `Quality_Gate_Selection_3Session_Reviewed.ipynb` — thay notebook trong `02_Quality_Check`.
- `VAD_Trigger_Selection_3Session_Reviewed.ipynb` — thay notebook trong `03_VAD_Trigger`.

Các code cell gốc và kết quả đã chạy được giữ nguyên. Các code cell mới ở **mục 7** chưa chạy trên WAV của dự án; cần thực hiện trên máy đang lưu Dataset.

## Chuẩn bị nguồn

1. Giữ nguyên `silence_5min.wav` và `room_noise_session_02` tại vị trí Dataset V2 cũ. Cell tự tìm các WAV này qua manifest Calibration.
2. Chép `vad_silence_session_01.wav` vào một trong các folder sau:
   - `03_VAD_Trigger/extra_validation/`
   - `02_Quality_Check/extra_validation/`
   - `Final_V1_Validation/extra_validation/`
3. Nếu để ở đường dẫn khác, sửa biến `SILENCE_NEW_PATH = Path(r"D:\\...\\vad_silence_session_01.wav")` tại cell **7.1** trong **từng notebook**.
4. WAV phải là PCM16 mono 16000 Hz, không normalize hay DSP.

**Không** thêm hai bản ghi mới vào `Env_session.csv`, `quality_window_manifest.csv` hoặc `vad_source_manifest.csv`. `room_noise_session_02` đã có sẵn trong Calibration; `vad_silence_session_01.wav` ở ngoài manifest chính.

## Chạy và nhận kết quả

- Trong Quality Check, mở notebook mới, có thể chạy riêng **7.1 → 7.2** sau khi đã chạy Setup (mục 0). Mục 7 ghi kết quả vào `results/supplemental_validation/three_session_quality_windows.csv`.
- Trong VAD Trigger, mở notebook mới, chạy Setup (mục 0) rồi **7.1 → 7.2**. Mục 7 ghi `three_session_vad_sources.csv` và `three_session_vad_qc_events.csv` vào `03_VAD_Trigger/results/supplemental_validation/`.
- Cả hai tạo thêm các biểu đồ đối chiếu. Không cần chạy lại sweep, Freeze hoặc Held-out Test để xem kết quả bổ sung.

## Diễn giải và bảo toàn tính độc lập

- `silence_5min.wav`: Silence lịch sử có tín hiệu/nhiễu nền lớn hơn, từng dùng cho 139 mẫu Asthma time_shift; không coi là Non-Asthma hay nguồn Test AI độc lập.
- `vad_silence_session_01.wav`: Silence mới ngoài manifest. Nếu dùng để lựa chọn lại ngưỡng VAD/Quality, nó trở thành dữ liệu Development, không còn là Test độc lập cho cấu hình mới.
- `room_noise_session_02`: môi trường hoạt động, **không** dùng làm Silence.
- VAD chỉ kích hoạt thu; Quality Gate chỉ kiểm tra PCM16. `AUDIO_OK` chưa phải một vote; còn phải chạy DSP/AI thành công. Chỉ State Machine thực tế mới kiểm chứng được Voting 3 lần.
- Kết quả mới không làm thay đổi JSON Quality Gate V1 đã FROZEN. Nếu có lý do thay đổi, tạo V2 riêng với phép đánh giá độc lập phù hợp.
