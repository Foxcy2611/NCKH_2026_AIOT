#include <Arduino.h>
#include "ESP32_A7680C_AT.h"
#include "Network/gateway_lte.h"
#include "Network/gateway_mqtt_lte.h"
#include "Config/gateway_types.h"

// ============================================================
// 1. CAU HINH THONG SO HIVEMQ CLOUD / MQTT BROKER
//    --> BAN CO THE THAY DOI CAC THAM SO NAY TAI DAY <--
// ============================================================
#define MQTT_BROKER       "6ff32dfda1cd49c49496e5b35f957f87.s1.eu.hivemq.cloud"
#define MQTT_PORT         8883                       // Port 8883 (SSL/TLS cho HiveMQ Cloud), hoac 1883 (TCP thuong)
#define MQTT_CLIENT_ID    "NCKH_Gateway_A7680C_01"   // Client ID tuy y
#define MQTT_USERNAME     "AIOT_2026"               // <<-- NHAP USERNAME HIVEMQ TAI DAY
#define MQTT_PASSWORD     "12345678"                // <<-- NHAP PASSWORD HIVEMQ TAI DAY

#define MQTT_PUB_TOPIC    "nckh2026/gateway/patient_event" // Topic dung de publish du lieu

// Chu ky tu dong publish goi tin gia lap len broker (ms). Dat bang 0 neu chi muon bam phim de gui
#define AUTO_PUBLISH_INTERVAL_MS  10000             // Mac dinh: 10 giay tu dong tao & gui 1 ban tin

// ============================================================
// 2. CAU HINH PHAN CUNG MODULE SIM A7680C & NHA MANG
// ============================================================
#define SIM_RX_PIN        16                        // ESP32 RX (GPIO16) noi vao TX module SIM
#define SIM_TX_PIN        17                        // ESP32 TX (GPIO17) noi vao RX module SIM
#define SIM_BAUDRATE      115200

// APN cua cac nha mang tai Viet Nam:
// - Viettel:   "v-internet"
// - Vinaphone: "m3-world"
// - Mobifone:  "m-wap"
#define LTE_APN           "v-internet"

HardwareSerial SimSerial(2); // Su dung UART2 cua ESP32

// ============================================================
// BIEN TOAN CUC THEO DOI
// ============================================================
static uint32_t packetCounter = 0;

// ============================================================
// HAM TAO DU LIEU GIA LAP (MOCK PATIENT DATA)
// Mo phong dung theo cau truc PatientEventPacket cua he thong NCKH AIoT:
// - nhip tim (heart_rate)
// - nong do oxy trong mau (SpO2)
// - ket qua phan loai AI (ASTHMA_LIKE hoac NON_ASTHMA)
// - diem so tin cay AI (model_score)
// - muc pin & cuong do song LTE CSQ
// ============================================================
static void generateMockPatientData(char* jsonBuffer, size_t maxLen, int forceType = 0)
{
    packetCounter++;

    uint32_t deviceId = 1001;
    uint32_t sessionId = 1;
    unsigned long timestamp = millis();
    int csq = A7680C_GetSignalQuality();

    // forceType: 0 = Ngau nhien (20% co con hen), 1 = Ep Normal, 2 = Ep Asthma Alert
    bool isAsthma = false;
    if (forceType == 2) {
        isAsthma = true;
    } else if (forceType == 1) {
        isAsthma = false;
    } else {
        isAsthma = (random(0, 100) < 20); // 20% ti le xuat hien con hen gia lap
    }

    const char* classification = isAsthma ? "ASTHMA_LIKE" : "NON_ASTHMA";
    float modelScore = isAsthma ? (0.85f + (random(0, 140) / 1000.0f)) : (0.05f + (random(0, 200) / 1000.0f));
    int asthmaVotes = isAsthma ? random(8, 11) : random(0, 3);
    int nonAsthmaVotes = 10 - asthmaVotes;
    int heartRate = isAsthma ? random(105, 135) : random(68, 88);
    int spo2 = isAsthma ? random(88, 93) : random(96, 100);
    int battery = random(88, 99);

    snprintf(jsonBuffer, maxLen,
             "{\"device_id\":%lu,\"seq\":%lu,\"session_id\":%lu,\"timestamp\":%lu,"
             "\"event_type\":\"MONITOR\",\"classification\":\"%s\",\"model_score\":%.3f,"
             "\"asthma_votes\":%d,\"non_asthma_votes\":%d,\"heart_rate\":%d,\"spo2\":%d,"
             "\"battery\":%d,\"csq\":%d}",
             (unsigned long)deviceId,
             (unsigned long)packetCounter,
             (unsigned long)sessionId,
             timestamp,
             classification,
             modelScore,
             asthmaVotes,
             nonAsthmaVotes,
             heartRate,
             spo2,
             battery,
             csq);
}

