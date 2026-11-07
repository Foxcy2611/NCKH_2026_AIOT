# Hợp đồng dữ liệu và ánh xạ Python–C++

[Mục lục C++](README.md)

## Mục lục

- [1. Hợp đồng của frontend C4](#muc-1)
- [2. Ánh xạ theo công đoạn](#muc-2)
- [3. Thứ tự gọi](#muc-3)
- [4. Đơn vị và dtype](#muc-4)
- [5. Phạm vi của crop](#muc-5)

<a id="muc-1"></a>

## 1. Hợp đồng của frontend C4

| Thuộc tính | Giá trị hiện hành | Nguồn C++ |
|---|---|---|
| Sample rate | 16.000 Hz | I2S_Mic.h, Mel_Scale.h |
| Cửa sổ | 5 s = 80.000 mẫu | I2S_Mic.cpp |
| PCM | mono int16_t | audio_buffer |
| Normalize waveform | Chia peak tuyệt đối | Normalize_To_Float |
| Bandpass | 100–2000 Hz, Butterworth prototype order5 | DSP_Filter.cpp |
| Dạng thực thi | ba, Direct Form II Transposed, bậc10 | Butterworth_Process_Sample |
| Pre-emphasis | Không dùng, coefficient 0 | Không có bước biến đổi trong Node |
| FFT/window | 2048 / Hann tuần hoàn | Compute_Mel_Power_Spectrogram |
| Hop | 625 mẫu = 39,0625 ms | HOP_LENGTH |
| Center/padding | 1024 mẫu mỗi bên, constant zero | Get_Centered_Frame |
| Mel | 40, Slaney, 100–2000 Hz, area norm | Init_Mel_Filterbank |
| Log | ref-max, amin1e-10, top_db80 | Power_To_dB_RefMax |
| Output feature | 40×129 float, Mel trước time | mel_spectrogram_buffer |
| Normalization model | min=-80, max=0 | Inference_Asthma.cpp |
| Tensor | INT8 [1,40,129,1] | TFLite runtime |

Cả bandpass waveform lẫn giới hạn Mel đều dùng 100–2000 Hz nhưng có vai trò khác nhau. Bandpass biến đổi tín hiệu thời gian; Mel chọn vùng phổ được tổng hợp thành feature.

<a id="muc-2"></a>

## 2. Ánh xạ theo công đoạn

| Python | C++ | Đầu vào → đầu ra |
|---|---|---|
| load_model_audio_window | Thu bằng I2S hoặc header PCM16 | WAV/ADC → 80.000 mẫu |
| librosa.util.normalize | Normalize_To_Float | PCM/float → float peak-normalized |
| butter + lfilter | Hệ số B/A + Butterworth_Reset/Process_Buffer | Waveform → waveform lọc |
| pre_emphasis=0 | Không gọi hàm biến đổi | Waveform lọc → giữ nguyên |
| center=True | Get_Centered_Frame | Waveform → frame2048 |
| window='hann', STFT | Hann thủ công + ArduinoFFT | Frame → phổ phức |
| power=2 | Real² + Imag² | Phổ phức → 1.025 power bins |
| melspectrogram filterbank | Init_Mel_Filterbank + phép nhân tổng | Power → 40 Mel/frame |
| power_to_db | Power_To_dB_RefMax | Mel power → Log-Mel |
| Min-max Train | Run_Asthma_Inference | dB → [0,1] |
| TFLite quantization | lrintf + clamp | Float → int8 |
| Interpreter.invoke | MicroInterpreter::Invoke | Input tensor → output tensor |

C++ không đọc WAV header khi chạy live mic. Các công đoạn load/resample/crop file thuộc Python hoặc generator PCM; không đem nguyên hàm load WAV sang firmware rồi giả định I2S đang có container WAV.

<a id="muc-3"></a>

## 3. Thứ tự gọi

```cpp
// Mã minh họa thứ tự; buffer phải được cấp phát và kiểm tra trước.
Normalize_To_Float(pcm, audio_float, 80000);
Butterworth_Reset();
Butterworth_Process_Buffer(audio_float, 80000);
int frames = Compute_Mel_Power_Spectrogram(audio_float, 80000, mel, 129);
Power_To_dB_RefMax(mel, mel, frames);
Asthma_Result result = Run_Asthma_Inference(mel);
```

Quality Gate gọi trước chuỗi trên ở State_Machine. `Init_Mel_Filterbank` và `Init_Asthma_Model` được gọi một lần trong setup. Không dùng Mel khi filterbank chưa cấp phát thành công.

<a id="muc-4"></a>

## 4. Đơn vị và dtype

| Vùng | Đơn vị | Kiểu số |
|---|---|---|
| audio_buffer | ADC sau dịch/clip về PCM16 | int16_t |
| audio_float_buffer | Biên độ tương đối | float32 |
| B/A và state IIR | Hệ số/trạng thái nội bộ | double |
| Filterbank | Trọng số phổ | float32, dựng điểm bằng double |
| FFT/Mel/dB | Phổ/Log-Mel | float32 |
| Tensor model | Mã lượng tử affine | int8_t |

C++ float và Python feature float64 không bit-exact mặc định. Phần IIR dùng double giảm sai số nhạy ở bậc cao, nhưng mỗi output sample vẫn cast float trước bước sau. Cần đo sai số thực tế theo tầng.

<a id="muc-5"></a>

## 5. Phạm vi của crop

Playback dataset được crop 1–6 s để bỏ lead-in đã nghiên cứu. Live mic Monitor lấy onset theo VAD và thu đủ 5 s; CHECK thu trực tiếp 5 s. Hai quy tắc cùng tạo kích thước80.000 nhưng không bảo đảm cùng vị trí sự kiện âm thanh nếu thao tác phát khác nhau.

Đổi hợp đồng đầu vào cần cập nhật Python, generator, C++ và model phù hợp. Nếu chỉ đổi shape trong header mà weights vẫn cũ, việc compile thành công không chứng minh model còn đúng.

