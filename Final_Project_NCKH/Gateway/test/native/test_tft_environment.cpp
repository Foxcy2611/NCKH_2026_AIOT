#include <cassert>
#include <cstring>
#include "Display_TFT/gateway_environment_text.h"
#include "System/gateway_dht22_cache.h"
#include "System/gateway_record.h"
int main() {
    char t[16], h[16];
    GatewayFormatEnvironment(NAN, NAN, t, h);
    assert(!strcmp(t,"N/A") && !strcmp(h,"N/A"));
    GatewayFormatEnvironment(INFINITY, -INFINITY, t, h);
    assert(!strcmp(t,"N/A") && !strcmp(h,"N/A"));
    GatewayFormatEnvironment(-40, 100, t, h);
    assert(!strcmp(t,"-40.0") && !strcmp(h,"100%"));
    GatewayFormatEnvironment(0, 0, t, h);
    assert(!strcmp(t,"0.0") && !strcmp(h,"0%"));
    GatewayFormatEnvironment(81, 101, t, h);
    assert(!strcmp(t,"N/A") && !strcmp(h,"N/A"));
    LatestDht22 cache;
    EnvironmentSnapshot env{};
    float temperature, humidity;
    cache.copyTo(env);
    GatewayEnvironmentValues(GatewayBuildPayload(env,100), temperature, humidity);
    assert(isnan(temperature) && isnan(humidity));
    assert(cache.update(0,29.5f,55));
    assert(!cache.update(1,NAN,NAN));
    cache.copyTo(env);
    auto gate=GatewayBuildPayload(env,100000);
    GatewayEnvironmentValues(gate,temperature,humidity);
    GatewayFormatEnvironment(temperature,humidity,t,h);
    assert(!strcmp(t,"29.5") && !strcmp(h,"55%"));
    gate.sensor_valid_mask=0;
    GatewayEnvironmentValues(gate,temperature,humidity);
    assert(isnan(temperature) && isnan(humidity));
    puts("PASS: TFT NA, finite values, ranges, zero, DHT cache, validity mask");
}
