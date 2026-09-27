#include "Network/gateway_lte.h"

bool LTE_Init(
    HardwareSerial& serialPort,
    uint8_t rxPin,
    uint8_t txPin,
    uint32_t baudrate
)
{
    return A7680C_Init(
        serialPort,
        rxPin,
        txPin,
        baudrate
    );
}

bool LTE_Connect(const char* apn)
{
    char command[128];
    char response[256];

    // 1. Kiểm tra SIM
    if (!A7680C_CheckSIM())
    {
        Serial.println("LTE: Kiểm tra SIM thất bại");
        return false;
    }

    // 2. Kiểm tra đăng ký mạng (thử tối đa 5 lần cách nhau 2s để module có thời gian dò sóng trạm BTS)
    bool registered = false;
    for (int i = 0; i < 5; i++) {
        if (A7680C_CheckNetwork()) {
            registered = true;
            break;
        }
        if (i < 4) {
            Serial.println("LTE: Dang cho dang ky mang di dong...");
            vTaskDelay(pdMS_TO_TICKS(2000));
        }
    }

    if (!registered)
    {
        Serial.println("LTE: Đăng ký mạng thất bại");
        return false;
    }

    // 3. Cấu hình APN
    int length = snprintf(
        command,
        sizeof(command),
        "AT+CGDCONT=1,\"IP\",\"%s\"",
        apn
    );

    if (length < 0 || length >= (int)sizeof(command))
    {
        Serial.println("LTE: Lệnh APN quá dài");
        return false;
    }

    if (!A7680C_SendCommand(
            command,
            "OK",
            response,
            sizeof(response),
            5000))
    {
        Serial.println("LTE: Cấu hình APN thất bại");
        return false;
    }

    Serial.println("LTE: Đã cấu hình APN");

    // 4. Attach packet domain
    if (!A7680C_SendCommand(
            "AT+CGATT=1",
            "OK",
            response,
            sizeof(response),
            10000))
    {
        Serial.println("LTE: Gắn gói dữ liệu thất bại");
        return false;
    }

    Serial.println("LTE: Đã gắn gói dữ liệu");

    // 5. Activate PDP context
    if (!A7680C_SendCommand(
            "AT+CGACT=1,1",
            "OK",
            response,
            sizeof(response),
            15000))
    {
        Serial.println("LTE: Kích hoạt PDP thất bại");
        return false;
    }

    Serial.println("LTE: Đã kích hoạt PDP");

    // 6. Lấy IP
    if (!A7680C_SendCommand(
            "AT+CGPADDR=1",
            "OK",
            response,
            sizeof(response),
            5000))
    {
        Serial.println("LTE: Không lấy được IP");
        return false;
    }

    // In response để xem modem trả gì
    Serial.print("LTE phản hồi IP: ");
    Serial.println(response);

    // 7. Cấu hình Socket PDP Context cho SIMCom A7680C (TCP/IP & MQTT)
    snprintf(command, sizeof(command), "AT+CGSOCKCONT=1,\"IP\",\"%s\"", apn);
    A7680C_SendCommand(command, "OK", response, sizeof(response), 3000);
    A7680C_SendCommand("AT+CSOCKSETPN=1", "OK", response, sizeof(response), 3000);

    // 8. Đảm bảo đóng socket network stack cũ nếu còn kẹt/desync từ session trước
    A7680C_SendCommand("AT+NETCLOSE", "OK", response, sizeof(response), 3000);
    vTaskDelay(pdMS_TO_TICKS(500));

    // 9. Mở socket network stack (AT+NETOPEN) - BẮT BUỘC cho TCP/IP & MQTT
    if (!A7680C_SendCommand(
            "AT+NETOPEN",
            "OK",
            response,
            sizeof(response),
            10000))
    {
        if (strstr(response, "already opened") != nullptr)
        {
            Serial.println("LTE: Network stack da mo tu truoc");
        }
        else
        {
            Serial.println("LTE: Mo network stack (AT+NETOPEN) that bai!");
            Serial.println(response);
            return false;
        }
    }
    else
    {
        Serial.println("LTE: Da mo network stack (AT+NETOPEN) thanh cong");
    }

    Serial.println("LTE: Đã kết nối dữ liệu và mở network stack hoàn tất");

    return true;
}

bool LTE_IsConnected(void)
{
    char response[128];

    // 1. Đã đăng ký mạng nhà mạng?
    if (!A7680C_CheckNetwork())
    {
        return false;
    }

    // 2. Đã packet attached?
    if (!A7680C_SendCommand(
            "AT+CGATT?",
            "+CGATT:",
            response,
            sizeof(response),
            5000))
    {
        return false;
    }

    if (strstr(response, "+CGATT: 1") == NULL)
    {
        return false;
    }

    // 3. Đã được cấp IP?
    if (!A7680C_SendCommand(
            "AT+CGPADDR=1",
            "OK",
            response,
            sizeof(response),
            5000))
    {
        return false;
    }

    if (strstr(response, "+CGPADDR: 1,") == NULL)
    {
        return false;
    }

    return true;
}

bool LTE_Reconnect(const char* apn)
{
    Serial.println("LTE: Đang kết nối lại...");

    // Thực hiện lại toàn bộ quy trình kết nối LTE
    if (!LTE_Connect(apn))
    {

        Serial.println("LTE: Kết nối lại thất bại");
        return false;
    }

    Serial.println("LTE: Kết nối lại thành công");

    return true;
}

bool LTE_Disconnect(void)
{
    char response[128];

    if (!A7680C_SendCommand(
            "AT+CGACT=0,1",
            "OK",
            response,
            sizeof(response),
            10000))
    {
        Serial.println("LTE: Ngắt kết nối dữ liệu thất bại");
        return false;
    }


    Serial.println("LTE: Đã ngắt kết nối dữ liệu");

    return true;
}