# Defense Package - Bộ tài liệu bảo vệ đề tài

Thư mục này gộp hai nhu cầu khi chuẩn bị bảo vệ:

1. luyện trả lời câu hỏi của hội đồng;
2. mở nhanh hình ảnh, kết quả và log gốc để chứng minh câu trả lời.

Tên `Defense_Package` được chọn thay cho việc để riêng `Committee_QnA` và
`Defense_Evidence`, vì đây là một gói làm việc hoàn chỉnh cho phiên bảo vệ chứ
không chỉ là ngân hàng câu hỏi.

## Cấu trúc

```text
Defense_Package/
├── 01_Committee_QnA/       # 80 câu hỏi và câu trả lời luyện tập
├── 02_Defense_Evidence/    # Bản sao ảnh, bảng dữ liệu và log đã tuyển chọn
└── 03_Defense_Notebook/    # 5 notebook trình chiếu theo từng nhóm phản biện
```

## Cách sử dụng khi tập vấn đáp

1. Đọc câu hỏi trong [`01_Committee_QnA/README.md`](01_Committee_QnA/README.md).
2. Tập trả lời mà chưa nhìn đáp án.
3. Đối chiếu file `Answers/Qxx.md`.
4. Mở [`03_Defense_Notebook/README.md`](03_Defense_Notebook/README.md), chọn notebook đúng chủ đề và chuyển đến đúng mục `Qxx`.
5. Trình bày theo thứ tự: **kết luận → số liệu → hình/log → giới hạn**.

Nhóm Q59–Q80 tập trung vào phản biện lựa chọn: **vì sao dùng phương án hiện tại thay vì phương án thay thế**. Đây là nhóm nên tập sau khi đã nắm luồng tổng thể Q01–Q58.

## Quy tắc minh chứng

- Ảnh và log trong `02_Defense_Evidence` là bản sao phục vụ trình chiếu.
- `Evidence_Index.csv` luôn ghi đường dẫn artifact gốc để truy vết.
- Không biến kết quả mô phỏng/native test thành kết quả phần cứng thật.
- Không tuyên bố một giá trị đã đo nếu artifact chỉ là cấu hình hoặc dự kiến.
- Khi artifact được tái tạo, cần cập nhật lại bản sao và ngày kiểm tra trong chỉ mục.

