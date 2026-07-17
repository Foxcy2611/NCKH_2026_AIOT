#include "ESP32_A7680C_AT.h"

static HardwareSerial* sim_serial = nullptr;

// Gửi lệnh và chờ phản hồi
static String A7680C_SendCommand(const char* cmd, const char* exp_resp, uint32_t timeout){
    if(sim_serial == nullptr) return "";

    String response = "";
    sim_serial->println(cmd);

    // Nên thay = xTaskGetTickCount()
    uint32_t timeStart = millis();
    while((millis() - timeStart) < timeout){
        while(sim_serial->available()){
            char c = sim_serial->read();
            response += c;
        }
        // Nếu exp_resp ko có trong response thì hủy
        if(response.indexOf(exp_resp) != -1){
            break;
        }
    }
    
    // vTaskDelay(pdMS_TO_TICKS(10));
    delay(10);
    
    return response;
}

bool A7680C_Init(HardwareSerial& serialPort, uint8_t rxPin, uint8_t txPin, uint32_t baudrate){
    sim_serial = &serialPort;
    sim_serial->begin(baudrate, SERIAL_8N1, rxPin, txPin);

    // RTOS thay = xTaskDelay()
    delay(1000);

    bool isAlive = false;
    for(int i = 0 ; i < 5 ; i++){
        if(A7680C_SendCommand("AT", "OK", 1000).indexOf("OK") != -1){
            isAlive = true;
            break;
        }
        
        // RTOS thay = xTaskDelay()
        delay(500);
    }

    if(! isAlive) return false;

    // Tắt chế độ nhại lệnh
    A7680C_SendCommand("ATE0", "OK", 1000);
    return true;
}

// Ping kiểm tra kết nối
bool A7680C_CheckAlive(){
    return (A7680C_SendCommand("AT", "OK", 1000).indexOf("OK") != -1);
}

// Kiểm tra SIM sẵn sàng hay khóa
bool A7680C_CheckSIM(){
    String res = A7680C_SendCommand("AT+CPIN?", "OK", 2000);
    return (res.indexOf("READY") != -1);
}

int A7680C_GetSignalQuality(){
    // +CSQ: 20,0
    String res = A7680C_SendCommand("AT+CSQ", "OK", 2000);

    int idx = res.indexOf("+CSQ: ");
    if(idx != -1){
        int cmd_Idx = res.indexOf(",", idx);

        String Csq_Str = res.substring(idx + 6, cmd_Idx); // 20
        return Csq_Str.toInt();
    }
    return 0;
}

bool A7680C_CheckNetwork(){
    String res = A7680C_SendCommand("AT+CEREG?", "OK", 2000);
    
    if(res.indexOf(",1") != -1 || res.indexOf(",5") != -1){
        return true;
    }

    return false;
}

// Gọi điện (Bắt buộc có dấu ; ở cuối)
bool A7680C_MakeCall(const char* phoneNumber){
    String cmd = "ATD" + String(phoneNumber) + ";";
    // c_str: Biến String C++ thành chuỗi C thuần
    String res = A7680C_SendCommand(cmd.c_str(), "OK", 5000);
    return (res.indexOf("OK") != -1);

}

// Cúp máy
bool A7680C_HangUp(){
    String res = A7680C_SendCommand("ATH", "OK", 2000);
    return (res.indexOf("OK") != -1);
}

bool A7680C_SendSMS(const char* phoneNumber, const char* message){
    if(A7680C_SendCommand("AT+CMGF=1", "OK", 2000).indexOf("OK") == -1) return false;

    // Ký tử \": Làm trong chuỗi xuất hiện dấu ""
    String cmd = "AT+CMGS=\"" + String(phoneNumber) + "\"";
    String res = A7680C_SendCommand(cmd.c_str(), ">", 2000);
    
    if (res.indexOf(">") != -1) {
        sim_serial->print(message);
        sim_serial->write(26); 
        
        String finalRes = A7680C_SendCommand("", "+CMGS", 10000);
        return (finalRes.indexOf("+CMGS") != -1);
    }
    return false;

}

// Hàm gọi điện thông minh: Tự động cúp máy sau X giây (Có hỗ trợ ghi chú chuyển đổi RTOS)
bool A7680C_CallWithAutoHangUp(const char* phoneNumber, uint8_t activeDuration_sec, uint8_t maxTimeout_sec){
    String cmd = "ATD" + String(phoneNumber) + ";"; 
    if (A7680C_SendCommand(cmd.c_str(), "OK", 5000).indexOf("OK") == -1) return false;

    uint32_t start_time = millis();
    uint32_t timeout_ms = maxTimeout_sec * 1000;
    bool isAnswered = false;

    // Vòng lặp polling kiểm tra trạng thái
    while ((millis() - start_time) < timeout_ms) {
        String clcc_res = A7680C_SendCommand("AT+CLCC", "OK", 1000);
        
        if (clcc_res.indexOf("+CLCC: 1,0,0") != -1) {
            isAnswered = true;
            break; 
        }
        
        if (clcc_res.indexOf("+CLCC: 1,0,6") != -1) {
            return false; // Đã cúp máy
        }

        // [RTOS NOTE]: BẮT BUỘC thay delay(1000) bằng vTaskDelay(pdMS_TO_TICKS(1000))
        delay(1000); 
    }

    if (isAnswered) {
        // Thay delay() bằng vTaskDelay()
        delay(activeDuration_sec * 1000);
        A7680C_HangUp();
        return true;
    } else {
        A7680C_HangUp();
        return false;
    }
}

// Test trong main.cpp
void A7680C_TestMain(){
    Serial.begin(115200);
    Serial.println("\n----- A7680C Test -----");

    if (A7680C_Init(Serial2, SIM_RX_PIN, SIM_TX_PIN, 115200)) {
        Serial.println("[OK] Khoi tao module thanh cong!");
    } else {
        Serial.println("[ERR] Loi khoi tao. Kiem tra phan cung!");
        while(1);
    }

    if (A7680C_CheckSIM()) {
        Serial.println("[OK] Da nhan SIM.");
    } else {
        Serial.println("[ERR] Khong nhan SIM.");
    }

    Serial.printf("[INFO] Chat luong song (CSQ): %d\n", A7680C_GetSignalQuality());

    if (A7680C_CheckNetwork()) {
        Serial.println("[OK] Da dang ky mang LTE. San sang hoat dong!");
        
        // --- TEST CẢNH BÁO ---
        Serial.println("Thuc hien gui SMS...");
        A7680C_SendSMS("0987654321", "Canh bao thu nghiem he thong.");
        
        Serial.println("Thuc hien cuoc goi Auto-Hangup...");
        // Cho toi da 30s de bat may. Neu bat may, giu may 7s roi cup.
        A7680C_CallWithAutoHangUp("0987654321", 7, 30); 
        
    } else {
        Serial.println("[WARN] Chua dang ky vao mang 4G.");
    }
}