#ifndef NCKH_CHECKSUM_CRC32_H
#define NCKH_CHECKSUM_CRC32_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

uint32_t Crc32_Update(uint32_t previous_crc, const void *data, size_t length);
uint32_t Crc32_Compute(const void *data, size_t length);

#ifdef __cplusplus
}
#endif

#endif /* NCKH_CHECKSUM_CRC32_H */
