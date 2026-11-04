#include <cassert>
#include <cstdio>
#include <cstring>
#include "System/gateway_dht22_cache.h"
#include "System/gateway_record.h"
#include "System/gateway_json.h"

static void check(const LatestDht22 &cache, uint64_t now, bool valid, float t, float h) {
    EnvironmentSnapshot env{};
    env.gateway_timestamp_ms = 100;
    env.pressure_valid = true; env.pressure_hpa = 1013;
    cache.copyTo(env);
    UplinkRecord item{};
    item.record.gate = GatewayBuildPayload(env, now);
    const auto &g = item.record.gate;
    assert(bool(g.sensor_valid_mask & SENSOR_DHT22_VALID) == valid);
    if (valid) assert(g.temperature == t && g.humidity == h);
    else assert(isnan(g.temperature) && isnan(g.humidity));
    if (now > 100 + ENV_SNAPSHOT_MAX_AGE_MS) assert(isnan(g.pressure));
    char json[4096], expected[128];
    assert(GatewaySerializeJson(item, json, sizeof(json)));
    if (valid) snprintf(expected, sizeof(expected), "\"temperature\":%.6f,\"humidity\":%.6f", t, h);
    else strcpy(expected, "\"temperature\":null,\"humidity\":null");
    assert(strstr(json, expected));
}
int main() {
    LatestDht22 cache;
    check(cache, 100, false, 0, 0);
    assert(!cache.update(1, 25, 60)); check(cache, 100, false, 0, 0);
    assert(cache.update(0, 25, 60)); check(cache, 100, true, 25, 60);
    assert(!cache.update(1, 26, 61));
    assert(!cache.update(2, 26, 61));
    assert(!cache.update(0, NAN, 61));
    assert(!cache.update(0, 26, INFINITY));
    assert(!cache.update(0, 81, 61));
    assert(!cache.update(0, 26, -1));
    check(cache, 100, true, 25, 60);
    check(cache, 1000000, true, 25, 60); // DHT retained; other sensor ages out
    assert(cache.update(0, 29.5f, 55)); check(cache, 1000000, true, 29.5f, 55);
    assert(cache.update(0, -40, 0)); check(cache, 100, true, -40, 0);
    assert(cache.update(0, 80, 100)); check(cache, 100, true, 80, 100);
    LatestDht22 restarted; check(restarted, 100, false, 0, 0);
    puts("PASS: latest DHT22 initial null, failures retained, atomic pair, replacement, stale JSON, bounds, restart");
}
