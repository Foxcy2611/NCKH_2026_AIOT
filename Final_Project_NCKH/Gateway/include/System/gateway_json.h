#pragma once
#include <stddef.h>
#include "Config/gateway_types.h"
// Returns false on overflow; output becomes empty, never truncated JSON.
bool GatewaySerializeJson(const UplinkRecord &item, char *out, size_t capacity);
bool GatewaySerializeStatusJson(const NetworkSnapshot &network, bool node_valid,
                                bool node_dirty, uint64_t node_revision,
                                uint64_t uptime_ms, uint32_t free_heap,
                                char *out, size_t capacity);
bool GatewaySerializeAlertJson(const UplinkRecord &item, char *out, size_t capacity);

// Complete cloud packet. Node data is attached only while node_dirty is true;
// node_valid independently reports whether Gateway still keeps a latest Node event.
bool GatewaySerializeDashboardJson(const UplinkRecord &item,
    const NetworkSnapshot &network, bool node_valid, bool node_dirty,
    uint64_t node_revision,
    uint64_t uptime_ms, uint32_t free_heap, char *out, size_t capacity);
