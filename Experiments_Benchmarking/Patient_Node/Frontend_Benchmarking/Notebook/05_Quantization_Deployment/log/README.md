# Log profiling ESP32-S3 dùng trong notebook D

Thư mục này chứa bản sao log đo tĩnh được notebook `D_Quantization_ESP32S3_ThreeLogs_Final.ipynb` đọc trực tiếp:

| File | Ứng viên |
|---|---|
| `F0_PTQ.log` | Baseline F0, PTQ INT8 |
| `C3_QAT.log` | Combo C3, QAT INT8 |
| `C4_QAT.log` | Combo C4, QAT INT8 |

Các log được copy từ `Deploy_Model/1_Test_Model_Static_Profiling`. Chúng phản ánh kích thước arena và thời gian `Invoke()` của model trên tensor tĩnh; không bao gồm thời gian thu microphone hoặc tiền xử lý DSP/Log-Mel.

Không sửa số đo thủ công. Khi benchmark lại firmware, hãy thay log bằng output mới và chạy lại notebook D.
