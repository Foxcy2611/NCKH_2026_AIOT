# ĐÁNH GIÁ TỔNG QUÁT CÁC WAV MÔI TRƯỜNG 1 PHÚT

Ngày tổng hợp: 04/10/2026

## 1. Phạm vi đánh giá

Báo cáo này đánh giá **32 phiên môi trường tự thu mới**, mỗi phiên dài 60 giây, dựa trên:

- Danh sách phiên trong `Env_session.csv`.
- Các chỉ số trong `Phan_Tich/*_metrics.csv`.
- Hình dạng tín hiệu trong `Phan_Tich/*_waveform.png`.

Ba file master cũ dài 5 phút (`podcast_5min.wav`, `key_fan_5min.wav`, `silence_5min.wav`) không được tính vào thống kê 1 phút. File `silence_5min.wav` chỉ nên phục vụ kiểm tra chất lượng âm thanh, phát hiện âm thanh và tăng cường dữ liệu; không coi là một mẫu bệnh `Non-Asthma` thông thường.

## 2. Kết luận nhanh

- Đã có đủ **32/32 file WAV 1 phút** và đủ **32/32 bộ CSV + PNG phân tích**.
- Cả 32 file đều đúng định dạng: mono, PCM16, 16 kHz và đủ 60 giây.
- Cả 32 file đều được công cụ hiện tại kết luận `AUDIO_OK`.
- Không file nào bị cắt đỉnh: tỷ lệ clipping của toàn bộ file bằng 0%.
- Không thấy dấu hiệu file trống hoàn toàn hoặc hỏng dữ liệu.
- Các nhóm có sự khác biệt biên độ và mật độ âm thanh rõ ràng, phù hợp mục tiêu tạo dữ liệu môi trường đa dạng.
- Bộ WAV này **đủ điều kiện giữ lại làm nguồn thô cho Dataset V2**. Tuy nhiên, khi cắt thành đoạn 5 giây phải kiểm tra theo từng loại âm thanh; không được coi mọi đoạn cắt ra đều tự động hợp lệ.

> `AUDIO_OK` chỉ có nghĩa file vượt các ngưỡng kiểm tra hiện tại (`RMS >= 20`, tỷ lệ block hoạt động `>= 1%`, clipping `<= 1%`). Đây chưa phải bằng chứng rằng mọi đoạn 5 giây trong file đều hữu ích cho huấn luyện.

## 3. Thống kê theo nhóm

Các giá trị Peak và RMS bên dưới được đo trực tiếp trên PCM16, không chuẩn hóa biên độ trước khi đo.

| Nhóm | Số phiên | Peak nhỏ nhất–lớn nhất | RMS nhỏ nhất–lớn nhất | RMS trung bình | Tỷ lệ hoạt động | Nhận xét |
|---|---:|---:|---:|---:|---:|---|
| `podcast` | 5 | 599–1532 | 85.52–266.75 | 173.59 | 66.24–81.97% | Có lời nói và khoảng nghỉ tự nhiên; biên độ đa dạng |
| `fan` | 5 | 5194–8222 | 487.29–919.57 | 744.76 | 99.79–99.81% | Tín hiệu liên tục, ổn định, đúng đặc trưng tiếng quạt |
| `clap` | 6 | 16957–27794 | 181.08–871.15 | 528.63 | 12.08–99.81% | Các xung vỗ tay rõ, không clipping; cần cắt theo sự kiện |
| `knock` | 5 | 417–4751 | 37.17–165.23 | 83.48 | 20.03–39.89% | Có các cụm tiếng gõ; phiên 04–05 khá nhẹ nhưng vẫn có cấu trúc |
| `room_noise` | 6 | 387–19785 | 27.93–241.06 | 119.03 | 19.71–99.20% | Rất đa dạng từ phòng yên đến nhiễu/xung mạnh |
| `speech` | 5 | 1038–1980 | 109.84–148.61 | 135.25 | 56.00–72.29% | Khá đồng đều, có lời nói xen khoảng nghỉ |

Tổng số: **32 phiên = 32 phút âm thanh môi trường mới**.

## 4. Đánh giá chi tiết

### 4.1. Podcast

