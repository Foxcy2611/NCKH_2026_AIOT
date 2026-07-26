# 🧠 AI Training Pipeline - Quy trình Huấn luyện AI Chuẩn Đoán Hen Suyễn (TinyML) 🚀🩺

Thư mục này chứa toàn bộ quy trình "từ A đến Z" 🅰️➡️🇿, bắt đầu từ thu thập, xử lý âm thanh thô 🎤, trích xuất đặc trưng (Mel-Spectrogram) 🎼, huấn luyện mô hình mạng nơ-ron (TensorFlow/Keras) 🤖, cho đến lượng tử hóa (Quantization) 🗜️ và xuất ra file C-header 📄 để sẵn sàng triển khai lên vi điều khiển ESP32-S3 🎛️.

---

## 💻 1. Cài đặt Môi trường (Setup & Run) 🛠️🔥

Để chạy mượt mà các script huấn luyện AI trong thư mục này, vui lòng cài đặt các thư viện Python sau nhé (Mở CMD hoặc PowerShell lên và gõ lệnh) 💻✨:

    pip install numpy librosa scikit-learn tensorflow matplotlib

⚠️ **LƯU Ý CỰC KỲ QUAN TRỌNG VỀ PHIÊN BẢN PYTHON:** ⚠️
TensorFlow hiện tại hoạt động ổn định nhất trên **Python 3.11 trở về trước** 🐍. Hãy check nhanh phiên bản môi trường Python trên máy của bạn bằng lệnh:

    python --version

🚨 Nếu phiên bản Python của bạn cao hơn 3.11 (vd: 3.12, 3.13), bạn **bắt buộc** phải cài đặt thêm một môi trường Python tương thích nhé (Ưu tiên cài bản **3.11.9** 🌟).
🔗 Tải xuống tại đây luôn: https://www.python.org/downloads/ 📥

---

## ⚙️ 2. Quy Trình Huấn Luyện Cốt Lõi 🎯🧠

Quy trình tạo ra "bộ" 🧠 siêu việt cho ESP32 được chia làm 4 giai đoạn chính:

