# Asthma Playback Calibration

Dự án độc lập dùng để kiểm tra toàn bộ đường truyền:

```text
WAV gốc -> loa -> không gian phòng -> INMP441 -> ESP32-S3
        -> DSP/Mel C4 -> V1 QAT INT8 -> p_non_asthma
```

Firmware này được tách khỏi `Deploy_Model/3_Model_Complete` vì có thêm chức năng
dump PCM16 qua Serial và các công cụ calibration trên PC. Đây là **test harness**, không
phải firmware triển khai cuối cùng.

## Mục lục

- [Mục tiêu](#mục-tiêu)
- [Cấu hình đã khóa](#cấu-hình-đã-khóa)
- [Cấu trúc dự án](#cấu-trúc-dự-án)
- [Chuẩn bị](#chuẩn-bị)
- [Các script Python](#các-script-python)
- [Quy trình chạy](#quy-trình-chạy)
- [Dữ liệu đầu ra](#dữ-liệu-đầu-ra)
- [Lưu ý](#lưu-ý)

## Mục tiêu

Dự án trả lời các câu hỏi sau:

1. ESP32 có thu đủ đúng `80.000` mẫu PCM16 của cửa sổ 5 giây không?
2. Preprocessing và inference trên ESP32 có khớp với Python C4 V1 s44 QAT INT8 không?
3. Khi WAV Asthma bị dự đoán sai sau khi phát qua loa, nguyên nhân chính là cửa sổ
   VAD bị lệch hay đường truyền âm học loa/phòng/micro làm đổi đặc trưng?
4. Việc thêm playback vào dataset cải thiện khả năng nhận playback đến mức nào và
   có ảnh hưởng gì đến miền raw/common test?

Phần tổng hợp kết quả và kết luận domain shift nằm tại
[calibration_results/README.md](calibration_results/README.md).

## Cấu hình đã khóa

| Thành phần | Giá trị |
|---|---|
| Board | ESP32-S3 N16R8, PSRAM bật |
| Micro | INMP441 |
| Chân I2S | SCK `GPIO14`, WS `GPIO15`, SD `GPIO16` |
| Sample rate | `16.000 Hz`, mono PCM16 |
| Cửa sổ model | `5 s = 80.000 mẫu` |
| Ring lịch sử | 1 giây |
| VAD | năng lượng `> 75`, xác nhận 4 chunk liên tiếp |
| Kích thước chunk | 256 mẫu, khoảng 16 ms |
| Model | C4 V1 s44, SepConv2D + Flatten, QAT INT8 |
| Frontend | pre=0, FFT 2048, 40 Mel, hop 625 |
| Input model | `[1, 40, 129, 1]`, INT8 |
| Tensor Arena | 280 KiB trong PSRAM |
| Chuẩn hóa | Mel dB `[-80, 0]` -> `[0, 1]` -> INT8 |
| Ngưỡng kết luận | `p_non <= 0.20`: Asthma; `p_non >= 0.95`: Non-Asthma; còn lại: Unsure |
| Serial calibration | `460800 baud`, mặc định `COM11` |
| Số vote firmware | 3 |

Sau khi warm-up, firmware luôn giữ 1 giây gần nhất trong ring buffer. Chunk active đầu
tiên được đánh dấu làm candidate onset. Khi đủ 4 chunk active liên tiếp, firmware truy
hồi từ candidate onset rồi thu tiếp cho đến đủ đúng 5 giây. Toàn bộ cửa sổ này vừa được
đưa vào pipeline model, vừa được dump qua Serial khi:

```cpp
constexpr bool kEnableCaptureSerialDump = true;
```

## Cấu trúc dự án

```text
Asthma_Playback_Calibration/
├── include/                         Header firmware, model V1 INT8
├── src/                             I2S, DSP/Mel, inference và main
├── doc/                             Ghi chú về VAD/ring buffer
├── calibration_results/             Capture và báo cáo calibration
├── debug_capture/                   Artifact của một capture chạy bằng Python
├── Capture_Wav_From_Serial.py       Thu một frame PCM16 thành capture.wav
├── Run_Capture_V1_PTQ.py            Chạy capture.wav qua Python C4 QAT (giữ tên file lịch sử)
├── Run_Playback_Calibration.py      Tự động chạy 18 lượt playback
├── Analyze_Capture_Offset.py        Đo offset raw/capture bằng cross-correlation
├── Analyze_Shifted_Original_vs_Capture.py
│                                    Tách ảnh hưởng alignment và acoustic path
├── Analyze_Asthma_02_03.py          Batch phân tích Asthma file 02 và 03
└── platformio.ini
```

Các nguồn dùng chung được đọc trực tiếp từ repository:

- preprocessing: `AI_Training_Model/Phase2_Preprocess_&_Traning/Preprocess_Audio.py`;
- normalization: đọc trực tiếp từ `conversion_metadata.json` của C4 QAT;
- model: `Frontend_Benchmarking/artifacts/D_Quantization/combo_pre0_mel40_fft2048__V1__s44/methods/QAT_INT8/QAT_INT8.tflite`;
- WAV/manifest calibration: `Experiments_Benchmarking/Patient_Node/.../Playback_Calibration/`.

## Chuẩn bị

### Phần cứng

- ESP32-S3 N16R8 và INMP441 nối đúng các chân ở bảng trên.
- Loa giữ cố định vị trí, hướng phát và âm lượng trong toàn bộ 18 trial.
- Không thay phòng, khoảng cách hoặc thiết bị phát giữa các trial nếu mục tiêu là đo
  độ lặp lại.

### Python

Các script cần môi trường Python đã dùng để train/quantize model. Những package trực
tiếp gồm:

```powershell
py -m pip install numpy pyserial scipy matplotlib tensorflow
```

`Run_Playback_Calibration.py` tự phát WAV bằng `winsound`, do đó chức năng tự động này
hiện chỉ hỗ trợ Windows.

### Cấu hình cần kiểm tra

- `upload_port` trong `platformio.ini`;
- `SERIAL_PORT` trong `Capture_Wav_From_Serial.py`;
- `SERIAL_PORT` trong `Run_Playback_Calibration.py`;
- `kEnableCaptureSerialDump = true` trong `src/I2S_Mic.cpp`.

Không được mở PlatformIO Serial Monitor đồng thời với script Python vì một cổng COM
không thể được hai chương trình chiếm cùng lúc.

## Các script Python

### `Capture_Wav_From_Serial.py`

Thu đúng một cửa sổ từ ESP32:

- chờ marker `[CAPTURE_BEGIN]`;
- đọc đúng số byte firmware công bố, thông thường `160.000 byte`;
- kiểm tra metadata và checksum FNV-1a 32-bit;
- chờ `[CAPTURE_END]`;
- ghi WAV mono PCM16 16 kHz thành `capture.wav`.

Script không DSP, không chuẩn hóa và không sửa biên độ PCM. `capture.wav` là dữ liệu
đầu vào thực tế trước preprocessing.

### `Run_Capture_V1_PTQ.py`

Kiểm tra một `capture.wav` độc lập:

1. xác nhận WAV là mono PCM16, 16 kHz và đúng 80.000 mẫu;
2. import trực tiếp preprocessing chính thức của Phase 2;
3. chuẩn hóa bằng min/max Train trong conversion metadata;
4. lượng tử theo `input_scale/input_zero_point` của model;
5. chạy `QAT_INT8.tflite` của C4 V1 s44;
6. xuất `p_non_asthma`, class ba trạng thái và tensor debug.

Output nằm trong `debug_capture/`:

- `capture_mel_db.npy`;
- `capture_input_int8.npy`;
- `capture_inference_result.json`.

Capture đã là cửa sổ 5 giây tính từ onset nên script đọc `0-5 s`; không áp dụng lại
quy tắc crop playback `1-6 s` của dataset.

### `Run_Playback_Calibration.py`

Chạy phép đo chính `3 Asthma + 3 Non-Asthma x 3 trial = 18 trial`:

1. đọc manifest và sáu WAV calibration;
2. tính `p_non_original_python` của WAV gốc;
3. chờ ring buffer ESP32 sẵn sàng;
4. tự phát WAV qua loa mặc định của Windows;
5. nhận và lưu capture PCM16 từ ESP32;
6. nhận `p_non_esp32` của chính cửa sổ đó;
7. chạy capture qua Python để lấy `p_non_capture_python`;
8. tính RMS/peak và append ngay một dòng CSV.

Script có thể tiếp tục sau khi bị dừng: cặp `(file, trial)` đã có trong CSV sẽ được bỏ
qua. Không đổi tên file nguồn hoặc sửa CSV giữa một phiên calibration.

### `Analyze_Capture_Offset.py`

Phân tích ba capture của một WAV Asthma bằng cross-correlation:

- resample về 16 kHz nếu cần;
- bandpass 100-1800 Hz để alignment ổn định hơn;
- ước lượng sample đầu capture tương ứng với vị trí nào trong WAV gốc;
- xuất offset, normalized correlation coefficient (NCC), waveform và đồ thị correlation;
- đánh dấu offset ổn định nếu spread không vượt `32 ms`.

File mặc định được chọn bởi `TARGET_FILE` ở đầu script. Mỗi target phải có đủ trial
1/2/3 trong `playback_calibration_results.csv`.

### `Analyze_Shifted_Original_vs_Capture.py`

Tách hai nguyên nhân:

```text
WAV gốc crop theo đúng offset đã đo  <->  capture qua loa và INMP441
```

Với mỗi trial, script crop WAV gốc đúng 5 giây tại offset, chạy C4 QAT rồi so:

- `p_non_original_python`;
- `p_non_shifted_python`;
- `p_non_capture_python`;
- `p_non_esp32`.

Nếu shifted-original cũng tăng mạnh, alignment/window góp phần lớn. Nếu shifted-original
vẫn gần Asthma nhưng capture tăng mạnh, đường truyền loa/phòng/INMP441 chiếm ưu thế.
Script yêu cầu `Analyze_Capture_Offset.py` đã chạy cho target đó.

### `Analyze_Asthma_02_03.py`

Batch dành cho hai target Asthma 02 và 03. Script:

1. đo offset cả hai file;
2. chỉ load Python preprocessing + C4 QAT một lần;
3. chạy shifted-original vs capture cho từng file.

Không cần kết nối ESP32 vì chỉ đọc capture và CSV đã lưu.

## Quy trình chạy

Các lệnh dưới đây chạy từ thư mục dự án:

```powershell
cd ESP32_Standalone_Modules_Test/Asthma_Playback_Calibration
```

### A. Kiểm tra một capture

1. Clean/upload firmware bằng PlatformIO.
2. Đóng Serial Monitor.
3. Chạy:

```powershell
py Capture_Wav_From_Serial.py
```

4. Khi script đang chờ, phát âm thanh để vượt VAD.
5. Sau khi có `capture.wav`, chạy:

```powershell
py Run_Capture_V1_PTQ.py
```

So `p_non_asthma` trong `debug_capture/capture_inference_result.json` với dòng `[AI]`
trên ESP32 của cùng cửa sổ.

### B. Chạy đủ 18 trial

Đóng Serial Monitor, cố định setup loa/micro rồi chạy:

```powershell
py Run_Playback_Calibration.py
```

Kết quả chính:

```text
calibration_results/playback_calibration_results.csv
calibration_results/captures/<class>/*.wav
```

### C. Phân tích nguyên nhân

Target Asthma 01:

```powershell
py Analyze_Capture_Offset.py
py Analyze_Shifted_Original_vs_Capture.py
```

Target Asthma 02 và 03:

```powershell
py Analyze_Asthma_02_03.py
```

## Dữ liệu đầu ra

Mô tả schema, cấu trúc output, bảng tổng hợp định lượng và kết luận domain shift nằm tại:

- [calibration_results/README.md](calibration_results/README.md)

`capture.wav`, `debug_capture/` và dữ liệu sinh trong `calibration_results/` được ignore
để tránh commit WAV/tensor lớn. Riêng `calibration_results/README.md` được giữ trong
source control làm báo cáo kết luận.

## Lưu ý

- Firmware này cố ý dump PCM qua Serial ở 460800 baud, vì vậy không dùng làm firmware
  deployment hoặc benchmark timing cuối cùng.
- Khi hoàn tất calibration, bản triển khai phải dùng `Deploy_Model/3_Model_Complete`
  hoặc `Final_Project_NCKH/Patient_Node`, không copy ngược cơ chế dump vào bản final.
- Cross-correlation chỉ đo độ lệch thời gian, không chứng minh nguyên nhân nhân quả về
  đáp ứng tần số, méo loa, gain micro hay nhiễu phòng.
- Playback qua loa không tương đương hoàn toàn với âm hô hấp thật đi trực tiếp vào
  micro. Kết quả ở đây dùng để đánh giá robustness và domain shift, không thay thế dữ
  liệu bệnh nhân thật hay chẩn đoán y khoa.