- Năm phiên đều có dạng lời nói liên tục xen khoảng nghỉ, không có clipping.
- `podcast_session_02` và `podcast_session_03` mạnh nhất nhóm.
- `podcast_session_05` nhẹ nhất với Peak 599 và RMS 85.52, nhưng hình sóng vẫn thể hiện nhiều cụm lời nói rõ ràng; không nên loại chỉ vì âm lượng thấp.
- Sự khác biệt mức âm giữa các phiên có ích để mô hình bớt phụ thuộc vào một khoảng cách hoặc âm lượng cố định.

Ảnh đại diện: [podcast_session_02](Phan_Tich/podcast_session_02_waveform.png), [podcast_session_05](Phan_Tich/podcast_session_05_waveform.png).

### 4.2. Quạt

- Đây là nhóm ổn định nhất: cả năm phiên có tỷ lệ hoạt động gần 100% và không bị cắt đỉnh.
- RMS thay đổi từ 487.29 đến 919.57, cho thấy đã có độ mạnh khác nhau giữa các phiên thay vì sao chép cùng một điều kiện.
- Có thể cắt liên tục theo cửa sổ 5 giây vì tiếng quạt hiện diện gần như toàn phiên.

Ảnh đại diện: [fan_session_03](Phan_Tich/fan_session_03_waveform.png).

### 4.3. Vỗ tay

- Sáu phiên có các xung ngắn, mạnh, phân bố theo từng cụm; Peak cao nhưng không có clipping.
- `clap_session_06` nhẹ và thưa nhất, có ích như một trường hợp khó.
- `clap_session_05` đã được bổ sung đầy đủ CSV và PNG. File có Peak 25526, RMS 862.93, không clipping; hình sóng cho thấy nhiều cụm vỗ tay rõ.
- Tỷ lệ hoạt động 99.81% của `clap_session_05` không có nghĩa tiếng vỗ tay kéo dài toàn bộ 60 giây. Nền tín hiệu của phiên này đã vượt ngưỡng block rất thấp (`20 PCM`), vì vậy chỉ số Active bị đẩy lên cao. Khi chọn đoạn cần nhìn sự kiện thực tế thay vì chỉ dựa vào Active.
- Không nên cắt mù toàn bộ thời gian rồi gán mọi đoạn là vỗ tay, vì các khoảng giữa hai cụm có thể chủ yếu là tiếng nền.

Ảnh đại diện: [clap_session_03](Phan_Tich/clap_session_03_waveform.png), [clap_session_05](Phan_Tich/clap_session_05_waveform.png), [clap_session_06](Phan_Tich/clap_session_06_waveform.png).

### 4.4. Tiếng gõ

- `knock_session_01` đến `knock_session_03` có các cụm tiếng gõ tương đối rõ.
- `knock_session_04` và đặc biệt `knock_session_05` có biên độ thấp. Riêng phiên 05 có Peak 417 và RMS 37.17, nhưng hình sóng vẫn thấy các cụm lặp lại nên chưa có lý do để loại file gốc.
- Hai phiên nhẹ nên được giữ làm mẫu môi trường khó/xa micro. Khi cắt 5 giây phải bảo đảm đoạn được chọn có tiếng gõ, tránh lấy nhầm khoảng yên hoàn toàn.

Ảnh đại diện: [knock_session_03](Phan_Tich/knock_session_03_waveform.png), [knock_session_05](Phan_Tich/knock_session_05_waveform.png).

### 4.5. Nhiễu phòng

- Đây là nhóm có độ biến thiên lớn nhất, đúng với mục tiêu mô tả môi trường thực tế không đồng nhất.
- `room_noise_session_02` có hoạt động gần như liên tục và một số xung lớn, nhưng không clipping.
- `room_noise_session_01` và `room_noise_session_06` khá yên; phiên 06 có RMS 27.93 và Peak 387. Hình sóng vẫn có thay đổi theo thời gian nên không phải file rỗng.
- Những cửa sổ 5 giây gần im lặng không nên tự động đưa hết vào lớp `Non-Asthma`; chúng cần đi qua quy tắc kiểm tra chất lượng/phát hiện âm thanh hoặc được đánh dấu riêng.

Ảnh đại diện: [room_noise_session_02](Phan_Tich/room_noise_session_02_waveform.png), [room_noise_session_06](Phan_Tich/room_noise_session_06_waveform.png).

### 4.6. Lời nói trực tiếp

