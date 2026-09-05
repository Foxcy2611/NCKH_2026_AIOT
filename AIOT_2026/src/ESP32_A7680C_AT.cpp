#include "ESP32_A7680C_AT.h"
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static HardwareSerial* sim_serial = nullptr;
const char* const A7680C_ALERT_MESSAGE = "Canh bao thu nghiem he thong.";
static const size_t A7680C_RESPONSE_CAPACITY = 256;
static const size_t A7680C_COMMAND_CAPACITY = 32;
#ifndef A7680C_DEBUG_DIAGNOSTICS
#define A7680C_DEBUG_DIAGNOSTICS 1
#endif

// Gửi lệnh và chờ phản hồi
static bool A7680C_SendCommand(const char* cmd,
                               const char* exp_resp,
                               char* response,
                               size_t responseCapacity,
                               uint32_t timeout){
    if(response == nullptr || responseCapacity == 0) return false;
    response[0] = '\0';

    if(sim_serial == nullptr || cmd == nullptr || exp_resp == nullptr) return false;

    // Chuỗi rỗng chỉ dùng để chờ phản hồi; không gửi CRLF thừa sau Ctrl+Z.
    if(cmd[0] != '\0'){
        sim_serial->println(cmd);
    }

    size_t responseLength = 0;
    bool expectedResponseFound = false;
    bool responseOverflow = false;
    uint32_t timeStart = millis();
    while((millis() - timeStart) < timeout){
        bool receivedData = false;
        while(sim_serial->available()){
            int value = sim_serial->read();
            if(value < 0) break;

            receivedData = true;
            if(responseLength + 1 >= responseCapacity){
                responseOverflow = true;
                continue;
            }

            response[responseLength++] = static_cast<char>(value);
            response[responseLength] = '\0';
        }
        if(responseOverflow){
            break;
        }
        // Module đã báo lỗi thì thoát ngay, tránh giữ task đến hết timeout dài.
        if(strstr(response, "ERROR") != nullptr){
            break;
        }
        if(strstr(response, exp_resp) != nullptr){
            expectedResponseFound = true;
            break;
        }
        // Nhường CPU cho IDLE task khi UART chưa có dữ liệu, tránh watchdog reset.
        if(!receivedData){
            vTaskDelay(pdMS_TO_TICKS(1));
        }
    }
    
    vTaskDelay(pdMS_TO_TICKS(10));
    return expectedResponseFound;
}

static void A7680C_LogResponse(const char* command,
                               const char* response){
#if A7680C_DEBUG_DIAGNOSTICS
    Serial.printf("[SIM-AT] %s\n", command);
    if(response[0] == '\0'){
        Serial.println("<EMPTY>");
        return;
    }

    Serial.print(response);
    size_t length = strlen(response);
    if(response[length - 1] != '\n'){
        Serial.println();
    }
#else
    (void)command;
    (void)response;
#endif
}

static bool A7680C_HasConfiguredSMSC(const char* response){
    const char* csca = strstr(response, "+CSCA:");
    if(csca == nullptr) return false;

    const char* firstQuote = strchr(csca, '"');
    if(firstQuote == nullptr) return false;

    const char* secondQuote = strchr(firstQuote + 1, '"');
    return secondQuote != nullptr && secondQuote > firstQuote + 1;
}

static void A7680C_ConfigureSMS(){
    char response[A7680C_RESPONSE_CAPACITY];
    bool charsetReady = A7680C_SendCommand("AT+CSCS=\"GSM\"",
                                           "OK",
                                           response,
                                           sizeof(response),
                                           2000);
    A7680C_LogResponse("AT+CSCS=\"GSM\"", response);
    if(!charsetReady){
        Serial.println("[WARN] Khong the dat charset GSM!");
    }

    bool smscRead = A7680C_SendCommand("AT+CSCA?",
                                       "OK",
                                       response,
                                       sizeof(response),
                                       2000);
    A7680C_LogResponse("AT+CSCA?", response);
    if(!smscRead || !A7680C_HasConfiguredSMSC(response)){
        Serial.println("[WARN] SMSC rong, SMS co the khong duoc gui!");
    }
}

