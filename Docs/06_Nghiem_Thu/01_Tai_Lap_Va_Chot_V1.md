# Tái lập và nghiệm thu bản cuối

[Trang chủ tài liệu](../README.md)

## Mục lục

- [1. Mục tiêu và trạng thái tài liệu](#muc-1)
- [2. Định danh model trước mọi phép đo](#muc-2)
- [3. Những cấu hình phải kiểm tra lại](#muc-3)
- [4. Tầng 1 - Static inference](#muc-4)
- [5. Tầng 2 - Preprocess C++ từ PCM cố định](#muc-5)
- [6. Tầng 3 - Live mic, onset và domain](#muc-6)
- [7. Chốt Quality Gate, VAD và threshold](#muc-7)
- [8. Ma trận nghiệm thu Node](#muc-8)
- [9. Ma trận nghiệm thu end-to-end](#muc-9)
- [10. Hồ sơ bàn giao tối thiểu](#muc-10)

<a id="muc-1"></a>

## 1. Mục tiêu và trạng thái tài liệu

Đây là checklist cần thực hiện với bản firmware/model chốt, không phải phiếu xác nhận đã PASS. Lần xây bộ tài liệu chỉ đọc source/artifact và viết Markdown; không chạy train, preprocess, inference, build hay upload.

Nguồn lịch sử: [step_done_V1.md](../../Docs_Member/Chien/step_done_V1.md). Không đánh dấu checklist lịch sử hoàn tất chỉ vì đã thay model.

<a id="muc-2"></a>

## 2. Định danh model trước mọi phép đo

| Thuộc tính | Artifact được chọn |
|---|---|
| Trial | `combo_pre0_mel40_fft2048__V1__s44` |
| Kiến trúc | V1 SepConv2D + Flatten |
| Dataset | Dataset_Chia_V2 |
| Lượng tử | QAT_INT8 |
| TFLite size | 347.968 byte |
| SHA-256 TFLite | `d081c1cfcd873c4e2182f9d9e0f8aff07a69ea0b041cf0d6d845d3222efc46b9` |
| Input | INT8 [1,40,129,1] |
| Input scale / zero point | 0.003921568859368563 / -128 |
| Output | INT8 [1,1], p_non sau giải lượng tử |
| Output scale / zero point | 0.00390625 / -128 |
| Mel normalization | Train min -80, max 0 |
| Header runtime | `Asthma_Model.h`, mảng `model_data` |

Nguồn bàn giao: [AI_Model/README.md](../../Final_Project_NCKH/AI_Model/README.md). Hash header text khác hash TFLite bytes vì header có tên biến/comment/định dạng; khi đối chiếu phải so phần byte model hoặc file TFLite.

<a id="muc-3"></a>

## 3. Những cấu hình phải kiểm tra lại

| Thành phần | Quan sát hiện tại | Việc cần làm |
|---|---|---|
| Static profiling | Selector đang là model ID 5 | Đổi đúng selector/model cần đo trước upload |
| LiveMic test | Chế độ raw PCM header được bật mặc định | Chọn header hoặc mic đúng mục tiêu test |
| Node / 3_Complete arena | 192 KiB được cấp; profiling C4 used 169.380 B | Xác nhận AllocateTensors, chạy lặp và biên RAM trên firmware cuối |
| Node classification | 0,47 / 0,77 | Đối chiếu đúng threshold C4 đã freeze |
| 3_Complete classification | 0,47 / 0,77 | Giữ đồng bộ với Node khi dùng làm bản đối chiếu |
| Quality Gate Node | JSON FROZEN: RMS20, active1%, clipping1%, block-MAV20 | Xác nhận source đúng JSON và lưu test phần cứng |
| VAD | JSON FROZEN: MAV75, 4 chunk ×256 mẫu | Xác nhận source đúng JSON; tiếp tục báo false trigger/miss theo miền thật |
| Gateway alert | Asthma và score >=0.80 | Kiểm tra đồng nhất chính sách với Node/vote |
| Phase4 generator | Có tham chiếu cấu hình lượng tử Phase3 | Kiểm tra lại model/normalize trước tạo header tham chiếu mới |

Các mục này không được tự suy diễn từ tên file. Đây là điểm bàn giao để tránh vô tình đo F0/V5 hoặc reference model cũ rồi ghi thành kết quả C4 s44.

<a id="muc-4"></a>

## 4. Tầng 1 - Static inference

Project: [1_Test_Model_Static_Profiling](../../Deploy_Model/1_Test_Model_Static_Profiling/).

- Dùng tensor reference tạo từ đúng hợp đồng Mel/normalize.
- Kiểm tra model checksum, input/output shape/type/scale/zp.
- Ghi resolver operators, arena capacity/used, PSRAM/internal placement.
- Tách thời gian init/AllocateTensors khỏi thời gian Invoke.
- Warm-up trước khi ghi min/max/mean/std; ghi số lần lặp.
- Kiểm tra output INT8 và p_non với Python TFLite trên cùng tensor.

Nếu tensor đã giống nhau mà output khác lớn, tập trung TFLM/operator/quantization/model, không sửa I2S hay VAD.

<a id="muc-5"></a>

## 5. Tầng 2 - Preprocess C++ từ PCM cố định

Project: [2_Test_Model_LiveMic](../../Deploy_Model/2_Test_Model_LiveMic/).

Đưa cùng 80.000 mẫu PCM16 vào Python và firmware. So các tầng: normalize, bandpass, FFT2048 power, Mel40, Log-Mel, min-max, INT8 input và p_non. C4 không có tầng pre-emphasis. Với mỗi tầng ghi max absolute error, mean absolute error, RMSE; thêm tỷ lệ byte input khác và số phần tử lệch nhiều mức lượng tử.

Không so trực tiếp WAV gốc với một bản thu qua loa rồi quy mọi khác biệt cho float32. Loa, phòng, mic, gain và cửa sổ tạo sai khác vật lý khác với sai số số học.

Xem [quy trình kiểm chứng chuyên sâu](../03_Preprocess_CPP/07_Kiem_Chung_Python_CPP.md).

<a id="muc-6"></a>

## 6. Tầng 3 - Live mic, onset và domain

Project: [3_Model_Complete](../../Deploy_Model/3_Model_Complete/) và bộ calibration tại [Asthma_Playback_Calibration](../../ESP32_Standalone_Modules_Test/Asthma_Playback_Calibration/).

| Phép thử | Dữ liệu cần giữ |
|---|---|
| Thu cùng nguồn nhiều lần | WAV gốc, capture, điều kiện loa/mic |
| Kiểm tra onset | Offset correlation, chất lượng correlation, độ biến thiên giữa lần |
| Shifted original | Cùng crop 5 s theo offset capture |
| So inference | p_non original, shifted-original, capture Python, ESP32 |
| Kiểm tra mức âm | PCM RMS, peak, clipping, active ratio |
| Hiệu năng toàn pipeline | Capture, DSP, Invoke và tổng thời gian riêng |

Kết luận phải có điều kiện: nếu original dịch crop vẫn đúng nhưng capture sai, chênh lệch nhiều khả năng liên quan domain loa–mic; nếu cả original dịch crop cũng sai, temporal sensitivity góp phần. Correlation kém không đủ để khẳng định chính xác offset.

<a id="muc-7"></a>

## 7. Chốt Quality Gate, VAD và threshold

### Quality Gate

Quality Gate đã freeze trong `02_Quality_Check/results/final_quality_gate.json`. PASS/REJECT dựa trên PCM trước DSP và định nghĩa chất lượng thu, không dựa vào model đoán đúng hay sai.

Các nhóm gồm normal, nhỏ nhưng dùng được, silence, too quiet, clipping, ít hoạt động. Khi tái lập, phải giữ nguyên calibration/test provenance; không retune bằng Test. Báo cáo false reject/false accept, không chỉ accuracy tổng.

### VAD/onset

VAD đã freeze trong `03_VAD_Trigger/results/final_vad_trigger.json` ở MAV75 và4 chunk liên tiếp. Khi nghiệm thu phần cứng vẫn đo kích hoạt giả, bỏ sót, delay từ onset và tính liền mạch của cửa sổ trên miền thật. Ngưỡng VAD không phải ngưỡng phân loại Asthma.

### Classification

Chọn LOW/HIGH trên validation theo mục tiêu false negative/false positive và tỷ lệ Unsure. Cần định nghĩa rõ score của Unsure. Model output lượng tử có bước 1/256; ngưỡng phải được kiểm tra theo luật so sánh thực tế trong firmware.

Test đã dùng ở các bước D/E chỉ được gọi là tập đánh giá đã có lịch sử truy cập; không tuyên bố đó là một tập hoàn toàn chưa từng xem để chứng minh lựa chọn mới.

<a id="muc-8"></a>

## 8. Ma trận nghiệm thu Node

| Mã | Tình huống | Mong đợi |
|---|---|---|
| N01 | Boot không có mic | Không READY, OLED/log báo lỗi |
| N02 | Boot có mic đúng | READY; không yêu cầu hot-plug |
| N03 | CHECK audio tốt | Đủ 80.000 mẫu, quality và AI có kết quả |
| N04 | CHECK silence/clipping | Reject đúng lý do, không coi là class bệnh |
| N05 | CHECK đo PPG có tay | Kết quả hợp lệ trong deadline hoặc báo invalid rõ |
| N06 | CHECK không tay/FIFO thiếu | Timeout, valid=0 và HR/SpO2=0, không NaN |
| N07 | Bỏ vitals | Audio giữ lại và packet vẫn đúng |
| N08 | MONITOR 3 vote | Đúng đa số; score chỉ trung bình class thắng |
| N09 | MONITOR A/N/U | Unsure do hòa, score 0 |
| N10 | MONITOR quality reject | Không tính thành vote |
| N11 | Một lần bấm MONITOR | Không tự bật rồi tắt do cùng lần nhấn |
| N12 | ACK thành công/hết retry | Kết thúc về STANDBY; không tự mở vòng vote mới |
| N13 | Lặp nhiều phiên | Không rò bộ nhớ hoặc dùng lẫn buffer phiên |
| N14 | ESP-NOW init/queue lỗi | Có trạng thái chờ/lỗi rõ, không báo đã gửi |

<a id="muc-9"></a>

## 9. Ma trận nghiệm thu end-to-end

| Mã | Tình huống | Bằng chứng cần lưu |
|---|---|---|
| E01 | CHECK valid → Gateway → UI | Session/event ID, ACK, JSON, ảnh UI |
| E02 | CHECK rồi MONITOR | Vitals không mất; cờ phiên vẫn đúng |
| E03 | Retry duplicate | Không thêm điểm HR giả |
| E04 | Wi-Fi mất, LTE hoạt động | Log transport transition và JSON sau chuyển |
| E05 | Cả hai uplink mất | Mô tả rõ latest-state, không hứa giữ mọi event |
| E06 | JSON/sensor invalid | UI không crash, không dựng số đo giả |
| E07 | Gateway/Dashboard reboot | Cache mất được giải thích và phục hồi bằng dữ liệu mới |
| E08 | Classification Unsure | Enum/nhãn/score đi qua đúng |
| E09 | Asthma score dưới/trên 0.80 | Alert Gateway khớp chính sách đã chốt |
| E10 | Chạy kéo dài | Heap/stack/reset/watchdog ổn định theo log đo |

<a id="muc-10"></a>

## 10. Hồ sơ bàn giao tối thiểu

Lưu commit source, phiên bản dependency/toolchain, model SHA, preprocessing config, threshold cuối, sơ đồ dây, nguồn cấp, thiết bị thu/phát, manifest test và log đo. Gắn thời điểm đo và phiên bản firmware cho từng bảng kết quả.

Báo cáo kết thúc nên có ba cột: “đã triển khai”, “đã kiểm chứng bằng log nào”, “giới hạn còn lại”. Các mục như cảnh báo SMS, lưu mọi sự kiện offline, nhận biết mic bị tháo giữa phiên hay độ chính xác trên bệnh nhân thật chỉ đưa vào phần đã hoàn thành khi có đúng implementation và bằng chứng tương ứng.

