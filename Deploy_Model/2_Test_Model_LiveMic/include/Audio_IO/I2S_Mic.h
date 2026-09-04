#ifndef I2S_MIC_H
#define I2S_MIC_H

#include <Arduino.h>
#include <driver/i2s.h>

#include "DSP_Preprocessing/DSP_Filter.h"
#include "DSP_Preprocessing/Mel_Scale.h"
#include "Model_AI/Interface_Asthma.h"

#define I2S_WS 15
#define I2S_SD 16 
#define I2S_SCK 14
// #define L_R_Pin 3.3V

/**/ // THAY ĐỔI P4: Chọn đúng một chế độ kiểm tra; direct tensor bỏ qua mic và DSP.
#define RUN_PARITY_20_TEST 0
#define RUN_VALIDATION_108_TEST 0
#define RUN_TEST_113_TEST 0
/**/ // THAY ĐỔI P5: Bật chế độ đo năng lượng VAD, không chạy mô hình.
/**/ // THAY ĐỔI P5: Đã đo xong, trả về 0 để chạy pipeline AI thật.
#define RUN_VAD_CALIBRATION_TEST 0
#define RUN_DIRECT_TENSOR_TEST (RUN_VALIDATION_108_TEST || RUN_TEST_113_TEST)

/**/ // THAY ĐỔI P5: Chỉ cho phép bật đúng một chế độ kiểm tra.
#if (RUN_PARITY_20_TEST + RUN_VALIDATION_108_TEST + RUN_TEST_113_TEST + RUN_VAD_CALIBRATION_TEST) > 1
#error "Chỉ được bật một chế độ kiểm tra tại một thời điểm"
#endif

enum System_State {
    STATE_LISTENING, // Đang nghe ngóng để quyết định
    STATE_RECORDING, // Ghi đủ 5s, chạy đủ 312 lần (312.5 x 256 = 80k)
    STATE_PROCESSING, // TXL
    STATE_INTERFACE, // Chạy AI, gọi hàm Invoke()
    STATE_DONE, // Đã chạy xong bộ kiểm tra tự động
};

// Thu đc 256 mẫu thì ném vào mảng
// Ứng với 256/16k = 0.016s
const uint16_t Buffer_Samples = 256;

// Tốc độ lấy mẫu 16k => 1s đẻ ra 16k mẫu
const uint32_t Sample_Rate = 16000;

const i2s_port_t I2S_Port = I2S_NUM_0;

// Pipeline đã chuẩn hóa từng đoạn theo biên độ lớn nhất, vì vậy nhân 4 không
// làm tín hiệu hữu ích mạnh hơn nhưng có thể gây cắt đỉnh trước khi chuẩn hóa.
const uint8_t Amplify_Factor = 1;

void I2S_Mic_Init(
    int SCK_Pin,
    int WS_Pin,
    int SD_Pin
);

void Process_Audio_Stream(void);

/**/ // THAY ĐỔI P5: Đo năng lượng nền và năng lượng tín hiệu để chọn ngưỡng VAD.
void Run_VAD_Calibration(void);

#endif
