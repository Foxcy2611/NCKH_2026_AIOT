# 🌐 Quy trình Train AI Model

## Giai đoạn 1: Thu thập & Gán nhãn (Data Collection & Labeling) - Tìm data và phân loại

> AI không học từ không khí, nó học từ ví dụ. Cần chuẩn bị dữ liệu đầu vào cực kỳ chuẩn.

* Với INMP441 (Âm thanh): Thu thập hàng trăm/ngàn file .wav ngắn (1-2 giây) và chia vào các thư mục rõ ràng:
  * Cough_asthma (ho do hen)
  * Wheeze (tiếng khò khè)
  * Normal_speech (nói chuyện)
  * Background_noise (tiếng quạt, tiếng đường phố)

* Với Cảm biến (SpO2, Bụi mịn, Khí độc): Thu thập các mảng số liệu tương ứng với các trạng thái: Bình thường, Nguy cơ, Đang lên cơn hen.

> Bí quyết: Dữ liệu của càng đa dạng (nhiều người ho khác nhau, nhiều môi trường nhiễu khác nhau), con AI dự đoán chuẩn và ít đoán sai.

## Giai đoạn 2: Tiền xử lý (Preprocessing) - Xử lý data

> Nhét nguyên file .wav vào AI là nó "chết nghẹn" ngay. Sử dụng code Python (thư viện librosa) để biến đổi.

* Trích xuất đặc trưng:
  * Chuyển sóng âm thành biểu đồ MFCC
  * Đây là lúc sóng âm thanh biến thành một ma trận số liệu toán học gọn gàng.

* Chuẩn hóa (Normalization):
  * Dữ liệu SpO2 dao động từ 90-100, nhưng dữ liệu bụi mịn có thể từ 10-500.
  * Cần phải đưa tất cả về cùng một hệ quy chiếu (ví dụ từ 0 đến 1) bằng Scikit-learn để AI không bị "thiên vị" cảm biến nào.

## Giai đoạn 3: Huấn luyện (Training)

> Đây là lúc viết code dùng TensorFlow/Keras để tạo hình Mạng Nơ-ron.

* Định nghĩa kiến trúc mô hình (ví dụ: một mạng CNN 1D để phân tích MFCC).
  * Đưa dữ liệu đã tiền xử lý ở Bước 2 vào.
  * AI sẽ bắt đầu lặp đi lặp lại nhiều vòng (gọi là Epochs).
  * Ở mỗi vòng, nó thử đoán, nếu sai nó sẽ tự điều chỉnh lại các "trọng số" toán học bên trong nó để lần sau đoán đúng hơn.
    
* Quá trình này tạo ra 2 đường cong sống còn:
  * Đường Loss (Độ lỗi - càng thấp càng tốt)
  * Đường Accuracy (Độ chính xác - càng cao càng tốt).

## Giai đoạn 4: Đánh giá & Tinh chỉnh (Evaluation & Tuning) - Kiểm tra chất lượng

> Không phải cứ Train xong là đem xài luôn. Cần phải dùng một bộ dữ liệu "Lạ" (Validation/Test Set) mà AI chưa từng thấy bao giờ để test nó.

* Nếu nó nhận diện đúng 95% dữ liệu học, nhưng chỉ nhận diện đúng 50% dữ liệu test
  *  AI của bạn bị "Học Vẹt" (Overfitting).
  *  Lúc này cần phải quay lại Bước 3 để chỉnh sửa (thêm nhiễu vào dữ liệu, giảm bớt lớp nơ-ron).

## Giai đoạn 5: Ép khuôn & Triển khai (Deploy to ESP32) - Nhét não vào vi điều khiển

> Sau khi đã có một model Keras (.h5) cực kỳ thông minh trên máy tính:

* Dùng TFLite Converter ép nó từ dạng số thực 32-bit to đùng xuống dạng số nguyên 8-bit siêu nhẹ (Quantization).
* Chuyển file .tflite thành một mảng code C++ (Hex array).
* Nạp mảng C++ đó vào ESP32, gọi hàm Invoke() của thư viện TFLite Micro

---   
   ESP32 đã biết nghe tiếng ho.
