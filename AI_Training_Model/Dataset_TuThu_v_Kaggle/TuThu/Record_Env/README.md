# Hướng dẫn thu dữ liệu Environment — Dataset V2

Tài liệu này mô tả cách thu **environment / hard-negative samples** cho Dataset V2 của Patient Node. Mục tiêu là tăng độ đa dạng âm học để giảm False Positive của mô hình **Asthma vs Non-Asthma**.

> Environment là dữ liệu **Non-Asthma / hard-negative**, không phải bài toán phân loại riêng từng loại môi trường. Các nhãn `fan`, `clap`, `knock`, `speech`... chủ yếu dùng để quản lý dữ liệu và phân tích lỗi.

## Tóm tắt cách chia session

Toàn bộ **33 session chính được chia theo `session_id` trước khi cắt clip**.
Mỗi session chỉ thuộc một split; sau đó mỗi session mới được cắt thành 10 clip,
mỗi clip dài 5 giây. Cách làm này ngăn các đoạn âm thanh từ cùng một lần thu
xuất hiện đồng thời ở Train và Validation/Test.

| Nhóm Environment | Tổng session | Train | Validation | Test |
|---|---:|---:|---:|---:|
| Podcast | 6 | 5 | 1 | 0 |
| Fan | 5 | 4 | 1 | 0 |
| Clap | 6 | 5 | 1 | 0 |
| Knock | 5 | 4 | 0 | 1 |
| Room noise | 6 | 5 | 0 | 1 |
| Speech | 5 | 4 | 0 | 1 |
| **Tổng** | **33** | **27** | **3** | **3** |

- Validation gồm một session của `Podcast`, `Fan` và `Clap`.
- Test gồm một session của `Knock`, `Room noise` và `Speech`.
- Các session còn lại thuộc Train; phép chọn được cố định bằng seed `42` và
  được truy vết trong `Phase1_Split_Data/Output/03_Cut_Environment/environment_session_split.csv`.
- `key_fan_5min.wav` và `silence_5min.wav` không nằm trong bộ 33 session trên.

---
 
## 1. Nguyên tắc chung

Trong toàn bộ quá trình thu:

- Giữ nguyên ESP32-S3 + INMP441.
- Giữ nguyên sample rate, gain, firmware thu, định dạng WAV và cách lưu PCM.
- Không normalize biên độ trước khi lưu.
- Không thay đổi gain chỉ để session “đẹp” hơn.
- Mỗi lần thu độc lập là một `session_id`.
- Mỗi session nên khoảng **30–90 s**, khuyến nghị **45–60 s**.
- Lưu WAV master trước, chưa cắt 5 s ngay.
- Lưu metadata như RMS, Peak, Active Ratio, Clipping Ratio, điều kiện thu.
- Không xóa raw chỉ vì Quality Check hiện tại báo FAIL.

Quy trình chuẩn:

```text
Thu raw session dài
        ↓
Lưu WAV master + metadata
        ↓
Thu xong toàn bộ Environment
        ↓
Chia Train / Val / Test theo session_id
        ↓
Sau đó mới cắt thành clip 5 s
```

Không được để các clip 5 s sinh ra từ cùng một session nằm ở nhiều split khác nhau.

---

## 2. Cấu trúc Environment đề xuất

```text
Environment/
├── podcast/
├── fan/
├── clap/
├── knock/
├── speech/
├── room_noise/
├── mixed/
└── silence/
```

`silence/` chủ yếu dùng cho Quality Check / AUDIO_INACTIVE / augmentation, không coi là Non-Asthma classifier sample chính.

## 2.1. Các WAV master 5 phút kế thừa từ V1

Bên cạnh các session mới dài khoảng 30–90 giây, repository hiện giữ lại ba
WAV master cũ, mỗi file dài khoảng 5 phút và đều là PCM16 mono 16 kHz:

| File | Vị trí trong `Record_Env/` | `session_id` | Nhóm quản lý | Vai trò |
|---|---|---|---|---|
| `podcast_5min.wav` | `Podcast/` | `podcast_old_01` | `podcast` | Một session Podcast độc lập, được tính trong bộ 33 Environment chính. |
| `key_fan_5min.wav` | `Mixed/` | `keyfan_old_01` | `fan_keyboard` | Session mixed cũ, giữ ở Train và không thuộc bộ 33 session chính. |
| `silence_5min.wav` | `Silence/` | `silence_old_01` | `silence` | Tài sản cho Quality Check, VAD và augmentation; không phải mẫu Non-Asthma classifier chính. |

