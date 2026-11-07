# Quy trình chia và tăng cường dữ liệu V2

## Mục lục

1. [Mục tiêu](#1-mục-tiêu)
2. [Nguyên tắc bắt buộc](#2-nguyên-tắc-bắt-buộc)
3. [Luồng thực hiện](#3-luồng-thực-hiện)
4. [Bước 00 - Chia dữ liệu Core](#4-bước-00---chia-dữ-liệu-core)
5. [Bước 01 - Chọn nguồn Playback](#5-bước-01---chọn-nguồn-playback)
6. [Bước 02 - Ánh xạ Playback vào đúng tập](#6-bước-02---ánh-xạ-playback-vào-đúng-tập)
7. [Bước 03 - Chia session môi trường](#7-bước-03---chia-session-môi-trường)
8. [Bước 04 - Cắt session và xây dựng dữ liệu môi trường](#8-bước-04---cắt-session-và-xây-dựng-dữ-liệu-môi-trường)
9. [Bước 05 - Tăng cường Asthma Train](#9-bước-05---tăng-cường-asthma-train)
10. [Số lượng dữ liệu cuối](#10-số-lượng-dữ-liệu-cuối)
11. [Thứ tự chạy](#11-thứ-tự-chạy)
12. [Kiểm tra trước khi tiền xử lý](#12-kiểm-tra-trước-khi-tiền-xử-lý)

---

## 1. Mục tiêu

Phase 1 tạo bộ dữ liệu V2 có thể truy vết và không làm rò rỉ dữ liệu giữa
Train, Validation và Test.

Dữ liệu được hình thành từ ba nguồn:

- **Core:** WAV gốc lấy từ bộ dữ liệu Kaggle.
- **Playback:** WAV Kaggle được phát qua loa và thu lại bằng INMP441.
- **Environment:** âm thanh môi trường tự thu bằng INMP441.

Tăng cường chỉ được dùng để cân bằng **Asthma Train** với
**Non-Asthma Train**. Validation và Test phải giữ nguyên dữ liệu độc lập để
đánh giá đúng khả năng hoạt động trên dữ liệu chưa học.

> Trong tên script hiện dùng từ `Argument`, nhưng ý nghĩa đúng trong quy trình
> này là **augmentation - tăng cường dữ liệu**.

---

## 2. Nguyên tắc bắt buộc

1. Chia Core theo `group_id`/mã bệnh nhân trước khi tăng cường.
2. Toàn bộ WAV của cùng một bệnh nhân chỉ được nằm trong một tập.
3. Playback phải kế thừa tập của Core nguồn:
   - Core Train → Playback Train.
   - Core Validation → Playback Validation.
   - Core Test → Playback Test.
4. Toàn bộ clip sinh từ cùng một session môi trường phải cùng một tập.
5. Chỉ tăng cường **Asthma Core Train**.
6. Không tăng cường Playback, Validation hoặc Test.
7. Nguồn môi trường dùng để trộn với Asthma phải thuộc Train.
8. Không dùng dữ liệu tăng cường làm file cha để tăng cường lần tiếp theo.
9. Không nhân bản Validation/Test chỉ để cân bằng số lượng hai lớp.
10. Mọi phép chia và tăng cường dùng seed `42` để có thể tái tạo kết quả.

---

## 3. Luồng thực hiện

```text
Core WAV gốc
    |
    v
00_Split_Core_Data.py
    |-- Core Train / Validation / Test
    |
    v
01_Random_Playback.py
    |-- Danh sách Core đủ chất lượng để phát lại
    |
    v
Thu Playback bằng loa -> INMP441
    |
    v
02_Map_Playback.py
    |-- Playback kế thừa split của Core nguồn

Session môi trường gốc
    |
    v
03_Cut_Environment.py
    |-- Chia nguyên session thành Train / Validation / Test
    |
    v
04_Build_Dataset.py
    |-- Mỗi session sinh 10 clip x 5 giây
    |-- Gộp vào Non_Asthma_Disease

Asthma Core Train + nguồn môi trường Train
    |
    v
05_Argument_Asthma.py
    |-- Sinh 695 file Asthma tăng cường
    `-- Cân bằng Train: 987 Asthma / 987 Non-Asthma
```

---

## 4. Bước 00 - Chia dữ liệu Core

Script: `00_Split_Core_Data.py`

### Đầu vào

Các thư mục WAV Core tại:

```text
AI_Training_Model/Dataset_TuThu_v_Kaggle/
|-- asthma/
|-- Bronchial/
|-- copd/
|-- healthy/
`-- pneumonia/
```

### Cách làm

- Tính SHA-256 để phát hiện file trùng.
- Lấy mã bệnh nhân làm `group_id`.
- Xáo trộn bằng seed `42`.
- Chia nhóm bệnh nhân theo tỷ lệ gần `80/10/10`.
- Chép WAV sang đúng lớp và đúng tập trong `Dataset_Chia_V2`.

### Kết quả Core hiện tại

| Lớp | Train | Validation | Test |
|---|---:|---:|---:|
| Asthma Core | 228 | 30 | 30 |
| Non-Asthma bệnh lý Core | 653 | 78 | 83 |

### Báo cáo

```text
Output/00_Core_Split/
|-- core_split_manifest.csv
|-- core_group_split.csv
`-- core_duplicates.csv
```

`core_split_manifest.csv` là nguồn đối chiếu chính cho các bước sau.

---

## 5. Bước 01 - Chọn nguồn Playback

Script: `01_Random_Playback.py`

### Mục đích

Chọn Core đủ rõ và đủ lớn để phát qua loa rồi thu lại bằng INMP441.

### Điều kiện chất lượng nguồn

- Mono PCM16.
- Thời lượng ít nhất 4,5 giây.
- Peak tối thiểu 5.000 trên thang PCM16.
- RMS tối thiểu 1.000 trên thang PCM16.
- Tỷ lệ clipping không quá 0,5%.

### Số nguồn được chọn

| Nhóm | Số Core nguồn |
|---|---:|
| Asthma | 40 |
| Bronchial | 10 |
| COPD | 10 |
| Healthy | 10 |
| Pneumonia | 10 |
| **Tổng** | **80** |

Mỗi Core nguồn được thu Playback hai lần. Danh sách được tạo tại:

```text
Output/01_Random_Playback/Playback_Source_List.csv
```

---

## 6. Bước 02 - Ánh xạ Playback vào đúng tập

Script: `02_Map_Playback.py`

Script đọc `Playback_Source_List.csv`, tìm các WAV đã thu và chép chúng vào
đúng tập mà Core nguồn đang thuộc về. Playback không được chia ngẫu nhiên lại.

### Kết quả Playback cho mỗi lớp

| Lớp Playback | Train | Validation | Test | Tổng |
|---|---:|---:|---:|---:|
| Asthma | 64 | 8 | 8 | 80 |
| Non-Asthma bệnh lý | 64 | 8 | 8 | 80 |

### Báo cáo

```text
Output/02_Map_Playback/playback_map_manifest.csv
```

Sau bước này:

| Lớp | Train | Validation | Test |
|---|---:|---:|---:|
| Asthma Core + Playback | 292 | 38 | 38 |
| Non-Asthma bệnh lý Core + Playback | 717 | 86 | 91 |

---

## 7. Bước 03 - Chia session môi trường

Script: `03_Cut_Environment.py`

Tên script có chữ `Cut`, nhưng bước 03 **chưa cắt clip**. Script chỉ chia và
chép nguyên session vào `Out_Split_Session`.

### Quy tắc chia 33 session chính

| Nhóm | Tổng | Train | Validation | Test |
|---|---:|---:|---:|---:|
| Podcast | 6 | 5 | 1 | 0 |
| Fan | 5 | 4 | 1 | 0 |
| Clap | 6 | 5 | 1 | 0 |
| Knock | 5 | 4 | 0 | 1 |
| Room noise | 6 | 5 | 0 | 1 |
| Speech | 5 | 4 | 0 | 1 |
| **Tổng** | **33** | **27** | **3** | **3** |

Validation gồm một session Podcast, Fan và Clap. Test gồm một session Knock,
Room noise và Speech. Những session còn lại thuộc Train.

### Đầu ra session

```text
AI_Training_Model/Dataset_TuThu_v_Kaggle/Out_Split_Session/
|-- train/
|-- val/
`-- test/
```

### Báo cáo

```text
Output/03_Cut_Environment/
|-- environment_session_split.csv
`-- environment_session_split.md
```

`key_fan_5min.wav` là session mixed cũ, được khóa ở Train và không nằm trong
33 session chính. `silence_5min.wav` chỉ được dùng làm nền cho phép dịch vị trí
âm thanh.

---

## 8. Bước 04 - Cắt session và xây dựng dữ liệu môi trường

Script: `04_Build_Dataset.py`

### Cách cắt

- Mỗi session sinh đúng 10 clip.
- Mỗi clip dài 5 giây.
- Các đoạn được phân bố trên toàn bộ thời lượng session.
- Không resample, chuẩn hóa biên độ hoặc tăng cường tại bước này.
- Clip kế thừa tập của session cha.
- Tất cả clip được gắn nhãn `Non_Asthma_Disease`.

### Kết quả

| Tập | Session | Clip môi trường |
|---|---:|---:|
| Train | 27 | 270 |
| Validation | 3 | 30 |
| Test | 3 | 30 |
| **Tổng** | **33** | **330** |

Sau khi thêm môi trường, Non-Asthma có:

| Tập | Trước Environment | Environment | Tổng |
|---|---:|---:|---:|
| Train | 717 | 270 | 987 |
| Validation | 86 | 30 | 116 |
| Test | 91 | 30 | 121 |

### Báo cáo

```text
Output/04_Build_Dataset/
|-- environment_clip_manifest.csv
`-- environment_clip_summary.md
```

---

## 9. Bước 05 - Tăng cường Asthma Train

Scripts:

- `Argument_Oversampling.py`: chứa các phép biến đổi.
- `05_Argument_Asthma.py`: kiểm tra đầu vào, phân bổ file cha, sinh WAV và
  tạo báo cáo.
- Đặc tả chi tiết: [`ASTHMA_AUGMENTATION_SPEC.md`](ASTHMA_AUGMENTATION_SPEC.md).

### Dữ liệu được phép làm cha

Chỉ dùng **228 Asthma Core Train** từ `core_split_manifest.csv`.

Không dùng:

- 64 Asthma Playback Train.
- Asthma Validation/Test.
- File Asthma đã tăng cường.

### Số file tăng cường

| Phương pháp | Số file | Tham số |
|---|---:|---|
| `mix_environment` | 139 | gain ngẫu nhiên 0,02-0,10 |
| `time_shift` | 139 | đặt vùng âm chính 4 giây vào vị trí ngẫu nhiên trong 5 giây |
| `white_noise` | 139 | noise level 0,001 |
| `time_stretch` | 139 | rate ngẫu nhiên 0,90-1,10 |
| `pitch_shift` | 139 | -0,5 đến +0,5 bán âm |
| **Tổng** | **695** | |

### Phân bổ file cha

- 217 Core nhận 3 bản tăng cường.
- 11 Core nhận 4 bản tăng cường.
- Mỗi phương pháp chỉ được áp dụng tối đa một lần trên cùng một Core cha.
- Mỗi phương pháp chọn 139 Core cha khác nhau.

### Nguồn cho `mix_environment`

- 270 clip Environment Train đã tạo ở bước 04.
- `key_fan_5min.wav` được xem như một session Train và có trọng số tương
  đương 10 clip.
- Không sử dụng bất kỳ nguồn môi trường Validation/Test nào.

### Chuẩn đầu ra

- Mono.
- 16 kHz.
- Đúng 5 giây, tương ứng 80.000 mẫu.
- PCM16 khi ghi WAV.
- Tín hiệu được giới hạn trong miền `[-1, 1]` trước khi ghi.
- Tên file bắt đầu bằng `AUGV2__`.

### Cơ chế an toàn

Script sẽ dừng nếu:

- Core Train không đúng 228 file.
- Playback Asthma Train không đúng 64 file.
- Asthma Train ban đầu không đúng 292 file.
- Non-Asthma Train không đúng 987 file.
- Hash Core không khớp manifest.
- Thiếu nguồn môi trường hoặc file im lặng.
- Đã tồn tại file `AUGV2__*.wav` hoặc báo cáo bước 05.

### Báo cáo dự kiến sau khi chạy

```text
Output/05_Argument_Asthma/
|-- asthma_augmentation_manifest.csv
`-- asthma_augmentation_summary.md
```

Manifest lưu file cha, bệnh nhân, phương pháp, seed, tham số thực tế, nguồn
môi trường, đường dẫn đầu ra và SHA-256.

---

## 10. Số lượng dữ liệu cuối

### Train

| Lớp | Thành phần | Tổng |
|---|---|---:|
| Asthma | 228 Core + 64 Playback + 695 tăng cường | **987** |
| Non-Asthma | 653 Core bệnh lý + 64 Playback + 270 Environment | **987** |

Train được cân bằng chính xác `987/987`.

### Validation và Test

| Tập | Asthma | Non-Asthma |
|---|---:|---:|
| Validation | 38 | 116 |
| Test | 38 | 121 |

Validation/Test không cân bằng tuyệt đối là chấp nhận được. Điều quan trọng là
không có dữ liệu họ hàng, bản tăng cường hoặc bản sao giữa các tập.

---

## 11. Thứ tự chạy

Chạy từ thư mục gốc dự án:

```powershell
python AI_Training_Model/Phase1_Split_Data/00_Split_Core_Data.py
python AI_Training_Model/Phase1_Split_Data/01_Random_Playback.py
```

Sau bước 01, dùng danh sách CSV để thu đủ Playback bằng INMP441. Sau đó chạy:

```powershell
python AI_Training_Model/Phase1_Split_Data/02_Map_Playback.py
python AI_Training_Model/Phase1_Split_Data/03_Cut_Environment.py
python AI_Training_Model/Phase1_Split_Data/04_Build_Dataset.py
python AI_Training_Model/Phase1_Split_Data/05_Argument_Asthma.py
```

Không chạy lại một bước lên chính đầu ra cũ nếu chưa kiểm tra/xóa đúng đầu ra
của bước đó, vì các script cố ý bảo vệ dữ liệu khỏi bị ghi chồng.

---

## 12. Kiểm tra trước khi tiền xử lý

Sau bước 05 cần xác nhận:

- [x] Asthma Train có 987 WAV.
- [x] Non-Asthma Train có 987 WAV.
- [x] Asthma Validation/Test lần lượt có 38/38 WAV.
- [x] Non-Asthma Validation/Test lần lượt có 116/121 WAV.
- [x] Có đúng 695 tên file bắt đầu bằng `AUGV2__`.
- [x] Mỗi phương pháp có đúng 139 file.
- [x] Không có `AUGV2__` trong Validation/Test.
- [x] Không có Playback nào xuất hiện trong manifest tăng cường.
- [x] Không có nguồn Environment Validation/Test trong manifest tăng cường.
- [x] Các báo cáo CSV/Markdown của bước 00-05 được lưu đầy đủ.

Khi tất cả điều kiện trên đạt, `Dataset_Chia_V2` mới được chuyển sang Phase 2
để tạo Mel-Spectrogram và huấn luyện mô hình.
