#ifndef NCKH_SYSTEM_STATE_H
#define NCKH_SYSTEM_STATE_H

#include <stdint.h>

/* HEADER này chứa các enum luôn chuyển trạng thái */

// ============================
// 1. Các trạng thái của hệ thống
// ============================
typedef enum {
    STATE_STANDBY = 0,      // Chế độ chờ, ngủ đông
    STATE_MANUAL_CHECK,     // Đang ghi âm 5s thủ công bằng nút CHECK
    STATE_AUTO_MONITOR,     // Chạy VAD liên tục, ghi âm tự động
    STATE_PROCESSING,       // Đang chạy DSP, Quality Gate và DS-CNN
    STATE_AUDIO_RESULT,     // Đã có kết quả AI, hiển thị OLED, chờ Vitals
    STATE_VITAL_CHECK,      // Đang đo HR/SpO2 qua MAX30102
    STATE_SESSION_READY,    // Gói dữ liệu xong, chuẩn bị ESP-NOW
    STATE_ERROR_STATE       // Lỗi hệ thống / Timeout
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
    INTERFACE_UNCERTAIN = 0,    // Không chắc chắn
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
// 6. Cấu trúc lưu trữ cục bộ (PATIENT SESSION)
// ============================
typedef struct {
    // -- Nhóm định danh --
    uint32_t session_id;    // ID ngẫu nhiên duy nhất cho mỗi phiên
    uint32_t sequence;      // Số thứ tự gói tin, tăng dần
    uint64_t timestamp;     // Dấu thời gian lúc thực hiện phiên đo

    // --- Nhóm Xử lý Âm thanh & AI ---
    Audio_Quality_t audio_quality;      // Đánh giá sơ bộ file ghi âm trước khi cho phép suy luận
    Interface_TinyML_t classification;  // Nhãn kết quả cuối cùng từ mạng DS-CNN (Asthma-like / Non-Asthma)
    float model_score;                  // Xác suất tự tin của AI (dải 0.0 đến 1.0)

    // --- Nhóm Sinh tồn (Vitals) ---
    bool vitals_valid;         // Cờ báo hiệu user có đo HR/SpO2 không. Nếu bỏ qua đo, cờ này = false (phiên vẫn hợp lệ)
    uint16_t heart_rate;       // Chỉ số Nhịp tim (BPM) kéo từ MAX30102
    uint8_t spo2;              // Nồng độ Oxy trong máu (%) kéo từ MAX30102

    // --- Nhóm Trạng thái Hệ thống ---
    uint8_t battery;           // Phần trăm pin hiện tại của Patient Node
    bool synced;               // Cờ theo dõi gửi ESP-NOW. Nếu Gateway chưa trả ACK, cờ = false, lưu lại gửi bù sau
} Patient_Session_t;


// ==========================================
// 7. Cấu trúc PAYLOAD ESP-NOW (TRUYỀN TẢI)
// ==========================================
#pragma pack(push, 1) // Ép không cho trình biên dịch chèn byte trống (padding) để truyền sóng RF chuẩn từng byte
typedef struct {
    uint32_t device_id;        // Định danh thiết bị (đọc từ MAC address) để Gateway nhận diện nguồn phát
    uint32_t sequence;         // Số thứ tự gói tin để Gateway đồng bộ lịch sử
    uint32_t session_id;       // ID phiên đo liên kết các tập dữ liệu
    uint64_t timestamp;        // Dấu thời gian lúc đóng gói bản tin

    uint8_t event_type;        // Phân loại mục đích gói tin 

    uint8_t classification;    // Kết quả AI (Sử dụng AiResult ép kiểu uint8_t)
    float model_score;         // Độ tự tin của mô hình AI

    uint8_t audio_quality;     // Tình trạng file âm thanh (Sử dụng AudioQuality ép kiểu uint8_t)

    bool vitals_valid;         // Cờ xác nhận dữ liệu nhịp tim/SpO2 bên dưới có giá trị thực hay không
    uint16_t heart_rate;       // Dữ liệu nhịp tim
    uint8_t spo2;              // Dữ liệu SpO2

    uint8_t battery;           // Phần trăm pin hiện hành
} Patient_Event_Packet_t;
#pragma pack(pop)

#endif /* NCKH_SYSTEM_STATE_H */