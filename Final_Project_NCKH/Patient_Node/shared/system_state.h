#ifndef NCKH_SYSTEM_STATE_H
#define NCKH_SYSTEM_STATE_H

#include <stdint.h>

#include "Secure_Protocol.h"

/* HEADER này chứa các enum luôn chuyển trạng thái */

// -------------------- STATE TRẠNG THÁI -------------------- // 

// ============================
// 1. Các trạng thái của hệ thống
// ============================
typedef enum {
    // Không có phiên đang chạy; chờ người dùng bấm CHECK hoặc MONITOR.
    STATE_STANDBY = 0,

    // CHECK thủ công: INMP441 đang ghi đúng một đoạn âm thanh 5 giây.
    STATE_MANUAL_CAPTURE,

    // Kiểm tra đoạn âm thanh vừa thu có đủ điều kiện chạy mô hình không.
    STATE_AUDIO_QUALITY,

    // Tiền xử lý Mel và chạy mô hình TinyML.
    STATE_AI_PROCESSING,

    // Đã có kết luận âm thanh; chờ CHECK để đo sinh hiệu hoặc SLEEP để bỏ qua.
    STATE_AUDIO_RESULT,

    // MAX30102 đang đo nhịp tim và SpO2.
    STATE_VITAL_CHECK,

    // Phiên đã đủ dữ liệu; chờ gửi hoặc lưu chờ gửi lại rồi mới kết thúc.
    STATE_SESSION_READY,

    // Monitor đang nghe liên tục và chờ VAD phát hiện âm thanh phù hợp.
    STATE_MONITOR_LISTENING,

    // VAD đã kích hoạt; Monitor đang hoàn thiện đoạn âm thanh 5 giây.
    STATE_MONITOR_CAPTURE,

    // Có lỗi hoặc âm thanh không đạt; chờ CHECK thử lại hoặc SLEEP hủy.
    STATE_ERROR
    
} Patient_State_t;

// ============================
// 2. Các sự kiện vật lý của nút
// ============================
typedef enum {
    BTN_NONE = 0,
    BTN_CHECK_PRESSED,
    BTN_MONITOR_PRESSED,
    BTN_SLEEP_PRESSED       // Ưu tiên cao nhất, hủy ngang tác vụ
} Button_Event_t;

// ============================
// 3. Các trạng thái đánh giá chất lượng âm thanh
// ============================
typedef enum {
    AUDIO_OK = 0,       // PASS: Đạt chuẩn để interface
    AUDIO_TOO_WEAK,     // FAIL: Biên độ quá nhỏ
    AUDIO_TOO_LOUD,     // FAIL: Nhiễu rác
    AUDIO_INACTIVE      // FAIL: Không có tiếng động
} Audio_Quality_t;

// ============================
// 4. Kết quả phân loại từ TinyML
// ============================
typedef enum {
    INTERFACE_UNSURE = 0,    // Không chắc chắn
    INTERFACE_ASTHMA_LIKE,
    INTERFACE_NON_ASTHMA
} Interface_TinyML_t;

// ============================
// 5. Phân loại sự kiện
// ============================
typedef enum {
    EVENT_MANUAL_CHECK = 0,     // Do người dùng ấn nút check
    EVENT_MONITOR_EVENT,        // Do máy tự phát hiện khi bật MONITOR
    EVENT_STATUS                // Gói tin cập nhật trạng thái định kỳ
} Event_Type_t;

// ============================
// 6. Trạng thái tổng thể khi gửi 1 packet qua ESP-NOW
// ============================
typedef enum {
    STATUS_IDLE = 0,          // Không có packet cần gửi
    STATUS_QUEUED,            // Packet đã nằm trong hàng đợi
    STATUS_SENDING,           // Đã gọi esp_now_send()
    STATUS_ACK_PENDING,       // ESP-NOW báo gửi được, đang chờ Gateway phản hồi
    STATUS_RETRY_WAIT,        // Đang chờ đến thời điểm gửi lại
    STATUS_ACK_CONFIRMED,     // Gateway xác nhận packet hợp lệ
    STATUS_NACK_RECEIVED,     // Gateway từ chối packet
    STATUS_RETRY_EXCEEDED,    // Đã vượt số lần gửi lại
    STATUS_SEND_ERROR         // Không thể gửi ở mức ESP-NOW
} Event_Send_Status_t;

// -------------------- STRUCT GÓI BẢN TIN -------------------- //

// ============================
// 1. Cấu trúc lưu trữ cục bộ (PATIENT SESSION)
// ============================
typedef struct {
    uint32_t session_id;       // Sinh một lần khi bắt đầu phiên, dùng khi đóng gói packet
    Event_Type_t event_type; // Phiên thủ công hay sự kiện do Monitor phát hiện

    // --- Nhóm Xử lý Âm thanh & AI ---
    Audio_Quality_t audio_quality;      // Đánh giá sơ bộ file ghi âm trước khi cho phép suy luận
    Interface_TinyML_t classification;  // Nhãn kết quả cuối cùng từ mạng DS-CNN (Asthma-like / Non-Asthma)
    float model_score;                  // Xác suất tự tin của AI (dải 0.0 đến 1.0)

    // --- Nhóm Sinh tồn (Vitals) ---
    bool vitals_valid;         // Cờ báo hiệu user có đo HR/SpO2 không. Nếu bỏ qua đo, cờ này = false (phiên vẫn hợp lệ)
    uint16_t heart_rate;       // Chỉ số Nhịp tim (BPM) kéo từ MAX30102
    uint8_t spo2;              // Nồng độ Oxy trong máu (%) kéo từ MAX30102

    // --- Nhóm Trạng thái Hệ thống ---
    uint64_t event_timestamp;
} Patient_Session_t;

// ==========================================
// 2. Struct hàng đợi Pending ACK khi gửi qua ESP-NOW
// ==========================================
typedef struct {
    Event_Send_Status_t status;         // PENDING / CON
    Secure_EspNow_Packet_t packet;      // Bản sao packet bảo mật đã gửi, để retry y hệt

    uint8_t retry_count;                // Đã retry bao nhiêu lần ?
    uint32_t last_sent_timestamp;       // millis() lúc gửi gần nhất 
} Pending_ACK_Entry_t;

#endif /* NCKH_SYSTEM_STATE_H */
