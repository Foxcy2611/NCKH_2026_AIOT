# 🫁 Asthma Detection trên ESP32-S3 — Tổng quan hệ thống

Dự án nhận diện tiếng ho/thở bất thường (Asthma) theo thời gian thực, chạy hoàn toàn trên vi điều khiển **ESP32-S3** bằng TinyML. Toàn bộ pipeline: **thu âm → xử lý tín hiệu số (DSP) → trích xuất đặc trưng Mel-Spectrogram → suy luận AI (TFLite Micro) → ra quyết định** được chia thành 4 thư viện, mỗi thư viện đảm nhiệm 1 vai trò riêng và phải khớp chính xác với pipeline Python lúc train model.

---

## 🧩 Sơ đồ pipeline tổng thể

```
🎙️ I2S_Mic (thu âm + điều phối)
        │
        ▼
🎚️ DSP_Filter (chuẩn hóa + lọc Butterworth + pre-emphasis)
        │
        ▼
🎵 Mel_Scale (STFT + Mel filterbank + power→dB)
        │
        ▼
🫁 Interface_Asthma (quantize + TFLite Micro inference + quyết định)
        │
        ▼
🗳️ Voting 3 lần đo → Kết luận Asthma / Normal / Không chắc chắn
```

---

## 🎙️ 1. I2S_Mic — "Nhạc trưởng" điều phối toàn hệ thống

**Vai trò:** Thu âm qua I2S từ mic **INMP441**, chạy máy trạng thái (state machine) điều phối các bước DSP → AI, và tổng hợp kết quả qua cơ chế voting.

- 🔄 4 trạng thái: `LISTENING → RECORDING → PROCESSING → INTERFACE`
- 👂 Phát hiện tiếng động bằng thuật toán MAV (Mean Absolute Value)
- ⏺️ Gom đủ 80,000 mẫu (5 giây) vào buffer PSRAM
- 🗳️ Voting 3 lần đo để giảm báo động giả
- 📊 Thống kê tỷ lệ báo động dài hạn

📄 Không có tương ứng Python 1-1 — đây là phần logic điều khiển runtime thuần firmware.

---

## 🎚️ 2. DSP_Filter — Lọc tín hiệu tiền xử lý

**Vai trò:** Làm sạch tín hiệu âm thanh thô trước khi đưa vào STFT, khớp chính xác với `scipy.signal` lúc train.

- 🔺 Bộ lọc **Butterworth bandpass** dạng SOS (cascade biquad) — ổn định số học tốt hơn Direct Form
- 📉 **Pre-emphasis** bù suy hao tần số cao
- 📏 **Normalize** biên độ tín hiệu về [-1, 1]

⚠️ Điểm dễ sai: thứ tự vòng lặp pre-emphasis, và tràn số `int16_t` khi tính `abs()`.

---

## 🎵 3. Mel_Scale — Trích xuất đặc trưng Mel-Spectrogram

**Vai trò:** Tái hiện chính xác `librosa.feature.melspectrogram()` bằng C++.

- 📐 Công thức **Slaney** (không phải HTK) để đổi Hz ↔ Mel
- 🎯 Mô phỏng `center=True` của `librosa.stft()` (đệm 0 hai đầu)
- 🔺 Dựng 64 bộ lọc tam giác + chuẩn hóa Slaney-norm
- 🌊 STFT (Hann window + FFT) rồi áp Mel filterbank
- 🔊 Chuyển power → dB (`ref=np.max`, `top_db=80`)

⚠️ Điểm dễ sai: nhầm thang HTK/Slaney, thiếu clip đáy `top_db`.

---

## 🫁 4. Interface_Asthma — Giao tiếp với model TFLite Micro

**Vai trò:** Nạp model đã quantize, chuẩn bị input tensor, chạy inference, và diễn giải kết quả.

- 💾 Tensor Arena cấp phát trên PSRAM
- ⚙️ Quantize input: chuẩn hóa [0,1] bằng hằng số cố định lúc train → quantize int8 theo scale/zero_point của model
- 📈 Output **Sigmoid 1 giá trị**: gần 0 → Asthma, gần 1 → Normal
- 🚦 Ngưỡng quyết định 3 mức (`<0.35` / `>0.65` / vùng giữa "không chắc chắn")

⚠️ Điểm dễ sai nhất: dùng min/max động thay vì hằng số cố định lúc train.

---

## 🔗 Tính nhất quán xuyên suốt

Cả 4 thư viện đều bám sát nguyên tắc: **mọi phép biến đổi trên ESP32-S3 phải khớp tuyệt đối thứ tự và công thức với pipeline Python lúc train** (`5_Extract_Features.py`, `6_Train_Model.py`, `7_Quantize_Export.py`). Bất kỳ sai lệch nhỏ nào (đảo thứ tự bước, sai công thức, quên reset trạng thái trễ, tràn số...) đều có thể khiến model dự đoán sai dù code "chạy được" bình thường — đây là lý do mỗi file đều có phần ghi chú kỹ các bug đã từng gặp.