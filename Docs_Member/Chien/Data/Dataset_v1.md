# Quy trình thu dữ liệu và tạo Dataset Patient Node

## 1. Mục đích

Tài liệu này tóm tắt cách thu âm và tạo dataset cho bài toán phân loại:

```text
0 = Asthma
1 = Non-Asthma
```

Mục tiêu là tạo dữ liệu gần với đường thu thật của Patient Node, đồng thời tránh
để các đoạn âm thanh cùng nguồn xuất hiện ở cả train và test.

---

## 2. Dữ liệu baseline hiện tại

| Nguồn | Nội dung | Số lượng gốc |
|---|---|---:|
| Kaggle Asthma | Âm thanh Asthma | 288 file |
| Kaggle Non-Asthma | COPD, Healthy, Bronchial, Pneumonia | 820 file trước loại trùng |
| INMP441 tự thu | Im lặng, podcast/người nói, quạt + phím | 180 file, 60 file/nhóm |

Luồng baseline:

```text
WAV gốc
→ loại file trùng bằng SHA-256
→ gom theo bệnh nhân/nguồn thu
→ chia Train/Validation/Test
→ chỉ tăng cường Asthma Train
→ chuẩn hóa 16 kHz, mono, 5 giây
→ tạo Mel-Spectrogram 64 × 129 × 1
→ lưu X/Y/Files dạng NPY
```

Số lượng sau khi chia và tăng cường:

| Tập | Asthma | Non-Asthma |
|---|---:|---:|
| Train | 833 | 833 |
| Validation | 30 | 78 |
| Test | 30 | 83 |

Trong baseline, 180 mẫu môi trường đều nằm trong Non-Asthma Train vì dữ liệu cũ
chưa có nhiều phiên thu độc lập để chia an toàn sang validation/test.

---

## 3. Dữ liệu nên thu thêm

### 3.1. Asthma playback

- Phát raw Asthma chưa dùng hoặc đã được xác định rõ nguồn qua loa.
- Tắt EQ, bass boost, spatial sound và các chế độ tăng cường âm thanh.
- Giữ cố định loa, mức âm lượng và khoảng cách tới INMP441 trong một phiên.
- Thu lại bằng đúng INMP441 của Patient Node.
- Mục tiêu vòng đầu: khoảng 80–120 clip 5 giây, ưu tiên nhiều source khác nhau.

### 3.2. Non-Asthma playback

- Phát COPD, Healthy, Bronchial hoặc Pneumonia qua cùng thiết lập loa–micro.
- Điều kiện thu phải tương đương Asthma playback để tránh model học thiết bị
  phát thay vì học đặc trưng âm thanh.
- Mục tiêu vòng đầu: khoảng 80–120 clip 5 giây.

### 3.3. Âm môi trường và hard-negative

Thu trực tiếp bằng INMP441:

- người nói/podcast;
- quạt và bàn phím;
- vỗ tay, gõ bàn, gõ vỏ thiết bị;
- tiếng phòng, TV và tiếng xe nhẹ.

Chạy model baseline trước. Mẫu nào bị dự đoán thành Asthma hoặc Unsure được ưu
tiên đưa vào Non-Asthma Train. Không cần đưa toàn bộ noise dễ vào dataset.

### 3.4. Dữ liệu chỉ dành cho Quality Check/VAD

Các trường hợp sau dùng để kiểm tra firmware, không bắt buộc train DS-CNN:

- im lặng;
- tín hiệu quá nhỏ;
- clipping/quá lớn;
- tín hiệu lỗi rõ ràng.

---

## 4. Quy cách thu âm

Thông số đích:

```text
Micro          : INMP441
Sample rate    : 16.000 Hz
Số kênh        : Mono
Định dạng      : WAV PCM16
Độ dài model   : 5 giây = 80.000 mẫu
```

Âm kéo dài như podcast, quạt hoặc tiếng phòng có thể thu thành phiên 1–3 phút,
sau đó cắt thành các cửa sổ 5 giây không chồng lấn ở vòng đầu.

Raw bệnh lý dài khoảng 6 giây nên được phát và thu lại toàn bộ trước. Sau đó mới
thử các cửa sổ `0–5 s`, `0,5–5,5 s` hoặc `1–6 s`. Mọi cửa sổ từ cùng raw vẫn
phải có chung `source_id`.

