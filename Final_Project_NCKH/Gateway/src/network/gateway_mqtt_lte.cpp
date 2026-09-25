#include "Network/gateway_mqtt_lte.h"
#include "Network/gateway_lte.h"
#include "Network/gateway_mqtt_wifi.h"
#include "Sensor/ESP32_A7680C_AT.h"
#include "Config/gateway_config.h"
#include "Config/gateway_network_config.h"

// ============================================================
// BIEN TRANG THAI NOI BO & CACHE CAU HINH
// ============================================================
static bool mqttLteStarted = false;
static bool mqttLteConnected = false;

// Cache thong tin broker de dung cho MQTT_LTE_Reconnect()
static char cachedBroker[128] = {0};
static uint16_t cachedPort = 8883;
static char cachedClientId[64] = {0};
static char cachedUsername[64] = {0};
static char cachedPassword[64] = {0};

// ============================================================
// HAM NOI BO: RESET SACH SERVICE MQTT TREN A7680C
// Giup giai phong hoan toan Client bi ket khi ESP32 reset dot ngot
// ============================================================
static void MQTT_LTE_ForceCleanService(void)
{
    if (!A7680C_Lock(20000))
    {
        Serial.println("MQTT-LTE: [RESET] Khong the lay khoa modem de reset MQTT service!");
        return;
    }

    char response[128];
    Serial.println("MQTT-LTE: [RESET] Dang giai phong va reset MQTT service tren A7680C...");

    // 1. Thu ngat ket noi client 0
    A7680C_SendCommand("AT+CMQTTDISC=0,120", "OK", response, sizeof(response), 2000);

    // 2. Thu giai phong client 0
    A7680C_SendCommand("AT+CMQTTREL=0", "OK", response, sizeof(response), 2000);

    // 3. Dung service MQTT de giai phong hoan toan bo nho va SSL context cu
    A7680C_SendCommand("AT+CMQTTSTOP", "OK", response, sizeof(response), 3000);
    delay(500);

    // 4. Khoi dong lai service MQTT
    if (A7680C_SendCommand("AT+CMQTTSTART", "+CMQTTSTART: 0", response, sizeof(response), 5000))
    {
        Serial.println("MQTT-LTE: [RESET] Da khoi dong lai MQTT service thanh cong");
        mqttLteStarted = true;
    }
    else if (strstr(response, "23") != nullptr || strstr(response, "already") != nullptr)
    {
        Serial.println("MQTT-LTE: [RESET] MQTT service da san sang");
        mqttLteStarted = true;
    }
    else
    {
        Serial.println("MQTT-LTE: [RESET] Canh bao - khoi dong lai MQTT service chua xac nhan OK");
        mqttLteStarted = false;
    }
    delay(500);

    mqttLteConnected = false;
    A7680C_Unlock();
}

