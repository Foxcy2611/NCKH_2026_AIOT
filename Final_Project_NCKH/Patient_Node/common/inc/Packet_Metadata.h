#ifndef NCKH_PACKET_METADATA_H
#define NCKH_PACKET_METADATA_H

#include <stdbool.h>
#include <stdint.h>

// Khởi tạo định danh thiết bị và bộ đếm packet.
void PacketMetadata_Init(void);

// Device ID ổn định, được rút gọn từ MAC/eFuse của ESP32-S3.
uint32_t PacketMetadata_GetDeviceId(void);

// Tạo ID mới cho mỗi phiên đo CHECK hoặc MONITOR.
uint32_t PacketMetadata_NewSessionId(void);

// Chỉ gọi một lần khi packet được tạo và đưa vào hàng đợi gửi.
uint32_t PacketMetadata_NextSequence(void);

// Gateway cấp offset = Unix time (ms) - millis() của Node lúc đồng bộ.
void PacketMetadata_SetTimeOffset(int64_t offset_ms);
void PacketMetadata_ClearTimeOffset(void);
bool PacketMetadata_HasTimeSync(void);

// Trả về Unix time theo ms; trả về 0 nếu Node chưa nhận time offset.
uint64_t PacketMetadata_GetTimestamp(uint64_t local_millis);

#endif /* NCKH_PACKET_METADATA_H */
