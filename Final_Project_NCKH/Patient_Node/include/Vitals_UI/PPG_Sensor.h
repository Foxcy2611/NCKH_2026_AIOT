#ifndef NCKH_PPG_SENSOR_H
#define NCKH_PPG_SENSOR_H

#include <Arduino.h>

/* =========================================================
 * TRẠNG THÁI ĐO (state machine, không blocking)
 * ========================================================= */
enum MAX30102_State
{
    MAX30102_STATE_COLLECTING,   // đang thu mẫu (lần đầu 100, các lần sau 25)
    MAX30102_STATE_RESULT_READY, // vừa có kết quả HR/SpO2 mới trong lần Poll() này
    MAX30102_STATE_NO_FINGER,    // mất ngón tay giữa chừng, buffer bị reset
    MAX30102_STATE_TIMEOUT       // quá lâu không có mẫu mới (I2C/ngắt lỗi)
};

// Deadline chung của một phiên đo Vitals. State machine cũng dùng đúng giá trị
// này cho trường hợp không có ngón tay, nên mọi nhánh đều tự thoát nhất quán.
static constexpr uint32_t MAX30102_MEASUREMENT_TIMEOUT_MS = 10000UL;

/* =========================================================
 * PUBLIC API
 * ========================================================= */

bool MAX30102_Init(void);

// Chuyển MAX30102 từ shutdown sang SpO2 khi bắt đầu phiên CHECK. Không xóa
// FIFO; phiên đo sạch vẫn được tạo bởi MAX30102_BeginMeasurement().
bool MAX30102_Wake(void);

// Tắt LED RED/IR và ngắt dữ liệu khi không ở phiên CHECK. Cấu hình cảm biến
// vẫn được giữ nên lần CHECK sau không phải reset/khởi tạo lại toàn bộ chip.
bool MAX30102_Shutdown(void);

bool MAX30102_IsActive(void);

/*
 * Bắt đầu một phiên đo độc lập:
 * - bỏ toàn bộ 75/100 mẫu còn giữ từ cửa sổ trước;
 * - vô hiệu cache HR/SpO2 cũ;
 * - xóa FIFO phần cứng và trạng thái interrupt;
 * - khởi động lại mốc timeout.
 *
 * Trả false nếu cảm biến không thể wake hoặc không thể reset FIFO/I2C.
 */
bool MAX30102_BeginMeasurement(void);

/* ISR chỉ set flag, không I2C / delay / Serial. */
void IRAM_ATTR MAX30102_ISR(void);

/*
 * Gọi liên tục trong loop() hoặc 1 task, KHÔNG chặn.
 * Mỗi lần gọi: đọc tối đa các mẫu đang sẵn có trong FIFO (thường 1-4 mẫu)
 * rồi return ngay. Khi đủ mẫu cho 1 lần tính -> tự tính HR/SpO2 và trả
 * trạng thái MAX30102_STATE_RESULT_READY.
 */
MAX30102_State MAX30102_Poll(void);

/*
 * Lấy kết quả HR/SpO2 mới nhất đã tính. Chỉ có ý nghĩa khi cờ valid tương
 * ứng khác 0. Khi bắt đầu phiên mới, mất ngón tay, timeout hoặc thuật toán
 * trả kết quả invalid, giá trị HR/SpO2 được trả về là 0 thay vì sentinel/NaN.
 */
void MAX30102_GetLastResult(
    int32_t *heartRate,
    int8_t *validHeartRate,
    int32_t *spo2,
    int8_t *validSpO2
);

/* Reset toàn bộ buffer, quay lại thu 100 mẫu từ đầu (gọi khi rút ngón tay ra). */
void MAX30102_ResetBuffer(void);

#endif /* NCKH_PPG_SENSOR_H */
