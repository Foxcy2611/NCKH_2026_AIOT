#ifndef NCKH_PACKET_METADATA_H
#define NCKH_PACKET_METADATA_H

#include <stdint.h>

// Khởi tạo định danh thiết bị và bộ đếm packet.
void PacketMetadata_Init(void);

// Device ID ổn định, được rút gọn từ MAC/eFuse của ESP32-S3.
uint32_t PacketMetadata_GetDeviceId(void);

// Tạo ID mới cho mỗi phiên đo CHECK hoặc MONITOR.
uint32_t PacketMetadata_NewSessionId(void);

// Chỉ gọi một lần khi packet được tạo và đưa vào hàng đợi gửi.
uint32_t PacketMetadata_NextSequence(void);

#endif /* NCKH_PACKET_METADATA_H */