// ============================================================
// HAM GUI DU LIEU LEN HIVEMQ
// ============================================================
bool publishMockData(int forceType = 0, const char* customPayload = nullptr)
{
    if (!MQTT_LTE_IsConnected())
    {
        Serial.println("\n[MQTT] Chua ket noi Broker, dang thu ket noi lai...");
        if (!MQTT_LTE_Reconnect())
        {
            Serial.println("[MQTT] Ket noi lai that bai!");
            return false;
        }
    }

    char payload[384];
    if (customPayload != nullptr && strlen(customPayload) > 0)
    {
        snprintf(payload, sizeof(payload), "%s", customPayload);
    }
    else
    {
        generateMockPatientData(payload, sizeof(payload), forceType);
    }

    Serial.println();
    Serial.println("==================================================");
    Serial.printf("[PUSH MQTT] GOI TIN #%lu LEN TOPIC:\n", (unsigned long)packetCounter);
    Serial.printf("  Topic  : %s\n", MQTT_PUB_TOPIC);
    Serial.printf("  Payload: %s\n", payload);
    Serial.println("--------------------------------------------------");

    bool ok = MQTT_LTE_Publish(MQTT_PUB_TOPIC, payload);
    if (ok)
    {
        Serial.println("[THÀNH CÔNG] >> DA PUSH DU LIEU LEN HIVEMQ CLOUD!");
    }
    else
    {
        Serial.println("[THẤT BẠI]  >> PUSH DU LIEU THAT BAI!");
    }
    Serial.println("==================================================");
    return ok;
}

// ============================================================
// SETUP
// ============================================================
void setup()
{
    Serial.begin(115200);
    delay(1000);

    Serial.println();
    Serial.println("==================================================");
    Serial.println("      ESP32 - PUSH DU LIEU GIA LAP LEN HIVEMQ     ");
    Serial.println("==================================================");
    Serial.printf(" Broker   : %s:%d\n", MQTT_BROKER, MQTT_PORT);
    Serial.printf(" ClientId : %s\n", MQTT_CLIENT_ID);
    Serial.printf(" Username : %s\n", MQTT_USERNAME);
    Serial.printf(" Topic    : %s\n", MQTT_PUB_TOPIC);
    Serial.println("==================================================");

    // 1. Khoi tao giao tiep UART2 voi module A7680C
    Serial.println("\n[1] Khoi tao module SIM A7680C tren UART2 (RX:16, TX:17)...");
    if (!LTE_Init(SimSerial, SIM_RX_PIN, SIM_TX_PIN, SIM_BAUDRATE))
    {
        Serial.println("[LOI] Khong the ket noi voi module A7680C! Kiem tra day va nguon.");
        return;
    }
    Serial.println("[OK] Khoi tao module thanh cong.");

    // 2. Kiem tra SIM va dang ky mang
    Serial.println("\n[2] Kiem tra SIM & trang thai song LTE...");
    if (!A7680C_CheckSIM())
    {
        Serial.println("[LOI] SIM chua san sang!");
        return;
    }
    Serial.println("[OK] SIM san sang.");

    int csq = A7680C_GetSignalQuality();
    Serial.printf("    Cuong do song RF (CSQ): %d / 31\n", csq);

    int retry = 0;
    while (!A7680C_CheckNetwork() && retry < 10)
    {
        Serial.printf("    Chua co song mang LTE, dang cho ket noi lai (%d/10)...\n", retry + 1);
        delay(2000);
        retry++;
    }

    if (!A7680C_CheckNetwork())
    {
        Serial.println("[LOI] Chua dang ky duoc vao mang LTE!");
        return;
    }
    Serial.println("[OK] Da dang ky vao mang LTE thanh cong!");

    // 3. Kich hoat du lieu LTE (APN & PDP Context)
    Serial.printf("\n[3] Kich hoat ket noi du lieu LTE voi APN \"%s\"...\n", LTE_APN);
    if (!LTE_Connect(LTE_APN))
    {
        Serial.println("[CANH BAO] Kich hoat APN/PDP that bai, van thu ket noi MQTT...");
    }
    else
    {
        Serial.println("[OK] Ket noi du lieu LTE san sang.");
    }

    // 4. Ket noi MQTT den HiveMQ Cloud qua TLS
    Serial.println("\n[4] Ket noi den HiveMQ Cloud qua SSL/TLS (port 8883)...");
    bool mqttOk = MQTT_LTE_Connect(
        MQTT_BROKER,
        MQTT_PORT,
        MQTT_CLIENT_ID,
        MQTT_USERNAME,
        MQTT_PASSWORD
    );

    if (mqttOk)
    {
        Serial.println("[THÀNH CÔNG] >> DA KET NOI HIVEMQ CLOUD THANH CONG!");

        // 5. Push ngay goi tin dau tien khi ket noi thanh cong
        delay(1000);
        publishMockData(0);
    }
    else
    {
        Serial.println("[THẤT BẠI]  >> KHONG THE KET NOI DEN HIVEMQ!");
        Serial.println("  Kiem tra lai: Username/Password HiveMQ, Cluster URL va dung luong data SIM.");
    }

    // Huong dan dieu khien
    Serial.println();
    Serial.println("==================================================");
    Serial.println("[PHIM TAT DIEU KHIEN]");
    Serial.println(" - 'p' + Enter : Push ngau nhien 1 goi tin gia lap");
    Serial.println(" - 'a' + Enter : Mo phong su co HEN CAP (ASTHMA_LIKE, SpO2 giam, tim nhanh)");
    Serial.println(" - 'n' + Enter : Mo phong chi so BINH THUONG (NON_ASTHMA, SpO2 98%, tim 75)");
    Serial.println(" - 's' + Enter : Kiem tra trang thai song & ket noi");
    Serial.println(" - 'r' + Enter : Yeu cau ket noi lai MQTT");
#if (AUTO_PUBLISH_INTERVAL_MS > 0)
    Serial.printf(" - Che do AUTO : Tu dong push sau moi %lu giay\n", (unsigned long)(AUTO_PUBLISH_INTERVAL_MS / 1000));
#endif
    Serial.println("==================================================");
}

