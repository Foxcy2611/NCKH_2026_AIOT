# Defense Evidence - Minh chứng phục vụ vấn đáp

Folder này chứa một bộ artifact nhỏ, ổn định và dễ mở khi hội đồng đặt câu hỏi.
Các file không thay thế output nghiên cứu gốc; nguồn thật được ghi trong
[`Evidence_Index.csv`](Evidence_Index.csv).

## Nhóm minh chứng chính

| Câu hỏi | Minh chứng ưu tiên | Nội dung trình bày |
|---|---|---|
| Q01 | `figures/01_Dataset/` | Core theo bệnh nhân, Playback theo WAV nguồn, Environment theo session, thành phần nhãn |
| Q03-Q07 | `figures/02_DSP/` | PCM16 → Butterworth → STFT/Mel → Log-Mel C4 `40×129×1` |
| Q12-Q14 | `figures/03_AI_Model/` | Training history, FP32/QAT, FN/FP và kết quả lượng tử |
| Q21-Q23 | `figures/04_Final_Validation/`, workflow | CHECK, threshold, Quality Gate và VAD |
| Q25-Q27 | `figures/05_Deployment/`, `logs/C4_QAT_ESP32_Static.log` | Model size, arena dùng thực tế, latency và parity |
| Q36-Q39 | source Gateway + notebook | Gói 56 byte, Queue, AES-GCM, ACK/NACK |
| Q44-Q48 | source Gateway + `Gateway_Test_Result.txt` | Wi-Fi/LTE failover, MQTT; phân biệt native test và hardware test |
| Q49-Q53 | `data/Dashboard_MQTT_Example.json` | JSON MQTT ánh xạ lên Dashboard |
| Q54-Q58 | `figures/06_System/` và log tích hợp | Luồng toàn hệ thống và các giới hạn khi mất Gateway/MQTT |
| Q59-Q65 | Dataset + DSP | Patient split, Playback, silence, cửa sổ 5 s, pre-emphasis và C4 |
| Q66-Q70 | AI Model + Final Validation | Kiến trúc, seed, metric, QAT/PTQ và threshold |
| Q71-Q80 | Validation + Deployment + System | VAD/Quality Gate, edge AI, truyền thông, vitals, giới hạn và parity |

## Ảnh nên ưu tiên khi hội đồng phản biện

- `01_Dataset/03_Playback_Ablation_V2_V3.png`: trả lời Playback có thực sự cần thiết hay không.
- `02_DSP/05_C4_LogMel_Disease_Comparison.png`: minh họa đặc trưng đầu vào cuối cùng.
- `03_AI_Model/04_Quantization_Method_Overview.png`: đối chiếu FP32, PTQ và QAT.
- `03_AI_Model/06_Test_FN_FP_Heatmaps.png`: giải thích vì sao không chỉ nhìn Accuracy.
- `05_Deployment/01_ESP32_Invoke_Logs.png`: chứng minh model đã chạy trên MCU.
- `06_System/01_System_Workflow.png`: trả lời luồng end-to-end và tình huống mất Gateway.

Điều hướng trình chiếu nằm tại [`../03_Defense_Notebook/README.md`](../03_Defense_Notebook/README.md).

## Minh chứng bổ sung nên chụp/thu sau

Hiện repository chưa có đủ ảnh hoặc log phần cứng cho mọi câu hỏi. Nên bổ sung:

- ảnh OLED sau CHECK và MONITOR;
- log Node gửi packet, nhận ACK và trường hợp retry hết;
- log phần cứng thật `Wi-Fi down → 15 s → LTE attach → MQTT connected`;
- ảnh Dashboard đầy đủ các tab khi nhận một JSON thực;
- demo Gateway tắt, Node vẫn suy luận cục bộ;
- ảnh đo dòng/điện áp ở Standby và Light Sleep;
- log Quality Gate/VAD trên phiên thu thực tế mới.

Các bằng chứng trên mạnh hơn sơ đồ lý thuyết vì chứng minh trực tiếp hành vi của
build cuối trên phần cứng.