bool A7680C_Init(HardwareSerial& serialPort, uint8_t rxPin, uint8_t txPin, uint32_t baudrate){
    sim_serial = &serialPort;
    sim_serial->begin(baudrate, SERIAL_8N1, rxPin, txPin);

    vTaskDelay(pdMS_TO_TICKS(1000));

    char response[A7680C_RESPONSE_CAPACITY];
    bool isAlive = false;
    for(int i = 0 ; i < 5 ; i++){
        if(A7680C_SendCommand("AT",
                              "OK",
                              response,
                              sizeof(response),
                              1000)){
            isAlive = true;
            break;
        }
        
        vTaskDelay(pdMS_TO_TICKS(500));
    }

    if(! isAlive) return false;

    // Tắt chế độ nhại lệnh
    A7680C_SendCommand("ATE0",
                       "OK",
                       response,
                       sizeof(response),
                       1000);
    A7680C_ConfigureSMS();
    return true;
}

// Ping kiểm tra kết nối
bool A7680C_CheckAlive(){
    char response[A7680C_RESPONSE_CAPACITY];
    return A7680C_SendCommand("AT",
                              "OK",
                              response,
                              sizeof(response),
                              1000);
}

// Kiểm tra SIM sẵn sàng hay khóa
bool A7680C_CheckSIM(){
    char response[A7680C_RESPONSE_CAPACITY];
    if(!A7680C_SendCommand("AT+CPIN?",
                           "OK",
                           response,
                           sizeof(response),
                           2000)){
        return false;
    }

    return strstr(response, "READY") != nullptr;
}

int A7680C_GetSignalQuality(){
    // +CSQ: 20,0
    char response[A7680C_RESPONSE_CAPACITY];
    if(!A7680C_SendCommand("AT+CSQ",
                           "OK",
                           response,
                           sizeof(response),
                           2000)){
        return 0;
    }

    const char* csq = strstr(response, "+CSQ: ");
    if(csq == nullptr) return 0;

    char* end = nullptr;
    long value = strtol(csq + 6, &end, 10);
    return end != csq + 6 && end != nullptr && *end == ','
               ? static_cast<int>(value)
               : 0;
}

bool A7680C_CheckNetwork(){
    char response[A7680C_RESPONSE_CAPACITY];
    bool ceregRead = A7680C_SendCommand("AT+CEREG?",
                                        "OK",
                                        response,
                                        sizeof(response),
                                        2000);
    A7680C_LogResponse("AT+CEREG?", response);
    bool networkRegistered = ceregRead &&
        (strstr(response, ",1") != nullptr ||
         strstr(response, ",5") != nullptr);

#if A7680C_DEBUG_DIAGNOSTICS
    A7680C_SendCommand("AT+CREG?",
                       "OK",
                       response,
                       sizeof(response),
                       2000);
    A7680C_LogResponse("AT+CREG?", response);

    A7680C_SendCommand("AT+COPS?",
                       "OK",
                       response,
                       sizeof(response),
                       5000);
    A7680C_LogResponse("AT+COPS?", response);
#endif

    return networkRegistered;
}

bool A7680C_InitAndDiagnose(HardwareSerial& serialPort,
                            uint8_t rxPin,
                            uint8_t txPin,
                            uint32_t baudrate){
    if(!A7680C_Init(serialPort, rxPin, txPin, baudrate)){
        Serial.println("[ERR] Loi khoi tao. Kiem tra phan cung!");
        return false;
    }
    Serial.println("[OK] Khoi tao module thanh cong!");

    bool simReady = A7680C_CheckSIM();
    Serial.println(simReady ? "[OK] Da nhan SIM."
                            : "[ERR] Khong nhan SIM.");

    Serial.printf("[INFO] Chat luong song (CSQ): %d\n",
                  A7680C_GetSignalQuality());

    bool networkReady = A7680C_CheckNetwork();
    Serial.println(networkReady
                       ? "[OK] Da dang ky mang LTE. San sang hoat dong!"
                       : "[WARN] Chua dang ky vao mang 4G.");

    return simReady && networkReady;
}

