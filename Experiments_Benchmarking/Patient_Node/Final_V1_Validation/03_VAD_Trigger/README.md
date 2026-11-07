# 03 — VAD & Trigger | Patient Node Final V1

## 1. Mục tiêu và phạm vi

Nghiệm thu thuật toán kích hoạt **Auto Monitor** trong `I2S_Mic.cpp` trên bản ghi PCM16 của ESP32-S3 + INMP441; sau đó thử trên Node thật. Kế thừa WAV, `source_group` và Calibration/Test đã khóa từ `02_Quality_Check`. **Không** sửa hay thu lại Dataset V2. **Không** tinh chỉnh lại Quality Gate hoặc Classification Threshold.

- **Manual Check**: người dùng yêu cầu, thu liên tục đúng 80.000 mẫu/5s, **không VAD**, không tham gia khảo sát này.
- **Auto Monitor**: chờ trigger → thu 5s → Quality Gate → DSP → AI; State Machine điều phối các lần thu tới **ba kết quả để Voting**. Script offline **chỉ mô phỏng VAD/listen/capture/re-arm**, không mô phỏng Quality/AI/Voting.
- **Silence**: `silence_old_01` (`silence_5min.wav`), bản thu môi trường im lặng có nhiễu nền thực, là **một** session.
- **Room noise**: các nguồn sinh hoạt phòng như âm thanh xa, xe cộ, cửa/bước chân, không phải Silence; VAD energy-based hoàn toàn có thể kích hoạt bởi âm thanh này.

## 2. Hợp đồng firmware đang giữ nguyên

| Tham số | Giá trị baseline | Ý nghĩa |
|---|---:|---|
| Sample rate | 16000 Hz | PCM16, không normalize |
| Chunk | 256 mẫu | 16 ms/chunk |
| `kVadThreshold` | 75 | Trigger khi integer MAV `>75` |
| `kVadConsecutiveRequired` | 4 | 4 chunk liên tục → xác nhận ~64 ms |
| `kWarmupChunks` | 100 | 1,6 s sau Monitor Reset |
| `kPreRollSamples` | 16000 | Dung lượng ring 1s, chỉ dùng phục hồi candidate onset |
| `kTotalSamples` | 80000 | 5s tính **từ candidate onset** |

VAD `MAV = floor(sum(abs(PCM16_i))/num_samples)` tính **trực tiếp trên chunk**; `abs(-32768)=32768`. Khi một chunk không đạt ngưỡng, `consecutive` reset. Khi đủ bốn chunk, code truy hồi 1024 mẫu (64 ms) từ vị trí **chunk active đầu tiên**, **không** tự chèn 1 giây ring trước nó. Nếu sự kiện âm học bắt đầu nhỏ hơn ngưỡng thì có thể bỏ phần onset yếu trước candidate; phần này phải đánh giá riêng trên waveform/event annotations. **Pre-onset margin 160/250 ms chưa hề được triển khai** trong firmware.

Sau capture, `I2S_MonitorPrepareNextCapture()` xóa ring và trạng thái candidate, không warm-up micro lại. Muốn trigger tiếp cần đổ đầy lại ring ít nhất 1 giây.

## 3. Files

```text
03_VAD_Trigger/
├── README.md
├── vad_utils.py                    # thuật toán đúng MAV, ring, capture, re-arm
├── Simulate_VAD_Trigger.py         # plan / calibrate / test
├── test_vad_utils.py               # unit tests cạnh biên
├── VAD_Trigger_Selection.ipynb     # phân tích, 9 candidates, onset, freeze, test
├── hardware_validation_template.csv
├── results/                         # output chỉ sinh khi chạy
└── figures/
```

## 4. Chạy trên Windows (PowerShell)

Đặt folder `03_VAD_Trigger` **cùng cấp** `02_Quality_Check` trong:

`Experiments_Benchmarking/Patient_Node/Final_V1_Validation/`

Điều kiện: [quality_window_manifest.csv](../02_Quality_Check/results/quality_window_manifest.csv) và [final_quality_gate.json](../02_Quality_Check/results/final_quality_gate.json) đã tồn tại, `manifest_sha256` khớp. Thư mục WAV tại vị trí như manifest của Quality (manifest lưu **đường dẫn tuyệt đối**).

```powershell
py -3.11 -m pip install numpy pandas matplotlib jupyter nbformat

cd "Experiments_Benchmarking/Patient_Node/Final_V1_Validation/03_VAD_Trigger"
py -3.11 .\test_vad_utils.py
py -3.11 .\Simulate_VAD_Trigger.py plan
py -3.11 .\Simulate_VAD_Trigger.py calibrate
```

Nếu Quality ở vị trí khác, truyền đường dẫn tường minh (chỉ đối với `plan`):

```powershell
py -3.11 .\Simulate_VAD_Trigger.py plan --qc-manifest "D:\path\02_Quality_Check\results\quality_window_manifest.csv" --qc-freeze "D:\path\02_Quality_Check\results\final_quality_gate.json"
```

### Khác biệt so với thí nghiệm 02

