#include "ESP32_DHT22_Lib.h"
#include <esp_timer.h>

static portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;
static const uint32_t DHT22_SIGNAL_TIMEOUT_US = 120;
static const uint32_t DHT22_ONE_HIGH_THRESHOLD_US = 50;

enum class DHT22_PulseResult : uint8_t {
    OK,
    WAIT_TIMEOUT,
    PULSE_TIMEOUT
};

#if SENSOR_TIMING_DEBUG
static DHT22_TimingProfile DHT22_timingProfile = {};
#endif

// Chờ đúng state rồi đo độ dài xung bằng microsecond thực.
static DHT22_PulseResult DHT22_ExpectPulse(bool state,
                                           uint32_t *durationUs){
    int64_t startUs = esp_timer_get_time();
    while(digitalRead(DHT22_PIN) != state){
        if(esp_timer_get_time() - startUs >= DHT22_SIGNAL_TIMEOUT_US){
            *durationUs = 0;
            return DHT22_PulseResult::WAIT_TIMEOUT;
        }
    }

    startUs = esp_timer_get_time();
    while(digitalRead(DHT22_PIN) == state){
        int64_t elapsedUs = esp_timer_get_time() - startUs;
        if(elapsedUs >= DHT22_SIGNAL_TIMEOUT_US){
            *durationUs = static_cast<uint32_t>(elapsedUs);
            return DHT22_PulseResult::PULSE_TIMEOUT;
        }
    }

    *durationUs = static_cast<uint32_t>(esp_timer_get_time() - startUs);
    return DHT22_PulseResult::OK;
}

// Gọi trong setup
void DHT22_Init(void){
    pinMode(DHT22_PIN, INPUT_PULLUP);
}

