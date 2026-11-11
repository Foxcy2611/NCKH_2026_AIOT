# Defense Notebooks - Bộ notebook trình chiếu vấn đáp

Các notebook trong thư mục này là **bảng minh chứng để mở khi hội đồng hỏi**, không phải pipeline tạo lại kết quả nghiên cứu. Chúng chỉ đọc ảnh, CSV, JSON, log và source đã có trong repository.

## Danh sách notebook

| Thứ tự | Notebook | Dùng khi hội đồng hỏi |
|---:|---|---|
| 0 | [`Defense_Evidence_Presentation.ipynb`](Defense_Evidence_Presentation.ipynb) | Tổng quan nhanh toàn hệ thống theo Q01, Q03, Q14, Q21, Q25, Q36, Q44, Q50, Q54 |
| 1 | [`01_Dataset_DSP_Evidence.ipynb`](01_Dataset_DSP_Evidence.ipynb) | Dataset split, Playback, silence, cửa sổ 5 s, Butterworth, Log-Mel và frontend C4 |
| 2 | [`02_Model_Selection_Quantization.ipynb`](02_Model_Selection_Quantization.ipynb) | So sánh kiến trúc, seed, Accuracy/Recall/FN, FP32–PTQ–QAT và lý do chốt model |
| 3 | [`03_Embedded_System_Evidence.ipynb`](03_Embedded_System_Evidence.ipynb) | VAD, Quality Gate, threshold, TFLM, parity Python/C++, ESP-NOW, Gateway và Dashboard |
| 4 | [`04_Why_Not_Tradeoffs.ipynb`](04_Why_Not_Tradeoffs.ipynb) | Tập nhanh nhóm Q59–Q80: “vì sao dùng A thay vì B” và giới hạn của lựa chọn |

## Cách dùng khi bảo vệ

1. Trước buổi bảo vệ, mở từng notebook và chọn **Restart Kernel + Run All**.
2. Giữ notebook `04_Why_Not_Tradeoffs.ipynb` ở một tab để tra nhanh mã câu hỏi.
3. Khi được hỏi, trả lời bằng lời trước theo cấu trúc:
   **kết luận → trade-off → số liệu → giới hạn**.
4. Chỉ sau đó mới mở hình, bảng hoặc log tương ứng.
5. Nếu một cell báo thiếu file, kiểm tra `Defense_Package/02_Defense_Evidence/Evidence_Index.csv` để truy về artifact gốc.

## Nguyên tắc trình bày

- Không nói “tốt nhất” nếu số liệu chỉ chứng minh “được chọn cho pipeline cuối”.
- Không dùng Test như bằng chứng đã tham gia tối ưu nếu Test chỉ dùng hậu kiểm.
- Không gọi native/mock test là kiểm thử phần cứng.
- Với Wi-Fi/LTE failover, hiện chỉ trình bày code + native test cho đến khi có log hardware thật.
- Với QAT, nói rõ QAT **không mặc định** tốt hơn PTQ; kết luận chỉ áp dụng cho checkpoint đã đo.
- Các notebook không thay thế file trả lời chi tiết trong [`../01_Committee_QnA/Answers/`](../01_Committee_QnA/Answers/).

## Phụ thuộc tối thiểu

```powershell
py -3.11 -m pip install jupyter pandas matplotlib
py -3.11 -m jupyter notebook
```

Notebook tự tìm repository root bằng folder `Defense_Package`, nên có thể mở từ VS Code hoặc Jupyter mà không cần sửa đường dẫn tuyệt đối.

