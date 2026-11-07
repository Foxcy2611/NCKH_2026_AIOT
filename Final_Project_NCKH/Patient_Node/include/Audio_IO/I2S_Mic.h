#ifndef NCKH_I2S_MIC_H
#define NCKH_I2S_MIC_H

#include <Arduino.h>
#include <driver/i2s.h>

#include "DSP_Preprocessing/Mel_Scale.h"
#include "system_state.h"

const uint16_t Buffer_Samples = 256;
const uint32_t Sample_Rate = 16000;
const i2s_port_t I2S_Port = I2S_NUM_0;
const uint8_t Amplify_Factor = 1;

// Cấp phát các buffer trong PSRAM và khởi tạo I2S RX cho micro INMP441.
// Phải gọi một lần trong setup() trước mọi hàm thu hoặc xử lý âm thanh.
// Khoi tao I2S va kiem tra nhanh tin hieu vat ly cua INMP441.
// Chi tra true khi driver san sang va vung mau khoi dong khong bi zero/stuck/rac nang.
bool I2S_Mic_Init(int SCK_Pin, int WS_Pin, int SD_Pin);

// Trang thai READY duoc chot sau phep kiem tra luc khoi dong.
// Sau khi READY, khong duoc thao micro trong khi Node dang hoat dong.
bool I2S_Mic_IsReady(void);

// Dừng clock/DMA I2S trước khi vào Light Sleep nhưng giữ nguyên driver và
// các buffer PSRAM. Trả false nếu I2S chưa sẵn sàng hoặc không dừng được.
bool I2S_Mic_Suspend(void);

// Khởi động lại I2S sau Light Sleep và bỏ một vùng mẫu ngắn để DMA/INMP441
// ổn định. Không cấp phát lại buffer và không chạy lại full boot health-check.
bool I2S_Mic_Resume(void);

// Tiền xử lý buffer 5 giây đã thu và chạy mô hình TinyML.
// Trả về nhãn cùng điểm tin cậy đã chuẩn hóa trong khoảng 0.0 đến 1.0.
bool Process_Record_Audio(
    Inference_TinyML_t* out_classification,
    float* out_score
);

/* API thêm */
// Thu đủ 80000 samples ở 16KHz, ko dùng VAD/pre-triger
// Block cho tới khi ghi đủ, hủy vẫn đc nếu là SLEEP
bool I2S_RecordSamples(void);

// Con trỏ buffer chứa kết quả manual check gần nhất
// Hợp lệ nếu record sample return true
const int16_t* I2S_GetRecordedBuffer(void);

// Số sample cố định 1 lần Manual Check (80000)
uint32_t I2S_GetRecordedSampleCount(void);

// Trả về buffer float trong PSRAM dùng chung cho các bước DSP.
// Chỉ hợp lệ sau khi I2S_Mic_Init() thành công.
float* I2S_GetFloatBuffer(void);

// Trả về vùng Mel Spectrogram dùng làm đầu vào cho mô hình TinyML.
// Dữ liệu chỉ hợp lệ sau khi Process_Record_Audio() hoàn tất tiền xử lý.
float (*I2S_GetMelBuffer(void))[MAX_FRAMES];

// Bắt đầu mới hoàn toàn chế độ Monitor: xóa capture cũ và chạy lại warmup micro.
// Gọi khi người dùng bật Monitor hoặc khi hủy Monitor giữa chừng.
void I2S_MonitorReset(void);

// Chuẩn bị đoạn thu kế tiếp trong cùng một phiên vote Monitor.
// Không warmup lại micro nhưng phải tạo mới bộ đệm trước kích hoạt 1 giây.
void I2S_MonitorPrepareNextCapture(void);

// Đọc một chunk, cập nhật ring lịch sử 1 giây và kiểm tra VAD liên tục tại
// STATE_MONITOR_LISTENING. Khi đủ 4 chunk active, hàm truy hồi audio từ chunk
// onset đầu tiên vào buffer 5 giây rồi trả true đúng một lần.
bool I2S_MonitorListenStep(void);

// True sau khi đã bỏ warmup và bộ đệm trước kích hoạt đã đủ đúng 1 giây.
// Dùng để UI đổi từ màn PREPARING sang màn chờ phát hiện âm thanh.
bool I2S_MonitorIsBufferReady(void);

// Thu tiếp sau đoạn onset đã truy hồi; phải gọi liên tục tại
// STATE_MONITOR_CAPTURE. Trả true khi buffer đủ đúng 80000 sample (5 giây
// tính từ onset VAD, không phải 1 giây lịch sử + 4 giây mới).
bool I2S_MonitorCaptureStep(void);

#endif /* NCKH_I2S_MIC_H */
