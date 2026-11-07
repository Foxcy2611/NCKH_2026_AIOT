# ESP32-S3 + INMP441 - Thu và kiểm tra Dataset V2

## 1. Mục đích project

Project này dùng ESP32-S3 và microphone INMP441 để:

1. thu các phiên âm thanh môi trường mới;
2. kiểm tra biên độ và chất lượng WAV sau khi thu;
3. phát lại các file bệnh lý qua loa rồi thu lại bằng INMP441;
4. tạo dữ liệu đúng miền phần cứng của Patient Node;
5. giữ metadata để tránh rò rỉ dữ liệu giữa Train, Validation và Test.

Đường thu được đồng nhất với Patient Node:

```text
INMP441
   ↓ I2S 32-bit / 16 kHz
ESP32-S3 dịch phải 16 bit
   ↓ gain = 1
PCM16 mono / 16 kHz
   ↓ Serial 460800 baud
Python lưu WAV
```

Project không thực hiện tiền xử lý Mel-Spectrogram và không chạy mô hình AI. WAV được giữ ở dạng thô để sử dụng cho các bước xây dựng Dataset V2 sau đó.

---

## 2. Cấu trúc chính

```text
ESP32_Read_INMP441/
├── platformio.ini
├── src/
│   └── main.cpp
├── Record_Audio.py
├── Test_Audio.py
├── Record_Playback.py
├── Playback_Source_List.csv
└── README.md
```

| File | Tác dụng |
|---|---|
| `src/main.cpp` | Đọc INMP441 và truyền PCM16 qua Serial |
| `platformio.ini` | Cấu hình ESP32-S3, COM và tốc độ Serial |
| `Record_Audio.py` | Thu một phiên âm thanh môi trường |
| `Test_Audio.py` | Đo Peak, RMS, clipping và vẽ waveform |
| `Record_Playback.py` | Phát WAV bệnh lý và thu lại qua INMP441 |
| `Playback_Source_List.csv` | Danh sách cố định 80 nguồn playback hợp lệ |

---

## 3. Kết nối INMP441

| INMP441 | ESP32-S3 | Ý nghĩa |
|---|---:|---|
| VDD | 3.3 V | Nguồn microphone |
| GND | GND | Mass chung |
| SCK/BCLK | GPIO 14 | Clock dữ liệu I2S |
| WS/LRCL | GPIO 15 | Clock chọn kênh |
| SD | GPIO 16 | Dữ liệu microphone |
| L/R | 3.3 V | Chọn kênh phải |

Firmware đang dùng:

```cpp
I2S_CHANNEL_FMT_ONLY_RIGHT
```

Vì vậy chân `L/R` của INMP441 phải được nối mức cao, thường là `3.3 V`. Nếu chân này nối GND nhưng firmware vẫn đọc kênh phải, dữ liệu có thể gần như im lặng.

Không cấp nguồn 5 V trực tiếp cho INMP441.

---

## 4. Chuẩn dữ liệu đầu ra

Mọi WAV do ESP32-S3 thu có định dạng:

```text
Sample rate : 16000 Hz
Số kênh     : 1 kênh — mono
Độ sâu      : PCM signed 16-bit
Gain        : 1
Nén         : Không nén
```

Firmware nhận hai lệnh qua Serial:

| Lệnh | Tác dụng |
|---|---|
| `R` | Bắt đầu truyền PCM16 |
| `S` | Dừng truyền PCM16 |

Python là phía gửi hai lệnh này. Không mở Serial Monitor trong lúc chạy script thu vì một cổng COM không thể bị hai chương trình sử dụng đồng thời.

---

## 5. Chuẩn bị phần mềm

### 5.1. Công cụ

- Visual Studio Code và PlatformIO;
- Python 3;
- Windows, vì `Record_Playback.py` dùng `winsound` để phát WAV;
- cáp USB có truyền dữ liệu.

