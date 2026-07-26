# I2S_Mic — Thu âm, Điều phối Pipeline và Ra Quyết Định

Thư viện này là "nhạc trưởng" của toàn hệ thống: thu âm qua I2S từ INMP441, điều phối máy trạng thái (state machine) qua các bước DSP → AI, và tổng hợp kết quả qua cơ chế voting nhiều lần đo. Không có tương ứng Python trực tiếp 1-1 như 3 thư viện kia — đây là phần logic điều khiển runtime thuần túy trên firmware.

---

## 1. Máy trạng thái tổng quan (State Machine)

STATE_LISTENING → STATE_RECORDING → STATE_PROCESSING → STATE_INTERFACE → (quay lại STATE_LISTENING)

| State | Việc làm | Điều kiện chuyển tiếp |
|---|---|---|
| `STATE_LISTENING` | Nghe ngóng, tính năng lượng từng khối 256 mẫu | Năng lượng > `Val_Threshold` → chuyển `STATE_RECORDING` |
| `STATE_RECORDING` | Gom đủ 80,000 mẫu (5 giây) vào `audio_buffer` | Đủ `Total_Samples` → chuyển `STATE_PROCESSING` |
| `STATE_PROCESSING` | Chạy toàn bộ chuỗi DSP (chuẩn hóa → lọc → Mel → dB) | Xong hết 5 bước → chuyển `STATE_INTERFACE` |
| `STATE_INTERFACE` | Gọi AI, cộng dồn vote, xuất thống kê | Luôn quay lại `STATE_LISTENING` |

Hàm `Process_Audio_Stream()` được gọi liên tục trong `loop()` — mỗi lần gọi chỉ đọc và xử lý **1 khối 256 mẫu** từ DMA buffer (`i2s_read`), không block toàn bộ chương trình, nhờ vậy `loop()` vẫn phản hồi nhanh dù xử lý audio thời gian thực.

---

## 2. `STATE_LISTENING` — Voice Activity Detection (VAD) đơn giản

```cpp
uint32_t sum_energy = 0;
for(int i = 0; i < samples_read; i++)
    sum_energy += abs(chunk[i]);

uint32_t avg_energy = sum_energy / samples_read;

if(avg_energy > Val_Threshold){ 
    ... chuyển sang ghi âm ... 
}
```

Đây là thuật toán **MAV (Mean Absolute Value)** — tính trung bình biên độ tuyệt đối của 256 mẫu (~16ms audio), so với ngưỡng cố định `Val_Threshold = 5000`. Đơn giản, không cần FFT hay xử lý phức tạp, phù hợp chạy real-time trên MCU.

**Không mất mẫu đầu:** ngay khi phát hiện tiếng động, khối 256 mẫu vừa đo (đã vượt ngưỡng) được nhét luôn vào `audio_buffer` thay vì bỏ đi — tránh mất phần đầu của tiếng ho/thở do độ trễ phát hiện.

---

## 3. `STATE_RECORDING` — Gom đủ 5 giây

```cpp
for(int i = 0; i < samples_read; i++){
    if(sample_cnt < Total_Samples){
        audio_buffer[sample_cnt] = chunk[i];
        sample_cnt++;
    }
}
```

Copy từng mẫu vào đúng vị trí `sample_cnt` trong `audio_buffer` (đã cấp phát PSRAM), tăng dần cho đến khi đạt `Total_Samples = 80000`. Vì mỗi lần `Process_Audio_Stream()` chỉ nhận 256 mẫu mới từ I2S, cần khoảng `80000/256 ≈ 313` lần gọi hàm liên tiếp mới gom đủ.

---

## 4. `STATE_PROCESSING` — Chuỗi 5 bước DSP, đúng thứ tự Python

```cpp
// 1. int16 -> float [-1,1]
Normalize_To_Float(...)       
// 2. Lọc thông dải       
Butterworth_Reset();
Butterworth_Process_Buffer(...)     
// 3. Bù suy hao tần số cao 
Apply_Pre_Emphasis(...)      
// 4. STFT + Mel filterbank       
Compute_Mel_Power_Spectrogram(...)   
// 5. Chuyển sang dB
Power_To_dB_RefMax(...)              
```

**Thứ tự này bắt buộc khớp chính xác với `5_Extract_Features.py`** (`Process_Audio_File()`): chuẩn hóa → Butterworth → Pre-emphasis → Mel-Spectrogram → dB. Đảo thứ tự bất kỳ 2 bước nào (ví dụ lọc trước rồi mới chuẩn hóa) sẽ khiến hệ số chuẩn hóa tính trên tín hiệu sai, làm lệch toàn bộ pipeline phía sau — đây từng là nguồn gốc 1 bug đã fix.

