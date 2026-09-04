# 🚀 TÀI LIỆU CHUẨN BỊ DỮ LIỆU TINYML (ASTHMA DETECTION ON ESP32-S3)

Tài liệu này hướng dẫn chi tiết quy trình xây dựng, chuẩn hóa và tăng cường dữ liệu (Data Pipeline) cho dự án NCKH: **Phân loại âm thanh hô hấp (Asthma vs. Non-Asthma)** triển khai trên vi điều khiển ESP32-S3. 

Vì lý do dung lượng và bản quyền, các file `.wav` gốc không được đẩy lên Repository này. Bạn cần tự tải và thu thập theo hướng dẫn dưới đây trước khi chạy các script Python.

---

## 📑 1. Cấu Trúc Thư Mục Yêu Cầu

Trước khi bắt đầu, hãy tạo cấu trúc thư mục sau tại thư mục gốc của project:

* `Dataset/0_Asthma/` : (Thư mục đích) Sẽ chứa 1000 mẫu hen suyễn sau khi chuẩn hóa & mix.
* `Dataset/1_Non_Asthma/` : (Thư mục đích) Sẽ chứa 1000 mẫu không phải hen suyễn.
* `Dataset/2_TuThu/` : (Kho nguyên liệu 1) Chứa các file tạp âm môi trường tự thu (5s, 16kHz).
* `Dataset/3_asthma/` : (Kho nguyên liệu 2) Chứa file Asthma gốc tải từ Kaggle.
* `Dataset/4_Raw_Non_Asthma/` : (Kho nguyên liệu 3) Chứa các bệnh lý khác tải từ Kaggle.

Số lượng mẫu đang có

| Tập | Số lượng |
|---|---|
| 0_Asthma | 1000 |
| 1_Non_Asthma | 1000 |
| 2_TuThu | 180 |
| 3_asthma | 288 |
| 4_Raw_Non_Asthma | 820 |

---

## 📥 2. Hướng Dẫn Thu Thập Dữ Liệu Gốc

### A. Dữ liệu bệnh lý (Tải từ Kaggle)
Sử dụng bộ dataset chuẩn y tế từ Kaggle: [Asthma Detection Dataset Version 2](https://www.kaggle.com/datasets/mohammedtawfikmusaed/asthma-detection-dataset-version-2?resource=download)

Sau khi tải về và giải nén, hãy phân bổ file như sau:
* Lấy toàn bộ file trong thư mục `Asthma` ném vào `Dataset/3_asthma/`.
* Lấy toàn bộ file COPD (401 file), Healthy (133 file), Bronchial (104 file), Pneumonia (182 file) ném chung vào `Dataset/4_Raw_Non_Asthma/`.

### B. Dữ liệu tạp âm môi trường (Tự thu)
Để mô hình hoạt động thực tế trên ESP32-S3 chống chịu được nhiễu, cần tự thu 3 loại tạp âm bằng chính micro I2S (VD: INMP441) sẽ dùng cho dự án. Thu 3 file `.wav` dài (khoảng 5-10 phút) cho 3 môi trường:
1. **Im lặng:** Để mạch trong phòng kín, không có tiếng động.
2. **Tiếng Podcast/Người nói:** Bật một đoạn podcast giọng đọc đều đều, âm lượng ổn định.
3. **Tiếng Quạt + Phím cơ:** Bật quạt gió vù vù và gõ phím cơ để lấy nhiễu dải tần thấp.

**Cách băm nhỏ file tự thu:**
Chạy script `1_Split_Audio.py` để tự động băm các file dài ở trên thành các đoạn nhỏ chuẩn 5 giây và lưu tự động vào `Dataset/2_TuThu/`.
*(Lưu ý: Mở file script và đổi biến `FILE_GOC` cùng `TIEN_TO` tương ứng cho mỗi lần chạy).*

---

## ⚙️ 3. Nguyên Tắc Chuẩn Hóa Dữ Liệu (Standardization)

Mọi file âm thanh thô (Kaggle và tự thu) có độ dài, tần số khác nhau sẽ được script Python (sử dụng thư viện `librosa`) tự động ép về chuẩn chung để tối ưu cho TinyML:
* **Sample Rate:** Ép về `16,000 Hz` (Giữ được dải tần wheezing 100-1000Hz, giảm 50% RAM xử lý).
* **Duration:** Ép chuẩn đúng `5.0 giây` (80,000 mẫu số). Dài hơn 5s sẽ bị cắt (Crop), ngắn hơn 5s sẽ được bù khoảng lặng (Zero-padding).

---

## 🧬 4. Chiến Lược Tăng Cường Dữ Liệu (Data Augmentation)

### A. Với tập Non-Asthma
Sau khi đưa các file tạp âm tự thu (Về 2_TuThu) và các file bệnh không phải Asthma (Về 4_Raw_Non_Asthma), hệ thống sẽ dùng script `2_Prep_Non_Asthma.py` để chuẩn hóa đủ 1000 file làm tập không phải bị bệnh Asthma

### B. Với tập Asthma

Do dữ liệu Asthma gốc chỉ có 288 mẫu, hệ thống sẽ dùng script `3_Prep_Asthma.py` để "hack" sinh ra thêm 712 mẫu ảo, đẩy tổng số lên 1000 mẫu nhằm cân bằng với nhóm Non-Asthma. Các kỹ thuật DSP (Xử lý tín hiệu số) bao gồm:

1. **Dynamic SNR Mixing:** Trộn tiếng hen suyễn với tiếng Quạt/Podcast với hệ số âm lượng ngẫu nhiên (Gain 0.2 - 0.7) giúp model không bị học vẹt tiếng ồn cố định.
2. **Time-Shifting (VAD Peak):** Dùng thuật toán tính đỉnh năng lượng (RMS) để xác định đúng lõi chứa tiếng rít, sau đó dịch chuyển lõi này vào vị trí ngẫu nhiên trên file Im lặng.
3. **White Gaussian Noise:** Bơm nhiễu trắng vào tín hiệu để mô phỏng noise floor của phần cứng thực tế.
4. **Time Stretching & Pitch Shifting:** Co giãn thời gian (mô phỏng nhịp thở gấp/chậm) và dịch cao độ siêu nhẹ ($\pm 1.5$ semitones) mô phỏng kích thước thanh quản (trẻ em/người lớn) mà không làm biến dạng phổ bệnh lý.