### 5.2. Cài thư viện Python

Chạy một lần:

```powershell
python -m pip install pyserial numpy matplotlib
```

`winsound` có sẵn trong Python trên Windows, không cần cài riêng.

### 5.3. Kiểm tra cổng COM

Trong `platformio.ini`:

```ini
upload_port = COM11
monitor_speed = 460800
```

Trong các script thu:

```python
SERIAL_PORT = "COM11"
```

Nếu Windows đổi số COM, phải sửa cả vị trí tương ứng trước khi chạy.

---

## 6. Nạp firmware vào ESP32-S3

Mở terminal tại thư mục project rồi chạy:

```powershell
pio run -t clean
pio run -t upload
```

Hoặc dùng nút `Clean` và `Upload` của PlatformIO.

Project ép:

```ini
ARDUINO_USB_CDC_ON_BOOT=0
```

để đường `Serial` đồng nhất với Patient Node Final. Sau khi upload, đóng Serial Monitor trước khi chạy Python.

---

## 7. Thu dữ liệu môi trường — `Record_Audio.py`

### 7.1. Tác dụng

Script dùng để thu một session môi trường độc lập, ví dụ:

- podcast;
- người nói;
- quạt;
- quạt và bàn phím;
- vỗ tay;
- gõ bàn;
- tiếng nền phòng.

Mỗi lần chạy tạo một `session_id` mới. Script không ghi đè WAV cũ và không mở biểu đồ sau khi thu.

Ngoài chế độ Environment nói trên, script có chế độ **custom VAD** để thu một hoặc hai master dài 5 phút với tên do người dùng đặt. File custom được giữ riêng và không tự ghi vào `Env_session.csv`; chỉ đăng ký vào metadata chính thức sau khi đã nghe và kiểm tra chất lượng.

### 7.2. Cấu hình

Sửa các biến đầu file:

```python
CAPTURE_MODE = "VAD_RESEARCH"  # hoặc "DATASET_ENV"

VAD_FILE_NAME = "vad_silence_session_01.wav"
VAD_RECORD_SECONDS = 300.0

ENV_NAME = "podcast"
DATASET_RECORD_SECONDS = 60.0
SERIAL_PORT = "COM11"
```

`VAD_RESEARCH` dùng `VAD_FILE_NAME`, thu 5 phút và lưu riêng mà không sửa CSV. `DATASET_ENV` dùng `ENV_NAME`, tự sinh session ID và cập nhật `Env_session.csv`.

`ENV_NAME` nhận một trong các giá trị:

```text
podcast
speech
fan
keyboard
fan_keyboard
clap
knock
room_noise
```

### 7.3. Chạy

Sau khi sửa các biến đầu file, chỉ cần mở đúng `Record_Audio.py` trong VS Code và nhấn `Ctrl+Alt+N`, hoặc chạy:

```powershell
python Record_Audio.py
```

Thu hai session nghiên cứu VAD, mỗi session 5 phút và tự đặt tên:

```powershell
python Record_Audio.py --mode VAD_RESEARCH --name vad_silence_session_01 --seconds 300 --port COM11
python Record_Audio.py --mode VAD_RESEARCH --name vad_silence_session_02 --seconds 300 --port COM11
```

Hai file trên mặc định được lưu tại:

```text
Experiments_Benchmarking/Patient_Node/Final_V1_Validation/
└── 03_VAD_Trigger/
    └── extra_validation/
```

Có thể chọn thư mục khác:

```powershell
python Record_Audio.py --mode VAD_RESEARCH --name vad_room_session_01 --seconds 300 --output-dir "D:\DuLieu\VAD"
```

Tên custom chỉ nhận chữ không dấu, số, `_` và `-`; phần mở rộng `.wav` có thể bỏ qua. Script luôn từ chối ghi đè file đã tồn tại.

Ví dụ với `ENV_NAME = "podcast"`, script tự sinh:

