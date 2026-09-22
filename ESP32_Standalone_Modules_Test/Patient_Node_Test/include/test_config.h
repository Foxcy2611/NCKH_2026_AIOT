#ifndef NCKH_PATIENT_NODE_TEST_CONFIG_H
#define NCKH_PATIENT_NODE_TEST_CONFIG_H

#include <stdint.h>

// Final 2 Gateway currently fixes ESP-NOW to channel 1.
static constexpr uint8_t ESPNOW_TEST_CHANNEL = 1;

// Broadcast is used for the first M4 transport test, so you do not have to
// hard-code the Gateway MAC. Gateway replies are still sent unicast to this
// Node's real MAC.
static const uint8_t ESP_NOW_BROADCAST_MAC[6] = {
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF
};

static constexpr uint32_t ACK_TIMEOUT_MS = 2500;

// Must match Final 2 Gateway.
static constexpr uint32_t GATEWAY_DEVICE_ID = 0x47575431UL;

static const uint8_t KEY_NODE_TO_GATEWAY[16] = {
    0x42, 0x91, 0xD7, 0x2C, 0xA5, 0x68, 0x1B, 0xEF,
    0x30, 0xC4, 0x7A, 0x16, 0x8D, 0x53, 0xB9, 0xE2
};

static const uint8_t KEY_GATEWAY_TO_NODE[16] = {
    0xC8, 0x35, 0x6E, 0xA1, 0x19, 0xF4, 0x82, 0x5B,
    0xD0, 0x27, 0x9C, 0x73, 0x4A, 0xBE, 0x06, 0xE9
};

#endif
