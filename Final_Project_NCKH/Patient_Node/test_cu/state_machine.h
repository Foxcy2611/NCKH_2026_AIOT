#ifndef NCKH_STATE_MACHINE_H
#define NCKH_STATE_MACHINE_H

#include <Arduino.h>

#include <stdint.h>
#include "system_state.h"

// 1. Khởi tạo GPIO/ISR 3 nút
// Reset current state về Standby, reset session
// Gọi 1 lần trong setup
void StateMachine_Init(void);

// 2. Đọc event đang chờ từ ISR
// Chạy Handler ứng vs current state
// Gọi liên tục trong loop
void StateMachine_Run(void);

// 3. Return về trạng thái hiện tại
// OLED dựa theo trạng thái hiện tại mà design
Patient_State_t StateMachine_GetCurrentState(void);

// 4. Trả về TRUE nếu SLEEP được yêu cầu nhưng chưa xử lý xong cleanup
// Dùng để dừng sớm thay vì ép cứng phải STOP về STANDBY
bool StateMachine_IsAbortRequested(void);

// 5. Nạp event từ ISR
// Chỉ ghi event vào biến, không làm gì khác
void StateMachine_PushButtonEvent(Button_Event_t btn_evt);

// 6. Kết quả phiên đo
// Audio_IO sẽ gọi hàm này sau khi có kết quả phân loại
// State Machine sẽ update Patient Session và chuyển sang STATE AUDIO RESULT
void StateMachine_SubmitAudioResult(
    Audio_Quality_t quality,
    Interface_TinyML_t classification,
    float model_score
);

// 7. MAX30102 sẽ gọi hàm này sao khi đo xong HR/SpO2
// Để State Machine hoàn thiện session và chuyển sang READY
void StateMachine_SubmitVitals(
    bool vitals_valid,
    uint16_t heart_rate,
    uint16_t spo2
);

// 8. Trả về con trỏ tới session hiện tại (chỉ đọc) 
// Dùng khi cần đóng gói ESP-NOW (PatientEventPacket) từ Patient_Session_t.
const Patient_Session_t* StateMachine_GetCurrentSession(void);

// 9. Gọi hàm này sau khi ghi đủ 80000 samples return true
// Chuyển từ STATE_MANUAL_CHECK/STATE_MONITOR -> PROCESSING
void StateMachine_NotifyCaptureDone(void);

// 10. ESP-NOW module gọi hàm này sau khi gửi packet xong (thành công hoặc đã
// lưu pending để gửi bù sau) -> quay lại STANDBY. Cùng pattern với
// NotifyCaptureDone: chỉ cho transition đúng lúc, không phải nút bấm.
void StateMachine_NotifyEventSent(void);

#endif /* NCKH_STATE_MACHINE_H */