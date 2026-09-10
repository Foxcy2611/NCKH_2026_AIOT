# Interface_Asthma — giao tiếp model DS-CNN INT8

Mô-đun `src/Interface_Asthma.cpp` chịu trách nhiệm khởi tạo TensorFlow Lite
Micro, chuyển Mel-dB thành tensor INT8, chạy `Invoke()` và diễn giải output.

## Hợp đồng model

| Thuộc tính | Giá trị |
|---|---|
| Header model | `include/Model_AI/Asthma_Model_3.h` |
| Kiểu input/output | INT8 |
| Shape input | `[1, 64, 129, 1]` |
| Số phần tử input | 8.256 |
| Tensor arena | 270 KiB, căn lề 16 byte trong PSRAM |
| Output | một giá trị sigmoid đã lượng tử |
| Ngưỡng quyết định | 0,5 |

Khởi tạo sẽ thất bại nếu schema không tương thích, không cấp phát được arena,
input/output không phải INT8 hoặc input không đúng shape.

## Mel-dB sang INT8

Mỗi giá trị Mel trong `[-80, 0] dB` được chuẩn hóa và giới hạn:

```text
normalized = clamp((dB + 80) / 80, 0, 1)
```

Sau đó lượng tử theo metadata thật của tensor:

```text
q = round(normalized / input_scale + input_zero_point)
q = clamp(q, -128, 127)
```

Code dùng `lrintf()` thay vì ép kiểu trực tiếp để không cắt phần thập phân.
Layout flatten là `mel_index × 129 + frame_index`.

## Đọc output và quy ước lớp

Giá trị output được dequantize:

```text
p_non = clamp((raw - output_zero_point) × output_scale, 0, 1)
```

```text
p_non < 0,5  → lớp 0: ASTHMA_LIKE
p_non ≥ 0,5  → lớp 1: NON_ASTHMA
```

`NON_ASTHMA` là tên lớp của dataset, không phải khẳng định người dùng bình
thường hoặc không có bệnh hô hấp.

## Các đường kiểm chứng

### PCM16 parity

`Run_Asthma_Interface()` nhận Mel-dB từ DSP C++, tạo tensor rồi so với tensor
Python **trước** `Invoke()`. Việc so trước là cần thiết vì TFLite Micro có thể
tái sử dụng vùng input làm bộ nhớ trung gian.

Kết quả so gồm:

- số phần tử khác;
- sai lệch tuyệt đối lớn nhất;
- sai lệch tuyệt đối trung bình.

### Direct tensor

`Run_Asthma_From_Int8_Tensor()` chép nguyên 8.256 phần tử INT8 do Python tạo vào
input, bỏ qua normalize, DSP và Mel. Đường này cô lập model header, runtime và
phép dequantize output khỏi phần tiền xử lý.

## Phân biệt inference và voting

Một lần gọi interface tạo một kết quả cho một tensor. Ở chế độ LiveMic của
Phase 2, bộ đếm vote tổng hợp kết quả của **ba đoạn thu riêng**, không gọi model
ba lần trên cùng một tensor. Voting là hậu xử lý điều phối và không thay đổi
ngưỡng parity 0,5 của model.

Không mô tả output là chẩn đoán hen suyễn; đây là kết quả phân loại mẫu âm
thanh phục vụ nguyên mẫu nghiên cứu.
