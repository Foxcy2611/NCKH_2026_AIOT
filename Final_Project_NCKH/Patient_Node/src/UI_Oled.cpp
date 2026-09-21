#include "Vitals_UI/UI_Oled.h"
#include "Vitals_UI/UI_Assets.h"

static uint8_t OLED_Buffer[OLED_WIDTH * OLED_HEIGHT / 8];
static uint8_t Current_X, Current_Y;

static void OLED_Write(uint8_t control, uint8_t data){
    Wire.beginTransmission(OLED_I2C_ADDR);
    Wire.write(control);
    Wire.write(data);
    Wire.endTransmission();
}

static void OLED_SendCommand(uint8_t cmd){
    OLED_Write(0x00, cmd);
}

static void OLED_SendData(uint8_t data){
    OLED_Write(0x40, data);
}

void OLED_Init(void){
    OLED_SendCommand(0xAE);
    OLED_SendCommand(0x20); OLED_SendCommand(0x00);
    OLED_SendCommand(0xB0);
    OLED_SendCommand(0xC8);
    OLED_SendCommand(0x00);
    OLED_SendCommand(0x10);
    OLED_SendCommand(0x40);
    OLED_SendCommand(0x81); OLED_SendCommand(0x7F);
    OLED_SendCommand(0xA1);
    OLED_SendCommand(0xA6);
    OLED_SendCommand(0xA8); OLED_SendCommand(OLED_HEIGHT - 1);
    OLED_SendCommand(0xA4);
    OLED_SendCommand(0xD3); OLED_SendCommand(0x00);
    OLED_SendCommand(0xD5); OLED_SendCommand(0x80);
    OLED_SendCommand(0xD9); OLED_SendCommand(0xF1);
    OLED_SendCommand(0xDA); OLED_SendCommand(0x12);
    OLED_SendCommand(0xDB); OLED_SendCommand(0x40);
    OLED_SendCommand(0x8D); OLED_SendCommand(0x14);
    OLED_SendCommand(0xAF);

    OLED_Clear_Display();
    OLED_UpdateScreen();
}

void OLED_Clear_Display(void){
    memset(OLED_Buffer, 0x00, sizeof(OLED_Buffer));
}

void OLED_UpdateScreen(void){
    for(uint8_t page = 0 ; page < (OLED_HEIGHT / 8) ; page++){
        OLED_SendCommand(0xB0 + page);
        OLED_SendCommand(0x00);
        OLED_SendCommand(0x10);

        for(uint8_t x = 0 ; x < OLED_WIDTH ; x++){
            OLED_SendData(OLED_Buffer[OLED_WIDTH * page + x]);
        }
    }
}

void OLED_GotoXY(uint8_t x, uint8_t y){
    Current_X = x;
    Current_Y = y;
}

void OLED_DrawPixel(uint8_t x, uint8_t y, bool color){
    if(x >= OLED_WIDTH || y >= OLED_HEIGHT) return;

    if(color){
        OLED_Buffer[x + (y / 8) * OLED_WIDTH] |= (1 << (y % 8));
    } else {
        OLED_Buffer[x + (y / 8) * OLED_WIDTH] &= ~(1 << (y % 8));
    }
}


void OLED_Println(const char* str){
    while(*str){
        char c = *str++;

        if(c == '\n'){
            Current_X = 0;
            Current_Y += 8;
            continue;
        }

        if(c < 32 || c > 126) c = '?';

        for(int i = 0 ; i < 5 ; i++){
            uint8_t line = Font5x7[c - 32][i];

            for(int j = 0 ; j < 8 ; j++){
                OLED_DrawPixel(Current_X + i, Current_Y + j, (line >> j) & 1);
            }
        }
        Current_X += 6;
    }
}

void OLED_Printf(const char* format, ...){
    char buffer[64];

    va_list args;
    va_start(args, format);
    vsnprintf(buffer, sizeof(buffer), format, args);
    va_end(args);
    
    // Gửi chuỗi đã format hoàn chỉnh xuống hàm vẽ
    OLED_Println(buffer);
}