- `plan`: **không dùng lại hai crop 5s** làm tín hiệu VAD. Dedupe manifest 02 thành **mỗi WAV master gốc một nguồn**, mỗi Playback take một WAV; xác minh đủ 33 Environment + hai legacy. Đọc header WAV của cả Calibration/Test, **không đọc PCM Test**.
- `calibrate`: chỉ đọc nguyên WAV *Calibration*, sinh `calibration_chunk_mav.npz` chứa MAV 256-sample (và `len` cho chunk cuối), cùng CSV metadata. Không áp dụng ngưỡng nào để huấn luyện hoặc đổi PCM.
- Notebook: mô phỏng từng tệp, sweep 9 cấu hình `{50,75,100} × {3,4,5}`, so sánh Playback activation/nhóm nguồn và Silence/Environment activations. Khảo sát 64ms với waveform MAV trước candidate onset. **Chọn thủ công**, không tự động lấy candidate đứng đầu.
- `Freeze`: bật `FREEZE_NOW=True` một lần **sau khi phân tích Calibration**. Lưu `results/final_vad_trigger.json` với hash manifest/Calibration. Không chỉnh Test rồi chốt lại.
- `Test`: sau Freeze mới bật `RUN_HELDOUT_TEST=True`. Script mở WAV Test một lần, mô phỏng cấu hình FROZEN, lưu `test_source_metrics.csv`, `test_chunk_mav.npz`, `test_trigger_events.csv`.

Notebook tự tìm `03_VAD_Trigger` khi được mở từ chính thư mục này, từ `Final_V1_Validation` hoặc từ root repository. Cách ít nhầm nhất vẫn là mở terminal tại `03_VAD_Trigger`; dùng kernel Python 3.11. Trước khi khởi tạo lại một thí nghiệm, lưu/di chuyển `results/` và `figures/`; script từ chối ghi đè.

## 5. Phân biệt hai điều kiện thời gian khi mô phỏng

**Environment/Silence master**: mô phỏng từ lúc Monitor Reset, bỏ warm-up 100 chunk, đợi ring >=16000 mẫu. VAD hoạt động khi ring sẵn sàng. Khi trigger và đang Capture, script **không** tính VAD; sau Capture ring được xóa và cần refill.

**Playback `__take01/02`**: bản ghi đã chứa ~1 giây phía trước cửa sổ 1–6 giây. Mô phỏng **đã warm-up trước lúc user phát**, lấy phần đầu WAV để refill ring và bắt đầu tìm trigger khi ring đủ dữ liệu. Đây là giả định thực nghiệm hợp lý cho nút LISTENING rồi mới phát Playback, **không** đại diện cho toàn bộ luồng power-on từ đầu file và **không** chứng minh sự kiện bắt đầu chính xác tại giây thứ 1. Dùng các mẫu PCM gốc của file, không nhân bản/normalize hoặc thêm im lặng giả.

Nếu playback WAV ngắn, trigger phát hiện gần cuối và không đủ 5 giây PCM để mô phỏng capture trọn vẹn, kết quả `capture_complete=False` là **WAV hết dữ liệu**, không phải lỗi DMA/Node. Để xác nhận Capture thực, xem log trên ESP32-S3.

## 6. Các chỉ số và hạn chế

- `activated_files` hoặc `activated_groups`: WAV/nhóm Playback có ít nhất một trigger. **Không gọi đây là respiratory onset recall** nếu thiếu ground truth thời gian của sự kiện.
- `silence_triggers_per_min`: số lần VAD kích hoạt trong một master im lặng. Chỉ một session, không đủ bao quát đa dạng phòng.
- `env_mean_activations_per_min`: số trigger/phút trung bình theo từng session thuộc Environment, không gọi tất cả là false trigger bởi đây là **các sự kiện âm thanh thật**.
- `candidate_onset_s`: thời điểm đầu chunk active đầu tiên; `confirmed_s`: thời điểm hoàn thành N chunk; `recovered_ms`: N × 16ms nếu nhận chunk đủ. **Không đồng nghĩa giữ được acoustic onset thực**.
- `complete_within_file`: còn đủ dữ liệu trong WAV nguồn sau trigger để hoàn thành cửa sổ 5 giây.
- Simulation không bao gồm `Quality_Check.cpp`, DSP, Model, 3-vote hoặc thời gian xử lý AI; `max_triggers=3` (nếu kiểm tra riêng) chỉ là ba *cơ hội capture*, không phải ba kết quả được chấp nhận.

## 7. Nghiệm thu phần cứng (một đợt thử ngắn)

| ID | Kịch bản | Khởi điểm | Kiểm tra |
|---|---|---|---|
| H01 | Phòng yên | Auto Monitor LISTENING 60s | Trigger/phút, READY ổn định |
| H02 | Playback Asthma | 5 WAV khác source, chọn cả mẫu yếu | Kích hoạt, lưu onset, capture 5s |
| H03 | Playback Non-Asthma | 5 WAV khác source | Kích hoạt, Quality Gate |
| H04 | Thở/ho tự nhiên không cố sức | Vài lượt phù hợp | Khả năng nhận sự kiện yếu, không gắng sức |
| H05 | Fan / speech / podcast | 30–60s/nguồn | Ghi sự kiện môi trường kích hoạt (không mặc định lỗi) |
| H06 | Room noise / clap / knock | 30–60s hoặc vài event tự nhiên | Phản ứng với biến động âm thanh |
| H07 | Auto Monitor 3 lượt | 3 lần phát khi **LISTENING READY** | 3 capture → Quality → DSP/AI → 3-vote thực; re-arm ring |

Ghi lại timestamp nếu đo độ trễ. Các log hữu ích: `[VAD] Xác nhận`, `[MIC] Monitor đã thu đủ 5 giây`, `[QUALITY]`, trạng thái Voting của State Machine. `recovered_ms = 64` **chỉ** cho biết thời gian 4 chunk đã lấy lại từ ring, chưa chứng minh không mất tín hiệu yếu trước candidate. Dùng [hardware_validation_template.csv](hardware_validation_template.csv) để thống nhất ghi kết quả.

**Điều kiện nghiệm thu:** Chốt `threshold/consecutive` trên Calibration, dùng Held-out Test để **báo cáo** mà không đổi lại tham số, rồi kiểm tra trực tiếp từng lượt trên Node. Giữ Quality Gate FROZEN độc lập.
