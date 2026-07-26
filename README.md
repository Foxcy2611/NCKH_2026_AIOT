# 🫁 Edge AI & IoT: Hệ Thống Giám Sát, Dự Báo Và Cảnh Báo Sớm Hen Suyễn Đa Yếu Tố

![ESP32](https://img.shields.io/badge/MCU-ESP32%20Dual--Core-red.svg)
![OS](https://img.shields.io/badge/OS-FreeRTOS-blue.svg)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![AI](https://img.shields.io/badge/AI-TensorFlow%20Lite%20Micro-orange.svg)
![C](https://img.shields.io/badge/C-00599C?style=for-the-badge&logo=c&logoColor=white)
![C++](https://img.shields.io/badge/C++-00599C?style=for-the-badge&logo=c%2B%2B&logoColor=white)
![Qt](https://img.shields.io/badge/Qt-6-41CD52?style=for-the-badge&logo=qt&logoColor=white)
![Network](https://img.shields.io/badge/Network-ESP--NOW%20%7C%204G%20LTE%20%7C%20MQTT-brightgreen.svg)

> 🔬 **Tên đề tài Nghiên cứu:** Nghiên cứu, thiết kế và chế tạo hệ thống IoT ứng dụng TinyML hỗ trợ theo dõi và cảnh báo sớm cho bệnh nhân hen suyễn.

---

## 📝 Giới thiệu

Dự án phát triển một hệ thống nhúng phân tán (**Distributed Embedded System**) nhằm giám sát toàn diện bệnh nhân hen suyễn. Khác với các hệ thống truyền thống, thiết bị không chỉ đo chỉ số sinh tồn (Nhịp tim, SpO2, Nhiệt độ cơ thể, Âm thanh hô hấp) mà còn theo dõi liên tục các thông số môi trường xung quanh (CO2, VOC, Nhiệt độ, Độ ẩm) — vốn là các tác nhân chính gây khởi phát cơn hen.

Trí tuệ nhân tạo (**TinyML**) được huấn luyện bằng Python (TensorFlow/Keras), lượng tử hóa INT8, và tích hợp trực tiếp trên Node Cảm biến (**Edge AI — ESP32-S3**) để phân tích âm thanh hô hấp theo thời gian thực, đưa ra mức độ cảnh báo trước khi gửi qua Gateway 4G/MQTT về trung tâm giám sát.

---

## 🚀 Tính năng nổi bật

- 🧠 **Edge AI (TinyML) trên ESP32-S3:** Mô hình DS-CNN (SeparableConv2D) nhận diện tiếng rít hen suyễn (wheezing) từ Mel-Spectrogram, chạy suy luận INT8 hoàn toàn on-device qua TensorFlow Lite Micro.
- 🎛️ **Pipeline DSP tự viết bằng C++:** Butterworth Bandpass (dạng SOS/cascade biquad), Pre-emphasis, STFT + Mel Filterbank (thang Slaney, chuẩn hóa Slaney-norm) — mô phỏng chính xác 1-1 với pipeline tiền xử lý Python dùng để train model.
- 🛡️ **Cơ chế quyết định chống nhiễu:** Ngưỡng 3 vùng (Asthma / Không chắc chắn / Bình thường) kết hợp Voting 3 lần đo liên tiếp, giảm đáng kể tỷ lệ báo động giả từ nhiễu môi trường thực tế.
- 🔗 **Sensor Fusion đa kênh:** Driver tự viết cho các module cảm biến sinh tồn và môi trường, đo đồng thời nhịp tim/SpO2, nhiệt độ cơ thể không tiếp xúc, khí CO2/VOC, nhiệt độ/độ ẩm/áp suất, và định vị GPS.
- 📡 **Mạng cục bộ ESP-NOW:** Truyền dữ liệu và trạng thái khẩn cấp giữa Sensor Node và Gateway, tốc độ cao và tiết kiệm năng lượng.
- ⏱️ **FreeRTOS Task Scheduling:** Quản lý đồng thời nhiều tác vụ đọc cảm biến phức tạp qua cơ chế Queue.
- 🚨 **Cảnh báo Đa phương thức:**
  - 📍 *Tại chỗ:* Màn hình OLED & Còi Buzzer.
  - 📱 *Từ xa:* SMS và gọi điện khẩn cấp qua module 4G A7680C kèm tọa độ GPS (NEO-M8N).
- 🖥️ **Giám sát Trung tâm:** Dashboard Qt6/QML kéo dữ liệu qua MQTT, kết hợp Firebase lưu trữ lịch sử phục vụ tái huấn luyện AI.

---

## ⭐ Sơ đồ hệ thống

<img width="967" height="821" alt="Screenshot 2026-07-22 000827" src="https://github.com/user-attachments/assets/452edd4e-4338-4e8b-9083-b12c9295a58d" />

---

## 🛠️ Yêu cầu Phần cứng (Hardware Requirements)

* ⚙️ **Vi điều khiển chính:** ESP32 (Node Gateway) & ESP32-S3-N16R8 (Node AI/Sensor — có PSRAM cho tensor arena)
* 🎤 **Cảm biến Âm thanh:** Micro INMP441 (Giao tiếp I2S)
* ❤️ **Cảm biến Sinh tồn:**
  * MAX30102 — Nhịp tim (HR) & SpO2
  * MLX90614 — Nhiệt độ cơ thể không tiếp xúc (Giao tiếp I2C)
* 🌤️ **Cảm biến Môi trường:** DHT11, BMP280, SGP30 (CO2/VOC)
* 🌍 **Định vị & Kết nối diện rộng:** NEO-M8N (GPS/GNSS), A7680C (4G LTE)
* 🔔 **Module Cảnh báo:** Còi Buzzer, Màn hình OLED SSD1306

> 📌 *Sơ đồ pinout chi tiết (ESP32 thường, ESP32-S3, và bảng bố trí SRAM/PSRAM) xem tại thư mục `ESP32_Pinout/`.*

---

## 🏗 Kiến trúc Hệ thống

Hệ thống được thiết kế theo kiến trúc 2 Node xử lý song song, giao tiếp qua giao thức ESP-NOW:

### 1. Node Cảm biến & AI (ESP32-S3)
Đảm nhiệm đọc dữ liệu môi trường/sinh tồn, thu âm thanh hô hấp, chạy mô hình AI on-device và cảnh báo tại chỗ.
- 📡 **Lớp Cảm biến (FreeRTOS Tasks):**
  - `MAX30102`: Nhịp tim (HR) và SpO2.
  - `INMP441`: Microphone (I2S), thu âm thanh hô hấp 5 giây/lần.
  - `SGP30`: Theo dõi CO2 và VOC.
  - `DHT11 + BMP280`: Nhiệt độ, độ ẩm, áp suất khí quyển.
  - `MLX90614`: Nhiệt độ cơ thể, đo không tiếp xúc qua I2C.
- 🧠 **Lớp Xử lý AI (chi tiết xem mục "Pipeline Huấn luyện & Triển khai AI"):** Chuẩn hóa → Butterworth Bandpass → Pre-emphasis → STFT/Mel-Spectrogram → dB → Quantize INT8 → TFLite Micro Invoke → Ngưỡng 3 vùng + Voting 3 lần đo.
- 📺 **Lớp Đầu ra:** Hiển thị OLED, kích hoạt Buzzer, gửi gói tin `{raw_data + alert_level}` qua ESP-NOW.

### 2. Node Gateway (Xử lý Đám mây & Khẩn cấp)
Đóng vai trò trạm trung chuyển dữ liệu diện rộng và cảnh báo khẩn cấp độc lập.
- 📥 **Lớp Đầu vào:** Nhận dữ liệu qua ESP-NOW; đọc liên tục tọa độ từ GPS NEO-M8N (Multi-GNSS) qua UART.
- ⚙️ **Lớp Xử lý (FreeRTOS Tasks):**
  - *Task 1 (MQTT Publish):* Đóng gói `raw_data`, Publish lên Mosquitto Broker để UI/Dashboard kéo về.
  - *Task 2 (SIM Alert):* Giám sát `alert_level`; nếu phát hiện cơn hen nguy kịch, kích hoạt module 4G A7680C gửi SMS + gọi cứu trợ (fallback: publish qua MQTT nếu có kết nối 4G).

### 3. Server & Application UI
- ☁️ **Mosquitto Broker:** Điều phối bản tin MQTT (Local/VPS).
- 📊 **QML Dashboard (Qt6/C++):** Hiển thị Biểu đồ (Chart), Bản đồ vị trí (Map), Bảng cảnh báo (Alert panel).
- 🔥 **Firebase:** Đồng bộ và lưu trữ chuỗi dữ liệu lịch sử (Cloud log) phục vụ tái huấn luyện AI.

---

## 🧠 Pipeline Huấn luyện & Triển khai AI (TinyML)

Đây là phần lõi công nghệ của dự án — quy trình đầy đủ từ dữ liệu thô đến firmware chạy trên ESP32-S3.

### A. Huấn luyện mô hình (Python) — Thư mục `AI_Training_Model/`

| Bước | Script | Vai trò |
|:---:|---|---|
| **1–2** | `1_Split_Audio.py`, `2_Prep_Non_Asthma.py` | Băm nhỏ audio tự thu, chuẩn hóa tập Non-Asthma |
| **3** | `3_Prep_Asthma.py` | Data augmentation tập Asthma (mix nhiễu, time-shift, white noise, time-stretch, pitch-shift) để cân bằng 1000/1000 mẫu |
| **4** | `4_Norma_&_Check_Spectrum.py` | Phân tích phổ, chốt dải tần Bandpass (100–2000 Hz) |
| **5** | `5_Extract_Features.py` | Trích xuất Mel-Spectrogram (Slaney scale, `power=2.0`, `top_db=80`) → `.npy` |
| **6** | `6_Train_Model.py` | Train DS-CNN (SeparableConv2D + BatchNorm), chuẩn hóa Min-Max toàn cục |
| **7** | `7_Quantize_Export.py` | Lượng tử hóa INT8 (representative dataset cân bằng 2 lớp), xuất `Asthma_Model.h` |
| **9** | `9_Coef_Butter.py` | Trích hệ số Butterworth dạng SOS cho C++ |
| **10–14** | `10_Test_Asthma_Raw.py` → `14_Get_Random_Name.py` | Bộ công cụ kiểm thử: xuất mẫu raw sang C++, đối chiếu Mel-Spectrogram Python↔C++, kiểm tra model không suy biến, test số lượng lớn mẫu ngẫu nhiên |

🏆 **Kết quả huấn luyện (bản mới nhất):** Test Accuracy ~93.5%, Precision/Recall cân bằng giữa 2 lớp Asthma/Non-Asthma.

### B. Triển khai lên ESP32-S3 (C++) — Thư mục `Deploy_Model/`

Quy trình kiểm thử đi qua 4 giai đoạn (chi tiết xem `Deploy_Model/README.md`):

1. 🧪 **Test tĩnh (Static Inference):** Xác nhận TFLite Micro load model và suy luận đúng trên phần cứng.
2. ⚡ **Ép xung & Đo lường (Profiling):** Đo latency, tối ưu `tensor_arena`, bật tối ưu vector hóa ESP-NN.
3. 🎤 **Kiểm thử toàn diện & Xử lý nhiễu (Real-time Pipeline):** Nối thông Micro → DSP → AI, phát hiện và xử lý vấn đề nhiễu môi trường thực tế qua ngưỡng 3 vùng + Voting.
4. 📦 **Đóng gói chính thức (Final Deployment):** Dọn dẹp mã nguồn, loại bỏ toàn bộ debug/test code, chỉ giữ vòng lặp sản xuất tinh gọn: `STATE_LISTENING → STATE_RECORDING → STATE_PROCESSING → STATE_INTERFACE`.

> 💡 *Toàn bộ quá trình chuyển đổi thuật toán DSP từ Python sang C++ (Butterworth SOS, Mel Slaney-scale, quantize INT8) được ghi chú chi tiết tại `Deploy_Model/doc/`.*

---

## 📊 Kết nối MQTT & Dashboard (Prototype)

Thư mục `ESP32-Qt-Telemetry/` chứa bản thử nghiệm đầu tiên của luồng dữ liệu MQTT:
- 🟢 `QtEnvDash-ESP32/`: Firmware ESP32 đọc DHT11, publish dữ liệu lên MQTT Broker.
- 📈 `Dashboard_DHT11/`: Ứng dụng Qt6 subscribe MQTT, vẽ biểu đồ thời gian thực.

*Đây là bản proof-of-concept cho luồng Gateway → MQTT → Dashboard, sẽ được mở rộng đầy đủ (thêm cảm biến, alert panel, bản đồ GPS) trong `Final_Project_NCKH/`.*

---

## 🔧 Driver Cảm biến (Sensor Suite)

Thay vì sử dụng các thư viện rác/chắp vá trên mạng, thư mục `ESP32-Sensor_Suite/` chứa toàn bộ driver C++ **tự viết và tối ưu hóa riêng** cho hệ sinh thái của dự án (DHT11, MAX30102, MLX90614, A7680C, BMP280, SGP30, NEO-M8N, SSD1306). 

Đặc điểm kiến trúc của bộ thư viện này:
- **Thiết kế hướng đối tượng (OOP):** Mỗi loại cảm biến được đóng gói thành một C++ Class riêng biệt (VD: `class Max30102_Sensor`), giúp mã nguồn module hóa, dễ bảo trì và dễ khởi tạo nhiều object nếu dùng nhiều cảm biến cùng loại.
- **Quản lý Bus chia sẻ (Mutex/Semaphore):** Tích hợp an toàn cơ chế khóa của FreeRTOS để nhiều task có thể đọc dữ liệu đồng thời qua chung 1 chuẩn giao tiếp (I2C/SPI) mà không bị xung đột tài nguyên.
- **Giao diện chuẩn hóa (Unified API):** Cung cấp các hàm gọi nhất quán như `init()`, `read()`, `calibrate()` giúp lớp Application (chương trình chính) gọi dữ liệu mượt mà, ẩn đi hoàn toàn sự phức tạp của thanh ghi (Registers) bên dưới.

Chi tiết kiến trúc từng driver, xem ở đây [ESP32 Module Link](./ESP32-Sensor_Suite/README.md).

---

## 📂 Tổ chức Thư mục Dự án (Cấp cao nhất)

```text
NCKH_2026_AIOT/
│
├── AI_Training_Model/          # Toàn bộ pipeline huấn luyện AI bằng Python (5→14, xem mục A)
│
├── Deploy_Model/               # Triển khai model lên ESP32-S3 qua 4 giai đoạn (xem mục B)
│   ├── 1_Test_Model_Static/
│   ├── 2_Test_Model_Profiling/
│   ├── 3_Test_Model_LiveMic/
│   └── 4_Test_Model_Official_Final/
│
├── ESP32_Pinout/               # Sơ đồ pinout ESP32/ESP32-S3, bảng bố trí SRAM/PSRAM
│
├── ESP32-Qt-Telemetry/         # Prototype luồng MQTT: firmware ESP32 + Dashboard Qt6
│   ├── QtEnvDash-ESP32/
│   └── Dashboard_DHT11/
│
├── ESP32-Sensor_Suite/         # Driver C++ cho các module cảm biến của dự án
│
└── Final_Project_NCKH/         # Tổng hợp toàn bộ firmware chính thức (đang cập nhật)
```

---

## 🛠 Cài đặt và Phát triển

- **Môi trường AI:** Python 3.x, TensorFlow/Keras, librosa, scipy — xem `AI_Training_Model/requirements.txt` (nếu có) hoặc cài thủ công theo import ở đầu mỗi script.
- **Môi trường Firmware:** PlatformIO (VS Code), framework Arduino cho ESP32/ESP32-S3.
- **Môi trường Dashboard:** Qt Creator (Qt6), MQTT client library.
- **Cấu hình phần cứng:** Kiểm tra kỹ sơ đồ đấu nối chân (I2C, SPI, UART, I2S) tại `ESP32_Pinout/`.

---

## 📌 Trạng thái hiện tại

- ✅ Pipeline huấn luyện AI (Python) hoàn chỉnh, đã kiểm chứng qua nhiều vòng đối chiếu Python↔C++.
- ✅ Firmware nhận diện Asthma trên ESP32-S3 (`Deploy_Model/4_Test_Model_Official_Final`) đã đạt bản ổn định, test qua mic thật cho kết quả nhất quán.
- 🚧 Tích hợp toàn bộ cảm biến + AI + ESP-NOW + Gateway vào `Final_Project_NCKH/` — đang triển khai.
- 🚧 Dashboard Qt6 đầy đủ (Chart, Map, Alert Panel) — đang mở rộng từ bản prototype MQTT hiện có.

---

*Dự án NCKH thực hiện bởi: ARM LAB - PTIT.*