// ==== APP UI FUNCTIONS ====

// Hàm vẽ Bitmap
void OLED_DrawBitmap(uint8_t x, uint8_t y, const uint8_t *bitmap, uint8_t w, uint8_t h, bool color) {
    int16_t byteWidth = (w + 7) / 8;
    uint8_t byte = 0;
    for (int16_t j = 0; j < h; j++, y++) {
        for (int16_t i = 0; i < w; i++) {
            if (i & 7) byte <<= 1;
            else       byte   = bitmap[j * byteWidth + i / 8];
            if (byte & 0x80) OLED_DrawPixel(x + i, y, color);
        }
    }
}

// Icon Microphone 32x32
static void OLED_PrintCenter(const char* str, uint8_t y) {
    uint8_t len = strlen(str);
    uint8_t x = (128 - (len * 6)) / 2;
    OLED_GotoXY(x, y);
    OLED_Println(str);
}
// hàm place near mouth
// 'Gemini_Generated_Image_wmba3xwmba3xwmba', 64x40px
void OLED_Show_Welcome() {
    OLED_Clear_Display();
    OLED_UpdateScreen();
    
    // Vị trí vẽ icon
    uint8_t x = 32;
    uint8_t y = 2;
    uint8_t w = 64;
    uint8_t h = 40;
    
    // Animation: Hiện nhanh hơn bằng cách vẽ 8 dòng rồi mới cập nhật màn hình
    for (uint8_t row = 0; row < h; row++) {
        for (uint8_t col = 0; col < w; col++) {
            uint16_t byte_idx = (row * w + col) / 8;
            uint8_t bit_idx = 7 - (col % 8);
            bool pixel = (epd_bitmap_welcome[byte_idx] & (1 << bit_idx)) != 0;
            if (pixel) {
                OLED_DrawPixel(x + col, y + row, true);
            }
        }
        // Cập nhật màn hình sau mỗi 8 hàng để tăng tốc độ quét hơn nữa
        if (row % 8 == 7) {
            OLED_UpdateScreen();
        }
    }
    
    // Hiển thị dòng chữ WELCOME ở dưới cùng
    OLED_PrintCenter("WELCOME", 48);
    OLED_UpdateScreen();
    
    
}

void OLED_Show_Sleep() {
    OLED_Clear_Display();
    OLED_UpdateScreen();
    
    // Vị trí vẽ icon
    uint8_t x = 32;
    uint8_t y = 2;
    uint8_t w = 64;
    uint8_t h = 40;
    
    // Animation: Hiện nhanh hơn bằng cách vẽ 8 dòng rồi mới cập nhật màn hình
    for (uint8_t row = 0; row < h; row++) {
        for (uint8_t col = 0; col < w; col++) {
            uint16_t byte_idx = (row * w + col) / 8;
            uint8_t bit_idx = 7 - (col % 8);
            bool pixel = (epd_bitmap_welcome[byte_idx] & (1 << bit_idx)) != 0;
            if (pixel) {
                OLED_DrawPixel(x + col, y + row, true);
            }
        }
        // Cập nhật màn hình sau mỗi 8 hàng để tăng tốc độ quét hơn nữa
        if (row % 8 == 7) {
            OLED_UpdateScreen();
        }
    }
    
    // Hiển thị dòng chữ SLEEP ở dưới cùng
    OLED_PrintCenter("SLEEP", 48);
    OLED_UpdateScreen();
    
    // Giữ màn hình trong 3 giây
    delay(3000);
}

void OLED_Show_PlaceNearMouth() {
    OLED_Clear_Display();
    // Vẽ icon head+mic ở giữa nửa trên (w=64 => x=(128-64)/2 = 32)
    OLED_DrawBitmap(32, 2, icon_head_mic_64x40, 64, 40, true);
    // Hiện text ở phía dưới
    OLED_PrintCenter("PLACE NEAR MOUTH", 44);
    OLED_UpdateScreen();
    delay(3000);
}

