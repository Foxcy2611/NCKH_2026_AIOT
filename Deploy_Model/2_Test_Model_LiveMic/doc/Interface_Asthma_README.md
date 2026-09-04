# Interface_Asthma — giao tiếp model INT8

- Model: `Asthma_Model_3.h`.
- Tensor arena: 270 KB, căn lề 16 byte, cấp phát trong PSRAM.
- Input bắt buộc: INT8 `[1, 64, 129, 1]`.
- Output bắt buộc: một giá trị INT8.
- Ngưỡng phân lớp khóa: 0,5.

Quy ước:

```text
p(Non-Asthma) < 0,5  → Asthma (lớp 0)
p(Non-Asthma) ≥ 0,5  → Non-Asthma (lớp 1)
```

Project kiểm thử còn hỗ trợ:

- So tensor INT8 ngay trước `Invoke()`.
- Nạp trực tiếp tensor INT8 để bỏ qua tiền xử lý C++.
- Đối chiếu output raw và xác suất với Python.

Vùng chưa chắc chắn là tầng quyết định của hệ thống sau này; không được trộn
vào phép kiểm tra độ khớp model Python–ESP32 đang dùng ngưỡng 0,5.