```text
podcast_session_02.wav
podcast_session_03.wav
...
```

### 7.4. Output

WAV được lưu tại:

```text
DATASET_ENV
└── AI_Training_Model/Dataset_TuThu_v_Kaggle/TuThu/Record_Env/
    └── <Nhóm>/<environment>_session_NN.wav

VAD_RESEARCH
└── Experiments_Benchmarking/Patient_Node/Final_V1_Validation/
    └── 03_VAD_Trigger/extra_validation/<ten_vad>.wav
```

Metadata được thêm vào:

```text
TuThu/TKe/Env_session.csv
```

`split` ban đầu là `unassigned`. Không chia Train/Validation/Test ngay trong lúc thu.

---

## 8. Phân tích WAV — `Test_Audio.py`

### 8.1. Tác dụng

Script đọc một WAV mà không tự resample hoặc tăng âm lượng rồi tính:

- Peak;
- RMS;
- MAV;
- DC offset;
- Peak dBFS và RMS dBFS;
- tỷ lệ clipping;
- tỷ lệ block có hoạt động;
- kết quả mô phỏng Quality Check hiện tại.

Script cũng lưu waveform và biểu đồ MAV theo thời gian.

### 8.2. Chọn WAV

`Test_Audio.py` dựng đường dẫn bằng `os.path` từ vị trí workspace, vì vậy
không cần ghi cứng đường dẫn kiểu `D:\\...` và vẫn chạy được bằng
`Ctrl+Alt+N`.

Kiểm tra WAV nghiên cứu VAD đã chuyển vào `03_VAD_Trigger`:

```python
AUDIO_SOURCE = "VAD"
VAD_WAV_RELATIVE = "vad_silence_session_01.wav"
```

Kiểm tra dữ liệu tự thu trong `Dataset_TuThu_v_Kaggle/TuThu`:

```python
AUDIO_SOURCE = "TUTHU"
TUTHU_WAV_RELATIVE = os.path.join(
    "Record_Env",
    "Silence",
    "silence_5min.wav",
)
```

Kiểm tra WAV Kaggle gốc nằm trong các thư mục lớp tại
`Dataset_TuThu_v_Kaggle`:

```python
AUDIO_SOURCE = "KAGGLE"
KAGGLE_GROUP = "asthma"
KAGGLE_WAV_RELATIVE = "P10AsthmaIE_49.wav"
```

`KAGGLE_GROUP` nhận một trong các giá trị:

```text
asthma, bronchial, copd, healthy, pneumonia
```

Tên thư mục thật được script ánh xạ tự động, bao gồm trường hợp `bronchial`
tương ứng với thư mục `Bronchial`.

Script vẫn hỗ trợ truyền đường dẫn tương đối ngay trên command line mà không
sửa source:

```powershell
python Test_Audio.py "vad_silence_session_01.wav"
python Test_Audio.py "extra_validation/vad_silence_session_01.wav"
python Test_Audio.py "TuThu/Record_Env/Silence/silence_5min.wav"
python Test_Audio.py "TuThu/Playback_Raw/Asthma/<ten_file>.wav"
```

Nếu chỉ truyền tên file và có nhiều file trùng tên trong dataset hoặc thư mục
VAD, script sẽ liệt kê các kết quả và yêu cầu nhập đường dẫn tương đối cụ thể.

Nếu WAV nằm ngoài dataset, truyền đường dẫn tuyệt đối trên command line:

```powershell
python Test_Audio.py "D:\DuLieu\audio_test.wav"
```

Chọn cách hiển thị:

```python
SHOW_PLOT = True   # Lưu ảnh và mở đồ thị
SHOW_PLOT = False  # Chỉ lưu ảnh, không mở cửa sổ
```

### 8.3. Chạy

