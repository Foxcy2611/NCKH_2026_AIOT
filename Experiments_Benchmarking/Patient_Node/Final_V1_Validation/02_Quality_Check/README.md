# 02 - Quality Check | Patient Node Final V1

## 1. Mục đích

Folder này dùng để hiệu chỉnh **Quality Gate** cho một cửa sổ âm thanh dài 5 giây trước khi đưa qua DSP và model AI.

Quality Gate trả lời câu hỏi:

> Đoạn PCM16 vừa thu có đủ chất lượng để inference hay phải từ chối và yêu cầu thu lại?

Nó phát hiện các trường hợp chính:

- âm thanh gần như không hoạt động: `AUDIO_INACTIVE`;
- âm thanh bị clipping/quá lớn: `AUDIO_TOO_LOUD`;
- âm thanh quá yếu: `AUDIO_TOO_WEAK`;
- cửa sổ đủ điều kiện inference: `AUDIO_OK`.

Quality Gate **không phân loại Asthma/Non-Asthma** và cũng **không thay thế VAD**:

- VAD quyết định thời điểm kích hoạt thu;
- Quality Gate kiểm tra cửa sổ 5 giây đã thu;
- model AI chỉ chạy nếu cửa sổ đạt `AUDIO_OK`.

```text
INMP441 -> VAD kích hoạt -> thu đủ 5 giây -> Quality Gate
                                              |
                          REJECT <-------------+-------------> AUDIO_OK -> DSP -> AI
```

Toàn bộ phép đo được thực hiện trực tiếp trên **PCM16 mono 16 kHz trước normalize và trước DSP**. Không dùng Log-Mel hoặc WAV Kaggle 4 kHz để chọn ngưỡng biên độ của INMP441.

## 2. Các thông số được khảo sát

### Hợp đồng tín hiệu cố định

| Thông số | Giá trị |
|---|---:|
| Định dạng | PCM16 little-endian, mono |
| Sample rate | 16.000 Hz |
| Độ dài cửa sổ | 5 giây |
| Số mẫu | 80.000 |
| Kích thước block | 256 mẫu |
| Số block | 313 |
| Mức kiểm tra clipping | `abs(sample) > 32000` |

### Bốn ngưỡng cần hiệu chỉnh

| Tham số Python | Hằng số C++ tương ứng | Ý nghĩa | Baseline hiện tại |
|---|---|---|---:|
| `min_rms` | `kMinRMS` | RMS tối thiểu của toàn bộ cửa sổ | `20.0` |
| `active_block_threshold` | `kActiveBlockThreshold` | MAV tối thiểu để một block được coi là active | `20` |
| `min_active_ratio` | `kMinActiveRatio` | Tỷ lệ block active tối thiểu | `0.01` |
| `max_clipped_ratio` | `kMaxClippedRatio` | Tỷ lệ mẫu clipping tối đa | `0.01` |

Hai thông số sau được giữ cố định trong thí nghiệm:

```text
clip_level = 32000
block_size = 256
```

Thứ tự quyết định phải giống firmware:

```text
active_ratio < min_active_ratio
    -> AUDIO_INACTIVE

clipped_ratio > max_clipped_ratio
    -> AUDIO_TOO_LOUD

rms < min_rms
    -> AUDIO_TOO_WEAK

còn lại
    -> AUDIO_OK
```

## 3. Thành phần trong folder

| File/thư mục | Chức năng |
|---|---|
| `quality_utils.py` | Tính RMS, Peak, clipping ratio, MAV nguyên từng block và active ratio; giữ logic quyết định tương đương C++. |
| `test_quality_utils.py` | Unit test bằng PCM tổng hợp để kiểm tra phép tính và thứ tự quyết định. Không dùng để chọn ngưỡng. |
| `Extract_Quality_Metrics.py` | Tạo kế hoạch cửa sổ và trích metric qua ba lệnh `plan`, `calibrate`, `test`. |
| `Quality_Gate_Selection.ipynb` | Phân tích phân bố, sweep ngưỡng, chọn thủ công, đóng băng cấu hình và mở Test. |
| `README_Run.md` | Hướng dẫn ngắn dành cho bộ script/notebook tái lập mới. |
| `results/` | Chứa manifest, metric Calibration/Test và cấu hình cuối. |
| `figures/` | Chứa biểu đồ sinh từ notebook. |

## 4. Cách chạy ngay

Mở PowerShell tại đúng thư mục:

```text
Experiments_Benchmarking/Patient_Node/Final_V1_Validation/02_Quality_Check
```

Nếu môi trường chưa có thư viện:

```powershell
py -3.11 -m pip install numpy pandas matplotlib jupyter
```

Sau đó chạy lần lượt:

```powershell
py -3.11 -m unittest -v test_quality_utils.py

py -3.11 .\Extract_Quality_Metrics.py plan --windows-per-session 2 --with-playback

py -3.11 .\Extract_Quality_Metrics.py calibrate
```

**Lưu ý trước khi chạy lại bản script đã cập nhật:** lưu trữ folder `results/` và `figures/` của bản thử cũ (202 Calibration / 28 Test trên manifest trước đây). `plan` cố ý không ghi đè. Không được giữ lại CSV cũ khi đổi thuật toán phân chia session.

