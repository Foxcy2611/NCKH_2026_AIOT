# Cấu trúc include

- `Audio_IO/I2S_Mic.h`: cấu hình INMP441, chế độ kiểm tra và máy trạng thái.
- `DSP_Preprocessing/DSP_Filter.h`: chuẩn hóa, Butterworth và pre-emphasis.
- `DSP_Preprocessing/Mel_Scale.h`: STFT, Mel Slaney và đổi power sang dB.
- `Model_AI/Asthma_Model_3.h`: model TFLite INT8 chính thức của phiên bản 1.
- `Model_AI/Interface_Asthma.h`: nạp model, lượng tử input và suy luận.
- `Raw_Include_Parity20/`: 20 mẫu PCM khóa để so pipeline Python–C++.
- `Tensor_Include_Validation108/`: tensor validation dùng kiểm tra trực tiếp.
- `Tensor_Include_Test113/`: tensor test khóa dùng chấm kết quả cuối.

Các bộ `Raw_Include_Phase_1/2/3` và model cũ đã được loại bỏ vì không còn được
tham chiếu sau khi pipeline tinh chỉnh được xác nhận.