// ============================================================
// LOOP: DUY TRI KET NOI VA XU LY LENH
// ============================================================
void loop()
{
    // 1. Duy tri MQTT Stack
    MQTT_LTE_Loop();

    // 2. Xu ly lenh nhap tu Serial Monitor
    if (Serial.available() > 0)
    {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();

        if (cmd.length() > 0)
        {
            if (cmd.equalsIgnoreCase("p"))
            {
                Serial.println("\n[LENH] Push goi tin ngau nhien!");
                publishMockData(0);
            }
            else if (cmd.equalsIgnoreCase("a"))
            {
                Serial.println("\n[LENH] GIA LAP CON HEN CAP (ASTHMA ALERT)!");
                publishMockData(2);
            }
            else if (cmd.equalsIgnoreCase("n"))
            {
                Serial.println("\n[LENH] GIA LAP BENH NHAN BINH THUONG (NORMAL)!");
                publishMockData(1);
            }
            else if (cmd.equalsIgnoreCase("s"))
            {
                int csq = A7680C_GetSignalQuality();
                bool net = A7680C_CheckNetwork();
                bool mqtt = MQTT_LTE_IsConnected();
                char cbc[64];
                A7680C_SendCommand("AT+CBC", "OK", cbc, sizeof(cbc), 1000);

                Serial.println("\n----- TRANG THAI HE THONG -----");
                Serial.printf("  Song RF (CSQ)   : %d / 31\n", csq);
                Serial.printf("  Mang LTE        : %s\n", net ? "DA VAO MANG" : "MAT MANG");
                Serial.printf("  MQTT HiveMQ     : %s\n", mqtt ? "CONNECTED" : "DISCONNECTED");
                Serial.printf("  Dien ap pin CBC : %s\n", cbc[0] ? cbc : "<N/A>");
                Serial.printf("  So goi da push  : %lu\n", (unsigned long)packetCounter);
                Serial.println("--------------------------------");
            }
            else if (cmd.equalsIgnoreCase("r"))
            {
                Serial.println("\n[LENH] Dang ket noi lai MQTT Broker...");
                MQTT_LTE_Reconnect();
            }
            else
            {
                Serial.printf("\n[LENH] Push payload tuy chon tu ban phim: %s\n", cmd.c_str());
                publishMockData(0, cmd.c_str());
            }
        }
    }

#if (AUTO_PUBLISH_INTERVAL_MS > 0)
    // 3. Tu dong push du lieu gia lap theo chu ky
    static uint32_t lastAutoPub = 0;
    if (millis() - lastAutoPub >= AUTO_PUBLISH_INTERVAL_MS)
    {
        lastAutoPub = millis();

        if (MQTT_LTE_IsConnected())
        {
            Serial.println("\n[AUTO] Dinh ky push du lieu len HiveMQ...");
            publishMockData(0);
        }
        else
        {
            Serial.println("\n[AUTO] MQTT dang ngat ket noi, dang thu ket noi lai...");
            MQTT_LTE_Reconnect();
        }
    }
#endif

    vTaskDelay(pdMS_TO_TICKS(50));
}