Sửa `AUDIO_SOURCE` (`VAD`, `TUTHU` hoặc `KAGGLE`), cấu hình đường dẫn tương
ứng và `SHOW_PLOT` ở đầu file;
sau đó mở `Test_Audio.py` và nhấn `Ctrl+Alt+N`, hoặc chạy:

```powershell
python Test_Audio.py
```

### 8.4. Output

```text
ESP32_Standalone_Modules_Test/ESP32_Read_INMP441/Test_Audio_Output/
├── <ten_file>_metrics.csv
└── <ten_file>_waveform.png
```

### 8.5. Ngưỡng Quality Check đang mô phỏng

```python
MIN_RMS = 20.0
MIN_ACTIVE_RATIO = 0.01
MAX_CLIPPED_RATIO = 0.01
CLIP_LEVEL = 32000
ACTIVE_BLOCK_THRESHOLD = 20
```

Các ngưỡng này phản ánh code Patient Node hiện tại, chưa phải ngưỡng Final của Model V2. Không xóa vĩnh viễn WAV chỉ vì script trả về `AUDIO_INACTIVE`, `AUDIO_TOO_WEAK` hoặc `AUDIO_TOO_LOUD`.

Khoảng `30–90 giây` chỉ là khuyến nghị cho một environment session. Playback take có thể ngắn hơn và không bị coi là lỗi chỉ vì nằm ngoài khoảng này.

---

## 9. Thu playback bệnh lý — `Record_Playback.py`

### 9.1. Mục đích

Luồng playback:

```text
WAV Kaggle gốc
        ↓
Loa mặc định của Windows
        ↓
INMP441 thu lại
        ↓
ESP32-S3 xuất PCM16 / 16 kHz
        ↓
WAV thuộc miền phần cứng thực tế
```

Danh sách hiện tại gồm:

| Nhóm | Số source | Take/source | Tổng take |
|---|---:|---:|---:|
| Asthma | 40 | 2 | 80 |
| Bronchial | 10 | 2 | 20 |
| COPD | 10 | 2 | 20 |
| Healthy | 10 | 2 | 20 |
| Pneumonia | 10 | 2 | 20 |
| **Tổng** | **80** |  | **160** |

### 9.2. Danh sách nguồn

`Playback_Source_List.csv` là danh sách cố định, không chọn ngẫu nhiên lại mỗi lần chạy.

Tiêu chí nguồn playback hiện tại:

```text
Mono PCM16
Thời lượng ≥ 4,5 giây
Peak ≥ 5000
RMS ≥ 1000
Clipping ≤ 0,5%
```

CSV lưu:

- `source_id`;
- nhãn và bệnh cụ thể;
- `group_id` bệnh nhân;
- split kế thừa từ V1;
- đường dẫn source;
- sample rate và thời lượng;
- Peak, RMS, RMS dBFS, clipping;
- SHA-256;
- tên hai output dự kiến.

Hai take của cùng source luôn có cùng split. Không tự đổi split hoặc rải hai take sang hai tập khác nhau.

### 9.3. Cấu hình trước khi chạy

```python
SERIAL_PORT = "COM11"

CAPTURE_GROUP = "Asthma"

LEAD_IN_SECONDS = 0.6
TAIL_OUT_SECONDS = 0.6
MIN_CAPTURE_SECONDS = 5.0

CONTINUOUS_MODE = False
DELAY_BETWEEN_TAKES_SECONDS = 0.0

PLAYBACK_VOLUME_PERCENT = 60
SPEAKER_DISTANCE_CM = 6.0
PLAYBACK_DEVICE_NOTE = "Loa mặc định của Windows"
```

`CAPTURE_GROUP` nhận:

```text
Asthma
Bronchial
COPD
Healthy
Pneumonia
ALL
```

`PLAYBACK_VOLUME_PERCENT`, `SPEAKER_DISTANCE_CM` và `PLAYBACK_DEVICE_NOTE` chỉ là metadata. Script không tự thay đổi âm lượng Windows và không tự đo khoảng cách.