// Chỉ dùng khi đổi sang module có hỗ trợ thoại (lệnh gọi cần dấu ; ở cuối).
bool A7680C_MakeCall(const char* phoneNumber){
    if(phoneNumber == nullptr) return false;

    char command[A7680C_COMMAND_CAPACITY];
    int written = snprintf(command,
                           sizeof(command),
                           "ATD%s;",
                           phoneNumber);
    if(written < 0 || static_cast<size_t>(written) >= sizeof(command)){
        return false;
    }

    char response[A7680C_RESPONSE_CAPACITY];
    return A7680C_SendCommand(command,
                              "OK",
                              response,
                              sizeof(response),
                              5000);
}

// Cúp máy
bool A7680C_HangUp(){
    char response[A7680C_RESPONSE_CAPACITY];
    return A7680C_SendCommand("ATH",
                              "OK",
                              response,
                              sizeof(response),
                              2000);
}

bool A7680C_SendSMS(const char* phoneNumber, const char* message){
    if(phoneNumber == nullptr || message == nullptr) return false;

    char response[A7680C_RESPONSE_CAPACITY];
    if(!A7680C_SendCommand("AT+CMGF=1",
                           "OK",
                           response,
                           sizeof(response),
                           2000)){
        return false;
    }

    // Ký tử \": Làm trong chuỗi xuất hiện dấu ""
    char command[A7680C_COMMAND_CAPACITY];
    int written = snprintf(command,
                           sizeof(command),
                           "AT+CMGS=\"%s\"",
                           phoneNumber);
    if(written < 0 || static_cast<size_t>(written) >= sizeof(command)){
        return false;
    }

    if(!A7680C_SendCommand(command,
                           ">",
                           response,
                           sizeof(response),
                           2000)){
        return false;
    }

    sim_serial->print(message);
    sim_serial->write(26);
    return A7680C_SendCommand("",
                              "+CMGS",
                              response,
                              sizeof(response),
                              10000);
}

// Chỉ dùng khi đổi sang module có hỗ trợ thoại.
bool A7680C_CallWithAutoHangUp(const char* phoneNumber, uint8_t activeDuration_sec, uint8_t maxTimeout_sec){
    if(phoneNumber == nullptr) return false;

    char command[A7680C_COMMAND_CAPACITY];
    int written = snprintf(command,
                           sizeof(command),
                           "ATD%s;",
                           phoneNumber);
    if(written < 0 || static_cast<size_t>(written) >= sizeof(command)){
        return false;
    }

    char response[A7680C_RESPONSE_CAPACITY];
    if(!A7680C_SendCommand(command,
                           "OK",
                           response,
                           sizeof(response),
                           5000)){
        return false;
    }

    uint32_t start_time = millis();
    uint32_t timeout_ms = (uint32_t)maxTimeout_sec * 1000U;
    bool isAnswered = false;

    // Vòng lặp polling kiểm tra trạng thái
    while ((millis() - start_time) < timeout_ms) {
        A7680C_SendCommand("AT+CLCC",
                           "OK",
                           response,
                           sizeof(response),
                           1000);
        
        if (strstr(response, "+CLCC: 1,0,0") != nullptr) {
            isAnswered = true;
            break; 
        }
        
        if (strstr(response, "+CLCC: 1,0,6") != nullptr) {
            return false; // Đã cúp máy
        }

        vTaskDelay(pdMS_TO_TICKS(1000));
    }

    if (isAnswered) {
        vTaskDelay(pdMS_TO_TICKS((uint32_t)activeDuration_sec * 1000U));
        A7680C_HangUp();
        return true;
    } else {
        A7680C_HangUp();
        return false;
    }
}