Metadata chuẩn của ba file nằm tại:

```text
AI_Training_Model/Dataset_TuThu_v_Kaggle/TuThu/TKe/Env_session.csv
```

Quy tắc sử dụng:

1. Mỗi WAV 5 phút vẫn chỉ được coi là **một session**, không phải nhiều session
   chỉ vì có thể cắt ra nhiều clip.
2. Mọi clip sinh từ cùng một master phải nằm trong cùng một split.
3. Không để một master 5 phút sinh quá nhiều clip làm áp đảo các session mới.
4. Với pipeline Dataset V2 hiện tại, mỗi Environment session chỉ lấy 10 clip
   dài 5 giây; tài sản cũ dùng cho augmentation phải tuân theo giới hạn riêng
   của bước tăng cường dữ liệu.
5. Không đưa `silence_5min.wav` vào đánh giá Asthma/Non-Asthma như một bệnh lý
   Non-Asthma. File này có vai trò chính trong Quality Gate và kiểm tra
   `AUDIO_INACTIVE`.

> `podcast_5min.wav` là session Podcast thứ sáu khi ghép với năm session mới.
> `key_fan_5min.wav` và `silence_5min.wav` không làm tăng tổng 33 session
> Environment chính.

## 2.2. Danh sách session hiện có trong repository

Bảng dưới đây là inventory thực tế, được đối chiếu giữa `Record_Env/` và
`TKe/Env_session.csv`. Đây là danh sách ID cần dùng trong script và báo cáo:

| Nhóm | Session ID hiện có | Số session thuộc bộ chính |
|---|---|---:|
| Podcast | `podcast_old_01`, `podcast_session_02`, `podcast_session_03`, `podcast_session_04`, `podcast_session_05`, `podcast_session_06` | 6 |
| Fan | `fan_session_01`, `fan_session_02`, `fan_session_03`, `fan_session_04`, `fan_session_06` | 5 |
| Clap | `clap_session_01`, `clap_session_02`, `clap_session_03`, `clap_session_04`, `clap_session_05`, `clap_session_06` | 6 |
| Knock | `knock_session_01`, `knock_session_02`, `knock_session_03`, `knock_session_04`, `knock_session_05` | 5 |
| Room noise | `room_noise_session_01`, `room_noise_session_02`, `room_noise_session_03`, `room_noise_session_04`, `room_noise_session_05`, `room_noise_session_06` | 6 |
| Speech | `speech_session_01`, `speech_session_02`, `speech_session_03`, `speech_session_04`, `speech_session_05` | 5 |
| Mixed legacy | `keyfan_old_01` | ngoài bộ 33 |
| Silence legacy | `silence_old_01` | ngoài bộ 33 |
| **Tổng Environment chính** | Podcast + Fan + Clap + Knock + Room noise + Speech | **33** |

Một số dãy ID không liên tục vì giữ nguyên tên của lần thu thực tế. Không đổi
tên chỉ để lấp số còn thiếu vì việc đó có thể làm sai liên kết giữa WAV,
metadata, manifest và các báo cáo đã sinh.

---

# 3. Podcast

## Mục tiêu

Mô phỏng các nguồn tiếng nói qua loa như:

- podcast,
- video,
- TV,
- điện thoại,
- nội dung truyền thông trong phòng.

Podcast khác speech trực tiếp vì tín hiệu đã đi qua loa.

## Các session hiện có

Hiện có năm session mới mang ID `02–06`; không có
`podcast_session_01.wav`. Master cũ được quản lý bằng ID riêng
`podcast_old_01`:

```text
podcast_old_01       → podcast_5min.wav, master cũ 5 phút
podcast_session_02
podcast_session_03
podcast_session_04
podcast_session_05
podcast_session_06
```

Có thể thay đổi:

- nội dung phát,
- khoảng cách loa ↔ mic,
- hướng loa,
- vị trí mic,
- mức âm lượng thực tế nếu hợp lý.

