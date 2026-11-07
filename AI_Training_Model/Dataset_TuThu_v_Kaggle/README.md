# Dataset tự thu và Kaggle

Thư mục này lưu **dữ liệu WAV nguồn** dùng để xây dựng các bộ dữ liệu huấn luyện Asthma/Non-Asthma. Dữ liệu tại đây chưa phải đầu vào cuối cùng cho preprocessing; việc chia Train/Validation/Test được thực hiện bởi các script trong `Phase1_Split_Data/`.

## Cấu trúc

```text
Dataset_TuThu_v_Kaggle/
├── asthma/                 # Core Asthma
├── Bronchial/              # Core Non-Asthma
├── copd/                   # Core Non-Asthma
├── healthy/                # Core Non-Asthma
├── pneumonia/              # Core Non-Asthma
├── TuThu/
│   ├── Playback_Raw/       # WAV phát qua loa và thu lại bằng INMP441
│   ├── Record_Env/         # Các session môi trường tự thu
│   └── TKe/                # Log, thống kê và kết quả phân tích khi thu
└── Out_Split_Session/      # Session môi trường đã khóa split ở bước 03
```

## Quy tắc sử dụng

- Core được chia theo nhóm bệnh nhân, tránh để cùng bệnh nhân xuất hiện ở nhiều tập.
- Playback phải kế thừa split của Core nguồn; không chia ngẫu nhiên lại.
- Environment được chia theo `session_id` trước, sau đó mới cắt thành clip 5 giây.
- Không augmentation hoặc duplicate dữ liệu Validation/Test để cân bằng lớp.
- Giữ nguyên WAV nguồn và metadata để có thể truy vết, kiểm tra và tái lập thí nghiệm.

## Pipeline liên quan

```text
Dataset_TuThu_v_Kaggle
        ↓
Phase1_Split_Data/00...04
        ↓
Dataset_Chia_V2
        ↓
Phase2_Preprocess_&_Traning
```

Xem hướng dẫn chi tiết tại [`../Phase1_Split_Data/README.md`](../Phase1_Split_Data/README.md) và quy tắc của dữ liệu playback tại [`TuThu/Playback_Raw/README.md`](TuThu/Playback_Raw/README.md).
