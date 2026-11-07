# Bộ tài liệu xây dựng preprocessing C++

[Trang chủ Docs](../README.md)

Mục tiêu của nhóm này là giúp đọc, tái tạo và kiểm chứng toàn bộ đường đi từ I2S đến tensor INT8 trên ESP32-S3. Mỗi bước phải khớp hợp đồng của model; việc cùng gọi một phép biến đổi là “Mel” hoặc “normalize” chưa đủ để bảo đảm tương đương.

## Lộ trình đọc

| Thứ tự | Tài liệu | Câu hỏi được giải đáp |
|---|---|---|
| 01 | [Hợp đồng và ánh xạ hàm](01_Hop_Dong_Du_Lieu_Va_Anh_Xa_Ham.md) | Python và C++ phải thống nhất những gì? |
| 02 | [I2S, PCM, VAD, Quality](02_I2S_PCM_VAD_Quality.md) | 80.000 mẫu đến từ đâu, onset được lấy thế nào? |
| 03 | [Normalize, Butterworth và trạng thái pre-emphasis](03_Normalize_Butterworth_PreEmphasis.md) | Bộ lọc được tính ra sao và vì sao C4 không dùng pre-emphasis? |
| 04 | [STFT, FFT, Hann](04_STFT_FFT_Hann.md) | Vì sao có 1.025 bin và 129 frame? |
| 05 | [Mel Slaney và Log-Mel](05_Mel_Slaney_LogMel.md) | Tạo filterbank, dB và layout thế nào? |
| 06 | [Tensor INT8, inference, bộ nhớ](06_Tensor_INT8_Inference_Bo_Nho.md) | Float32 vào TFLite INT8 bằng cách nào? |
| 07 | [Kiểm chứng Python–C++](07_Kiem_Chung_Python_CPP.md) | Đo sai số và tìm công đoạn gây lệch ra sao? |

## Ba ranh giới cần phân biệt

1. **Acquisition:** I2S, cửa sổ 5 s, VAD và chất lượng PCM.
2. **Feature extraction:** normalize waveform, lọc Butterworth, FFT 2048, Mel40 và dB. C4 không áp dụng pre-emphasis.
3. **Inference:** normalization theo Train, lượng tử tensor, invoke, giải lượng tử và hậu xử lý.

Chất lượng âm thanh cần được kiểm tra trước normalize. VAD chỉ chọn lúc bắt đầu thu; nó không phải bộ phân loại Asthma. Model có output nhị phân; UNSURE/voting thuộc tầng ứng dụng.

## Nguồn code ưu tiên

- [Patient_Node/src/I2S_Mic.cpp](../../Final_Project_NCKH/Patient_Node/src/I2S_Mic.cpp).
- [DSP_Filter.cpp](../../Final_Project_NCKH/Patient_Node/src/DSP_Filter.cpp).
- [Mel_Scale.cpp](../../Final_Project_NCKH/Patient_Node/src/Mel_Scale.cpp).
- [Inference_Asthma.cpp](../../Final_Project_NCKH/Patient_Node/src/Inference_Asthma.cpp).
- [Python Preprocess_Audio.py](../../AI_Training_Model/Phase2_Preprocess_&_Traning/Preprocess_Audio.py).

Hợp đồng hiện hành được chốt bởi [manifest C4](../README_AI_C4_Current.md) và source Node: 40 Mel, FFT 2048, hop 625, không pre-emphasis. Khi so các project deployment phải đối chiếu hash và selector model, không chỉ tên file.

Node và 3_Model_Complete hiện dùng LOW/HIGH 0,47/0,77; 2_Test_Model_LiveMic có thể dùng nhị phân0,5 cho đối chiếu model. Khi kiểm tra preprocessing, so `p_non` và tensor trước khi so nhãn.

