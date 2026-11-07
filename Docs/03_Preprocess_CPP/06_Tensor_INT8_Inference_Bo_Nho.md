# Tensor INT8, TFLite Micro và ngân sách bộ nhớ

[Mục lục C++](README.md)

## Mục lục

- [1. Từ Log-Mel sang input model](#muc-1)
- [2. Khởi tạo interpreter](#muc-2)
- [3. Output và ý nghĩa score](#muc-3)
- [4. Bộ nhớ chính của Node](#muc-4)
- [5. Arena capacity và arena used](#muc-5)
- [6. Ranh giới xử lý lỗi](#muc-6)

<a id="muc-1"></a>

## 1. Từ Log-Mel sang input model

Node lấy min/max đã chốt từ Train: -80 và0. Với từng ô dB:

```text
u = (dB + 80)/80
u = clamp(u, 0, 1)
q = lrintf(u / input_scale + input_zero_point)
q = clamp(q, -128, 127)
```

Lượng tử diễn ra trên **feature đã chuẩn hóa**, không phải trực tiếp biến80.000 mẫu PCM thành input8-bit. Kích thước input model C4 là5.160 giá trị, khác số mẫu audio.

Scale/zero-point lấy từ tensor runtime. Manifest C4 QAT INT8 ghi input scale≈1/255, zp=-128. Ví dụ lý tưởng u=0→-128 và u=1→127. Một ô dB=-40 cho u=0,5, gần ranh giới làm tròn; khi so bit-exact phải dùng cùng floating-point và rounding policy.

`np.rint` dùng tie-to-even; `lrintf` tuân rounding mode của runtime, thông thường nearest-even. Không thay bằng ép kiểu int vì phép ép cắt phần lẻ và có thể lệch một đơn vị lượng tử.

<a id="muc-2"></a>

## 2. Khởi tạo interpreter

[Init_Asthma_Model](../../Final_Project_NCKH/Patient_Node/src/Inference_Asthma.cpp) thực hiện:

1. Khởi tạo target và error reporter.
2. Cấp arena PSRAM, aligned16.
3. Lấy FlatBuffer model từ `model_data`.
4. Kiểm tra schema version.
5. Dựng MicroInterpreter và AllOpsResolver.
6. AllocateTensors.
7. Kiểm tra I/O INT8 và shape input [1,40,129,1].

Header model căn hàng4 giúp truy cập dữ liệu FlatBuffer. Alignment header và alignment arena phục vụ các vùng nhớ khác nhau. Chúng không thay thế việc kiểm tra số byte/hàm cấp phát.

Nếu đổi model, cần kiểm tra ops, shape, input/output dtype và arena. Một header compile được chưa bảo đảm AllocateTensors hoặc Invoke thành công.

<a id="muc-3"></a>

## 3. Output và ý nghĩa score

```text
p_non = (output_int8 - output_zero_point) * output_scale
p_asthma = 1 - p_non
```

Manifest hiện có output scale1/256 và zp=-128. Bước xác suất khoảng0,00390625; các điểm xác suất có độ phân giải rời rạc. Dù output sigmoid được diễn giải như xác suất, việc calibration thống kê của score là vấn đề riêng.

Node hiện áp policy đã freeze cho C4:

| Điều kiện p_non | Classification | Score đưa vào session |
|---|---|---|
| ≤0,47 | Asthma-like (0) | 1-p_non |
| ≥0,77 | Non-Asthma (1) | p_non |
| Còn lại | Unsure (2) | Implementation hiện dùng1-p_non |

`Unsure_Prob` là tên biến hậu xử lý, không phải neuron thứ ba. `model_score` vì thế không luôn bằng p_non; Dashboard phải đọc cùng classification. Với Monitor, score là trung bình các vote thuộc lớp thắng; hòa1–1–1 thành UNSURE và score0.

Node và 3_Model_Complete phải cùng dùng 0,47/0,77; benchmark nhị phân0,5 chỉ dùng để báo metric model. Khi kiểm tra nhãn giữa các project, xác nhận source đang build dùng cùng policy.

<a id="muc-4"></a>

## 4. Bộ nhớ chính của Node

| Vùng | Phép tính | Byte |
|---|---|---:|
| PCM5 s |80.000×2 |160.000 |
| Audio float |80.000×4 |320.000 |
| Ring1 s |16.000×2 |32.000 |
| Filterbank |40×1025×4 |164.000 |
| Mel/dB in-place |40×129×4 |20.640 |
| FFT real + imag |2×2048×4 |16.384 |
| Scratch frame |2048×4 |8.192 |
| Power spectrum |1025×4 |4.100 |
| Tensor arena Node |192×1024 |196.608 |
| **Tổng các vùng trên** | | **921.924** |

Đây là tổng từ khai báo, **không phải số heap sử dụng đo thực tế**. Chưa gồm stack, DMA, allocator overhead, interpreter metadata ngoài arena, UI, network và PPG. Input5.160 byte thuộc arena, không cộng lại nếu đang báo tổng arena. Model347.968 byte là dữ liệu weights/graph, không mặc định nằm trong heap cùng các buffer.

PCM/audio/ring/filterbank và arena có yêu cầu PSRAM trong source. Mel/FFT scratch là static; vị trí cuối phụ thuộc linker. Cần log free internal heap, free PSRAM và largest block trước/sau init để xác nhận.

<a id="muc-5"></a>

## 5. Arena capacity và arena used

Node/3_Model_Complete hiện cấp192 KiB; project profiling cấp1 MiB để tìm mức dùng thực tế. Log đúng model C4 QAT INT8 ghi `arena_used_bytes()=169.380 B` (khoảng165,4 KiB), nên 192 KiB còn khoảng26,6 KiB margin. Capacity là kích thước vùng dự phòng; used là lượng allocator thực sự cần. Không báo capacity là minimum arena.

Cách xác định: chạy model đúng hash, AllocateTensors, nhiều lượt Invoke, ghi used/peak nếu API hỗ trợ, rồi chọn margin có cơ sở. Giảm arena đến sát một lần chạy thành công có thể không an toàn với biến thể runtime/operator khác.

<a id="muc-6"></a>

## 6. Ranh giới xử lý lỗi

Hiện Invoke thất bại trả Asthma_Result có Predicted_Class=-1; `Process_Record_Audio` ánh xạ nhãn ngoài0/1 về UNSURE. Khi nghiệm thu phải theo dõi log Invoke riêng: không coi mọi UNSURE là một kết quả suy luận hợp lệ.

Các pointer/global scratch hiện thiết kế một pipeline suy luận tuần tự. Nếu mở rộng sang task thu âm và task inference chạy song song, cần ownership/buffer kép và đồng bộ; không chia sẻ cùng audio/Mel buffer đang ghi và đang đọc.

