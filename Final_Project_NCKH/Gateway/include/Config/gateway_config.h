#ifndef NCKH_GATEWAY_CONFIG_H
#define NCKH_GATEWAY_CONFIG_H

// ============================================================
// Serial
// ============================================================

#define GATEWAY_SERIAL_BAUD 115200


// ============================================================
// FreeRTOS Queue configuration
// ============================================================

// Queue chứa raw ESP-NOW packet
#define ESPNOW_RX_QUEUE_LENGTH 10

// Queue chứa PatientEventPacket
#define PATIENT_EVENT_QUEUE_LENGTH 10


// ============================================================
// FreeRTOS Task configuration
// ============================================================

#define TASK_ESPNOW_STACK_SIZE       4096
#define TASK_GATEWAY_STACK_SIZE      4096
#define TASK_SENSOR_STACK_SIZE       2048
#define TASK_NETWORK_STACK_SIZE      2048

#define TASK_ESPNOW_PRIORITY         3
#define TASK_GATEWAY_PRIORITY        2
#define TASK_SENSOR_PRIORITY         1
#define TASK_NETWORK_PRIORITY        1


// ============================================================
// ESP-NOW
// ============================================================

// Phase 10 chỉ cần receiver.
// Channel sau này phải thống nhất với Patient Node.
#define ESPNOW_CHANNEL 1


// ============================================================
// Phase 10 Mock test
//
// 1 = tự tạo packet giả để test Queue
// 0 = chỉ nhận packet ESP-NOW thật
// ============================================================

#define ENABLE_MOCK_PACKET 1

#define MOCK_PACKET_INTERVAL_MS 5000


#endif