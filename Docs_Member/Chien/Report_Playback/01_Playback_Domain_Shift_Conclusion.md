# Kết luận về Playback Domain Shift

## 1. Mục tiêu kiểm tra

Mục tiêu của phép thử playback là kiểm tra mức độ ổn định của mô hình V1 khi âm thanh không được đưa trực tiếp từ WAV vào pipeline Python, mà đi qua đường thu thực tế:

```text
WAV gốc
→ loa laptop
→ không khí
→ INMP441
→ ESP32-S3
→ DSP
→ V1 PTQ INT8
```

Playback chỉ là một cách **mô phỏng đường thu qua microphone**, không hoàn toàn tương đương với âm hô hấp thật từ cơ thể.

### 1.1. Các khái niệm sử dụng trong đánh giá

- **Domain (miền dữ liệu):** kiểu dữ liệu và điều kiện tạo ra dữ liệu mà model nhìn thấy. Hai tín hiệu có cùng nội dung bệnh lý nhưng đi qua hai chuỗi thu khác nhau vẫn có thể thuộc hai domain khác nhau.
- **Proxy (đại diện thay thế):** dữ liệu được dùng để mô phỏng gần đúng một điều kiện thực tế khi chưa thể thu trực tiếp điều kiện đó. Playback qua loa rồi thu lại bằng INMP441 là proxy cho việc âm hô hấp thật đi qua microphone.
- **Acoustic path / đường truyền acoustic:** toàn bộ đường truyền âm thanh vật lý trước khi tới microphone, gồm nguồn phát, loa, không khí, phản xạ phòng, khoảng cách, hướng, đáp tuyến tần số, nhiễu nền và microphone.

Có thể biểu diễn ba domain chính như sau:

```text
Domain A — Digital / Raw
WAV gốc
→ preprocessing
→ model

Domain B — Playback acoustic
WAV gốc
→ loa
→ không khí / phòng
→ INMP441
→ preprocessing
→ model

Domain C — Real deployment
Âm hô hấp thật từ người
→ không khí
→ INMP441
→ preprocessing
→ model
```

Domain B được tạo ra có chủ đích để mô phỏng gần hơn quá trình thu qua microphone so với việc chỉ dùng WAV digital. Tuy nhiên, Domain B vẫn không phải Domain C vì nó có thêm ảnh hưởng riêng của loa và điều kiện playback.

### 1.2. Vì sao cùng một WAV có thể tạo ra đặc trưng khác sau playback?

Có thể hiểu đơn giản theo mô hình:

```text
WAV gốc
→ đặc trưng A

WAV gốc
→ loa → không khí → INMP441
→ đặc trưng B
```

Nếu tín hiệu đi trực tiếp từ WAV vào preprocessing, model nhìn thấy đặc trưng `A`.

Khi cùng WAV đó được phát lại qua loa rồi thu bằng INMP441, đường truyền acoustic có thể làm thay đổi:

- năng lượng tương đối giữa các dải tần;
- đáp tuyến tần số;
- transient;
- mức noise;
- phản xạ và cộng hưởng phòng;
- biên độ tương đối của các thành phần quan trọng.

Khi đó model không còn nhìn thấy đúng `A`, mà nhìn thấy một biến thể `B`. Nếu `B` lệch đủ xa so với phân bố mà model đã học, `p_non_asthma` có thể tăng mạnh dù nhãn thật của file vẫn là Asthma.

Điều này **không có nghĩa playback làm hỏng model**. Ngược lại, việc đưa playback vào Dataset V2 là một cách để model được nhìn thấy thêm một phần của domain microphone/acoustic thay vì chỉ học trên WAV digital.

```text
Train chỉ raw:
model chủ yếu học Domain A

Train raw + playback:
model học Domain A
+
một phần Domain B
```

Bạn có thể xem về sự so sánh của tôi thực hiện tại đây
- [So sánh offset](/ESP32_Standalone_Modules_Test/Asthma_Playback_Calibration/calibration_results/offset_analysis/)
- [Model train không có Playback](/AI_Training_Model/Phase2_Preprocess_&_Traning/Output_Train_V3_V1_No_Playback/)

Vì chưa có đủ dữ liệu hô hấp thật thu trực tiếp qua đúng INMP441, playback là một lựa chọn proxy hợp lý. Tuy nhiên, nó chỉ giúp **thu hẹp khoảng cách giữa digital domain và microphone domain**, chứ không thể thay thế hoàn toàn dữ liệu real deployment.

