#ifndef NCKH_PPG_SENSOR_H
#define NCKH_PPG_SENSOR_H

#include <Arduino.h>

/* =========================================================
 * PINOUT - ESP32 DEVKIT
 * ========================================================= */
#define SDA_PIN 21
#define SCL_PIN 22
#define INT_PIN 27

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

/* =========================================================
 * PUBLIC API
 * ========================================================= */

bool MAX30102_Init(void);

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
 * Lấy kết quả HR/SpO2 mới nhất đã tính (chỉ có ý nghĩa ngay sau khi
 * MAX30102_Poll() trả về MAX30102_STATE_RESULT_READY, nhưng vẫn an toàn
 * gọi bất cứ lúc nào để đọc giá trị cache gần nhất).
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