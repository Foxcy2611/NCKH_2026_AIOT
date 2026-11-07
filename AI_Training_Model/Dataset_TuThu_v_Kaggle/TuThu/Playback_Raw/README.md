# Playback Raw

Thư mục này lưu các WAV bệnh hô hấp được **phát qua loa và thu lại bằng ESP32-S3 + INMP441**. Mục đích là mô phỏng miền âm thanh mà Patient Node thật nhận được, không phải tạo thêm bệnh nhân hay nhãn mới.

## Cấu trúc và số lượng

```text
Playback_Raw/
├── Asthma/       # 40 source × 2 take = 80 WAV
├── Non_Asthma/   # 40 source × 2 take = 80 WAV
└── README.md
```

Nhóm Non-Asthma gồm 10 source cho mỗi loại: `Bronchial`, `COPD`, `Healthy` và `Pneumonia`. Toàn bộ dữ liệu hiện tại có **80 source, 160 WAV playback**.

## Nguồn và quy tắc chọn

Danh sách source được tạo bởi:

```text
Phase1_Split_Data/01_Random_Playback.py
→ Output/01_Random_Playback/Playback_Source_List.csv
```

Script chọn ngẫu nhiên với `seed=42`, mỗi source thuộc một nhóm bệnh nhân và phải đạt các điều kiện nguồn tối thiểu:

| Thuộc tính | Ngưỡng |
|---|---:|
| Thời lượng | ≥ 4,5 giây |
| Peak PCM16 | ≥ 5.000 |
| RMS PCM16 | ≥ 1.000 |
| Tỉ lệ clipping | ≤ 0,5% |

Phân bổ source theo split là `64 Train / 8 Validation / 8 Test`. Hai take của cùng source **luôn kế thừa split của Core gốc**; tuyệt đối không chia lại playback một cách ngẫu nhiên.

## Quy trình thu

Sử dụng `ESP32_Standalone_Modules_Test/ESP32_Read_INMP441/Record_Playback.py` với cấu hình của bộ dữ liệu hiện tại:

- PCM16, mono, 16 kHz;
- mỗi source thu hai lần: `take01` và `take02`;
- giữ 0,6 giây lead-in và 0,6 giây tail-out;
- loa ở mức 60%, cách INMP441 khoảng 6 cm;
- metadata thu ghi tại `TuThu/TKe/Playback_capture_log.csv`.

Vị trí loa, micro, firmware, gain và âm lượng phải được giữ cố định giữa các take. Nếu một take lỗi, thu lại đúng source/take đó; không tự ý đổi source ID.

## Quy tắc đặt tên

```text
<source_id>__<tên_source_gốc>__take01.wav
<source_id>__<tên_source_gốc>__take02.wav
```

Ví dụ: `AST_001__P10AsthmaIU_50__take01.wav`. Các tiền tố `AST`, `BRO`, `COPD`, `HEA`, `PNE` dùng để truy vết subtype; nhãn cuối cùng vẫn là `Asthma` hoặc `Non-Asthma`.

## Đưa vào Dataset V2

Chạy `Phase1_Split_Data/02_Map_Playback.py` để kiểm tra hai take, giữ nguyên split nguồn và chép vào:

```text
Dataset_Chia_V2/Asthma/{train,val,test}/
Dataset_Chia_V2/Non_Asthma_Disease/{train,val,test}/
```

Kết quả sau map: Train 128, Validation 16 và Test 16 WAV playback; trong mỗi split, số Asthma và Non-Asthma bằng nhau. File `Output/02_Map_Playback/playback_map_manifest.csv` dùng để truy vết nguồn–đích.

Trong preprocessing V2, file có hậu tố `__take01`/`__take02` dùng cửa sổ **1,0–6,0 giây** để loại lead-in hệ thống; các WAV Core/Environment vẫn dùng 0–5 giây.

## Lưu ý

- Playback là dữ liệu tái thu qua loa–micro, không phải bản ghi lâm sàng độc lập.
- Không augmentation riêng các take playback trong Train.
- Không được để source gốc và playback của nó rơi vào hai split khác nhau.
- Playback có thể tạo domain shift do loa, khoảng cách và INMP441; cần báo cáo tách biệt với Core raw.
- Giữ nguyên WAV và capture log để có thể tái lập và đối chiếu.