Nếu `environment_session_split.csv` chưa tồn tại hoặc thiếu cột session/split, script sẽ dừng và hiển thị lý do; cung cấp đúng CSV xuất từ `03_Cut_Environment.py`, **không đổi sang chia ngẫu nhiên**.

Trong điều kiện Dataset V2 và Playback giống lần chạy trước, dự kiến **208 cửa sổ Calibration / 22 cửa sổ Test** (64/6 cửa sổ Environment+Legacy và 144/16 Playback), nhưng chỉ dùng số thực tế mà `plan` xác nhận.

Ý nghĩa từng lệnh:

1. `test_quality_utils.py`
   - kiểm tra Python có khớp các trường hợp biên của firmware không;
   - cần thấy toàn bộ test trả về `OK`.

2. `plan`
   - đọc danh sách Environment và Playback;
   - chia theo session/source group để tránh leakage;
   - chọn tối đa hai cửa sổ 5 giây cho mỗi Environment session;
   - tạo `results/quality_window_manifest.csv`.

3. `calibrate`
   - chỉ đọc các cửa sổ thuộc Calibration;
   - tính RMS, Peak, clipping ratio, active ratio và MAV từng block;
   - tạo `results/calibration_metrics.csv`;
   - chưa đọc tín hiệu Test.

Tùy chọn `--with-playback` đưa thêm WAV `__take01/02` đã thu qua INMP441 vào phép khảo sát. Các playback được crop từ **1–6 giây**, giống quy tắc preprocess trước đó. Mục đích là kiểm tra Quality Gate có loại nhầm tín hiệu hô hấp phát lại hay không.

Nếu chỉ muốn khảo sát Environment, bỏ tùy chọn này:

```powershell
py -3.11 .\Extract_Quality_Metrics.py plan --windows-per-session 2
```

### Chạy từ repository root

```powershell
py -3.11 "Experiments_Benchmarking/Patient_Node/Final_V1_Validation/02_Quality_Check/Extract_Quality_Metrics.py" plan --windows-per-session 2 --with-playback

py -3.11 "Experiments_Benchmarking/Patient_Node/Final_V1_Validation/02_Quality_Check/Extract_Quality_Metrics.py" calibrate
```

## 5. Chạy notebook và chọn ngưỡng

Mở `Quality_Gate_Selection.ipynb`, chọn kernel Python 3.11 rồi chạy theo thứ tự.

### Bước 0 - Setup

- tự tìm repository và folder thí nghiệm;
- đọc manifest và Calibration;
- kiểm tra không có session leakage sang Test.
 
### Bước 1 - Phân tích Calibration

- kiểm toán inventory 33 session và split chính thức (27/3/3) trước khi xem RMS;
- xem các mẫu có RMS thấp/cao;
- xem phân bố RMS, active ratio và clipping ratio;
- đối chiếu theo `subtype` và `source_kind`.

### Bước 2 - Sweep ứng viên

Notebook khảo sát nhiều tổ hợp của bốn ngưỡng. Kết quả được lưu tại:

```text
results/candidate_quality_sweep.csv
```

Notebook không tự động coi hàng đầu tiên là cấu hình tốt nhất. Cần kiểm tra:

- silence có được đưa về `AUDIO_INACTIVE` không;
- tín hiệu nghe được có bị reject nhầm không;
- playback hô hấp có bị loại nhầm không;
- tỷ lệ clipping có hợp lý không.

### Bước 3 - Chọn thủ công

Điền bốn giá trị:

```python
FINAL_MIN_RMS = ...
FINAL_ACTIVE_BLOCK_THRESHOLD = ...
FINAL_MIN_ACTIVE_RATIO = ...
FINAL_MAX_CLIPPED_RATIO = ...
SELECTION_NOTE = "Lý do lựa chọn dựa trên Calibration..."
```

Chạy cell để xem lại toàn bộ trạng thái trên Calibration trước khi đóng băng.

### Bước 4 - Freeze

Sau khi chắc chắn cấu hình cuối chỉ được chọn bằng Calibration:

```python
FREEZE_NOW = True
```

Cell này tạo:

```text
results/final_quality_gate.json
```

File JSON lưu threshold, hash manifest, hash Calibration và lý do lựa chọn. Sau khi freeze, không sửa manifest hoặc Calibration.

### Bước 5 - Held-out Test

Chỉ sau khi đã freeze mới đặt:

```python
RUN_HELDOUT_TEST = True
```

Notebook sẽ gọi tương đương:

```powershell
py -3.11 .\Extract_Quality_Metrics.py test
```

Test chỉ dùng để báo cáo khả năng tổng quát hóa, không dùng để quay lại điều chỉnh ngưỡng.

## 6. Các output chính

