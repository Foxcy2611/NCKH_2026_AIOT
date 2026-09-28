# Experiments_Benchmarking

## 1. Mục đích

Thư mục `Experiments_Benchmarking` lưu cấu hình đối chứng, kịch bản thí
nghiệm, dữ liệu đo và kết luận dùng trong báo cáo NCKH.

Trọng tâm hiện tại là **Patient Node**. Phần Gateway không thuộc phạm vi của
đợt đánh giá này.

Các thí nghiệm phải trả lời được:

- cấu hình đang chạy trong sản phẩm là gì;
- thông số nào đã được chốt và thông số nào còn phải kiểm chứng;
- thay đổi một thông số ảnh hưởng thế nào đến độ chính xác, độ trễ và tài
  nguyên;
- kết quả Python có tương ứng với ESP32-S3 hay không;
- cấu hình được chọn có hoạt động ổn định với micro và môi trường thực tế hay
  không.

---

## 2. Cấu trúc thư mục

```text
Experiments_Benchmarking/
├── Patient_Node/
│   ├── README.md
│   └── <nhóm_thí_nghiệm>/
│       ├── config.md
│       ├── outputs/
│       └── summary/
├── Gateway/                 # Ngoài phạm vi hiện tại
└── README.md
```

`Patient_Node/README.md` chỉ chứa kế hoạch và quy tắc kiểm thử. Cấu hình
**FINAL** hiện hành của Patient Node được ghi tại:

```text
Docs_Member/Chien/PATIENT_NODE_FINAL_SPEC.md
```

Không lấy thông số từ trí nhớ hoặc từ một bản source cũ.

---

## 3. Ý nghĩa của FINAL

Trong thư mục này, `FINAL` là cấu hình đang được đóng băng để:

- chạy lại phép đo;
- so sánh các phương án;
- lập bảng và biểu đồ cho báo cáo;
- đối chiếu với firmware thực tế.

Một số ngưỡng hiện hành như vùng phân lớp, Quality Gate và VAD vẫn cần thí
nghiệm chính thức. Trong thời gian chưa có kết luận mới, chúng vẫn là cấu hình
FINAL hiện hành để làm mốc. Chỉ thay đổi giá trị FINAL sau khi có đủ:

1. cấu hình phép thử;
2. dữ liệu đầu vào cố định;
3. kết quả thô;
4. bảng tổng hợp;
5. lý do lựa chọn;
6. kiểm tra lại trên phần cứng.

`FINAL` không có nghĩa là tối ưu tuyệt đối cho mọi bệnh nhân hoặc mọi môi
trường.

---

## 4. Nguồn đối chiếu chính thức

| Nội dung | Nguồn |
|---|---|
| Chia và tăng cường dữ liệu | `AI_Training_Model/P1_Chia_Du_Lieu/` |
| Tiền xử lý Python | `AI_Training_Model/P2_Preprocess_&_Traning_Model/Preprocess_Audio.py` |
| Huấn luyện | `AI_Training_Model/P2_Preprocess_&_Traning_Model/Training_Model.py` |
| Lượng tử hóa | `AI_Training_Model/P3_Quantize_Model/Quantize_Model.py` |
| Báo cáo model | `AI_Training_Model/P2_Preprocess_&_Traning_Model/Output_Train/` |
| Báo cáo INT8 | `AI_Training_Model/P3_Quantize_Model/Output_Quantize/` |
| Đối chiếu Python/C++ | `AI_Training_Model/P4_Kiem_Tra_CPP/` |
| Firmware FINAL | `Final_Project_NCKH/Patient_Node/` |
| Đặc tả cấu hình FINAL của Node | `Docs_Member/Chien/PATIENT_NODE_FINAL_SPEC.md` |
| Kế hoạch kiểm thử Node | `Experiments_Benchmarking/Patient_Node/README.md` |

Khi tài liệu và source không khớp, phải dừng phép thử, xác định bản đúng rồi
đồng bộ lại trước khi đo.

---

## 5. Nguyên tắc thí nghiệm

### 5.1. Chỉ thay đổi một nhóm thông số

Ví dụ khi kiểm tra ngưỡng Quality Gate:

- giữ nguyên model;
- giữ nguyên tiền xử lý;
- giữ nguyên file hoặc kịch bản âm thanh;
- giữ nguyên khoảng cách và mức âm lượng;
- chỉ thay đổi ngưỡng đang khảo sát.

