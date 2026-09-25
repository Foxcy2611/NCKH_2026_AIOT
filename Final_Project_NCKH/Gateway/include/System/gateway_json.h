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

// Complete latest-state snapshot, including clean (already published) Node data.
bool GatewaySerializeDashboardJson(const UplinkRecord &item,
    const NetworkSnapshot &network, bool node_dirty, uint64_t node_revision,
    uint64_t uptime_ms, uint32_t free_heap, char *out, size_t capacity);
