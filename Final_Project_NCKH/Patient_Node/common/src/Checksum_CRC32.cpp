#include "Checksum_CRC32.h"

uint32_t Crc32_Update(uint32_t previous_crc, const void *data, size_t length){
    const uint8_t *bytes = (const uint8_t *)data;
    uint32_t crc = ~previous_crc;

    if((bytes == NULL) && (length > 0U)){
        return previous_crc;
    }

    for(size_t i = 0U; i < length; ++i){
        crc ^= bytes[i];
        for(uint32_t bit = 0U; bit < 8U; ++bit){
            const uint32_t mask = 0U - (crc & 1U);
            crc = (crc >> 1U) ^ (UINT32_C(0xEDB88320) & mask);
        }
    }

    return ~crc;
}

uint32_t Crc32_Compute(const void *data, size_t length){
    return Crc32_Update(0U, data, length);
}