Có hai chế độ:

```python
CONTINUOUS_MODE = False
```

Script hỏi trước khi thu và cho nghe lại từng take trước khi chấp nhận.

Khi loa và micro đã được đặt cố định, có thể chạy tự động toàn bộ hàng đợi:

```python
CONTINUOUS_MODE = True
DELAY_BETWEEN_TAKES_SECONDS = 0.0
```

Ở chế độ liên tục:

- COM chỉ được mở và ổn định một lần;
- script tự phát, thu và chuyển sang take kế tiếp;
- không cần nhấn Enter giữa các file;
- output được kiểm tra nhanh RMS và clipping;
- nếu audio quá yếu, clipping hoặc Serial lỗi thì hàng đợi dừng ngay;
- take không đạt chỉ được giữ dưới tên `__pending.wav`, không ghi vào log chính thức.

Nếu muốn có một khoảng nghỉ tự động ngắn giữa các take:

```python
DELAY_BETWEEN_TAKES_SECONDS = 1.0
```

### 9.4. Chuẩn bị loa

1. Chọn đúng loa cần dùng làm thiết bị phát mặc định của Windows.
2. Đặt loa và INMP441 đúng khoảng cách khai báo.
3. Đặt âm lượng Windows đúng mức khai báo.
4. Không thay đổi âm lượng và khoảng cách giữa các source nếu không có chủ đích.
5. Tắt hiệu ứng tự cân bằng âm lượng, tăng bass hoặc xử lý âm thanh nếu có thể.
6. Thu thử vài source rồi kiểm tra output trước khi thu hàng loạt.

### 9.5. Chạy

```powershell
python Record_Playback.py
```

Script tự tìm take còn thiếu và chạy theo thứ tự CSV:

```text
AST_001 take01
AST_001 take02
AST_002 take01
AST_002 take02
...
```

Các take đã có output chính thức sẽ được bỏ qua. Có thể dừng rồi chạy tiếp mà không phải thu lại từ đầu.

### 9.6. Phím trước khi thu — chế độ thủ công

```text
Enter = bắt đầu phát source và thu bằng INMP441
P     = nghe thử source
S     = bỏ qua take hiện tại
Q     = dừng an toàn
```

### 9.7. Phím sau khi thu — chế độ thủ công

Take mới chỉ được lưu dưới tên tạm `__pending.wav` cho đến khi được chấp nhận.

```text
Enter = chấp nhận take
P     = nghe lại take vừa thu
R     = xóa take tạm và thu lại ngay
S     = bỏ take; lần chạy sau vẫn xem đây là take còn thiếu
Q     = xóa take tạm và dừng
```

Chỉ take được chấp nhận mới trở thành output chính thức và được ghi vào log.

### 9.8. Output

Playback raw chưa được tách thành thư mục Train/Validation/Test:

```text
TuThu/Playback_Raw/
├── Asthma/
└── Non_Asthma/
```

Thông tin bệnh cụ thể và split vẫn nằm trong:

```text
Playback_Source_List.csv
TuThu/TKe/Playback_capture_log.csv
```

Sau khi thu và kiểm tra chất lượng xong mới dùng metadata để chia dữ liệu.

### 9.9. Quy tắc tên file

Ví dụ:

```text
AST_001__P10AsthmaIU_50__take01.wav
AST_001__P10AsthmaIU_50__take02.wav
```

Không tự đổi tên output vì tên đang liên kết:

```text
source_id + source gốc + take_id
```

Nếu đã chấp nhận nhưng sau đó phát hiện một output lỗi:

1. xóa hoặc chuyển riêng đúng output lỗi;
2. chạy lại script với đúng `CAPTURE_GROUP`;
3. script nhận ra take bị thiếu và thu lại;
4. dòng log cũ cùng `source_id + take_id` được thay bằng lần thu mới.