// ============================================================
// 1. KHOI TAO MQTT SERVICE TREN A7680C
// ============================================================
bool MQTT_LTE_Init(void)
{
    if (mqttLteStarted)
    {
        return true;
    }

    if (!A7680C_Lock(25000))
    {
        Serial.println("MQTT-LTE: Khong the lay khoa modem de khoi tao service!");
        return false;
    }

    char response[256];

    // 1. Dam bao network stack (AT+NETOPEN) da duoc mo truoc khi khoi dong MQTT
    if (!A7680C_SendCommand("AT+NETOPEN?", "+NETOPEN: 1", response, sizeof(response), 2000))
    {
        Serial.println("MQTT-LTE: Network stack chua mo, dang goi AT+NETOPEN...");
        if (!A7680C_SendCommand("AT+NETOPEN", "OK", response, sizeof(response), 10000))
        {
            if (strstr(response, "already opened") == nullptr)
            {
                Serial.println("MQTT-LTE: Mo network stack that bai hoac da mo.");
            }
        }
        delay(1000);
    }

    Serial.println("MQTT-LTE: Dang khoi dong MQTT service (AT+CMQTTSTART)...");

    if (!A7680C_SendCommand(
            "AT+CMQTTSTART",
            "+CMQTTSTART: 0",
            response,
            sizeof(response),
            12000))
    {
        // Ma loi 23: Service da duoc start tu phien truoc (van san sang hoat dong)
        if (strstr(response, "+CMQTTSTART: 23") != nullptr ||
            strstr(response, "23") != nullptr ||
            strstr(response, "already") != nullptr)
        {
            Serial.println("MQTT-LTE: MQTT service da san sang (da start truoc do)");
            mqttLteStarted = true;
            A7680C_Unlock();
            return true;
        }

        // Tu dong khoi phuc: Neu bao ERROR, thu giai phong client cu, stop va start lai service
        Serial.println("MQTT-LTE: CMQTTSTART tra ve ERROR, dang thuc hien quy trinh reset sach MQTT service...");
        A7680C_SendCommand("AT+CMQTTDISC=0,120", "OK", response, sizeof(response), 2000);
        A7680C_SendCommand("AT+CMQTTREL=0", "OK", response, sizeof(response), 2000);
        A7680C_SendCommand("AT+CMQTTSTOP", "OK", response, sizeof(response), 3000);
        vTaskDelay(pdMS_TO_TICKS(1000));

        if (A7680C_SendCommand("AT+CMQTTSTART", "+CMQTTSTART: 0", response, sizeof(response), 8000) ||
            strstr(response, "+CMQTTSTART: 23") != nullptr ||
            strstr(response, "23") != nullptr ||
            strstr(response, "already") != nullptr)
        {
            Serial.println("MQTT-LTE: MQTT service da khoi dong thanh cong sau khi reset");
            mqttLteStarted = true;
            A7680C_Unlock();
            return true;
        }

        // Neu van loi, thu restart ca Network stack (AT+NETCLOSE -> AT+NETOPEN)
        Serial.println("MQTT-LTE: Thu khoi dong lai Network stack (AT+NETCLOSE -> AT+NETOPEN)...");
        A7680C_SendCommand("AT+NETCLOSE", "OK", response, sizeof(response), 3000);
        vTaskDelay(pdMS_TO_TICKS(1000));
        A7680C_SendCommand("AT+NETOPEN", "OK", response, sizeof(response), 10000);
        vTaskDelay(pdMS_TO_TICKS(1000));

        if (A7680C_SendCommand("AT+CMQTTSTART", "+CMQTTSTART: 0", response, sizeof(response), 8000) ||
            strstr(response, "+CMQTTSTART: 23") != nullptr ||
            strstr(response, "23") != nullptr ||
            strstr(response, "already") != nullptr)
        {
            Serial.println("MQTT-LTE: MQTT service da khoi dong thanh cong sau khi mo lai network stack");
            mqttLteStarted = true;
            A7680C_Unlock();
            return true;
        }

        Serial.println("MQTT-LTE: Khoi dong MQTT service that bai!");
        Serial.print("MQTT-LTE response: ");
        Serial.println(response[0] ? response : "<EMPTY>");
        A7680C_Unlock();
        return false;
    }

    mqttLteStarted = true;
    Serial.println("MQTT-LTE: MQTT service da khoi dong thanh cong");
    A7680C_Unlock();
    return true;
}

