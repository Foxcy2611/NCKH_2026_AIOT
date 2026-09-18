#include <Arduino.h>
#include "Network/gateway_espnow.h"
#include "Network/gateway_wifi.h"
#include "crc32.h"

// Cấu trúc packet dữ liệu gửi từ ESP A -> ESP B
// Packet thử nghiệm CRC32 cũ; không phải Secure_EspNow_Packet_t chính thức.
struct __attribute__((packed)) Legacy_Patient_Event_Packet_t
{
    uint32_t device_id;
    uint32_t sequence;
    uint32_t session_id;
    uint64_t timestamp;

    uint8_t event_type;
    uint8_t classification;
    float model_score;

    uint8_t audio_quality;

    bool vitals_valid;
    uint16_t heart_rate;
    uint8_t spo2;

    uint8_t battery;

    uint32_t crc32;
};

// MAC của ESP B (peer nhận data)
static const uint8_t peerMac[6] = {0x44, 0x1B, 0xF6, 0x81, 0xE8, 0xB0};

void setup()
{
    Serial.begin(9600);
    delay(1000);

    WiFi_Init();

    Serial.println("=== ESP A sender start ===");

    ESPNow_Init();
    ESPNow_AddPeer(peerMac);
}

void loop()
{
    static uint32_t lastSend = 0;
    static uint32_t sequence = 0;

    if (millis() - lastSend >= 2000)
    {
        Legacy_Patient_Event_Packet_t packet{};

        packet.device_id = 1001;
        packet.sequence = ++sequence;
        packet.session_id = 20260610;
        packet.timestamp = millis();
        packet.event_type = 1;
        packet.classification = 0;
        packet.model_score = 0.96f;
        packet.audio_quality = 2;
        packet.vitals_valid = true;
        packet.heart_rate = 78;
        packet.spo2 = 98;
        packet.battery = 87;

        packet.crc32 = 0;
        packet.crc32 = Crc32_Compute(&packet, sizeof(packet) - sizeof(packet.crc32));

        Serial.printf("[ESP A] Sending packet seq=%u, temp? no, event_type=%u\n",
                      packet.sequence,
                      packet.event_type);

        const uint8_t *raw = reinterpret_cast<const uint8_t *>(&packet);
        ESPNow_Send(peerMac, raw, sizeof(packet));

        lastSend = millis();
    }

    delay(50);
}
