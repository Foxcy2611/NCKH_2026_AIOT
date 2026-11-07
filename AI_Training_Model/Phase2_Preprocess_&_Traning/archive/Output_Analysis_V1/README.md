# Output phân tích model V1

Thư mục này gom toàn bộ kết quả kiểm tra và phân tích của model V0
`SepConv2D + Flatten` cũ. Dữ liệu preprocess và kết quả train vẫn được giữ ở thư mục gốc của Phase 2.

Bạn có thể truy cập link tại đây [V0 Old](../Output_Train_V0/) để biết về Model cũ.

## Cấu trúc

- `Output_Analysis/`: kết quả phân tích baseline cũ, được giữ lại để đối chiếu.
- `Output_Analysis_Accu8931/`: prediction, error và báo cáo của model V1 đã chốt.
- `Output_Playback_Alignment/`: so sánh alignment trên các source playback lỗi.
- `Output_Playback_Offset_Analysis/`: quét nhiều offset crop trên toàn bộ playback.
- `Output_Playback_Delay_Correlation/`: ước lượng độ trễ raw/playback bằng
  cross-correlation.
- `TXT_Analysis/`: các ghi chú và kết luận thủ công theo từng bước phân tích.

## Đường dẫn đầu vào dùng chung

- Preprocess: `../Output_Preprocess/`
- Model và tham số chuẩn hóa V1:
  `../Output_Train_V1_SepConv2D_Flatten/`

Các script `Analyze_*.py` tự tạo lại thư mục đầu ra tương ứng bên trong thư mục
này khi chạy.