### 1.3. Playback giúp model học những đặc tính acoustic 

Dataset V2 bổ sung một lượng nhỏ playback nhằm giúp model không chỉ học trên raw digital domain mà còn tiếp xúc với một phần biến đổi do acoustic path và INMP441 gây ra.
- Playback là proxy cho microphone acquisition domain, không phải dữ liệu hô hấp thực hoàn chỉnh.
- Việc giữ playback ở tỷ lệ nhỏ giúp duy trì raw-domain là thành phần chính của dataset, đồng thời bổ sung robustness với acoustic acquisition. 

Tuy nhiên, việc tỷ lệ nhỏ này có thực sự “ngăn model bias về playback” chưa được chứng minh trực tiếp, nên chỉ nên mô tả đó là mục đích thiết kế, không phải kết luận thực nghiệm.

---

## 2. Những gì đã xác minh

### 2.1. Không phải lỗi model hoặc cách tính `p_non_asthma`

Model triển khai trên ESP32 là đúng V1 PTQ INT8:

- model size: `543,976 bytes`;
- input INT8: scale `0.003921569`, zero-point `-128`;
- output INT8: scale `0.00390625`, zero-point `-128`.

Khi cùng một buffer PCM 5 giây được:

1. ESP32 chạy DSP + inference;
2. gửi về PC;
3. Python chạy lại đúng preprocessing + V1 PTQ;

thì hai phía cho kết quả gần nhau.

Do đó, hiện tượng `p_non_asthma` tăng cao sau playback **không xuất phát chủ yếu từ lỗi inference trên ESP32**.

### 2.2. Temporal shift do VAD không phải nguyên nhân chính

Cross-correlation cho thấy VAD có thể bắt đầu cửa sổ tại các offset khác nhau.

Tuy nhiên, khi WAV gốc được crop đúng theo các offset đã đo rồi chạy lại bằng Python:

- Asthma 01: shifted-original vẫn có `p_non_asthma ≈ 0`;
- Asthma 02: shifted-original mean ≈ `0.005`;
- Asthma 03: shifted-original mean ≈ `0.001`.

Trong khi đó, capture thật qua loa → INMP441 của Asthma 01 và 02 lại tăng rất mạnh.

Vì vậy:

> **VAD/window alignment có tồn tại sai lệch, nhưng không giải thích được hiện tượng `p_non_asthma` tăng mạnh.**

---

## 3. Kết quả quan trọng nhất

Ba WAV Asthma kiểm tra cho thấy hành vi khác nhau:

```text
Asthma 01
Raw/shifted-original → p_non gần 0
Playback capture     → p_non tăng mạnh (~0.58–0.96)

Asthma 02
Raw/shifted-original → p_non gần 0
Playback capture     → p_non tăng mạnh (~0.54–0.91)

Asthma 03
Raw/shifted-original → p_non gần 0
Playback capture     → p_non vẫn thấp (~0.04–0.19)
```

Điều này cho thấy:

> **Đường truyền acoustic `loa → không khí → INMP441` có thể làm thay đổi đặc trưng âm thanh theo từng sample.**

Không phải mọi Asthma playback đều bị lỗi. Một số WAV có đặc trưng Asthma đủ mạnh và vẫn được nhận đúng sau playback, trong khi một số WAV khác nhạy với biến đổi acoustic.

---

## 4. Ý nghĩa đối với hệ thống

Playback tạo thành một domain riêng:

```text
Domain 1: Raw / digital WAV
Domain 2: WAV → loa → không khí → INMP441
Domain 3: Âm hô hấp thật → không khí → INMP441
```

Domain 2 gần với quá trình thu thực tế hơn raw digital vì có microphone và môi trường, nhưng vẫn chứa thêm ảnh hưởng của:

- đáp tuyến loa;
- méo loa;
- volume;
- khoảng cách và hướng;
- phòng;
- noise nền;
- đặc tính riêng của session playback.

Vì vậy:

> **Playback là proxy cho real microphone domain, không phải bản sao của âm hô hấp thật.**

Điểm cần phân biệt rõ:

```text
Raw WAV
≠ Playback qua loa → INMP441
≠ Âm hô hấp thật → INMP441
```

Playback được đưa vào Dataset V2 vì đây là cách thực tế để một WAV đã biết nhãn đi qua chính microphone INMP441 và tạo ra dữ liệu gần với acquisition domain hơn. Tuy nhiên, nó đồng thời tạo thêm một biến thể domain do chính loa và môi trường playback.