**`Butterworth_Reset()` bắt buộc gọi trước mỗi lần lọc** — xóa trạng thái trễ còn sót từ lần đo trước, tránh nhiễu chéo giữa các lần đo độc lập.

---

## 5. `STATE_INTERFACE` — Voting 3 lần đo + Thống kê

### Cơ chế Voting

```cpp
if (result.Predicted_Class == 0) vote_asthma_count++;
else if (result.Predicted_Class == 1) vote_normal_count++;
else vote_unsure_count++;

current_vote_round++;

if (current_vote_round >= Vote_Round) {   
    // Vote_Round = 3
    // So sánh vote_asthma_count vs vote_normal_count => Kết luận
    // Reset cả 4 biến vote về 0 để bắt đầu chu kỳ đo tiếp theo
}
```

**Mục đích:** 1 lần đo đơn lẻ dễ bị nhiễu bởi môi trường (tiếng động bất chợt, vị trí mic thay đổi). Yêu cầu **quá bán trong 3 lần đo liên tiếp** mới đưa ra kết luận cuối cùng, giúp giảm đáng kể tỷ lệ báo động giả từ 1 lần đo lệch.

**Trường hợp hòa (`vote_asthma_count == vote_normal_count`)** — ví dụ 1 Asthma, 1 Normal, 1 Unsure — kết luận là "không chắc chắn, đề nghị đo lại" thay vì ép buộc chọn 1 phía.

### Thống kê dài hạn

```cpp
static uint32_t total_tests = 0;
static uint32_t total_asthma_alerts = 0;
```

Khác với biến vote (reset mỗi 3 lần đo), 2 biến này **cộng dồn suốt phiên hoạt động**, dùng `uint32_t` (không phải `uint8_t`) vì cần chứa được số lớn nếu thiết bị chạy demo/thực tế trong thời gian dài (uint8_t chỉ chứa tối đa 255, dễ tràn số nếu chạy hàng trăm lần đo). Cứ mỗi 10 lần đo, in ra 1 lần tỷ lệ % báo Asthma tổng thể — dùng làm số liệu tham khảo về tỷ lệ báo động giả (false positive rate) trong điều kiện thực tế.

---

## 6. `I2S_Mic_Init()` — Cấu hình phần cứng

**Cấp phát bộ nhớ trên PSRAM** (không dùng SRAM nội bộ vì `audio_buffer` + `audio_float_buff` tổng cộng chiếm ~470KB — vượt xa khả năng SRAM nội bộ còn trống của ESP32-S3):
```cpp
audio_buffer = (int16_t*)heap_caps_malloc(Total_Samples * sizeof(int16_t), MALLOC_CAP_SPIRAM);
audio_float_buff = (float*)heap_caps_malloc(Total_Samples * sizeof(float), MALLOC_CAP_SPIRAM);
```
Có kiểm tra `nullptr` và treo máy có chủ đích (`while(1)`) nếu cấp phát thất bại — tránh chạy tiếp với con trỏ null gây crash khó chẩn đoán.

**Cấu hình I2S cho INMP441:**
| Tham số | Giá trị | Ý nghĩa |
|---|---|---|
| `mode` | `I2S_MODE_MASTER \| I2S_MODE_RX` | ESP32 làm master, chỉ nhận (không phát) |
| `bits_per_sample` | `I2S_BITS_PER_SAMPLE_32BIT` | INMP441 xuất dữ liệu 24-bit đóng gói trong khung 32-bit |
| `channel_format` | `I2S_CHANNEL_FMT_ONLY_RIGHT` | Đọc kênh phải — khớp với việc nối chân `L/R` của mic lên `3.3V` |
| `dma_buf_count = 8`, `dma_buf_len = Buffer_Samples (256)` | Cấu hình double-buffering DMA để đọc dữ liệu I2S liên tục không ngắt quãng |

**Amplify_Factor và Clamp chống tràn số** (thực hiện ở `Process_Audio_Stream()`, không phải ở đây):
```cpp
int32_t amplified = (raw_samples[i] >> 16) * Amplify_Factor;
if(amplified > 32767) amplified = 32767;
if(amplified < -32768) amplified = -32768;
```
`raw_samples[i] >> 16` lấy phần dữ liệu 16-bit có nghĩa từ khung 32-bit thô của INMP441, nhân với hệ số khuếch đại phần mềm. Bắt buộc clamp trước khi ép về `int16_t` — nếu không, tín hiệu âm lượng lớn (như tiếng hét) sẽ tràn số, tạo nhiễu giả dạng răng cưa, dễ bị model nhận nhầm là đặc trưng bệnh lý.