### 🥇 Giai đoạn 1: Chuẩn bị tập dữ liệu (Data Collection) 📊
*   **Nguồn dữ liệu 🌐:** Dữ liệu âm thanh được tổng hợp công phu từ nhiều nguồn, bao gồm dữ liệu tự thu 🎙️ và tập dữ liệu chuẩn từ cộng đồng. Nguồn Kaggle xịn xò để tham khảo: [Asthma Detection Dataset Version 2](https://www.kaggle.com/datasets/mohammedtawfikmusaed/asthma-detection-dataset-version-2?resource=download) 🔗.
*   **Phân loại 🗂️:** Dữ liệu thô được chia thành 2 nhãn chính: `Asthma` 🤧 (Có tiếng rít đặc trưng của Hen suyễn) và `Non_Asthma` 😌 (Bình thường, tiếng thở khò khè của bệnh khác như COPD, viêm phổi, hoặc tạp âm môi trường).
*   **Lưu ý ❗:** Vui lòng đọc thêm `README.md` tại [Dataset README](Dataset/README.md) để hiểu rõ quy trình phân loại tập dữ liệu để training AI

### 🥈 Giai đoạn 2: Tiền xử lý (Preprocessing & Feature Extraction) 🛠️
*   **Mục đích 🎯:** Máy tính không hiểu âm thanh thô! Cần chuyển đổi sóng âm thanh miền thời gian (WAV) 🌊 sang ảnh phổ tần số (Mel-Spectrogram) 🖼️.
*   **Cách làm (Pipeline DSP 7 bước chuẩn chỉ) 🪄:**
    1.  **Đọc File 📂:** Dùng `librosa.load` ép tần số lấy mẫu về `16kHz`, cố định độ dài `5s` ⏱️.
    2.  **Chuẩn hóa biên độ (Peak Normalization) 📏:** Ép dải biến thiên tín hiệu về khoảng `[-1.0, 1.0]`.
    3.  **Lọc Butterworth Bandpass 🎛️:** Giữ lại dải tần `50Hz - 4000Hz`, gọt sạch rác và nhiễu ở hai đầu.
    4.  **Lọc Pre-emphasis 🚀:** Khuếch đại các tần số cao để làm nổi bật tiếng rít đặc trưng của Hen suyễn.
    5.  **Chia khung & Cửa sổ hóa (Framing & Hamming Window) 🪟:** Băm nhỏ tín hiệu âm thanh thành các khung `25ms` để chống hiện tượng rò rỉ phổ (spectral leakage).
    6.  **STFT (Short-Time Fourier Transform) 🧮:** Biến đổi tín hiệu từ miền thời gian sang miền tần số.
    7.  **Lọc thang Mel (Mel Filterbank) 🎹:** Chuyển đổi sang thang Mel, chuyển năng lượng sang thang đo Decibel (dB) 🔊 và tạo ra bức ảnh Mel-Spectrogram cuối cùng để đưa vào mạng DS-CNN 🕸️.

### 🥉 Giai đoạn 3: Huấn luyện Mô hình (Training - File `6_Train_Model.py`) 🤖

Trong bước này, ma trận đặc trưng sẽ được đưa vào mạng nơ-ron để tìm ra quy luật của tiếng rít Hen suyễn 🤧. Dưới đây là các kỹ thuật tối ưu cốt lõi được áp dụng trong script số 6:

*   **Chuẩn hóa dữ liệu (Min-Max Scaling) 📏:** Do ảnh Mel-Spectrogram thường chứa các giá trị dB âm lớn, hệ thống sẽ tự động ép toàn bộ dữ liệu đầu vào về khoảng `[0, 1]` để mạng học ổn định và hội tụ nhanh hơn ⚡.
*   **Kiến trúc mạng DS-CNN (Depthwise Separable CNN) 🧠:** Thay vì dùng CNN truyền thống khá nặng nề, mô hình sử dụng các lớp `SeparableConv2D`. Đây là kiến trúc siêu nhẹ (chân ái dành riêng cho TinyML 🪶), giúp giảm triệt để số lượng tham số nhưng vẫn thực hiện mượt mà 3 bước: trích xuất đặc trưng cơ bản, đào sâu đặc trưng bệnh lý, và phân tích chi tiết vệt rít 🔍.
*   **Cân bằng trọng số (Class Weights) ⚖️:** Thuật toán tự động tính toán `class_weight='balanced'` để điều chỉnh trọng số học, giúp AI không bị "thiên vị" nếu số lượng sample giữa nhãn `Asthma` và `Non-Asthma` bị chênh lệch 📉📈.
*   **Bộ Callbacks thông minh ⏱️:** Quá trình huấn luyện (Epochs) được giám sát gắt gao bởi các hàm callbacks xịn xò:
    *   **EarlyStopping & ModelCheckpoint 🛑:** Giám sát độ suy hao (`val_loss`). Nếu sau 10 vòng mà AI không thông minh hơn, quá trình sẽ tự động ngắt và chỉ xuất ra file lưu trọng số của epoch tốt nhất (`Bin_Asthma.keras`) 💾.
    *   **ReduceLROnPlateau 🐢:** Khi mô hình bị chững lại (plateau), tốc độ học (Learning Rate) sẽ tự động giảm đi một nửa để AI "nghiền ngẫm" dữ liệu chậm và sâu sắc hơn 🧘‍♂️.
*   **Kết quả tối ưu (Phase 2) 🏆:** Nhờ những tinh chỉnh "tới bến" này, mô hình đã đạt độ chính xác (Test Accuracy) lên tới **94.50%**, với độ nhạy phát hiện Hen suyễn (Recall) đạt **98%** trên tập dữ liệu Test 🎯🔥.

### 🏅 Giai đoạn 4: Lượng tử hóa (Quantization) 🗜️⚡
*   Mô hình TensorFlow gốc dùng số thực dấu phẩy động 32-bit (Float32) 🐘, rất nặng và ngốn RAM.
*   **Quantize 🪄:** Ép kiểu mô hình từ Float32 xuống số nguyên 8-bit (INT8) 🐜. Quá trình này giúp mô hình giảm 4 lần dung lượng 📉 và chạy cực nhanh trên vi điều khiển (ESP32-S3) 🚀 mà độ chính xác (Accuracy) gần như không suy suyển 🎯. Cuối cùng, mô hình được dịch sang mảng byte hex trong file C (`.h`) 📜.

---

## 📂 3. Cấu Trúc Thư Mục & File (Workspace Tree) 🌳📁

Toàn bộ project được tổ chức một cách khoa học để quá trình tiền xử lý, huấn luyện và test diễn ra trơn tru nhất. Dưới đây là bức tranh toàn cảnh:

```text
📦 Asthma_TinyML_Workspace
 ┣ 📂 .vscode/                   # ⚙️ Cấu hình môi trường VS Code
 ┃
 ┣ 📂 Dataset/                   # 🎧 Dữ liệu âm thanh gốc (WAV)
 ┃ ┣ 📂 0_Asthma/                # 👑 [FINAL] Dữ liệu chuẩn Hen suyễn 
 ┃ ┣ 📂 1_Non_Asthma/            # 👑 [FINAL] Dữ liệu chuẩn Không Hen suyễn 
 ┃ ┣ 📂 2_TuThu/                 # 🧱 Nguồn thô: Dữ liệu tự thu từ Micro
 ┃ ┣ 📂 3_asthma/                # 🧱 Nguồn thô: Dữ liệu Hen suyễn ban đầu
 ┃ ┣ 📂 4_Raw_Non_Asthma/        # 🧱 Nguồn thô: Tạp âm môi trường
 ┃ ┗ 📜 README.md                # 📝 Ghi chú riêng cho bộ Dataset
 ┃
 ┣ 📂 Training_Model_Phase_1/    # 👶 Mô hình huấn luyện phiên bản đầu
 ┃ ┣ 📂 4_JPG_Check_Spectrum/    # 👁️ Ảnh phổ Mel để kiểm tra bằng mắt thường
 ┃ ┣ 📂 5_Output_Features/       # 🧪 Ma trận đặc trưng .npy (X_data, Y_labels)
 ┃ ┣ 📂 6_Output_Model/          # 🧠 Chứa model .keras, log CSV và biểu đồ
 ┃ ┗ 📂 7_Output_TFLite/         # 🗜️ Model đã lượng tử hóa (.tflite)
 ┃
 ┣ 📂 Training_Model_Phase_2/    # 🚀 Mô hình hoàn thiện cuối cùng (Chính thức)
 ┃ ┣ 📂 4_JPG_Check_Spectrum/    # (Tương tự Phase 1 nhưng tối ưu hơn)
 ┃ ┣ 📂 5_Output_Features/        
 ┃ ┣ 📂 6_Output_Model/           
 ┃ ┗ 📂 7_Output_TFLite/          
 ┃
 ┣ 📂 8_Exported_C_Headers/         # 🏁 Chứa 2 mẫu test ĐÃ QUA TIỀN XỬ LÝ bằng Python
 ┃ ┣ 📜 Sample_Asthma_1.h         # Mảng C của mẫu CÓ Hen suyễn 
 ┃ ┗ 📜 Sample_Non_Asthma_1.h     # Mảng C của mẫu KHÔNG Hen suyễn 
 ┃
 ┣ 📂 10_Input_Asthma_Raw/          # 🧪 Chứa dữ liệu mảng C âm thanh thô để test DSP ESP32
 ┃ ┣ 📂 Raw_Include_Phase_1/      # Dữ liệu test cơ bản ban đầu
 ┃ ┣ 📂 Raw_Include_Phase_2/      # Dữ liệu test nhiễu nâng cao đã qua tinh chỉnh
 ┃ ┗ 📂 Raw_Include_Phase_3/      # Dữ liệu test tổng hợp cuối cùng
 ┃
 ┣ 📜 1_Split_Audio.py              # ✂️ Cắt âm thanh
 ┣ 📜 2_Prep_Non_Asthma.py          # 🧹 Làm sạch & phân loại data Non-Asthma
 ┣ 📜 3_Prep_Asthma.py              # 🧬 Làm sạch & tăng cường data Asthma
 ┣ 📜 4_Norma_&_Check_Spectrum.py   # 👁️ Chuẩn hóa biên độ & vẽ ảnh phổ
 ┣ 📜 5_Extract_Features.py         # 🧪 Trích xuất Mel-Spectrogram ra file .npy
 ┣ 📜 6_Train_Model.py              # 🏗️ Huấn luyện AI với kiến trúc DS-CNN
 ┣ 📜 7_Quantize_Export.py          # 🗜️ Lượng tử hóa mô hình sang INT8 (.tflite)
 ┣ 📜 8_Exported_C_Headers.py       # 📠 Dịch mô hình .tflite sang mảng Hex (C/C++)
 ┣ 📜 9_Coef_Butter.py              # 🧮 Tính toán hệ số cho bộ lọc Butterworth
 ┣ 📜 10_Test_Asthma_Raw.py         # 🧱 Xuất mảng C từ file WAV để test chay
 ┣ 📜 11_Debug_Deploy.py            # 🕵️‍♂️ Kịch bản debug đối chiếu Python vs ESP32
 ┣ 📜 12_Test_TF_Int8.py            # 🩺 Test suy luận mô hình tĩnh trên Python
 ┣ 📜 13_Test_TF_Quantize.py        # ⚖️ Đánh giá sai số của mô hình sau lượng tử hóa
 ┗ 📜 14_Get_Random_Name.py         # 🎲 Đổi tên file ngẫu nhiên chống trùng lặp
```

---

## ⚠️ 4. Ghi chú: Sự khác biệt giữa Phase 1 và Phase 2 🚨🔍

Trong quá trình huấn luyện và "độ" mô hình, hệ thống đã đẻ ra 2 thư mục:
*   📁 **`Training_Model_Phase_1/` 👶:** Là phiên bản huấn luyện đầu lòng. Dùng để tham khảo và đối chiếu sự tiến hóa của mô hình 📈.
*   📁 **`Training_Model_Phase_2/` 👑:** **ĐÂY LÀ KẾT QUẢ CUỐI CÙNG (END).** Phiên bản này chứa mô hình đã được tinh chỉnh siêu tham số 🎛️, tối ưu hóa dữ liệu đầu vào và đạt độ chính xác đỉnh chóp 🏔️ để triển khai thực tế. Nhớ dùng các file xuất ra từ Phase 2 nhé! 😉

---

## 📜 5. Chức Năng Các File Script Python 🐍⚙️

Hãy chạy các file theo đúng thứ tự đánh số từ 1 đến 14 cho mượt nhé:

**🛠️ Nhóm Xử Lý Dữ Liệu (Data Prep):**
*   **`1_Split_Audio.py` ✂️:** Cắt các file âm thanh dài thành các đoạn tiêu chuẩn.
*   **`2_Prep_Non_Asthma.py` 🧹:** Xử lý, lọc và phân loại tập dữ liệu âm thanh Bình thường/Tạp âm.
*   **`3_Prep_Asthma.py` 🧬:** Xử lý tập dữ liệu Hen suyễn (có thể bao gồm thêm nhiễu, đổi cao độ để Data Augmentation - hack thêm data).
*   **`14_Get_Random_Name.py` 🎲:** Đổi tên file ngẫu nhiên để tránh đụng hàng khi gom dữ liệu từ tứ phương tám hướng.

**🎼 Nhóm Trích Xuất Đặc Trưng (Feature Extraction):**
*   **`4_Norma_&_Check_Spectrum.py` 👁️:** Chuẩn hóa biên độ âm thanh và xuất ra ảnh phổ để soi lỗi dữ liệu bằng mắt thường.
*   **`5_Extract_Features.py` 🧪:** Chạy STFT, Mel Filterbank và đóng gói ma trận đặc trưng thành file `.npy` để Training.
*   **`9_Coef_Butter.py` 🧮:** Tính toán cấu hình hệ số (Coefficients) cho bộ lọc Butterworth Bandpass dùng cho C++.

**🚀 Nhóm Huấn Luyện & Chuyển Đổi (Train & Export):**
*   **`6_Train_Model.py` 🏗️:** Build mạng AI, nạp đồ ăn (`.npy`) vào huấn luyện và xuất ra file `.keras` xịn xò.
*   **`7_Quantize_Export.py` 🗜️:** Chuyển đổi `.keras` sang chuẩn TinyML (`.tflite`) và ép mỡ (lượng tử hóa INT8).
*   **`8_Exported_C_Headers.py` 📠:** Dịch file `.tflite` thành mảng Byte trong file `Asthma_Model.h`.

**🐛 Nhóm Kiểm Thử & Debug (Testing & Debugging):**
*   **`10_Test_Asthma_Raw.py` 🧱:** Chuyển file WAV thành mảng C thô phục vụ test độc lập phần cứng.
*   **`11_Debug_Deploy.py` 🕵️‍♂️:** Kịch bản soi lỗi, so sánh đối chiếu sai số giữa luồng chạy Python và luồng chạy C++ trên ESP32.
*   **`12_Test_TF_Int8.py` 🩺:** Chạy test mô hình tĩnh trên Python trước khi nạp để xem có ổn áp không.
*   **`13_Test_TF_Quantize.py` ⚖️:** Test kiểm tra chéo mô hình sau khi đã bị lượng tử hóa INT8 để đánh giá độ suy giảm chính xác.