Do đó, khi một số Asthma playback có `p_non_asthma` tăng cao, điều hợp lý nhất là xem đây là dấu hiệu của **acoustic/domain shift**, không phải bằng chứng rằng nhãn Asthma sai hoặc model bị đảo nhãn toàn cục.

Không nên dùng một vài kết quả playback để kết luận trực tiếp rằng model sẽ thất bại với âm hô hấp thật.

---

## 5. Liên hệ với Dataset V2

Dataset V2 có playback không phải vì playback được xem là dữ liệu thực tế hoàn hảo, mà vì đây là một cách để đưa một phần biến đổi của microphone/acoustic path vào quá trình học.

Ý tưởng của Dataset V2 là:

```text
Raw disease WAV
        +
Playback-captured WAV qua INMP441
        ↓
model nhìn thấy cả digital domain
và một phần microphone/acoustic domain
```

Thí nghiệm so sánh model có playback và không playback cho thấy đây là một trade-off:

- model không playback tốt hơn trên common raw test;
- model có playback tốt hơn rõ rệt trên playback-only test;
- Asthma Recall trên raw không giảm trong phép so sánh khóa test;
- playback giúp model học được một phần robustness với acoustic acquisition.

Tuy nhiên, playback chỉ đại diện cho các điều kiện playback đã xuất hiện trong dataset. Một session playback mới, loa khác, volume khác hoặc điều kiện phòng khác vẫn có thể tạo ra một biến thể domain mới.

Vì vậy, Dataset V2 được giữ như baseline hợp lý cho prototype, nhưng không được diễn giải rằng model đã robust với mọi tín hiệu thu qua microphone.

---

## 6. Ý nghĩa của vùng `UNSURE`

Vùng hậu xử lý hiện tại có ý nghĩa rõ hơn sau phép thử này.

Ví dụ với:

```text
LOW  = 0.20–0.25
HIGH = 0.95
```

các Asthma playback bị acoustic shift lên `p_non_asthma ≈ 0.5–0.9` sẽ rơi vào:

```text
UNSURE
```

thay vì bị kết luận chắc chắn thành `NON-ASTHMA`.

`UNSURE` vì vậy đóng vai trò **safety margin khi gặp tín hiệu lệch domain hoặc không đủ tin cậy**.

---

## 7. Quyết định cho demo

Vì playback không ổn định theo từng sample, demo phải chọn WAV có kiểm chứng trước.

Quy trình demo nên là:

```text
1. Chọn WAV Asthma đã test qua đúng loa + INMP441.
2. Phát mỗi WAV ít nhất 3 lần.
3. Chỉ dùng WAV có p_non_asthma ổn định và nằm rõ phía ASTHMA.
4. Giữ cố định loa, volume, khoảng cách và hướng mic.
5. Không chỉnh threshold chỉ để làm một WAV playback cụ thể cho kết quả đẹp.
```

Asthma 03 hiện là ví dụ tốt hơn Asthma 01/02 cho demo playback.

---

## 8. Kết luận cuối

- Không có bằng chứng cho thấy pipeline C++/TFLM là nguyên nhân chính.
- VAD/window shift không phải nguyên nhân chính.
- Nguyên nhân nổi bật là **acoustic domain shift qua loa → INMP441**.
- Cùng một WAV có thể tạo đặc trưng khác sau playback vì đường truyền acoustic biến đổi tín hiệu trước khi tới microphone.
- Playback tạo thành một domain riêng và chỉ là **proxy** cho real microphone domain.
- Việc đưa playback vào Dataset V2 là hợp lý để model học thêm một phần microphone/acoustic domain, không phải vì playback được coi là dữ liệu thực tế hoàn hảo.
- Mức ảnh hưởng của playback phụ thuộc từng sample và từng điều kiện acoustic.
- Playback không đại diện hoàn toàn cho âm hô hấp trực tiếp từ người thật.
- Final V1 không nên được tối ưu riêng cho loa laptop.
- Khi demo playback, cần **chọn WAV đã được xác minh trước**.
- Ngưỡng prototype nên được mô tả là ngưỡng vận hành của Final V1; deployment thực tế cần calibration lại bằng dữ liệu thu trực tiếp qua INMP441.
- Nghiên cứu robustness với nhiều loa, khoảng cách, môi trường hoặc dữ liệu thu trực tiếp từ người thật nên được đưa sang phần mở rộng.