Không cần chủ động normalize volume.

Metadata gợi ý:

```text
source_type = podcast
speaker_distance = near / medium / far
speaker_angle = front / side / off_axis
content_note = ...
```

---

# 4. Fan

## Mục tiêu

Fan là nguồn âm liên tục, thường chứa:

- tiếng motor,
- airflow,
- rung cơ học,
- noise nền liên tục.

## Kịch bản 5 session

```text
fan_session_01 → tốc độ thấp, khoảng cách trung bình
fan_session_02 → tốc độ trung bình
fan_session_03 → tốc độ cao
fan_session_04 → xa hơn
fan_session_06 → gần hơn hoặc lệch góc
``` 

Không cần RMS tăng/giảm tuyến tính theo khoảng cách vì còn phụ thuộc góc gió, phản xạ phòng và rung bề mặt.

### Lưu ý

- Tránh đặt INMP441 trực tiếp vào luồng gió mạnh nếu đó không phải điều kiện dùng thực tế.
- `Active Ratio ≈ 100%` là bình thường với fan.

---

# 5. Clap

## Mục tiêu

Clap là hard-negative dạng **transient**, có peak nhanh và có thể gây nhầm với các event âm thanh ngắn.

## Kịch bản

```text
clap_session_01 → nhẹ
clap_session_02 → vừa
clap_session_03 → mạnh hơn
clap_session_04 → đổi khoảng cách / góc
clap_session_05 → xa hơn, lệch góc hoặc nhịp thưa hơn
clap_session_06 → thay đổi nhịp clap hoặc điều kiện phòng
```

Trong session nên có:

```text
nền yên
→ clap
→ nghỉ vài giây
→ clap
→ đôi lúc 2 clap gần nhau
```

Không nên vỗ liên tục suốt session.

Khi cắt 5 s sau này nên có:

- clip 1 clap,
- clip 2 clap,
- burst ngắn,
- clap yếu,
- clap mạnh.

---

# 6. Knock / Impact / Vibration

## Mục tiêu

Thu các dạng:

- gõ bàn,
- gõ bề mặt,
- va đập,
- rung truyền qua bề mặt,
- structure-borne vibration.

## Kịch bản

```text
knock_session_01 → gõ nhẹ
knock_session_02 → gõ vừa
knock_session_03 → gõ mạnh
knock_session_04 → tác động mạnh làm bề mặt rung
knock_session_05 → thay khoảng cách / góc / bề mặt
```

Nếu board đặt trực tiếp trên bề mặt đang rung thì ghi rõ:

```text
subtype = impact_vibration
surface = bed / desk / other
device_on_surface = yes / no
```

Không cần loại bỏ session RMS thấp nếu nó phản ánh điều kiện thực tế.

---

# 7. Speech trực tiếp

## Mục tiêu

Speech trực tiếp khác podcast vì âm thanh chưa đi qua loa.

Nhóm này quan trọng vì Patient Node có thể được dùng khi:

- người dùng nói,
- người nhà nói gần đó,
- nhiều người trao đổi trong phòng.

## Kịch bản tối đa 5 session

Khuyến nghị có ít nhất 2 người nếu có thể:

```text
speech_session_01 → Người A nói bình thường, đọc liên tục, ngắt nghỉ nhịp nhàng
speech_session_02 → Người A bình thường, đọc 1 câu ngắt nghỉ 2-4s
speech_session_04 → Người B nói bình thường, đọc liên tục, ngắt nghỉ nhịp nhàng
speech_session_05 → Người B bình thường, đọc 1 câu ngắt nghỉ 2-4s
speech_session_03 → A + B đối thoại tự nhiên
```

Các session riêng mỗi người có thể
- Đọc 2 văn bản khác nhau
- Giọng điệu ngắt nhịp nhàng 1 file, 1 file ngắt lâu

`speech_session_03` là session đối thoại tự nhiên để tạo:

- đổi speaker,
- khoảng cách khác nhau,
- nhịp nói khác nhau,
- pause không đều,
- đôi lúc chồng tiếng nhẹ.

Không cần đọc script cứng.

Nếu session có nhiều nguồn âm khác như fan + speech + clap thì chuyển sang nhóm `mixed`.

---