### 9.10. Sample rate nguồn khác nhau có sao không?

Source Kaggle có thể là `4000 Hz` hoặc `44100 Hz`. Đây là sample rate của file được Windows phát qua loa.

INMP441 luôn thu lại trường âm thực tế ở:

```text
16000 Hz / mono / PCM16
```

Vì vậy output playback được đồng nhất với đầu vào Patient Node. Script không lấy mảng source rồi reshape trực tiếp thành 16 kHz.

---

## 10. Quy trình thu được khuyến nghị

### 10.1. Với environment

```text
Nạp firmware
→ chọn CAPTURE_MODE và chỉnh nhóm biến tương ứng
→ chạy Record_Audio.py
→ chạy Test_Audio.py
→ kiểm tra waveform và metrics
→ cập nhật điều kiện session nếu cần
```

### 10.2. Với playback

```text
Nạp firmware
→ đặt loa, volume và khoảng cách
→ chọn CAPTURE_GROUP
→ chạy Record_Playback.py
→ thu thử 2–3 source
→ nghe lại từng take
→ chạy Test_Audio.py trên output
→ nếu ổn mới thu hàng loạt
→ giữ nguyên điều kiện thu
→ kiểm tra đủ 160 take
→ chia dataset dựa trên metadata
```

Không nên thu toàn bộ 160 take ngay khi chưa kiểm tra một nhóm thử nghiệm nhỏ.

---

## 11. Xử lý lỗi thường gặp

### 11.1. `Không nhận được PCM trong 2 giây`

Kiểm tra lần lượt:

1. Serial Monitor đã đóng chưa;
2. `SERIAL_PORT` có đúng COM hiện tại không;
3. firmware mới đã được upload chưa;
4. `platformio.ini` còn `ARDUINO_USB_CDC_ON_BOOT=0` không;
5. cáp USB có truyền dữ liệu không;
6. có chương trình khác đang giữ COM không.

### 11.2. WAV gần như im lặng

Kiểm tra:

- VDD và GND;
- SCK = GPIO14;
- WS = GPIO15;
- SD = GPIO16;
- chân L/R đang chọn kênh phải;
- loa có thật sự phát ra thiết bị mặc định không;
- khoảng cách và âm lượng có đúng metadata không.

### 11.3. WAV clipping hoặc quá lớn

- giảm âm lượng loa;
- tăng khoảng cách;
- tránh dí loa sát microphone;
- chạy `Test_Audio.py` và xem `Clipped ratio`.

Không peak-normalize file output chỉ để làm kết quả đẹp hơn. Cần sửa điều kiện thu và thu lại.

### 11.4. Playback không phát ra loa mong muốn

`Record_Playback.py` dùng thiết bị âm thanh mặc định của Windows. Chọn lại Output Device trong Windows trước khi chạy.

### 11.5. Script bỏ qua một take

Nếu output chính thức đã tồn tại, script coi take đó đã hoàn thành.

Muốn thu lại:

```text
xóa/chuyển riêng file output lỗi
→ chạy lại script
→ take xuất hiện lại trong hàng đợi
```

---

## 12. Nguyên tắc bảo toàn dataset

1. Không sửa WAV Kaggle gốc.
2. Không đổi tên source hoặc output tùy ý.
3. Không để hai take của cùng source thuộc hai split khác nhau.
4. Không chia playback bằng cách random từng take độc lập.
5. Giữ `Playback_Source_List.csv` và `Playback_capture_log.csv` cùng dataset.
6. Không dùng Quality Check chưa Final để xóa vĩnh viễn dữ liệu.
7. Ghi đúng âm lượng, khoảng cách và thiết bị phát.
8. Thu thử và kiểm tra trước khi thu toàn bộ dataset.

Các quy tắc này giúp dữ liệu V2 có thể truy vết, tái lập và tránh đánh giá mô hình quá lạc quan do rò rỉ dữ liệu.
