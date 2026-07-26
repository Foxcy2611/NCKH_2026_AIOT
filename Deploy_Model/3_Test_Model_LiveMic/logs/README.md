# 📝 Thư mục Logs - Nhật ký kiểm thử mô hình

## 📌 Tổng quan
Thư mục này được sử dụng để lưu trữ các bản ghi (logs) đầu ra, được copy/paste trực tiếp từ Terminal/Serial Monitor trong quá trình chạy thực tế trên vi điều khiển.

## 🎯 Mục đích
- **Lưu vết dữ liệu:** Ghi nhận lại toàn bộ thông số tính toán (mel_db_buff, input_tensor...) và kết luận của từng mẫu âm thanh thô.
- **Đánh giá suy luận (Inference):** Dùng làm cơ sở để đối chiếu, xác định độ chính xác và kết quả phân loại của mô hình AI (Hen suyễn / Bình thường) qua từng giai đoạn tinh chỉnh.

## 📂 Cấu trúc file
* `*.log`: Các tệp chứa dữ liệu log thô (raw data) trích xuất trực tiếp từ quá trình test (VD: `Raw_Asthma_Phase_1.log`).
* `*.txt`: Các kết luận được đưa ra sau quá trình đối chiếu trực tiếp với các file .log và đưa ra còn đường đi tiếp theo (VD: `Report_Phase_1.txt`).

---
*Lưu ý: Các file trong thư mục này mang tính chất đọc và lưu trữ kết quả kiểm thử, cần có can thiệp vào mã nguồn hay bộ trọng số của mô hình.*