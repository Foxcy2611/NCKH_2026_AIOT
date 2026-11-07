# So sánh Dataset có Playback và không có Playback

## 1. Mục tiêu

Thí nghiệm ablation giữ nguyên kiến trúc:

```text
V1 SepConv2D + Flatten
```

và chỉ thay đổi một yếu tố:

```text
Model A — V2_1_With_Playback
Dataset có playback

Model B — V3_1_No_Playback
Dataset đã loại toàn bộ playback
```

Hai model được đánh giá trên cùng các tập test khóa sẵn để tránh so sánh sai do test set khác nhau.

---

## 2. Hai tập test

### Test 1 — Common Raw Test

```text
143 mẫu
30 Asthma
113 Non-Asthma
```

Đây là toàn bộ raw test có mặt chung ở cả V2 và V3.

### Test 2 — Playback-Only Test

```text
16 mẫu
8 Asthma
8 Non-Asthma
```

Đây là các playback có trong V2 nhưng bị loại khỏi V3.

---

## 3. Kết quả trên Common Raw Test

| Metric | V2 có Playback | V3 không Playback |
|---|---:|---:|
| Accuracy | 88.11% | **92.31%** |
| Asthma Precision | 65.85% | **77.14%** |
| Asthma Recall | **90.00%** | **90.00%** |
| Asthma F1 | 76.06% | **83.08%** |
| Non-Asthma Precision | 97.06% | **97.22%** |
| Non-Asthma Recall | 87.61% | **92.92%** |
| Non-Asthma F1 | 92.09% | **95.02%** |

Confusion matrix:

```text
V2 có Playback
[[27, 3],
 [14, 99]]

V3 không Playback
[[27, 3],
 [ 8,105]]
```

### Nhận xét

Hai model đều nhận đúng:

```text
27/30 Asthma
```

nên Asthma Recall trên raw đều bằng `90%`.

Khác biệt chủ yếu nằm ở Non-Asthma:

```text
V2: 14 Non-Asthma bị báo nhầm Asthma
V3:  8 Non-Asthma bị báo nhầm Asthma
```

Do đó model không playback có raw-domain accuracy cao hơn chủ yếu nhờ giảm false alarm.

---

## 4. Kết quả trên Playback-Only Test

| Metric | V2 có Playback | V3 không Playback |
|---|---:|---:|
| Accuracy | **100%** | 75% |
| Asthma Precision | **100%** | 100% |
| Asthma Recall | **100%** | 50% |
| Asthma F1 | **100%** | 66.67% |
| Non-Asthma Precision | **100%** | 66.67% |
| Non-Asthma Recall | **100%** | 100% |
| Non-Asthma F1 | **100%** | 80% |

Confusion matrix:

```text
V2 có Playback
[[8,0],
 [0,8]]

V3 không Playback
[[4,4],
 [0,8]]
```

### Nhận xét

Model có playback nhận đúng toàn bộ 16 mẫu.

Model không playback:

```text
Asthma playback đúng : 4/8
Asthma playback sai  : 4/8
Non-Asthma đúng      : 8/8
```

Như vậy, loại playback khỏi training làm Asthma Recall trên playback giảm từ:

```text
100% → 50%
```

---

## 5. Kết luận chính

Kết quả cho thấy một trade-off rõ ràng:

```text
Không Playback
→ tốt hơn trên raw-domain

Có Playback
→ tốt hơn rất rõ trên playback-domain
```

Playback không đơn thuần làm dataset "xấu hơn".

Nó làm bài toán khó hơn và buộc model học thêm một miền acoustic khác.

Kết quả raw:

```text
V3: 92.31%
V2: 88.11%
```

nhưng kết quả playback:

```text
V3: 75%
V2: 100%
```

Đặc biệt, Asthma Recall trên raw vẫn giữ nguyên `90%` ở cả hai model, trong khi Asthma Recall playback tăng từ `50%` lên `100%` khi playback được đưa vào training.

---

## 6. Quyết định cho Dataset V2

Với mục tiêu Patient Node sử dụng microphone INMP441, Dataset V2 có playback vẫn được giữ làm baseline hiện tại vì:

- không làm giảm Asthma Recall trên common raw test;
- tăng mạnh robustness trên playback-domain;
- mô phỏng được một phần biến đổi của acoustic acquisition;
- phù hợp hơn với mục tiêu deployment qua microphone so với dataset chỉ chứa raw digital.

Dataset V3 không playback được giữ như một **ablation experiment**, không thay thế Final V1.

---

## 7. Giới hạn của kết luận

Playback-only test chỉ có:

```text
16 mẫu
```

nên kết quả `100%` không có nghĩa model robust với mọi điều kiện playback.

Các thử nghiệm thực tế đã cho thấy cùng một model V2 vẫn có thể gặp domain shift khi thay đổi playback session hoặc đường truyền loa → INMP441.

Do đó cần phân biệt:

```text
Playback samples trong Dataset V2
≠
mọi điều kiện playback ngoài thực tế
```

Playback trong dataset giúp model học domain này, nhưng không bao phủ toàn bộ biến thiên do loa, khoảng cách, môi trường và session.

---

## 8. Kết luận cuối

> **Playback tạo ra trade-off giữa clean/raw-domain performance và acoustic-domain robustness.**

> **Playback được sử dụng như một dữ liệu proxy nhằm mô phỏng quá trình tín hiệu âm thanh đi qua đường truyền acoustic và microphone INMP441. Tuy nhiên, playback tạo ra một domain riêng do ảnh hưởng của loa, môi trường và đáp tuyến microphone, vì vậy chỉ phản ánh gần đúng chứ không hoàn toàn tương đương với tín hiệu hô hấp thu trực tiếp từ người dùng.**

Với Patient Node hiện tại:

```text
Final baseline : Dataset V2 có Playback
Ablation       : Dataset V3 không Playback
```

V2 được ưu tiên vì mục tiêu cuối là hệ thống audio chạy qua microphone, trong khi V3 có giá trị để chứng minh rằng việc thêm playback mang lại robustness thật sự chứ không chỉ tăng số lượng dữ liệu.