void OLED_Show_PlaceFinger() {
    OLED_Clear_Display();
    // In 2 dòng text
    OLED_PrintCenter("PLACE FINGER", 24);
    OLED_PrintCenter("PRESS CHECK", 40);
    OLED_UpdateScreen();
}

void OLED_Show_Recording() {
    for (int8_t i = 5; i >= 0; i--) {
        OLED_Clear_Display();
        // Vẽ icon mic (32x32) ở phần trên
        OLED_DrawBitmap(48, 2, icon_mic_32x32, 32, 32, true);
        
        // Hiện chữ RECORDING
        OLED_PrintCenter("RECORDING", 38);
        
        // Hiện số đếm ngược
        char buf[4];
        sprintf(buf, "%d", i);
        OLED_PrintCenter(buf, 50);
        
        OLED_UpdateScreen();
        
        if (i > 0) {
            delay(1000); // Đợi 1 giây giữa mỗi lần đếm ngược
        }
    }
}

// 'canva-caduceus-medical-symbol', 64x40px
void OLED_Show_Standby() {
    OLED_Clear_Display();
    // Vẽ icon 64x40 ở giữa phần trên màn hình
    OLED_DrawBitmap(32, 2, epd_bitmap_standby, 64, 40, true);
    // In chữ STANDBY ở dưới cùng
    OLED_PrintCenter("STANDBY", 48);
    OLED_UpdateScreen();
}

void OLED_Show_MonitorPreparing() {
    OLED_Clear_Display();
    OLED_PrintCenter("MONITOR START", 16);
    OLED_PrintCenter("PREPARING BUFFER", 32);
    OLED_PrintCenter("PLEASE WAIT...", 48);
    OLED_UpdateScreen();
}

void OLED_Show_Monitoring() {
    OLED_Clear_Display();
    OLED_PrintCenter("MONITORING", 12);
    OLED_PrintCenter("WAITING FOR SOUND", 30);
    OLED_PrintCenter("MONITOR TO EXIT", 50);
    OLED_UpdateScreen();
}

// '552871', 64x40px
void OLED_Show_SoundDetected() {
    OLED_Clear_Display();
    // Vẽ icon giống màn hình error (64x40) ở giữa phần trên màn hình
    OLED_DrawBitmap(32, 2, epd_bitmap_552871, 64, 40, true);
    
    // In chữ
    OLED_PrintCenter("SOUND DETECTED", 44);
    OLED_PrintCenter("CAPTURING...", 56);
    
    OLED_UpdateScreen();
}

void OLED_Show_QualityError(const char* error_type) {
    OLED_Clear_Display();
    // Vẽ hình ảnh 64x40 ở giữa phần trên màn hình
    OLED_DrawBitmap(32, 2, epd_bitmap_552871, 64, 40, true);
    // In nội dung lỗi
    OLED_PrintCenter(error_type, 44);
    // In chữ RETRY
    OLED_PrintCenter("RETRY", 54);
    OLED_UpdateScreen();
}

// 'ok', 64x40px
void OLED_Show_AudioOK() {
    OLED_Clear_Display();
    // Vẽ hình ảnh ok 64x40 ở giữa phần trên màn hình
    OLED_DrawBitmap(32, 2, epd_bitmap_ok, 64, 40, true);
    // In chữ AUDIO OK
    OLED_PrintCenter("AUDIO OK", 46);
    OLED_UpdateScreen();
}