- Năm phiên có RMS tương đối đồng đều, từ 109.84 đến 148.61.
- Hình sóng có lời nói xen khoảng nghỉ tự nhiên; `speech_session_03` và `speech_session_04` hoạt động nhiều nhất.
- Nhóm này phù hợp làm mẫu gây nhiễu khó để hạn chế việc mô hình nhầm tiếng nói hoặc tiếng thở thông thường thành Asthma.

Ảnh đại diện: [speech_session_03](Phan_Tich/speech_session_03_waveform.png).

## 5. Các file cần lưu ý khi tạo đoạn 5 giây

| File/nhóm | Trạng thái | Cách xử lý đề xuất |
|---|---|---|
| `podcast_session_05.wav` | Âm nhẹ hơn các podcast còn lại | Giữ; kiểm tra đoạn 5 giây có lời nói rõ |
| `clap_session_05.wav` | Active 99.81% do nền vượt ngưỡng thấp | Giữ; chọn theo vị trí xung vỗ tay, không dựa riêng vào Active |
| `clap_session_06.wav` | Vỗ tay nhẹ và thưa | Giữ làm mẫu khó; tránh các đoạn không có sự kiện |
| `knock_session_04.wav` | Tiếng gõ nhẹ | Giữ; chọn đoạn có cụm gõ |
| `knock_session_05.wav` | Nhẹ nhất nhóm gõ | Giữ làm mẫu xa/nhẹ; nghe lại các đoạn sau khi cắt |
| `room_noise_session_01.wav` | Phòng khá yên | Giữ; tách đoạn quá yên khỏi dữ liệu đưa trực tiếp vào bộ phân loại |
| `room_noise_session_06.wav` | Gần im lặng ở nhiều khoảng | Giữ file gốc; sàng lọc kỹ từng đoạn 5 giây |

Các mục trên là **cần lưu ý**, không phải danh sách file lỗi.

## 6. Quy tắc dùng cho Dataset V2

1. Giữ nguyên toàn bộ WAV gốc; không chuẩn hóa Peak và không ghi đè file trước khi chia dữ liệu.
2. Chia theo `session_id` thành Train/Validation/Test **trước khi cắt 5 giây hoặc tăng cường dữ liệu**.
3. Mọi đoạn sinh ra từ cùng một session phải nằm trong cùng một tập để tránh rò rỉ họ hàng.
4. Với `fan`, `podcast` và `speech`, có thể dùng cửa sổ 5 giây liên tiếp, sau đó vẫn kiểm tra chất lượng từng đoạn.
5. Với `clap` và `knock`, nên chọn cửa sổ bao quanh sự kiện; không lấy hàng loạt khoảng yên nằm giữa các cụm.
6. Với `room_noise`, giữ tính đa dạng tự nhiên nhưng tách các đoạn gần im lặng ra khỏi dữ liệu phân loại thông thường.
7. Các tên `fan`, `clap`, `knock`, `room_noise`, `speech`, `podcast` là nhãn mô tả nguồn âm. Khi huấn luyện nhị phân, chúng mới được gom vào phía `Non-Asthma` theo danh sách đã duyệt.

## 7. Hạn chế của lần đánh giá này

- Báo cáo mới đánh giá định dạng, thời lượng, biên độ theo thời gian, RMS, tỷ lệ hoạt động và clipping.
- Chưa đánh giá đầy đủ nội dung theo miền tần số hoặc mức giống với tiếng thở/khò khè Asthma.
- Ngưỡng Active hiện tại rất nhạy, thể hiện rõ ở `clap_session_05`; vì vậy Active chỉ là chỉ số tham khảo.
- `Env_session.csv` hiện chủ yếu ghi chú chung. Nếu còn nhớ điều kiện thu, nên bổ sung khoảng cách micro, vị trí, mức loa/quạt và đặc điểm căn phòng để việc phân tích sau này rõ hơn.

## 8. Kết luận cuối

Bộ 32 WAV môi trường tự thu 1 phút có chất lượng kỹ thuật tốt, không clipping, không hỏng định dạng và có độ đa dạng thực tế. Có thể **chốt giai đoạn thu nguồn môi trường hiện tại và chuyển sang bước chia session/cắt đoạn cho Dataset V2**. Việc cần kiểm soát ở bước kế tiếp không phải loại hàng loạt file nhẹ, mà là bảo đảm từng đoạn 5 giây thật sự chứa nội dung mong muốn và không để các đoạn cùng session rơi vào nhiều tập khác nhau.