// ============================================================
// 2. KET NOI DEN MQTT BROKER QUA LTE
// ============================================================
bool MQTT_LTE_Connect(
    const char* broker,
    uint16_t port,
    const char* clientId,
    const char* username,
    const char* password)
{
    char command[512];
    char response[256];

    // Neu tham so khong duoc truyen, su dung mac dinh tu gateway_mqtt_wifi.h
    const char* b = (broker != nullptr) ? broker : MQTT_BROKER;
    uint16_t p = (port != 0) ? port : MQTT_PORT;
    const char* cId = (clientId != nullptr) ? clientId : MQTT_CLIENT_ID;
    const char* u = (username != nullptr) ? username : MQTT_USERNAME;
    const char* pwd = (password != nullptr) ? password : MQTT_PASSWORD;

    if (b == nullptr || cId == nullptr)
    {
        Serial.println("MQTT-LTE: Thieu thong tin Broker hoac ClientId!");
        return false;
    }

    // Luu lai cau hinh vao cache de phuc vu cho MQTT_LTE_Reconnect()
    strncpy(cachedBroker, b, sizeof(cachedBroker) - 1);
    cachedBroker[sizeof(cachedBroker) - 1] = '\0';
    cachedPort = p;
    strncpy(cachedClientId, cId, sizeof(cachedClientId) - 1);
    cachedClientId[sizeof(cachedClientId) - 1] = '\0';
    if (u != nullptr)
    {
        strncpy(cachedUsername, u, sizeof(cachedUsername) - 1);
        cachedUsername[sizeof(cachedUsername) - 1] = '\0';
    }
    else
    {
        cachedUsername[0] = '\0';
    }
    if (pwd != nullptr)
    {
        strncpy(cachedPassword, pwd, sizeof(cachedPassword) - 1);
        cachedPassword[sizeof(cachedPassword) - 1] = '\0';
    }
    else
    {
        cachedPassword[0] = '\0';
    }

    if (mqttLteConnected && MQTT_LTE_IsConnected())
    {
        Serial.println("MQTT-LTE: Da ket noi broker truoc do.");
        return true;
    }

    if (!A7680C_Lock(50000))
    {
        Serial.println("MQTT-LTE: Khong the lay khoa modem de ket noi broker!");
        return false;
    }

    // Khoi dong service neu chua bat
    if (!MQTT_LTE_Init())
    {
        A7680C_Unlock();
        return false;
    }

    // Kiem tra du lieu LTE (APN/PDP)
    if (!LTE_IsConnected())
    {
        Serial.println("MQTT-LTE: Du lieu LTE (PDP) chua active, huy bo ket noi MQTT!");
        A7680C_Unlock();
        return false;
    }

    bool isSsl = (p == 8883);
    int serverType = isSsl ? 1 : 0; // 1 = SSL/TLS, 0 = TCP plain

    // --------------------------------------------------------
    // 2.1. Acquire MQTT client (client_index = 0)
    // --------------------------------------------------------
    int length = snprintf(
        command,
        sizeof(command),
        "AT+CMQTTACCQ=0,\"%s\",%d",
        cId,
        serverType
    );

    if (length < 0 || length >= (int)sizeof(command))
    {
        Serial.println("MQTT-LTE: Lenh CMQTTACCQ qua dai!");
        A7680C_Unlock();
        return false;
    }

    Serial.print("MQTT-LTE: ");
    Serial.println(command);

    if (!A7680C_SendCommand(
            command,
            "OK",
            response,
            sizeof(response),
            5000))
    {
        // Neu client 0 bi ket do lan chay truoc (vi du ESP32 reset), thuc hien reset sach stack
        Serial.println("MQTT-LTE: CMQTTACCQ loi, dang tien hanh reset sach MQTT stack va thu lai...");
        MQTT_LTE_ForceCleanService();

        if (!A7680C_SendCommand(
                command,
                "OK",
                response,
                sizeof(response),
                5000))
        {
            Serial.println("MQTT-LTE: CMQTTACCQ that bai sau khi reset stack!");
            Serial.println(response[0] ? response : "<EMPTY>");
            A7680C_Unlock();
            return false;
        }
    }

    Serial.println("MQTT-LTE: Da acquire MQTT client thanh cong");

    // --------------------------------------------------------
    // 2.2. Cau hinh SSL Context (Neu su dung port 8883 / TLS)
    // --------------------------------------------------------
    if (isSsl)
    {
        Serial.println("MQTT-LTE: Dang cau hinh SSL/TLS context cho HiveMQ/Cloud...");

        // TLS version 1.2
        A7680C_SendCommand("AT+CSSLCFG=\"sslversion\",0,4", "OK", response, sizeof(response), 3000);
        // Authmode: 0 = khong xac thuc chung chi may chu (insecure/bo qua CA)
        A7680C_SendCommand("AT+CSSLCFG=\"authmode\",0,0", "OK", response, sizeof(response), 3000);
        // Bo qua chenh lech thoi gian he thong RTC
        A7680C_SendCommand("AT+CSSLCFG=\"ignorelocaltime\",0,1", "OK", response, sizeof(response), 3000);
        // BAT SNI (Server Name Indication) - BAT BUOC doi voi HiveMQ Cloud!
        A7680C_SendCommand("AT+CSSLCFG=\"enableSNI\",0,1", "OK", response, sizeof(response), 3000);

        // Gan SSL context 0 vao MQTT client 0
        if (!A7680C_SendCommand(
                "AT+CMQTTSSLCFG=0,0",
                "OK",
                response,
                sizeof(response),
                5000))
        {
            Serial.println("MQTT-LTE: Gan SSL context that bai!");
            Serial.println(response[0] ? response : "<EMPTY>");
            A7680C_Unlock();
            return false;
        }

        Serial.println("MQTT-LTE: Da gan SSL context thanh cong");
    }

    // --------------------------------------------------------
    // 2.3. Ket noi den MQTT broker
    // --------------------------------------------------------
    if (u != nullptr && strlen(u) > 0 && pwd != nullptr)
    {
        length = snprintf(
            command,
            sizeof(command),
            "AT+CMQTTCONNECT=0,\"tcp://%s:%u\",60,1,\"%s\",\"%s\"",
            b,
            p,
            u,
            pwd
        );
    }
    else
    {
        length = snprintf(
            command,
            sizeof(command),
            "AT+CMQTTCONNECT=0,\"tcp://%s:%u\",60,1",
            b,
            p
        );
    }

    if (length < 0 || length >= (int)sizeof(command))
    {
        Serial.println("MQTT-LTE: Lenh CMQTTCONNECT qua dai!");
        A7680C_Unlock();
        return false;
    }

    Serial.print("MQTT-LTE: Dang ket noi broker ");
    Serial.print(b);
    Serial.print(":");
    Serial.println(p);

    if (!A7680C_SendCommand(
            command,
            "+CMQTTCONNECT: 0,0",
            response,
            sizeof(response),
            35000))
    {
        Serial.println("MQTT-LTE: Ket noi broker that bai!");
        Serial.println(response[0] ? response : "<EMPTY>");

        if (strstr(response, "+CMQTTCONNECT: 0,6") != nullptr)
        {
            Serial.println("   [!] Ma loi 6: Handshake SSL hoac ket noi mang khong thanh cong.");
        }
        else if (strstr(response, "+CMQTTCONNECT: 0,4") != nullptr)
        {
            Serial.println("   [!] Ma loi 4: Sai username hoac password!");
        }
        else if (strstr(response, "+CMQTTCONNECT: 0,32") != nullptr)
        {
            Serial.println("   [!] Ma loi 32: Loi cau hinh SSL / SNI.");
        }

        mqttLteConnected = false;
        A7680C_Unlock();
        return false;
    }

    mqttLteConnected = true;
    Serial.println("MQTT-LTE: Da ket noi MQTT broker thanh cong!");
    A7680C_Unlock();
    return true;
}

