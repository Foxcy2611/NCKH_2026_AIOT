#include "Packet_Metadata.h"

#include <Arduino.h>
#include <Preferences.h>
#include <esp_system.h>

namespace {
    constexpr char NVS_NAMESPACE[] = "packet_meta";
    constexpr char NVS_SEQUENCE_KEY[] = "sequence";

    uint32_t device_id = 0;
    uint32_t next_sequence = 0;
}  // namespace

void PacketMetadata_Init(void) {
    const uint64_t efuse_mac = ESP.getEfuseMac();
    device_id = static_cast<uint32_t>(efuse_mac)
        ^ static_cast<uint32_t>(efuse_mac >> 32U);
    if (device_id == 0U) device_id = 1U;

    Preferences preferences;
    next_sequence = preferences.begin(NVS_NAMESPACE, true)
        ? preferences.getUInt(NVS_SEQUENCE_KEY, 0U)
        : 0U;
    preferences.end();
}

uint32_t PacketMetadata_GetDeviceId(void) {
    return device_id;
}

uint32_t PacketMetadata_NewSessionId(void) {
    uint32_t session_id = esp_random();
    if (session_id == 0U) session_id = 1U;
    return session_id;
}

uint32_t PacketMetadata_NextSequence(void) {
    ++next_sequence;
    if (next_sequence == 0U) ++next_sequence;

    Preferences preferences;
    if(preferences.begin(NVS_NAMESPACE, false)){
        preferences.putUInt(NVS_SEQUENCE_KEY, next_sequence);
        preferences.end();
    }

    return next_sequence;
}
