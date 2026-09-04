# Tinh chỉnh pipeline Python và ESP32-S3

Ngày kiểm tra: 17/08/2026.

## Pipeline được chọn làm chuẩn

Pipeline chuẩn nằm trong `AI_Training_Model`:

1. Đọc một kênh, đổi tần số lấy mẫu về 16 kHz và cố định 5 giây.
2. Chuẩn hóa từng đoạn âm thanh theo trị tuyệt đối lớn nhất.
3. Butterworth bandpass bậc 5, 100–2.000 Hz, dùng hệ số `b, a` và `lfilter`.
4. Tiền nhấn với hệ số 0,97.
5. Mel-Spectrogram: FFT 1.024, bước nhảy 625, 64 dải Mel, 100–2.000 Hz,
   `center=True`, Hann tuần hoàn, thang Mel Slaney và chuẩn hóa diện tích Slaney.
6. Đổi công suất sang dB với đỉnh làm mốc 0 dB và giới hạn dưới -80 dB.
7. Chuẩn hóa dB cố định từ [-80, 0] về [0, 1], rồi lượng tử theo thông số
   thật của tensor đầu vào.

## Các sai khác nghiêm trọng đã sửa trong phase 3

- Thay model cũ bằng `Asthma_Model_3.h` được tạo từ model INT8 mới.
- Khi đổi đầu vào sang INT8, dùng làm tròn tới số nguyên gần nhất thay vì cắt
  phần thập phân.
- Kiểm tra bắt buộc kiểu tensor INT8 và kích thước `[1, 64, 129, 1]` lúc khởi tạo.
- Dùng ngưỡng 0,5 giống lúc đánh giá Python. Chưa trộn vùng "không chắc chắn"
  vào phép kiểm tra độ khớp pipeline.
- Đổi tên lớp 1 từ `Normal` thành `Non-Asthma`, vì lớp này còn chứa COPD,
  viêm phế quản, viêm phổi và tiếng môi trường.
- Thay bộ lọc SOS cũ bằng đúng hệ số `b, a` và cấu trúc tính của
  `scipy.signal.lfilter`; trạng thái bộ lọc dùng số 64-bit.
- Thay cửa sổ Hann của `arduinoFFT` bằng Hann tuần hoàn đúng công thức của Python.
- Không làm tròn các đỉnh tam giác Mel về chỉ số FFT; trọng số được tính tại tần
  số thật của từng ô FFT, sau đó chuẩn hóa diện tích Slaney.
- Bỏ khuếch đại số ×4 trước chuẩn hóa để tránh cắt đỉnh. Ngưỡng phát hiện âm
  thanh giảm từ 5.000 xuống 1.250 để giữ độ nhạy gần tương đương.

## Kết quả kiểm tra trên máy tính

Firmware biên dịch thành công bằng PlatformIO:

- RAM tĩnh: 236.492 / 327.680 byte (72,2%).
- Flash: 1.221.449 / 6.553.600 byte (18,6%).

Đã mô phỏng phép tính số 32-bit và chính thuật toán FFT của `arduinoFFT` trên
7 file huấn luyện 16 kHz thuộc cả Asthma và Non-Asthma:

| Chỉ số mẫu | Sai số dB lớn nhất | Số ô INT8 khác | Độ lệch INT8 lớn nhất |
|---:|---:|---:|---:|
| 0 | 0,001671 | 1 / 8.256 | 1 |
| 100 | 0,003138 | 3 / 8.256 | 1 |
| 300 | 0,001893 | 0 / 8.256 | 0 |
| 600 | 0,002187 | 0 / 8.256 | 0 |
| 833 | 0,000063 | 0 / 8.256 | 0 |
| 893 | 0,000546 | 0 / 8.256 | 0 |
| 1.012 | 0,000145 | 1 / 8.256 | 1 |

Kết quả này cho thấy công thức hiện đã rất sát pipeline Python. Tuy nhiên,
đây chưa phải bằng chứng phần cứng và không được ghi là "khớp 100%".

## Việc phải kiểm tra tiếp trên ESP32-S3

1. Nạp cùng một tensor INT8 đã tạo sẵn vào Python và ESP32 để kiểm tra riêng
   model, file header và bộ suy luận.
2. Nạp cùng một mảng PCM16 dài 80.000 mẫu vào hai pipeline, xuất toàn bộ tensor
   INT8 từ ESP32 và so sánh đủ 8.256 ô.
3. Chỉ khi hai bước trên đạt yêu cầu mới kiểm tra WAV hoàn chỉnh, sau đó mới đến
   loa → INMP441 → ESP32-S3.
4. Dùng file thuộc tập học để sửa pipeline. Không xem trước kết quả tập kiểm tra
   khóa kín trong lúc tinh chỉnh.