void OLED_Show_Processing() {
    // Dùng biến static để lưu trạng thái vị trí của thanh loading giữa các lần gọi hàm
    static int16_t fill_pos = 0;
    static int8_t direction = 5; // Bước dịch chuyển mỗi frame
    
    OLED_Clear_Display();
    
    // In chữ PROCESSING
    OLED_PrintCenter("PROCESSING...", 20);
    
    // Vẽ khung thanh tiến trình (progress bar)
    uint8_t bar_x = 14;
    uint8_t bar_y = 35;
    uint8_t bar_w = 100;
    uint8_t bar_h = 10;
    uint8_t fill_w = 20; // Chiều dài của khối chạy qua lại
    
    // Vẽ đường viền
    for (uint8_t i = bar_x; i < bar_x + bar_w; i++) {
        OLED_DrawPixel(i, bar_y, true);
        OLED_DrawPixel(i, bar_y + bar_h - 1, true);
    }
    for (uint8_t i = bar_y; i < bar_y + bar_h; i++) {
        OLED_DrawPixel(bar_x, i, true);
        OLED_DrawPixel(bar_x + bar_w - 1, i, true);
    }
    
    // Vẽ khối chữ nhật bên trong (chạy qua chạy lại)
    for (uint8_t i = bar_x + 2 + fill_pos; i < bar_x + 2 + fill_pos + fill_w; i++) {
        for (uint8_t j = bar_y + 2; j < bar_y + bar_h - 2; j++) {
            OLED_DrawPixel(i, j, true);
        }
    }
    
    OLED_UpdateScreen();
    
    // Tính toán vị trí cho lần hiển thị tiếp theo
    fill_pos += direction;
    // Đảo chiều nếu đụng tường phải
    if (fill_pos >= (bar_w - 4 - fill_w)) {
        fill_pos = bar_w - 4 - fill_w;
        direction = -5;
    } 
    // Đảo chiều nếu đụng tường trái
    else if (fill_pos <= 0) {
        fill_pos = 0;
        direction = 5;
    }
}

// 'unknown', 64x40px
void OLED_Show_AI_Result(int ai_status) {
    OLED_Clear_Display();
    if (ai_status == 0) {
        // Icon cảnh báo cho ASTHMA
        OLED_DrawBitmap(32, 2, epd_bitmap_552871, 64, 40, true);
        OLED_PrintCenter("ASTHMA", 48);
    } else if (ai_status == 1) {
        // Icon check (OK) cho NON-ASTHMA
        OLED_DrawBitmap(32, 2, epd_bitmap_ok, 64, 40, true);
        OLED_PrintCenter("NON-ASTHMA", 48);
    } else {
        // Icon unknown
        OLED_DrawBitmap(32, 2, epd_bitmap_unknown, 64, 40, true);
        OLED_PrintCenter("UNKNOWN", 48);
    }
    OLED_UpdateScreen();
}

void OLED_Show_FinalResult(int ai_status, int hr, int spo2) {
    OLED_Clear_Display();
    
    // In kết quả AI ở trên cùng
    if (ai_status == 0) {
        OLED_PrintCenter("ASTHMA", 12);
    } else if (ai_status == 1) {
        OLED_PrintCenter("NON-ASTHMA", 12);
    } else {
        OLED_PrintCenter("UNKNOWN", 12);
    }
    
    char buf[32];
    
    // In nhịp tim (HR)
    sprintf(buf, "HR: %d bpm", hr);
    OLED_PrintCenter(buf, 32);
    
    // In SpO2
    sprintf(buf, "SpO2: %d %%", spo2);
    OLED_PrintCenter(buf, 48);
    
    OLED_UpdateScreen();
}

void OLED_Show_DataSent() {
    OLED_Clear_Display();
    // Vẽ hình ảnh ok 64x40 ở giữa phần trên màn hình
    OLED_DrawBitmap(32, 2, epd_bitmap_ok, 64, 40, true);
    // In chữ DATA SENT
    OLED_PrintCenter("DATA SENT", 46);
    OLED_UpdateScreen();
}

void OLED_Show_ReplyOK() {
    OLED_Clear_Display();
    // Vẽ hình ảnh ok 64x40 ở giữa phần trên màn hình
    OLED_DrawBitmap(32, 2, epd_bitmap_ok, 64, 40, true);
    // In chữ REPLY OK
    OLED_PrintCenter("REPLY OK", 46);
    OLED_UpdateScreen();
}

void OLED_Show_NoReply() {
    OLED_Clear_Display();
    // Vẽ icon giống màn hình error (64x40) ở giữa phần trên màn hình
    OLED_DrawBitmap(32, 2, epd_bitmap_552871, 64, 40, true);
    // In chữ NO REPLY
    OLED_PrintCenter("NO REPLY", 46);
    OLED_UpdateScreen();
}