# 8. Room Noise / Ambient

## Mục tiêu

`room_noise` là **ambient tự nhiên**, không nên ép theo một kịch bản cứng.

Khác với fan, clap hay knock, room noise không đại diện cho một nguồn âm duy nhất. Nó đại diện cho môi trường sinh hoạt thực tế mà Patient Node có thể gặp.

### Có thể chứa tự nhiên

- gió tự nhiên,
- tiếng xe ngoài đường,
- tiếng người nói xa,
- tiếng điện thoại,
- TV/phòng khác vọng sang,
- tiếng cửa,
- bước chân,
- kéo ghế,
- đồ vật va chạm,
- tiếng đồ đạc rơi/vỡ,
- âm thanh hành lang,
- tiếng sinh hoạt,
- tiếng quạt xa,
- âm thanh ngoài trời nếu Node được mang ra ngoài.

### Không cần session nào giống session nào

Ví dụ:

```text
room_noise_session_01
→ Để gần ngoài đường, xe cộ đi lại, tiếng người nói vọng xa

room_noise_session_05
→ phòng có người đi lại, kéo ghế, cửa đóng mở, kéo mở rèm cửa

room_noise_session_03
→ gần cửa sổ / ngoài trời, có gió tự nhiên + người nói xa, vị trí đổi

room_noise_session_02
→ phòng sinh hoạt có điện thoại / TV / vật dụng

room_noise_session_04
→ môi trường tự nhiên hỗn hợp, không dàn dựng, nhiều đồ dùng, tiếng nói

room_noise_session_06
→ tiếng mưa nhỏ cửa sổ, 1 chút tiếng nói chuyện
```

Không bắt buộc phải thu đúng 5 kiểu trên.

### Không nên làm

Không nên tạo một kịch bản sân khấu kiểu:

```text
10 s nói
10 s clap
10 s knock
10 s fan
```

vì đó không còn là ambient tự nhiên.

Nếu trong lúc thu tự nhiên xuất hiện người nói, điện thoại, gió, tiếng xe, va đập hoặc đồ vật rơi thì cứ giữ nguyên.

### Có thể thu ngoài phòng

Hoàn toàn được nếu phù hợp với cách Node có thể được sử dụng thực tế, ví dụ:

- cửa sổ / ban công,
- hành lang,
- sân,
- ngoài nhà,
- nơi có gió nhẹ.

Chỉ cần metadata ghi rõ địa điểm và điều kiện.

---

# 10. Mixed / Challenge Environment

Hiện repository chỉ có một session mixed legacy:

```text
keyfan_old_01 → key_fan_5min.wav → fan + keyboard
```

Session này được giữ riêng ở Train và không thuộc bộ 33 Environment chính.
Nếu mở rộng dữ liệu sau này, có thể thu thêm **2–4 session** hỗn hợp với ID
mới rõ ràng, ví dụ:

Ví dụ:

```text
mixed_01 → fan + speech
mixed_02 → podcast + fan
mixed_03 → speech + clap nhẹ
mixed_04 → room ambient phức tạp
```

Mục tiêu là cho mô hình gặp nhiều nguồn âm chồng nhau. Không cần biến mọi nhóm thành mixed.

---

# 11. Silence

Session silence hiện có:

```text
silence_old_01 → silence_5min.wav
```

Silence lưu riêng để dùng cho:

- Quality Check,
- AUDIO_INACTIVE,
- kiểm tra false trigger,
- augmentation,
- time shifting.

Không coi silence là nhóm Non-Asthma classifier chính.

---

# 12. Metadata đề xuất

Mỗi WAV master nên có metadata tương ứng.

Ví dụ CSV:

```csv
file_name,session_id,category,subtype,duration_s,rms,peak,active_ratio,clipping_ratio,location,source_distance,source_angle,notes
fan_session_01.wav,fan_session_01,fan,continuous,60,487.29,5194,99.81,0,room,medium,front,fan low mode
```

Các field hữu ích:

```text
file_name
session_id
category
subtype
duration
RMS
Peak
Active Ratio
Clipping Ratio
location
distance
angle
notes
```

Không cần mọi field đều có giá trị ở mọi category.

---

# 13. Quy tắc Train / Val / Test

Environment phải được split theo `session_id`.