// ============================================================
// 3. PUBLISH MESSAGE QUA LTE
// ============================================================
bool MQTT_LTE_Publish(
    const char* topic,
    const char* payload)
{
    if (topic == nullptr || payload == nullptr)
    {
        Serial.println("MQTT-LTE: Topic hoac Payload khong hop le!");
        return false;
    }

    if (!mqttLteConnected)
    {
        Serial.println("MQTT-LTE: Chua ket noi MQTT broker, khong the publish!");
        return false;
    }

    if (!A7680C_Lock(30000))
    {
        Serial.println("MQTT-LTE: Khong the lay khoa modem de publish!");
        return false;
    }

    char command[64];
    char response[256];
    size_t topicLen = strlen(topic);
    size_t payloadLen = strlen(payload);

    // --------------------------------------------------------
    // Buoc 1: Gui Topic (AT+CMQTTTOPIC=0,<len>)
    // --------------------------------------------------------
    snprintf(command, sizeof(command), "AT+CMQTTTOPIC=0,%u", (unsigned)topicLen);
    if (!A7680C_SendCommand(command, ">", response, sizeof(response), 5000))
    {
        Serial.println("MQTT-LTE: Khong nhan duoc dau nhac '>' cho Topic!");
        A7680C_Unlock();
        return false;
    }

    // Truyen chinh xac topicLen byte raw khong kem CRLF
    if (!A7680C_SendRawData((const uint8_t*)topic, topicLen))
    {
        Serial.println("MQTT-LTE: Ghi du lieu Topic that bai!");
        A7680C_Unlock();
        return false;
    }

    // Cho xac nhan OK
    if (!A7680C_SendCommand("", "OK", response, sizeof(response), 5000))
    {
        Serial.println("MQTT-LTE: Xac nhan Topic that bai!");
        A7680C_Unlock();
        return false;
    }

    // --------------------------------------------------------
    // Buoc 2: Gui Payload (AT+CMQTTPAYLOAD=0,<len>)
    // --------------------------------------------------------
    snprintf(command, sizeof(command), "AT+CMQTTPAYLOAD=0,%u", (unsigned)payloadLen);
    if (!A7680C_SendCommand(command, ">", response, sizeof(response), 5000))
    {
        Serial.println("MQTT-LTE: Khong nhan duoc dau nhac '>' cho Payload!");
        A7680C_Unlock();
        return false;
    }

    // Truyen chinh xac payloadLen byte raw khong kem CRLF
    if (!A7680C_SendRawData((const uint8_t*)payload, payloadLen))
    {
        Serial.println("MQTT-LTE: Ghi du lieu Payload that bai!");
        A7680C_Unlock();
        return false;
    }

    // Cho xac nhan OK
    if (!A7680C_SendCommand("", "OK", response, sizeof(response), 5000))
    {
        Serial.println("MQTT-LTE: Xac nhan Payload that bai!");
        A7680C_Unlock();
        return false;
    }

    // --------------------------------------------------------
    // Buoc 3: Phat lenh Publish (QoS 1, pub_timeout = 60s)
    // --------------------------------------------------------
    if (!A7680C_SendCommand(
            "AT+CMQTTPUB=0,1,60",
            "+CMQTTPUB: 0,0",
            response,
            sizeof(response),
            15000))
    {
        // Mot so phien ban firmware tra ve OK truoc khi tra URC
        if (strstr(response, "OK") == nullptr && strstr(response, "+CMQTTPUB: 0,0") == nullptr)
        {
            Serial.println("MQTT-LTE: Publish message that bai!");
            Serial.println(response[0] ? response : "<EMPTY>");
            A7680C_Unlock();
            return false;
        }
    }

    Serial.printf("MQTT-LTE: Publish thanh cong len topic \"%s\"\n", topic);
    A7680C_Unlock();
    return true;
}

