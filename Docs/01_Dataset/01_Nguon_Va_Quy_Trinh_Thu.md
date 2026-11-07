# Nguồn dữ liệu và quy trình thu âm

[Trang chủ tài liệu](../README.md)

## Mục lục

- [1. Phân biệt ba nguồn audio](#muc-1)
- [2. Nhãn và nguồn độc lập](#muc-2)
- [3. Bộ công cụ thu INMP441](#muc-3)
- [4. Thu môi trường](#muc-4)
- [5. Thu playback](#muc-5)
- [6. Đánh giá chất lượng trước khi nhận session](#muc-6)
- [7. Metadata cần giữ](#muc-7)

<a id="muc-1"></a>

## 1. Phân biệt ba nguồn audio

| Nguồn | Vị trí trong AI_Training_Model | Ý nghĩa |
|---|---|---|
| Core gốc | `Dataset_TuThu_v_Kaggle/{asthma,Bronchial,copd,healthy,pneumonia}` | WAV nguồn từ bộ dữ liệu được đưa vào dự án |
| Playback tự thu | `Dataset_TuThu_v_Kaggle/TuThu/Playback_Raw/` | Phát Core qua loa, thu lại bằng INMP441 |
| Môi trường | `Dataset_TuThu_v_Kaggle/TuThu/Record_Env/` | Session phòng, quạt, podcast, lời nói, gõ, vỗ tay |
| Metadata | `Dataset_TuThu_v_Kaggle/TuThu/TKe/` | Log thu, session CSV, biểu đồ và metric |

Các thư mục nguồn giữ WAV chưa phân vào bộ Train/Validation/Test đích. `Out_Split_Session/` là output trung gian đã chia session; `Dataset_Chia_V2/` là bộ dùng cho model hiện hành. WAV bị ignore khi commit; `.gitkeep` giữ layout, vì vậy clone repository chưa đủ để train nếu chưa đặt lại dữ liệu nguồn.

<a id="muc-2"></a>

## 2. Nhãn và nguồn độc lập

Nhãn `0=Asthma`; nhãn `1=Non-Asthma` gom Bronchial, COPD, Healthy, Pneumonia và clip môi trường theo quy hoạch dự án. Không đổi nhãn bệnh lý nguồn chỉ vì nghe nhỏ hoặc model dự đoán sai.

Một Core và hai take playback là cùng nguồn nội dung. Chúng không tạo ba bệnh nhân độc lập. Với môi trường, một session liên tục có thể sinh nhiều clip nhưng các clip vẫn thuộc một nhóm thu. Metadata phải cho phép nối từ clip/take về nguồn này.

Các WAV Kaggle có thể khác sample rate và thời lượng. Chỉ khi vào preprocessing mới áp dụng hợp đồng 16 kHz/5 s. Không mô tả mọi Core nguồn đều đã là PCM16/16 kHz nếu chưa kiểm tra header.

<a id="muc-3"></a>

## 3. Bộ công cụ thu INMP441

Nguồn thực thi nằm tại [ESP32_Read_INMP441](../../ESP32_Standalone_Modules_Test/ESP32_Read_INMP441/README.md).

| Thành phần | Công việc |
|---|---|
| Firmware `src/main.cpp` | Đọc I2S và chuyển luồng PCM ra Serial |
| `record_audio.py` | Thu môi trường, tạo session ID theo dữ liệu hiện có, ghi WAV và log |
| `Record_Playback.py` | Dùng danh sách Core để tổ chức phát/thu các take |
| `Test_Audio.py` | Đo biên độ/RMS và tạo kết quả phân tích |
| `Playback_Source_List.csv` | Bảng đối chiếu ID, source và split |

Định dạng tự thu của pipeline là mono PCM16, 16 kHz. Với 60 giây, số mẫu danh định là 960.000 và phần dữ liệu PCM là 1.920.000 byte, chưa tính WAV header. Không lấy số byte Serial làm thời lượng nếu stream có xen log chữ.

<a id="muc-4"></a>

## 4. Thu môi trường

Trong `record_audio.py`, kiểm tra các biến đầu file như `ENV_NAME`, `RECORD_SECONDS`, `SERIAL_PORT`, `BAUD_RATE`. Source hiện dùng cổng ví dụ COM11 và 460800 baud; cần chọn đúng thiết bị của máy thu.

Trình tự:

1. Nạp firmware thu Serial và đóng Serial Monitor đang giữ cổng.
2. Giữ dây, gain và vị trí micro ổn định; ghi lại điều kiện thu.
3. Chọn loại môi trường và thời lượng; chạy script bằng môi trường Python có dependencies.
4. Script tạo WAV dưới `TuThu/Record_Env/<loại>/` và cập nhật `TKe/Env_session.csv`.
5. Nghe thử, kiểm tra thời lượng và metric bằng `Test_Audio.py`.
6. Nếu thu lại, lưu rõ bản nào thay thế bản lỗi; tránh giữ hai bản gần như trùng nhau ở hai split.

Session ID có thể nhảy từ 05 đến 06; số ID không quyết định số session hợp lệ. Cần đếm các bản thu được chấp nhận trong manifest.

<a id="muc-5"></a>

## 5. Thu playback

Bộ hiện có được tổ chức 40 source Asthma × 2 take và 40 source Non-Asthma × 2 take. Nhóm Non-Asthma lấy 10 nguồn mỗi loại trong bốn nhóm Core. Danh sách nguồn do `01_Random_Playback.py` chọn và lưu lại.

Theo [README Playback](../../AI_Training_Model/Dataset_TuThu_v_Kaggle/TuThu/Playback_Raw/README.md), tiêu chí nguồn là thời lượng ít nhất 4,5 s, peak PCM16 ít nhất 5.000, RMS ít nhất 1.000 và clipping không quá 0,5%. Đây là điều kiện chọn WAV để phát, không bảo đảm mức âm tại micro chắc chắn vượt VAD.

Quy trình thực tế phải cố định loa, khoảng cách, gain và âm lượng trong một đợt thu. Tên take theo mẫu `<source_id>__<source_stem>__take01.wav`. Take02 là lần thu riêng; lỗi cần thu lại đúng ID/take để bảo toàn đối chiếu.

Lead-in của bộ playback hiện được xử lý bằng crop 1–6 s trong Python. Việc cắt này là quy ước của bộ dữ liệu đã thu; không tự cắt mất 1 giây trên mọi tín hiệu live mic.

<a id="muc-6"></a>

## 6. Đánh giá chất lượng trước khi nhận session

| Chỉ số | Dùng để phát hiện | Điều chưa thể kết luận |
|---|---|---|
| RMS/MAV | Quá nhỏ, thay đổi mức thu | Đúng nhãn bệnh lý |
| Peak | Xung lớn và khoảng biên độ | Có đủ thông tin hô hấp |
| Clipping ratio | Bão hòa ADC/PCM | Mọi dạng méo của loa |
| Active ratio | Quá ít block có hoạt động | Hoạt động đó là ho hay tiếng nói |
| Waveform/Log-Mel | Khoảng lặng, discontinuity, thay đổi phổ | Accuracy của model |

Phải đo trên PCM trước peak normalization. Sau khi chia theo peak, một file nhiễu cực nhỏ cũng có thể lên biên độ gần 1 và che mất dấu hiệu “thu quá yếu”.

<a id="muc-7"></a>

## 7. Metadata cần giữ

Tối thiểu nên có `file_path, session_id/source_id, take_id, subtype, sample_rate, duration, device, gain, distance, volume, note`. Những thông tin chưa được script tự ghi có thể ghi vào cột note hoặc nhật ký thu; không tự suy ra sau này.

Lưu riêng lỗi thu và dữ liệu được chấp nhận. Khi dùng tập calibration cho ngưỡng Quality/VAD, cần một tập validation khác phiên thu; không dùng accuracy model để gán PASS/REJECT cho chất lượng âm thanh.

Đọc tiếp [chia tập và augmentation](02_Chia_Tap_Tang_Cuong_Truy_Vet.md).