uint8_t DHT22_ReadData(float* temp, float* humi){
#if SENSOR_TIMING_DEBUG
    DHT22_timingProfile = {};
    DHT22_timingProfile.timeoutStage = "none";
    DHT22_timingProfile.timeoutBit = -1;
#endif

    if(temp == nullptr || humi == nullptr){
#if SENSOR_TIMING_DEBUG
        DHT22_timingProfile.timeoutStage = "argument";
#endif
        return 1;
    }

    uint8_t data[5] = {0};

    pinMode(DHT22_PIN, OUTPUT_OPEN_DRAIN);
    digitalWrite(DHT22_PIN, LOW);
#if SENSOR_TIMING_DEBUG
    DHT22_timingProfile.startLowUs = esp_timer_get_time();
#endif
    delay(2); // DHT22 yêu cầu xung start LOW tối thiểu 1ms

    // Bảo vệ từ lúc release bus để không bỏ lỡ handshake 80us.
    portENTER_CRITICAL(&mux);
#if SENSOR_TIMING_DEBUG
    DHT22_timingProfile.criticalEnterUs = esp_timer_get_time();
#endif

    digitalWrite(DHT22_PIN, HIGH);
    // Chuyển sang input ngay; hàm đo tự chờ LOW để không bỏ lỡ response.
    pinMode(DHT22_PIN, INPUT_PULLUP);

    // Response: DHT22 đáp lại bằng cách
    // Kéo LOW 80us sau đó HIGH 80us
    uint32_t responseLowUs = 0;
    DHT22_PulseResult responseLowResult =
        DHT22_ExpectPulse(LOW, &responseLowUs);
#if SENSOR_TIMING_DEBUG
    DHT22_timingProfile.responseLowUs = responseLowUs;
#endif
    if(responseLowResult != DHT22_PulseResult::OK){
#if SENSOR_TIMING_DEBUG
        DHT22_timingProfile.timeoutStage =
            responseLowResult == DHT22_PulseResult::WAIT_TIMEOUT
                ? "response_low_wait"
                : "response_low_pulse";
        DHT22_timingProfile.criticalExitUs = esp_timer_get_time();
#endif
        portEXIT_CRITICAL(&mux);
        return 1;
    }

    uint32_t responseHighUs = 0;
    DHT22_PulseResult responseHighResult =
        DHT22_ExpectPulse(HIGH, &responseHighUs);
#if SENSOR_TIMING_DEBUG
    DHT22_timingProfile.responseHighUs = responseHighUs;
#endif
    if(responseHighResult != DHT22_PulseResult::OK){
#if SENSOR_TIMING_DEBUG
        DHT22_timingProfile.timeoutStage =
            responseHighResult == DHT22_PulseResult::WAIT_TIMEOUT
                ? "response_high_wait"
                : "response_high_pulse";
        DHT22_timingProfile.criticalExitUs = esp_timer_get_time();
#endif
        portEXIT_CRITICAL(&mux);
        return 1;
    }

    for(int j = 0 ; j < 5 ; j++){
        uint8_t byte = 0;
        for(int i = 0 ; i < 8 ; i++){
            uint32_t lowUs = 0;
            DHT22_PulseResult lowResult =
                DHT22_ExpectPulse(LOW, &lowUs);
            if(lowResult != DHT22_PulseResult::OK){
                // portEXIT_CRITICAL: Mở lại ngắt nếu lỗi
#if SENSOR_TIMING_DEBUG
                DHT22_timingProfile.timeoutStage =
                    lowResult == DHT22_PulseResult::WAIT_TIMEOUT
                        ? "data_low_wait"
                        : "data_low_pulse";
                DHT22_timingProfile.timeoutBit = j * 8 + i;
                DHT22_timingProfile.criticalExitUs = esp_timer_get_time();
#endif
                portEXIT_CRITICAL(&mux);
                return 1;
            }

            uint32_t highUs = 0;
            DHT22_PulseResult highResult =
                DHT22_ExpectPulse(HIGH, &highUs);
            if(highResult != DHT22_PulseResult::OK){
#if SENSOR_TIMING_DEBUG
                DHT22_timingProfile.timeoutStage =
                    highResult == DHT22_PulseResult::WAIT_TIMEOUT
                        ? "data_high_wait"
                        : "data_high_pulse";
                DHT22_timingProfile.timeoutBit = j * 8 + i;
                DHT22_timingProfile.criticalExitUs = esp_timer_get_time();
#endif
                portEXIT_CRITICAL(&mux);
                return 1;
            }

            if(highUs >= DHT22_ONE_HIGH_THRESHOLD_US){
                byte |= (1 << (7 - i));
            }
        }

        data[j] = byte;
    }

    // Bật lại ngắt cho hệ thống bình thường
#if SENSOR_TIMING_DEBUG
    DHT22_timingProfile.criticalExitUs = esp_timer_get_time();
#endif
    portEXIT_CRITICAL(&mux);
    
    // Kiểm tra Checksum
    uint8_t sum = (data[0] + data[1] + data[2] + data[3]) & 0xFF;
    if (data[4] != sum) {
        return 2; // Lỗi dữ liệu nhiễu
    }

    // Xuất dữ liệu
    *humi = ((data[0] << 8) | data[1]) / 10.0;
    // 1. Lấy 7 bit của data[2] ghép với 8 bit của data[3] để tạo thành số nguyên, sau đó chia 10
    float t = (((data[2] & 0x7F) << 8) | data[3]) / 10.0;

    // 2. Kiểm tra bit cao nhất (bit thứ 8) của data[2]. Nếu là 1 thì nhiệt độ đang ở mức âm
    if (data[2] & 0x80) { 
        t = -t;
    }

    // 3. Xuất giá trị cuối cùng ra biến con trỏ
    *temp = t;
    return 0;
}

#if SENSOR_TIMING_DEBUG
void DHT22_GetTimingProfile(DHT22_TimingProfile *profile){
    if(profile != nullptr){
        *profile = DHT22_timingProfile;
    }
}
#endif

void DHT22_TestMain(void){
    float temp, humi;
    
    uint8_t err = DHT22_ReadData(&temp, &humi);

    if (err == 0) {
        Serial.printf("[OK] Nhiet do: %.1f *C  |  Do am: %.1f %%\n", temp, humi);
    } 
    else if (err == 1) {
        Serial.println("[ERR] Loi Timeout - Kiem tra day DHT22 hoac tro keo pull-up!");
    } 
    else if (err == 2) {
        Serial.println("[ERR] Loi Checksum - Nhieu tin hieu tren day DATA!");
    }
}