// ============================================================
// 4. KIEM TRA TRANG THAI MQTT CONNECTION
// ============================================================
bool MQTT_LTE_IsConnected(void)
{
    if (!mqttLteStarted || !mqttLteConnected)
    {
        return false;
    }

    // Gioi han tan suat gui lenh AT xuong modem (toi da 1 lan moi 3 giay)
    static uint32_t lastCheck = 0;
    uint32_t now = millis();
    if (now - lastCheck < 3000)
    {
        return mqttLteConnected;
    }
    lastCheck = now;

    char response[256];
    if (!A7680C_SendCommand(
            "AT+CMQTTCONNECT?",
            "OK",
            response,
            sizeof(response),
            3000))
    {
        mqttLteConnected = false;
        return false;
    }

    // Neu client 0 dang ket noi se co chuoi: +CMQTTCONNECT: 0,"tcp://..."
    if (strstr(response, "+CMQTTCONNECT: 0,") != nullptr)
    {
        mqttLteConnected = true;
        return true;
    }

    mqttLteConnected = false;
    return false;
}

// ============================================================
// 5. DUY TRI VA THEO DOI KET NOI (LOOP)
// ============================================================
void MQTT_LTE_Loop(void)
{
    if (!mqttLteStarted)
    {
        return;
    }

    // Kiem tra du lieu URC bat dong bo tren cong UART (vd: +CMQTTCONNLOST)
    if (A7680C_Lock(50))
    {
        HardwareSerial* serial = A7680C_GetSerial();
        if (serial != nullptr && serial->available())
        {
            char buf[128];
            size_t len = 0;
            while (serial->available() && len + 1 < sizeof(buf))
            {
                buf[len++] = (char)serial->read();
            }
            buf[len] = '\0';

            if (strstr(buf, "+CMQTTCONNLOST") != nullptr)
            {
                Serial.println("MQTT-LTE: Phat hien mat ket noi (URC: +CMQTTCONNLOST)!");
                mqttLteConnected = false;
            }
        }
        A7680C_Unlock();
    }

    MQTT_LTE_IsConnected();
}

