#ifndef NCKH_STATE_MACHINE_H
#define NCKH_STATE_MACHINE_H

#include <Arduino.h>
#include <stdint.h>

#include "system_state.h"

// Khởi tạo trạng thái, phiên dữ liệu và ngắt của ba nút vật lý.
void StateMachine_Init(void);

// Xử lý cờ nút, yêu cầu hủy và một bước của máy trạng thái.
void StateMachine_Run(void);

// Trả về state hệ thống tại thời điểm gọi.
Patient_State_t StateMachine_GetCurrentState(void);

// Cho tác vụ thu âm kiểm tra nhanh yêu cầu SLEEP/STOP được ISR đặt hay chưa.
bool StateMachine_IsAbortRequested(void);

// Dùng cho ISR hoặc chương trình kiểm thử; hàm chỉ đặt cờ sự kiện.
void StateMachine_PushButtonEvent(Button_Event_t event);

// VAD báo bắt đầu một phiên thu tự động.
void StateMachine_NotifyMonitorTriggered(void);

// Audio_IO báo đã ghi đủ mẫu: CAPTURE -> AUDIO_QUALITY.
void StateMachine_NotifyCaptureDone(void);

// Quality Gate báo kết quả. Chỉ AUDIO_OK mới được sang AI_PROCESSING.
void StateMachine_SubmitAudioQuality(Audio_Quality_t quality);

// TinyML báo kết quả; model_score bắt buộc nằm trong khoảng 0.0 đến 1.0.
void StateMachine_SubmitAudioResult(
    Audio_Quality_t quality,
    Interface_TinyML_t classification,
    float model_score
);

// MAX30102 báo kết quả đo hoặc vitals_valid=false nếu không đo được.
void StateMachine_SubmitVitals(
    bool vitals_valid,
    uint16_t heart_rate,
    uint16_t spo2
);

// Chỉ bật Poll() sau khi MAX30102_Init() thành công.
void StateMachine_SetVitalsAvailable(bool available);

// Mô-đun con báo lỗi để máy trạng thái chuyển sang STATE_ERROR.
void StateMachine_ReportError(const char* reason);

// Chỉ đọc phiên hiện tại để hiển thị hoặc đóng gói truyền tin.
const Patient_Session_t* StateMachine_GetCurrentSession(void);

// Mô-đun truyền tin báo đã gửi hoặc đã lưu chờ gửi lại.
void StateMachine_NotifyEventSent(void);

// Chỉ true khi SESSION_READY đã được chuyển thành packet hoàn chỉnh có CRC32.
bool StateMachine_IsPacketReady(void);

// Trả con trỏ chỉ đọc tới packet sẵn sàng; trả nullptr nếu packet chưa sẵn sàng.
// Tầng truyền tin phải copy packet trước khi gọi StateMachine_NotifyEventSent().
const Patient_Event_Packet_t* StateMachine_GetReadyPacket(void);

#endif /* NCKH_STATE_MACHINE_H */
