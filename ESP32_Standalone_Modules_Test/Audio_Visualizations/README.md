# Audio Visualizations

Thư mục này chứa các script Python tạo hình minh họa tín hiệu và DSP cho báo
cáo. Đây là công cụ trực quan hóa offline: không train model, không sửa WAV và
không thay đổi artifact của pipeline AI.

## Thành phần

| Script | Input | Output | Mục đích |
|---|---|---|---|
| `Visualize_Core_Audio_Examples.py` | Hai WAV core, một playback, một environment trong `AI_Training_Model/Dataset_Chia_V2` và pipeline `Phase2_Preprocess_&_Traning/Preprocess_Audio.py` | Ảnh biên độ gốc PCM16, waveform sau DSP và Log-Mel, mỗi ảnh gồm 4 panel | So sánh trực quan bốn nhóm trước/sau tiền xử lý bằng đúng pipeline Python đã huấn luyện model. |
| `Plot_Butterworth_Bandpass_Response.py` | `fs`, low/high cutoff và order | PNG + SVG đáp ứng tần số | Minh họa Butterworth band-pass, gain dB và hai tần số cắt 100/2000 Hz. |
| `Apply_Butterworth_To_Audio.py` | Một WAV thật và pipeline Phase 2 | Ảnh trước/sau, WAV đã lọc và metrics JSON | Thử nghiệm tác động thực tế của Butterworth lên waveform và phổ Welch. |

## 1. Waveform và Log-Mel của bốn nhóm âm thanh

Chạy từ root repository:

```powershell
py -3.11 .\ESP32_Standalone_Modules_Test\Audio_Visualizations\Visualize_Core_Audio_Examples.py
```

Bốn mẫu mặc định:

| Nhóm | WAV | Lý do chọn |
|---|---|---|
| Asthma core | `P14WheezingRS_68.wav` | Có nhiều cụm dao động rõ và phân bố gần toàn bộ cửa sổ 5 giây (khoảng 11 đỉnh năng lượng), dễ quan sát hơn trên waveform. |
| Non-Asthma core | `P16COPDPr_127.wav` | Năng lượng đủ rõ nhưng ổn định hơn theo thời gian; không phải silence, environment, playback hoặc augmentation. |
| Asthma playback | `AST_004__P14WheezingRS_68__take01.wav` | Là bản thu lại qua loa - micro của đúng mẫu Asthma core phía trên, phù hợp quan sát domain shift. |
| Environment | `ENV__room_noise__room_noise_session_06__clip01.wav` | Đại diện nhiễu phòng thuộc lớp Non-Asthma. |

Kết quả mặc định:

```text
Core_Audio_Visualization/
├── 00_Four_Groups_Original_Waveform_PCM16.png
├── 00B_Four_Groups_Normalized_Waveform_Before_DSP.png
├── 01_Four_Groups_Waveform_C4.png
└── 02_Four_Groups_LogMel_C4.png
```

Ảnh `00` giữ biên độ PCM16 tương đương trước peak-normalize và Butterworth để đối
chiếu mức tín hiệu thật giữa bốn nguồn. Ảnh `00B` peak-normalize độc lập từng file
về `[-1, 1]` nhưng chưa Butterworth/Log-Mel; đây là dạng waveform chuẩn hóa rõ nét
dùng để minh họa hình dạng tín hiệu. Ảnh `01` dùng cửa sổ 5 giây sau resample 16
kHz, fix-length, chuẩn hóa đỉnh và Butterworth; các panel dùng chung giới hạn trục
Y. Ảnh Log-Mel dùng đầy
đủ pipeline C4 đã khóa:

```text
16 kHz / 5 s
→ peak normalize
→ Butterworth band-pass 100–2000 Hz, order 5
→ không pre-emphasis (coefficient = 0)
→ Hann + FFT 2048 + hop 625
→ 40 Mel bins, Slaney → tensor 40 × 129
→ power-to-dB [-80, 0]
```

Chọn WAV core khác:

```powershell
py -3.11 .\ESP32_Standalone_Modules_Test\Audio_Visualizations\Visualize_Core_Audio_Examples.py `
  --asthma "AI_Training_Model/Dataset_Chia_V2/Asthma/train/TEN_FILE.wav" `
  --non-asthma "AI_Training_Model/Dataset_Chia_V2/Non_Asthma_Disease/train/TEN_FILE.wav" `
  --playback "AI_Training_Model/Dataset_Chia_V2/Asthma/train/TEN_PLAYBACK.wav" `
  --environment "AI_Training_Model/Dataset_Chia_V2/Non_Asthma_Disease/test/TEN_ENV.wav"
```

Hai đối số core từ chối file có dấu hiệu playback (`__take01`, `__take02`), environment
(`ENV__`) hoặc năm kiểu augmentation của Phase 1. Hai đối số `--playback` và
`--environment` nhận WAV tương ứng để phục vụ đối chiếu.

Hai WAV mặc định được chọn để **minh họa trực quan**, không phải bằng chứng rằng
mọi Asthma và Non-Asthma có thể tách chỉ bằng biên độ waveform. Khi diễn giải,
ưu tiên đối chiếu Log-Mel sau cùng pipeline và kết quả đánh giá trên toàn bộ tập
Validation/Test.

## 2. Đáp ứng Butterworth band-pass

Chạy cấu hình chính thức của pipeline:

```powershell
py -3.11 .\ESP32_Standalone_Modules_Test\Audio_Visualizations\Plot_Butterworth_Bandpass_Response.py
```

Biểu đồ có:

- trục ngang: `Frequency (Hz)`;
- trục tần số dùng thang logarithmic từ 10 Hz để vùng cutoff thấp 100 Hz không
  bị dồn sát mép trái;
- trục dọc: `Magnitude / Gain (dB)`;
- hai vạch dọc tại `100 Hz` và `2000 Hz`;
- vùng passband được tô màu;
- chú thích `Butterworth band-pass`, `order = 5`, `fs = 16 kHz` và đường `-3 dB`.

Kết quả:

```text
Butterworth_Filter_Visualization/
├── Butterworth_Bandpass_100_2000Hz_Order5.png
└── Butterworth_Bandpass_100_2000Hz_Order5.svg
```

Có thể khảo sát cấu hình khác mà không sửa source:

```powershell
py -3.11 .\ESP32_Standalone_Modules_Test\Audio_Visualizations\Plot_Butterworth_Bandpass_Response.py `
  --fs 16000 --low 100 --high 2000 --order 5
```

`Plot_Butterworth_Bandpass_Response.py` tính đáp ứng trực tiếp từ hệ số số của
bộ lọc; nó không đọc một WAV cụ thể. Để xem tác động trên dữ liệu thật, dùng
script ở mục tiếp theo.

## 3. Áp dụng Butterworth lên WAV thật

Chạy với mẫu Asthma core mặc định `P14WheezingRS_68.wav`:

```powershell
py -3.11 .\ESP32_Standalone_Modules_Test\Audio_Visualizations\Apply_Butterworth_To_Audio.py
```

Kết quả được lưu trong `Butterworth_Audio_Experiment/`:

```text
P14WheezingRS_68_Butterworth_Before_After.png
P14WheezingRS_68_Butterworth_100_2000Hz_Order5.wav
P14WheezingRS_68_Butterworth_Metrics.json
```

Ảnh gồm waveform trước lọc, waveform sau lọc và phổ Welch trước/sau. JSON lưu
RMS cùng tỷ lệ năng lượng nằm trong passband để có số liệu ngoài hình ảnh.

Thử WAV khác:

```powershell
py -3.11 .\ESP32_Standalone_Modules_Test\Audio_Visualizations\Apply_Butterworth_To_Audio.py `
  --input "AI_Training_Model/Dataset_Chia_V2/Non_Asthma_Disease/train/P16COPDPr_127.wav"
```

## Phụ thuộc

```text
numpy
scipy
matplotlib
librosa
```

Lần đầu gọi pipeline Librosa có thể mất thêm thời gian để khởi tạo cache/JIT.