// ============================================================
// 6. NGAT KET NOI VA GIAI PHONG TAI NGUYEN
// ============================================================
bool MQTT_LTE_Disconnect(void)
{
    if (!mqttLteStarted && !mqttLteConnected)
    {
        return true;
    }

    if (!A7680C_Lock(25000))
    {
        return false;
    }

    char response[128];

    Serial.println("MQTT-LTE: Dang ngat ket noi MQTT...");

    // 1. Ngat ket noi khoi broker
    A7680C_SendCommand("AT+CMQTTDISC=0,120", "OK", response, sizeof(response), 10000);

    // 2. Giai phong MQTT client
    A7680C_SendCommand("AT+CMQTTREL=0", "OK", response, sizeof(response), 5000);

    // 3. Dung MQTT service
    A7680C_SendCommand("AT+CMQTTSTOP", "OK", response, sizeof(response), 5000);

    mqttLteConnected = false;
    mqttLteStarted = false;

    Serial.println("MQTT-LTE: Da ngat ket noi va giai phong service thanh cong");
    A7680C_Unlock();
    return true;
}

// ============================================================
// 7. KET NOI LAI MQTT BROKER (SU DUNG CAU HINH DA CACHE)
// ============================================================
bool MQTT_LTE_Reconnect(void)
{
    Serial.println("\nMQTT-LTE: [RECONNECT] Dang thuc hien ket noi lai MQTT Broker...");

    const char* b = (cachedBroker[0] != '\0') ? cachedBroker : MQTT_BROKER;
    uint16_t p = (cachedPort != 0) ? cachedPort : MQTT_PORT;
    const char* cId = (cachedClientId[0] != '\0') ? cachedClientId : MQTT_CLIENT_ID;
    const char* u = (cachedUsername[0] != '\0') ? cachedUsername : MQTT_USERNAME;
    const char* pwd = (cachedPassword[0] != '\0') ? cachedPassword : MQTT_PASSWORD;

    // Chu dong giai phong va reset stack MQTT tren module SIM de dam bao khong con socket/client treo
    MQTT_LTE_ForceCleanService();

    return MQTT_LTE_Connect(b, p, cId, u, pwd);
}