| Output | Nội dung |
|---|---|
| `results/quality_window_manifest.csv` | Danh sách file, session, split và vị trí crop của từng cửa sổ. |
| `results/calibration_metrics.csv` | Metric PCM16 của tập Calibration. |
| `results/candidate_quality_sweep.csv` | Kết quả sweep các tổ hợp threshold. |
| `results/final_quality_gate.json` | Cấu hình đã đóng băng và hash bảo vệ dữ liệu. |
| `results/test_metrics.csv` | Metric và trạng thái cuối trên held-out Test. |
| `results/test_metrics_provenance.json` | SHA-256 ràng buộc Test với manifest, Calibration, cấu hình FROZEN và WAV nguồn. |
| `figures/calibration_quality_distributions.png` | Phân bố RMS, active ratio và clipping ratio. |

Nếu output đã tồn tại, script chủ động dừng để tránh ghi đè kết quả cũ. Muốn làm lại một thí nghiệm, hãy lưu trữ `results/` và `figures/` cũ trước khi chạy lại `plan`.

## 7. Nguồn dữ liệu và quy tắc chia

### Environment

Script đọc:

```text
AI_Training_Model/Dataset_TuThu_v_Kaggle/TuThu/TKe/Env_session.csv
AI_Training_Model/Dataset_TuThu_v_Kaggle/TuThu/Record_Env/
```

- Mỗi session được giữ nguyên trong một split.
- `train/val` được đưa vào Calibration.
- `test` được giữ làm held-out Test.
- **Bản V2 cuối:** 33 Environment chính phải khớp inventory trong `Environment_Data_Collection_Guide_V2.md`.
- **Split duy nhất được tin cậy** lấy từ `AI_Training_Model/Phase1_Split_Data/Output/03_Cut_Environment/environment_session_split.csv`, kiểm tra cơ cấu **Train=27 / Val=3 / Test=3** theo subtype.
- `Env_session.csv` dùng để xác nhận ID, tên WAV, subtype và metadata; nếu split cũ là `unassigned`, script đối chiếu CSV chia tập chính thức, **không tự chia lại 20%**. Nếu có split mâu thuẫn, dừng.
- `podcast_old_01` thuộc 33 session chính; `keyfan_old_01` là legacy Train; `silence_old_01` là quality_check_asset ngoài 33 và chỉ dùng trong Calibration.
- `not_applicable` chỉ áp dụng cho `silence_old_01`; nó không đại diện cho các session Silence độc lập ở Test.

### Playback

Khi dùng `--with-playback`, script đọc WAV PCM16 từ:

```text
AI_Training_Model/Dataset_Chia_V2/
```

Chỉ các file kết thúc bằng `__take01.wav` hoặc `__take02.wav` được dùng. Các take cùng nguồn nằm chung split và giữ split gốc của Dataset V2.

## 8. Áp dụng sang Patient Node

Sau khi chốt kết quả Calibration và báo cáo Test, đồng bộ bốn ngưỡng sang:

```text
Final_Project_NCKH/Patient_Node/src/Quality_Check.cpp
```

Các hằng số cần cập nhật:

```cpp
kMinRMS
kMinActiveRatio
kMaxClippedRatio
kActiveBlockThreshold
```

Sau đó dùng cùng một PCM16 để đối chiếu trạng thái Python với log `[QUALITY]` của Patient Node.

Không sửa VAD trong thí nghiệm này. Các tín hiệu như fan, podcast hoặc speech vẫn có thể là PCM hợp lệ; Quality Gate chỉ đánh giá **độ đủ dùng của cửa sổ**, không xác định nội dung âm thanh.

## 9. Lưu ý nghiệm thu

- Không dùng Test để chọn hoặc sửa threshold.
- Không thay manifest sau khi freeze.
- Không coi zero-buffer trong unit test là dữ liệu thực nghiệm.
- `silence_5min.wav` là **một** session legacy; hai cửa sổ 5 giây không phải hai phép đo độc lập. Trong Test hiện không có session Silence riêng; không tuyên bố độ nhạy AUDIO_INACTIVE trên nhiều môi trường chỉ từ một master.
- `silence` chỉ là tên nguồn thu: RMS/active ratio có thể cao nếu micro ghi nhận tiếng ù, nguồn thu chưa chắc là zero-signal. Phải xem waveform/nghe/đối chiếu metadata trước khi coi mọi cửa sổ Silence là ground truth.
- Nếu Test thiếu silence hoặc các tình huống lỗi clipping thực, ghi rõ giới hạn; không tăng ngưỡng cho tới khi toàn bộ playback hô hấp bị loại nhầm.
- Manifest chứa đường dẫn tuyệt đối, vì vậy không di chuyển dataset trong cùng một lần thí nghiệm.

## 10. Kiểm toán nguồn tham chiếu

Bản hướng dẫn dữ liệu dùng làm mốc: `Environment_Data_Collection_Guide_V2.md` bản inventory cuối (33 chính + 2 legacy). Không tự tạo các ID `podcast_session_01`, `fan_session_05`, `room_session_XX`. Nguồn chia tập chính thức là output `03_Cut_Environment`, không phải seed do notebook tự chọn. Quality Gate chỉ đo đặc tính biên độ và tính hợp lệ PCM16, không kết luận tiếng podcast/quạt là mẫu lỗi hoặc classifier nên chạy.
