# Kết quả chọn alignment bằng Train + Validation

Test chưa được sử dụng trong bước này.

## Onset/lead-in

- Detection rate: `1.0000`
- Median onset: `1.2100 s`
- Độ lệch chuẩn: `0.7463 s`
- Khoảng P90-P10: `0.6390 s`
- Nhận xét tự động: Onset dao động đáng kể hoặc phát hiện chưa đủ ổn định; ưu tiên đánh giá phương án `detect onset -> crop 5 s` thay vì hard-code 1 s.

## Phương án đứng đầu theo Train + Validation

- Alignment: `fixed_0.25s`
- Train Asthma recall: `0.968750000`
- Validation Asthma recall: `1.000000000`
- Điểm min recall: `0.968750000`

Đây chỉ là đề xuất để xem xét, chưa tự động chốt Test.
Muốn xác nhận Test, sửa cấu hình đầu script sang `CONFIRM_TEST` và chỉ
khai báo đúng một phương án đã chốt.
