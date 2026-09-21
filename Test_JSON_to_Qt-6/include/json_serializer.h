#ifndef JSON_SERIALIZER_H
#define JSON_SERIALIZER_H

#include <stddef.h>
#include "packet.h"

// Chuyen Complete_Packet_t noi bo thanh JSON de gui MQTT.
// Tra ve false neu bo dem dau ra khong du lon.
bool SerializeCompletePacketJson(const Complete_Packet_t &packet,
                                 char *output,
                                 size_t capacity);

#endif