Pipeline Dataset V2 hiện dùng 33 session chính và chia theo cấu trúc:

| Nhóm | Tổng | Train | Validation | Test |
|---|---:|---:|---:|---:|
| Podcast | 6 | 5 | 1 | 0 |
| Fan | 5 | 4 | 1 | 0 |
| Clap | 6 | 5 | 1 | 0 |
| Knock | 5 | 4 | 0 | 1 |
| Room noise | 6 | 5 | 0 | 1 |
| Speech | 5 | 4 | 0 | 1 |
| **Tổng** | **33** | **27** | **3** | **3** |

Validation có một session Podcast, Fan và Clap. Test có một session Knock,
Room noise và Speech. Script `03_Cut_Environment.py` chọn session cụ thể bằng
seed cố định; không suy luận split chỉ từ số thứ tự trong tên file. Danh sách
chính thức sau mỗi lần chạy nằm trong:

```text
AI_Training_Model/Phase1_Split_Data/Output/03_Cut_Environment/
├── environment_session_split.csv
└── environment_session_split.md
```

Bộ Fan thực tế gồm năm session:

```text
fan_session_01
fan_session_02
fan_session_03
fan_session_04
fan_session_06
```

Không có `fan_session_05.wav`; ID `06` là session hợp lệ thứ năm và không ảnh
hưởng đến cách chia theo `session_id`.

Sau đó mới cắt 5 s.

Không được:

```text
fan_session_01 clip_001 → Train
fan_session_01 clip_002 → Val
```

vì hai clip cùng đến từ một recording session.

Với Dataset V2:

```text
Environment Train
→ có thể dùng làm augmentation asset

Environment Val/Test
→ tuyệt đối không dùng để augmentation Train
```

---

# 14. Không cần cân bằng tuyệt đối số session

Không cần ép:

```text
5 podcast
5 fan
5 clap
5 knock
5 keyboard
5 speech
5 room
```

Mục tiêu là **diversity**, không phải số session bằng nhau.

Một cấu hình hợp lý có thể là:

```text
Podcast      5–6 sessions
Fan          5 sessions
Clap         5 sessions
Knock        5 sessions
Keyboard     0–5 sessions
Speech       5 sessions
Room Noise   3–5 sessions
Mixed        2–4 sessions
```

Sau khi cắt 5 s cũng không nên để một loại môi trường quá lớn áp đảo toàn bộ Non-Asthma Train.

---

# 15. Checklist kết thúc một session

```text
[x] WAV master đã lưu
[x] Tên file đúng
[x] session_id duy nhất
[x] Không thay đổi gain / firmware
[x] RMS đã ghi
[x] Peak đã ghi
[x] Active Ratio đã ghi
[x] Clipping Ratio đã ghi
[x] Điều kiện thu đã ghi
[x] Không xóa raw chỉ vì QC hiện tại FAIL
```

---

# 16. Workflow tổng quát Environment V2

```text
ESP32-S3 + INMP441 cấu hình cố định
                ↓
Thu từng environment thành session độc lập
                ↓
Podcast / Fan / Clap / Knock / Keyboard / Speech
                ↓
Thu Room Noise theo môi trường tự nhiên
                ↓
Thu thêm ít Mixed Challenge nếu cần
                ↓
Lưu WAV master + metadata
                ↓
Chia Train / Val / Test THEO SESSION
                ↓
Cắt 5 s trong từng split
                ↓
Environment Train
        ↓
Non-Asthma Train + augmentation asset phù hợp

Environment Val/Test
        ↓
Benchmark độ robust độc lập
```

---

## Kết luận

Mục tiêu của Dataset V2 không phải thu thật nhiều file giống nhau, mà là để Patient Node gặp được **nhiều điều kiện âm học thực tế khác nhau**.

```text
source diversity > số lượng take lặp lại
session diversity > số lượng clip cắt ra từ cùng một session
```

Riêng `room_noise`, không cần và cũng không nên cố định một kịch bản duy nhất. Những tình huống hỗn hợp tự nhiên như gió, người nói, điện thoại, xe cộ, tiếng đồ vật, va đập hoặc sinh hoạt trong/ngoài phòng chính là dữ liệu có giá trị cho nhóm này.