Không dùng hai lần chia dữ liệu khác nhau để so sánh trực tiếp hai cấu hình.

### 5.2. Không dùng tập test để chọn tham số

- Tập train dùng để học và tạo dữ liệu đại diện khi lượng tử hóa.
- Tập validation dùng để chọn ngưỡng và phương án.
- Tập test chỉ được dùng sau khi đã đóng băng phương án.
- Thử nghiệm loa → INMP441 → ESP32-S3 là đánh giá phần cứng độc lập, phải ghi
  rõ file nguồn, loa, âm lượng, khoảng cách và môi trường.

### 5.3. Không làm rò rỉ dữ liệu

- Chia theo bệnh nhân trước khi tăng cường.
- Mọi bản tăng cường của một file gốc chỉ thuộc tập train.
- Validation và test chỉ chứa file gốc.
- Không chuyển file từ test sang train sau khi đã xem kết quả.

### 5.4. Ghi đủ điều kiện đo

Mỗi lần chạy phải ghi:

- mã thí nghiệm và ngày giờ;
- mã nguồn hoặc Git commit đang dùng;
- model và SHA-256 của model;
- seed;
- số lượng mẫu từng lớp;
- phần cứng và phiên bản firmware;
- phiên bản Python, TensorFlow, librosa, scipy và các thư viện liên quan;
- thông số giữ nguyên;
- thông số thay đổi;
- số lần lặp;
- điều kiện phòng, nguồn nhiễu, loa, âm lượng và khoảng cách nếu dùng micro;
- kết quả thô và kết luận.

Không ghi khóa AES thật hoặc thông tin bí mật vào kết quả thí nghiệm.

---

## 6. Cấu trúc bắt buộc của một thí nghiệm

```text
ten_thi_nghiem/
├── config.md
├── run.py hoặc ten_thi_nghiem.ipynb
├── outputs/
│   ├── raw_results.csv
│   ├── runtime.log
│   └── ...
└── summary/
    ├── metrics.csv
    ├── figures/
    └── README.md
```

`config.md` phải chứa cấu hình trước khi chạy. Không sửa file này theo kết quả
đã nhìn thấy; nếu đổi cấu hình phải tạo mã lần chạy mới.

`summary/README.md` phải trả lời:

1. Đã thử những phương án nào?
2. Dữ liệu và điều kiện có giống nhau không?
3. Kết quả chính là gì?
4. Phương án nào được chọn?
5. Vì sao chọn?
6. Giới hạn của phép thử là gì?
7. Có được phép cập nhật cấu hình FINAL hay chưa?

---

## 7. Chỉ số đánh giá

### Model và phân lớp

- Accuracy;
- Precision, Recall và F1 của từng lớp;
- ma trận nhầm lẫn;
- số ca Asthma bị bỏ sót;
- tỷ lệ `UNSURE`;
- tỷ lệ mẫu được kết luận trực tiếp.

### VAD và Quality Gate

- kích hoạt sai;
- bỏ lỡ âm thanh cần thu;
- chấp nhận âm thanh lỗi;
- loại nhầm âm thanh hợp lệ;
- thời gian từ âm thanh đến lúc bắt đầu thu;
- số lần phải thu lại.

### ESP32-S3

- thời gian DSP;
- thời gian suy luận;
- tổng thời gian pipeline;
- RAM nội, PSRAM và Tensor Arena;
- kích thước model và firmware;
- số lần reset, lỗi cấp phát hoặc lỗi runtime.

---

## 8. Quy trình cập nhật cấu hình FINAL

```text
Đề xuất thông số
    ↓
Chọn bằng validation hoặc phép đo phần cứng đã định trước
    ↓
Đóng băng thông số
    ↓
Đánh giá một lần trên test / kịch bản độc lập
    ↓
Kiểm tra lại trên ESP32-S3
    ↓
Cập nhật đặc tả FINAL, kế hoạch/kết luận thí nghiệm và source liên quan
```

Không cập nhật bảng FINAL chỉ vì một lần chạy cho kết quả đẹp hơn. Kết luận
phải dựa trên toàn bộ chỉ số phù hợp, đặc biệt là khả năng bỏ sót Asthma và độ
ổn định trên phần cứng.