Tên file đề xuất:

```text
AST_SRC001_SES01_TAKE01.wav
NON_COPD_SRC015_SES01_TAKE02.wav
ENV_FAN_SES03_CLIP007.wav
QC_SILENCE_SES02_CLIP004.wav
```

Mỗi phiên nên lưu metadata tối thiểu:

| Trường | Ý nghĩa |
|---|---|
| `source_id` | Raw/bệnh nhân/nguồn âm thanh gốc |
| `session_id` | Một lần bố trí và thu liên tục |
| `label` | Asthma, Non-Asthma hoặc Quality_Check_Only |
| `capture_type` | Kaggle, playback_inmp441 hoặc environment |
| `distance_cm` | Khoảng cách loa/nguồn âm tới micro |
| `speaker_volume` | Mức âm lượng khi playback |
| `environment` | Phòng yên, quạt, tiếng nói nền... |
| `sample_rate` | Tần số lấy mẫu thực tế |

---

## 5. Quy tắc chia dữ liệu

Chia theo tỷ lệ tham khảo `80/10/10`, nhưng phải chia theo bệnh nhân,
`source_id` hoặc `session_id` trước khi cắt và tăng cường.

Đúng:

```text
SRC001 + toàn bộ take/crop của SRC001 → chỉ thuộc Train
FAN_SESSION_03 + toàn bộ clip          → chỉ thuộc Validation
```

Sai:

```text
SRC001_TAKE01 → Train
SRC001_TAKE02 → Test
```

Quy tắc bắt buộc:

- cùng bệnh nhân không được nằm ở nhiều tập;
- các đoạn cắt từ cùng phiên không được nằm ở nhiều tập;
- validation và test chỉ giữ dữ liệu gốc;
- noise dùng để tăng cường Train cũng phải thuộc phía Train;
- seed chia dữ liệu phải được lưu để tái tạo kết quả.

---

## 6. Tăng cường và cân bằng Train

Chỉ Asthma Train được tăng cường khi cần cân bằng với Non-Asthma Train:

- trộn noise môi trường;
- dịch vị trí vùng âm thanh;
- thêm white noise;
- time stretch khoảng `0,8–1,2`;
- pitch shift khoảng `±0,5` semitone.

Mỗi file tăng cường phải lưu:

```text
file mới
file cha
source/patient ID
phương pháp
seed
tham số biến đổi
```

Không tăng cường validation/test và không tạo nhiều bản gần giống chỉ để làm đẹp
số lượng.

---

## 7. Tiền xử lý đầu vào model

Sau khi chia xong, `Preprocess_Audio.py` xử lý riêng từng tập:

```text
Resample 16 kHz + sửa độ dài 5 giây
→ peak-normalize từng đoạn về [-1, 1]
→ Butterworth band-pass 100–2000 Hz
→ pre-emphasis 0,97
→ Mel-Spectrogram Slaney 64 × 129
→ dB trong khoảng [-80, 0]
→ lưu X, Y và danh sách tên file
```

Đầu ra:

```text
X_train/val/test_mel.npy
Y_train/val/test_mel.npy
Files_train/val/test.npy
```

Biên độ thô như RMS/Peak phải được đo trước bước peak-normalize nếu dùng để tinh
chỉnh Quality Check, VAD hoặc nghiên cứu thêm đặc trưng phụ cho Model V2.

---

## 8. Checklist trước khi train

- [ ] File WAV đọc được, không rỗng và không hỏng.
- [ ] Có `source_id/session_id` để truy vết.
- [ ] Không trùng nội dung theo SHA-256.
- [ ] Không có bệnh nhân/source/session nằm ở nhiều tập.
- [ ] Validation và test không chứa augmentation.
- [ ] Asthma và Non-Asthma dùng cùng quy cách playback khi so sánh.
- [ ] Dữ liệu Quality Check Only không bị đưa nhầm vào train DS-CNN.
- [ ] Lưu CSV chia dữ liệu và CSV nguồn gốc augmentation.
- [ ] Giữ nguyên model baseline để so sánh với candidate mới.

Quy trình rút gọn cần tuân theo:

```text
Thu có metadata
→ kiểm tra file/trùng lặp
→ chia theo source/session
→ cắt 5 giây
→ augmentation chỉ ở Train
→ preprocess riêng từng tập
→ train candidate
→ so sánh với baseline
```
