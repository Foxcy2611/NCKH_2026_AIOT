#include <Arduino.h>
#include <Wire.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/semphr.h>
#include <freertos/task.h>

#if SENSOR_TIMING_DEBUG
#include <esp_timer.h>
#endif

#include "ESP32_DHT22_Lib.h"
#include "ESP32_BMP280_Lib.h"
#include "ESP32_SGP30_Lib.h"
#include "ESP32_MAX30102_Lib.h"
#include "ESP32_SSD1306_Display.h"
#include "ESP32_A7680C_AT.h"

static const TickType_t ENVIRONMENT_PERIOD = pdMS_TO_TICKS(1000);
static const TickType_t SENSOR_RETRY_DELAY = pdMS_TO_TICKS(5000);
static const uint8_t SENSOR_FAILURE_LIMIT = 3;
static const TickType_t SIM_RETRY_DELAY = pdMS_TO_TICKS(5000);
static const uint8_t SIM_QUEUE_LENGTH = 4;
static const uint32_t SIM_TASK_STACK_SIZE = 8192;
static const UBaseType_t SIM_TASK_PRIORITY = 1;
static const BaseType_t SIM_TASK_CORE = 0;
static const size_t SIM_PHONE_NUMBER_CAPACITY = 20;
#define DEBUG_MAX30102 1
static const uint8_t MAX30102_STABLE_READINGS_REQUIRED = 3;
static const int32_t MAX30102_MAX_HR_DELTA_BPM = 28;
static const int32_t MAX30102_MAX_SPO2_DELTA_PERCENT = 6;
static const float MAX30102_EMA_ALPHA = 0.15f;

enum class MAX30102_State : uint8_t {
  NOT_READY,
  MEASURING,
  NO_FINGER,
  STABILIZING,
  READY,
  TIMEOUT
};

struct MAX30102_Result {
  MAX30102_State state;
  int32_t heartRate;
  int8_t validHeartRate;
  int32_t spo2;
  int8_t validSpO2;
};

enum class SimAlertType : uint8_t {
  NONE,
  NORMAL,
  DANGEROUS
};

struct SimRequest {
  SimAlertType type;
  char phoneNumber[SIM_PHONE_NUMBER_CAPACITY];
};

static SemaphoreHandle_t i2cMutex = nullptr;
static SemaphoreHandle_t simMutex = nullptr;
static QueueHandle_t maxResultQueue = nullptr;
static QueueHandle_t simRequestQueue = nullptr;
static bool environmentTaskCreated = false;
static bool maxTaskCreated = false;
static bool simTaskCreated = false;
static uint32_t measurementIndex = 0;

#if SENSOR_TIMING_DEBUG
static volatile TickType_t maxTaskLastActiveTick = 0;
static volatile TickType_t maxGetStartTick = 0;
static volatile TickType_t maxGetEndTick = 0;
static volatile bool maxGetInProgress = false;
#endif

static bool LockI2C() {
  return i2cMutex != nullptr &&
         xSemaphoreTake(i2cMutex, portMAX_DELAY) == pdTRUE;
}

static void UnlockI2C() {
  if (i2cMutex != nullptr) {
    xSemaphoreGive(i2cMutex);
  }
}

static bool LockSIM() {
  return simMutex != nullptr &&
         xSemaphoreTake(simMutex, portMAX_DELAY) == pdTRUE;
}

static void UnlockSIM() {
  if (simMutex != nullptr) {
    xSemaphoreGive(simMutex);
  }
}

static bool TickReached(TickType_t now, TickType_t deadline) {
  return static_cast<int32_t>(now - deadline) >= 0;
}

static bool QueueSimAlert(SimAlertType type,
                          const char *phoneNumber) {
  if (type == SimAlertType::NONE) {
    return true;
  }

  if (simRequestQueue == nullptr ||
      phoneNumber == nullptr) {
    return false;
  }

  size_t phoneLength = strlen(phoneNumber);
  if (phoneLength >= SIM_PHONE_NUMBER_CAPACITY) {
    return false;
  }

  SimRequest request = {};
  request.type = type;
  memcpy(request.phoneNumber, phoneNumber, phoneLength + 1);
  return xQueueSend(simRequestQueue, &request, 0) == pdTRUE;
}

static bool InitBMP280() {
  if (!LockI2C()) {
    return false;
  }

  bool ready = BMP280_Init(BMP280_ADDR_REG);
  UnlockI2C();
  return ready;
}

static bool ReadBMP280(float *temperature, float *pressure) {
  if (!LockI2C()) {
    return false;
  }

  bool success = BMP280_ReadData(temperature, pressure);
  UnlockI2C();
  return success;
}

static bool InitSGP30() {
  if (!LockI2C()) {
    return false;
  }

  bool ready = SGP30_Init();
  UnlockI2C();
  return ready;
}

static bool ReadSGP30(SGP30_Data_t *data) {
  if (!LockI2C()) {
    return false;
  }

  bool success = SGP30_Measure(data);
  UnlockI2C();
  return success;
}

static bool InitOLED() {
  if (!LockI2C()) {
    return false;
  }

  bool ready = OLED_Init();
  UnlockI2C();
  return ready;
}

static bool FlushOLED() {
  if (!LockI2C()) {
    return false;
  }

  bool success = OLED_UpdateScreen();
  UnlockI2C();
  return success;
}

static bool InitMAX30102() {
  if (!LockI2C()) {
    return false;
  }

  bool ready = MAX30102_Init();
  UnlockI2C();
  return ready;
}

static bool ClearMAX30102Interrupt() {
  if (!LockI2C()) {
    return false;
  }

  bool success = MAX30102_ClearInterrupt();
  UnlockI2C();
  return success;
}

static uint8_t ReadMAX30102OverflowCounter() {
  if (!LockI2C()) {
    return 0;
  }

  uint8_t overflow = MAX30102_GetOverflowCounter();
  UnlockI2C();
  return overflow;
}

static void LogSensorRetry(const char *sensor,
                           TickType_t now,
                           TickType_t retryAt) {
  Serial.printf("RETRY %s: now_tick=%lu | retry_tick=%lu\n",
                sensor,
                (unsigned long)now,
                (unsigned long)retryAt);
}

static void PublishMAX30102Result(const MAX30102_Result &result) {
  xQueueOverwrite(maxResultQueue, &result);
}

static void MAX30102Task(void *parameter) {
  (void)parameter;

  bool ready = false;
  bool interruptAttached = false;
  uint8_t consecutiveValidCount = 0;
  float emaHeartRate = 0.0f;
  float emaSpO2 = 0.0f;
  bool emaInitialized = false;
  TickType_t nextRetry = xTaskGetTickCount();

  while (true) {
    TickType_t now = xTaskGetTickCount();
#if SENSOR_TIMING_DEBUG
    maxTaskLastActiveTick = now;
#endif

    if (!ready) {
      if (!TickReached(now, nextRetry)) {
        vTaskDelay(pdMS_TO_TICKS(100));
        continue;
      }

      if (interruptAttached) {
        detachInterrupt(digitalPinToInterrupt(INT_PIN));
        interruptAttached = false;
      }

      ready = InitMAX30102();
      if (!ready) {
        PublishMAX30102Result({MAX30102_State::NOT_READY, 0, 0, 0, 0});
        nextRetry = now + SENSOR_RETRY_DELAY;
        continue;
      }
      consecutiveValidCount = 0;

      attachInterrupt(digitalPinToInterrupt(INT_PIN), MAX30102_ISR, FALLING);
      interruptAttached = true;
      if (!ClearMAX30102Interrupt()) {
        detachInterrupt(digitalPinToInterrupt(INT_PIN));
        interruptAttached = false;
        ready = false;
        PublishMAX30102Result({MAX30102_State::NOT_READY, 0, 0, 0, 0});
        nextRetry = now + SENSOR_RETRY_DELAY;
        continue;
      }
      PublishMAX30102Result({MAX30102_State::MEASURING, 0, 0, 0, 0});
    }

#if SENSOR_TIMING_DEBUG
    int64_t maxTaskStartUs = esp_timer_get_time();
    maxGetStartTick = xTaskGetTickCount();
    maxGetInProgress = true;
#endif
    MAX30102_Result result = {MAX30102_State::READY, 0, 0, 0, 0};
    bool fingerDetected = true;
    bool measurementOk = MAX30102_GetHeartRateSpO2(&result.heartRate,
                                                   &result.validHeartRate,
                                                   &result.spo2,
                                                   &result.validSpO2,
                                                   &fingerDetected);
#if SENSOR_TIMING_DEBUG
    int64_t maxGetEndUs = esp_timer_get_time();
    maxGetEndTick = xTaskGetTickCount();
    maxTaskLastActiveTick = maxGetEndTick;
    maxGetInProgress = false;
    MAX30102_TimingProfile maxTiming = {};
    MAX30102_GetTimingProfile(&maxTiming);
    int64_t maxOverflowStartUs = esp_timer_get_time();
#endif
    uint8_t overflow = ReadMAX30102OverflowCounter();
#if SENSOR_TIMING_DEBUG
    int64_t maxOverflowUs = esp_timer_get_time() - maxOverflowStartUs;
#endif
    if (overflow > 0) {
      Serial.printf("MAX30102: CẢNH BÁO FIFO overflow=%u\n",
                    (unsigned)overflow);
    }

    if (!fingerDetected) {
#if DEBUG_MAX30102
      uint8_t countBeforeReset = consecutiveValidCount;
      bool hadBaseline = emaInitialized;
#endif
      consecutiveValidCount = 0;
      emaInitialized = false;
#if DEBUG_MAX30102
      if (countBeforeReset > 0 || hadBaseline) {
        Serial.printf(
            "[MAX-V] hr=%ld spo2=%ld finger=0 hrValid=%u spo2Valid=%u "
            "decision=RESET reason=NO_FINGER count_before=%u count_after=0\n",
            (long)result.heartRate,
            (long)result.spo2,
            (unsigned)result.validHeartRate,
            (unsigned)result.validSpO2,
            (unsigned)countBeforeReset
        );
      }
#endif
      PublishMAX30102Result({MAX30102_State::NO_FINGER, 0, 0, 0, 0});
      continue;
    }

    if (measurementOk) {
#if SENSOR_TIMING_DEBUG
      int64_t maxLogicStartUs = esp_timer_get_time();
#endif
      bool validReading = result.validHeartRate &&
                          result.validSpO2;
      bool stableReading = false;
      bool likelyHalfOrDoubleRate = false;
      bool baselineValid = emaInitialized && consecutiveValidCount > 0;
      bool outlier = false;
      uint8_t countBefore = consecutiveValidCount;
      int32_t hrDelta = -1;
      int32_t spo2Delta = -1;
      float emaHeartRateBefore = emaHeartRate;
      float emaSpO2Before = emaSpO2;
      const char *validationReason = "STABLE";

      if (!result.validHeartRate && !result.validSpO2) {
        validationReason = "HR_SPO2_INVALID";
      } else if (!result.validHeartRate) {
        validationReason = "HR_INVALID";
      } else if (!result.validSpO2) {
        validationReason = "SPO2_INVALID";
      }

      if (validReading && baselineValid) {
        float ratio = (float)result.heartRate / emaHeartRate;
        likelyHalfOrDoubleRate =
            (ratio > 0.40f && ratio < 0.60f) ||
            (ratio > 1.8f && ratio < 2.2f);
        if (likelyHalfOrDoubleRate) {
          validReading = false;
          validationReason = "HALF_DOUBLE";
        }
      }

      if (validReading) {
        if (!baselineValid) {
          emaHeartRate = result.heartRate;
          emaSpO2 = result.spo2;
          emaInitialized = true;
          stableReading = true;
          validationReason = "NEW_BASELINE";
        } else {
          hrDelta =
              abs(result.heartRate - (int32_t)lroundf(emaHeartRate));
          spo2Delta =
              abs(result.spo2 - (int32_t)lroundf(emaSpO2));
          stableReading = hrDelta <= MAX30102_MAX_HR_DELTA_BPM &&
                          spo2Delta <= MAX30102_MAX_SPO2_DELTA_PERCENT;
          if (!stableReading) {
            outlier = true;
            if (hrDelta > MAX30102_MAX_HR_DELTA_BPM &&
                spo2Delta > MAX30102_MAX_SPO2_DELTA_PERCENT) {
              validationReason = "HR_SPO2_JUMP";
            } else if (hrDelta > MAX30102_MAX_HR_DELTA_BPM) {
              validationReason = "HR_JUMP";
            } else {
              validationReason = "SPO2_JUMP";
            }
          }
        }

        if (stableReading) {
          emaHeartRate += MAX30102_EMA_ALPHA *
                          (result.heartRate - emaHeartRate);
          emaSpO2 += MAX30102_EMA_ALPHA *
                     (result.spo2 - emaSpO2);

          if (consecutiveValidCount <
              MAX30102_STABLE_READINGS_REQUIRED) {
            consecutiveValidCount++;
          }
        }
      }

      if ((!validReading || !stableReading) && consecutiveValidCount > 0) {
        consecutiveValidCount--;
      }

#if SENSOR_TIMING_DEBUG
      int64_t maxLogicUs = esp_timer_get_time() - maxLogicStartUs;
      int64_t maxDebugSerialUs = 0;
#endif

#if DEBUG_MAX30102
#if SENSOR_TIMING_DEBUG
      int64_t maxDebugSerialStartUs = esp_timer_get_time();
#endif
      Serial.printf(
          "[MAX-V] hr=%ld spo2=%ld finger=%u hrValid=%u spo2Valid=%u "
          "halfDouble=%u outlier=%u baselineValid=%u stable=%u "
          "hrDelta=%ld spo2Delta=%ld decision=%s reason=%s "
          "count_before=%u count_after=%u emaHR=%.1f->%.1f "
          "emaSpO2=%.1f->%.1f\n",
          (long)result.heartRate,
          (long)result.spo2,
          (unsigned)fingerDetected,
          (unsigned)result.validHeartRate,
          (unsigned)result.validSpO2,
          (unsigned)likelyHalfOrDoubleRate,
          (unsigned)outlier,
          (unsigned)baselineValid,
          (unsigned)stableReading,
          (long)hrDelta,
          (long)spo2Delta,
          validReading && stableReading ? "ACCEPT" : "REJECT",
          validationReason,
          (unsigned)countBefore,
          (unsigned)consecutiveValidCount,
          emaHeartRateBefore,
          emaHeartRate,
          emaSpO2Before,
          emaSpO2
      );
#if SENSOR_TIMING_DEBUG
      maxDebugSerialUs = esp_timer_get_time() - maxDebugSerialStartUs;
#endif
#endif

      if (consecutiveValidCount < MAX30102_STABLE_READINGS_REQUIRED) {
        result.state = MAX30102_State::STABILIZING;
        result.validHeartRate = 0;
        result.validSpO2 = 0;
      }

      PublishMAX30102Result(result);
#if SENSOR_TIMING_DEBUG
      int64_t maxTaskEndUs = esp_timer_get_time();
      Serial.printf(
          "[MAX-T] t=%lld sample=%lld mutex=%lld fifo=%lld filter=%lld "
          "bpm=%lld spo2=%lld logic=%lld debug=%lld get=%lld "
          "overflow=%lld total=%lldus\n",
          (long long)maxTaskStartUs,
          (long long)maxTiming.sampleUs,
          (long long)maxTiming.mutexWaitUs,
          (long long)maxTiming.fifoUs,
          (long long)maxTiming.filterUs,
          (long long)maxTiming.bpmUs,
          (long long)maxTiming.spo2Us,
          (long long)maxLogicUs,
          (long long)maxDebugSerialUs,
          (long long)(maxGetEndUs - maxTaskStartUs),
          (long long)maxOverflowUs,
          (long long)(maxTaskEndUs - maxTaskStartUs)
      );
#endif
      continue;
    }

#if DEBUG_MAX30102
    uint8_t countBeforeReset = consecutiveValidCount;
#endif
    consecutiveValidCount = 0;
#if DEBUG_MAX30102
    Serial.printf(
        "[MAX-V] hr=%ld spo2=%ld finger=%u hrValid=%u spo2Valid=%u "
        "decision=RESET reason=READ_FAILED count_before=%u count_after=0\n",
        (long)result.heartRate,
        (long)result.spo2,
        (unsigned)fingerDetected,
        (unsigned)result.validHeartRate,
        (unsigned)result.validSpO2,
        (unsigned)countBeforeReset
    );
#endif
    ready = false;
    if (interruptAttached) {
      detachInterrupt(digitalPinToInterrupt(INT_PIN));
      interruptAttached = false;
    }

    PublishMAX30102Result({MAX30102_State::TIMEOUT, 0, 0, 0, 0});
#if SENSOR_TIMING_DEBUG
    int64_t maxTaskEndUs = esp_timer_get_time();
    Serial.printf(
        "[MAX-T] t=%lld result=TIMEOUT get=%lld overflow=%lld total=%lldus\n",
        (long long)maxTaskStartUs,
        (long long)(maxGetEndUs - maxTaskStartUs),
        (long long)maxOverflowUs,
        (long long)(maxTaskEndUs - maxTaskStartUs)
    );
#endif
    nextRetry = xTaskGetTickCount() + SENSOR_RETRY_DELAY;
  }
}

static void SimTask(void *parameter) {
  (void)parameter;

  bool ready = false;
  TickType_t nextRetry = xTaskGetTickCount();

  while (true) {
    if (!ready) {
      TickType_t now = xTaskGetTickCount();
      if (!TickReached(now, nextRetry)) {
        vTaskDelay(pdMS_TO_TICKS(100));
        continue;
      }

      if (!LockSIM()) {
        vTaskDelay(pdMS_TO_TICKS(100));
        continue;
      }

      ready = A7680C_InitAndDiagnose(Serial2,
                                     SIM_RX_PIN,
                                     SIM_TX_PIN,
                                     115200);
      UnlockSIM();

      if (!ready) {
        Serial.println("SIM: LỖI KHỞI TẠO, THỬ LẠI SAU 5 GIÂY");
        nextRetry = xTaskGetTickCount() + SIM_RETRY_DELAY;
        continue;
      }

      Serial.println("SIM: SẴN SÀNG");
    }

    SimRequest request = {};
    if (xQueueReceive(simRequestQueue,
                      &request,
                      portMAX_DELAY) != pdTRUE) {
      continue;
    }

    if (request.type == SimAlertType::NONE) {
      continue;
    }

    if (!LockSIM()) {
      Serial.println("SIM: KHÔNG THỂ KHÓA UART");
      continue;
    }

    // A7680C hiện tại không hỗ trợ thoại; cả hai mức đều dùng chung nội dung SMS.
    bool smsSent = A7680C_SendSMS(request.phoneNumber,
                                  A7680C_ALERT_MESSAGE);

    UnlockSIM();

    if (request.type == SimAlertType::NORMAL) {
      Serial.printf("SIM: SMS %s\n", smsSent ? "THÀNH CÔNG" : "THẤT BẠI");
    } else if (request.type == SimAlertType::DANGEROUS) {
      Serial.printf("SIM: SMS KHẨN CẤP %s\n",
                    smsSent ? "THÀNH CÔNG" : "THẤT BẠI");
    }
  }
}

static void EnvironmentTask(void *parameter) {
  (void)parameter;

  DHT22_Init();

  bool bmpReady = false;
  bool sgpReady = false;
  bool oledReady = false;
  uint8_t bmpFailures = 0;
  uint8_t sgpFailures = 0;
  uint8_t dhtFailures = 0;
  uint8_t oledFailures = 0;
  TickType_t nextBmpRetry = xTaskGetTickCount();
  TickType_t nextSgpRetry = nextBmpRetry;
  TickType_t nextOledRetry = nextBmpRetry;
  TickType_t lastWake = nextBmpRetry;
  uint32_t scheduleTick = 0;
#if SENSOR_TIMING_DEBUG
  int64_t scheduledWakeUs = esp_timer_get_time();
  int64_t lastDhtStartUs = 0;
#endif

  SGP30_Data_t sgp = {};
  bool sgpReadOk = false;

  while (true) {
    bool sendTestSms = false;
    while (Serial.available() > 0) {
      if (Serial.read() == '!') {
        sendTestSms = true;
      }
    }

    if (sendTestSms) {
      bool queued = simTaskCreated &&
          QueueSimAlert(
              SimAlertType::NORMAL,
              "0394168463");
      Serial.println(queued
                         ? "SIM: DA XEP HANG SMS TEST"
                         : "SIM: KHONG THE XEP HANG SMS TEST");
    }

#if SENSOR_TIMING_DEBUG
    int64_t actualWakeUs = esp_timer_get_time();
    int64_t wakeLatencyUs = actualWakeUs - scheduledWakeUs;
#endif
    TickType_t now = xTaskGetTickCount();

    if (!bmpReady && TickReached(now, nextBmpRetry)) {
      bmpReady = InitBMP280();
      bmpFailures = 0;
      if (!bmpReady) {
        nextBmpRetry = now + SENSOR_RETRY_DELAY;
        LogSensorRetry("BMP280", now, nextBmpRetry);
      }
    }

    if (!sgpReady && TickReached(now, nextSgpRetry)) {
      sgpReady = InitSGP30();
      sgpFailures = 0;
      if (!sgpReady) {
        nextSgpRetry = now + SENSOR_RETRY_DELAY;
        LogSensorRetry("SGP30", now, nextSgpRetry);
      }
    }

    if (!oledReady && TickReached(now, nextOledRetry)) {
      oledReady = InitOLED();
      oledFailures = 0;
      if (!oledReady) {
        nextOledRetry = now + SENSOR_RETRY_DELAY;
      }
    }

    sgpReadOk = false;
    if (sgpReady) {
      sgpReadOk = ReadSGP30(&sgp);
      if (sgpReadOk) {
        sgpFailures = 0;
      } else if (++sgpFailures >= SENSOR_FAILURE_LIMIT) {
        sgpReady = false;
        nextSgpRetry = now + SENSOR_RETRY_DELAY;
        LogSensorRetry("SGP30", now, nextSgpRetry);
      }
    }

    scheduleTick++;
    if ((scheduleTick % 2) == 0) {
      measurementIndex++;
#if SENSOR_TIMING_DEBUG
      int64_t preDhtSerialStartUs = esp_timer_get_time();
#endif
      Serial.printf("LẦN ĐO #%lu\n", (unsigned long)measurementIndex);
#if SENSOR_TIMING_DEBUG
      int64_t preDhtSerialUs =
          esp_timer_get_time() - preDhtSerialStartUs;
#endif

      float dhtTemp = 0.0f;
      float dhtHum = 0.0f;
#if SENSOR_TIMING_DEBUG
      int64_t dhtStartUs = esp_timer_get_time();
      int64_t sincePreviousDhtUs =
          lastDhtStartUs == 0 ? 0 : dhtStartUs - lastDhtStartUs;
      TickType_t maxActiveBeforeTick = maxTaskLastActiveTick;
      TickType_t maxGetStartBeforeTick = maxGetStartTick;
      bool maxGetInProgressBefore = maxGetInProgress;
#endif
      uint8_t dhtErr = DHT22_ReadData(&dhtTemp, &dhtHum);
#if SENSOR_TIMING_DEBUG
      int64_t dhtEndUs = esp_timer_get_time();
      TickType_t maxActiveAfterTick = maxTaskLastActiveTick;
      TickType_t maxGetEndAfterTick = maxGetEndTick;
      bool maxGetInProgressAfter = maxGetInProgress;
      DHT22_TimingProfile dhtTiming = {};
      DHT22_GetTimingProfile(&dhtTiming);
      int64_t criticalUs =
          dhtTiming.criticalExitUs >= dhtTiming.criticalEnterUs &&
          dhtTiming.criticalEnterUs != 0
              ? dhtTiming.criticalExitUs - dhtTiming.criticalEnterUs
              : 0;
      int64_t callToCriticalUs =
          dhtTiming.criticalEnterUs >= dhtStartUs
              ? dhtTiming.criticalEnterUs - dhtStartUs
              : 0;
      int64_t startLowToCriticalUs =
          dhtTiming.criticalEnterUs >= dhtTiming.startLowUs &&
          dhtTiming.startLowUs != 0
              ? dhtTiming.criticalEnterUs - dhtTiming.startLowUs
              : 0;
      const char *dhtResult =
          dhtErr == 0 ? "OK" : (dhtErr == 1 ? "TIMEOUT" : "CHECKSUM");

      Serial.printf(
          "[DHT-T] sched=%lld wake=%lld latency=%lldus start=%lld "
          "end=%lld duration=%lldus since_prev=%lldus result=%s\n",
          (long long)scheduledWakeUs,
          (long long)actualWakeUs,
          (long long)wakeLatencyUs,
          (long long)dhtStartUs,
          (long long)dhtEndUs,
          (long long)(dhtEndUs - dhtStartUs),
          (long long)sincePreviousDhtUs,
          dhtResult
      );
      Serial.printf(
          "[DHT-T] pre_serial=%lldus mutex=none wait=0us "
          "resp_low=%lldus resp_high=%lldus critical_enter=%lld "
          "critical_exit=%lld critical=%lldus stage=%s bit=%d\n",
          (long long)preDhtSerialUs,
          (long long)dhtTiming.responseLowUs,
          (long long)dhtTiming.responseHighUs,
          (long long)dhtTiming.criticalEnterUs,
          (long long)dhtTiming.criticalExitUs,
          (long long)criticalUs,
          dhtTiming.timeoutStage == nullptr
              ? "unknown"
              : dhtTiming.timeoutStage,
          (int)dhtTiming.timeoutBit
      );
      Serial.printf(
          "[DHT-X] call_to_critical=%lldus start_low_to_critical=%lldus "
          "max_active_before=%lu max_active_after=%lu max_ran_during=%u "
          "max_get_start=%lu max_get_end=%lu max_get_before=%u "
          "max_get_after=%u\n",
          (long long)callToCriticalUs,
          (long long)startLowToCriticalUs,
          (unsigned long)maxActiveBeforeTick,
          (unsigned long)maxActiveAfterTick,
          (unsigned)(maxActiveAfterTick != maxActiveBeforeTick),
          (unsigned long)maxGetStartBeforeTick,
          (unsigned long)maxGetEndAfterTick,
          (unsigned)maxGetInProgressBefore,
          (unsigned)maxGetInProgressAfter
      );
      lastDhtStartUs = dhtStartUs;
#endif
      if (dhtErr == 0) {
        dhtFailures = 0;
        Serial.printf("DHT: Nhiệt độ=%.1f C | Độ ẩm=%.1f %%\n", dhtTemp, dhtHum);
      } else {
        if (++dhtFailures >= SENSOR_FAILURE_LIMIT) {
          LogSensorRetry("DHT22", now, now);
          DHT22_Init();
          dhtFailures = 0;
        }

        if (dhtErr == 1) {
          Serial.println("DHT: LỖI (quá thời gian)");
        } else {
          Serial.println("DHT: LỖI (sai mã kiểm tra)");
        }
      }

      float bmpTemp = 0.0f;
      float bmpPress = 0.0f;
      bool bmpReadOk = false;
      if (bmpReady) {
        bmpReadOk = ReadBMP280(&bmpTemp, &bmpPress);
        if (bmpReadOk) {
          bmpFailures = 0;
        } else if (++bmpFailures >= SENSOR_FAILURE_LIMIT) {
          bmpReady = false;
          nextBmpRetry = now + SENSOR_RETRY_DELAY;
          LogSensorRetry("BMP280", now, nextBmpRetry);
        }
      }

      if (bmpReadOk) {
        float altitude = BMP280_CalculateAltitude(bmpPress, 1013.25f);
        Serial.printf("BMP: Nhiệt độ=%.2f C | Áp suất=%.2f hPa | Độ cao=%.2f m\n",
                      bmpTemp, bmpPress, altitude);
      } else if (bmpReady) {
        Serial.println("BMP: LỖI (đọc thất bại)");
      } else {
        Serial.println("BMP: LỖI (chưa sẵn sàng)");
      }

      if (sgpReadOk) {
        Serial.printf("SGP: Tổng hợp chất hữu cơ dễ bay hơi=%u ppb | CO2 tương đương=%u ppm\n",
                      sgp.TVOC, sgp.CO2_eq);
      } else if (sgpReady) {
        Serial.println("SGP: LỖI (đọc thất bại)");
      } else {
        Serial.println("SGP: LỖI (chưa sẵn sàng)");
      }

      MAX30102_Result maxResult = {MAX30102_State::NOT_READY, 0, 0, 0, 0};
      xQueuePeek(maxResultQueue, &maxResult, 0);

      if (maxResult.state == MAX30102_State::READY) {
        Serial.print("MAX30102: Nhịp tim=");
        if (maxResult.validHeartRate) {
          Serial.printf("%ld BPM", (long)maxResult.heartRate);
        } else {
          Serial.print("Không hợp lệ");
        }

        Serial.print(" | SpO2=");
        if (maxResult.validSpO2) {
          Serial.printf("%ld %%\n", (long)maxResult.spo2);
        } else {
          Serial.println("Không hợp lệ");
        }
      } else if (maxResult.state == MAX30102_State::MEASURING) {
        Serial.println("MAX30102: Đang thu mẫu");
      } else if (maxResult.state == MAX30102_State::NO_FINGER) {
        Serial.println("MAX30102: Không phát hiện ngón tay");
      } else if (maxResult.state == MAX30102_State::STABILIZING) {
        Serial.println("MAX30102: Đang ổn định tín hiệu");
      } else if (maxResult.state == MAX30102_State::TIMEOUT) {
        Serial.println("MAX30102: LỖI (quá thời gian đọc)");
      } else {
        Serial.println("MAX30102: LỖI (chưa sẵn sàng)");
      }

      if (oledReady) {
        OLED_Clear_Display();

        OLED_GotoXY(0, 0);
        if (dhtErr == 0) {
          OLED_Printf("DHT %.1fC %.1f%%", dhtTemp, dhtHum);
        } else {
          OLED_Println("DHT --");
        }

        OLED_GotoXY(0, 16);
        if (bmpReadOk) {
          OLED_Printf("BMP %.1fC %.0fhPa", bmpTemp, bmpPress);
        } else {
          OLED_Println("BMP --");
        }

        OLED_GotoXY(0, 32);
        if (sgpReadOk) {
          OLED_Printf(
              "SGP %uppm %uppb",
              (unsigned)sgp.CO2_eq,
              (unsigned)sgp.TVOC
          );
        } else {
          OLED_Println("SGP --");
        }

        OLED_GotoXY(0, 48);
        if (maxResult.state == MAX30102_State::READY &&
            maxResult.validHeartRate &&
            maxResult.validSpO2) {
          OLED_Printf(
              "HR %ld SpO2 %ld%%",
              (long)maxResult.heartRate,
              (long)maxResult.spo2
          );
        } else {
          OLED_Println("HR -- SpO2 --");
        }

        if (FlushOLED()) {
          oledFailures = 0;
        } else if (++oledFailures >= SENSOR_FAILURE_LIMIT) {
          oledReady = false;
          nextOledRetry = now + SENSOR_RETRY_DELAY;
        }
      }

      Serial.println();
    }

    vTaskDelayUntil(&lastWake, ENVIRONMENT_PERIOD);
#if SENSOR_TIMING_DEBUG
    scheduledWakeUs +=
        (int64_t)ENVIRONMENT_PERIOD * portTICK_PERIOD_MS * 1000;
#endif
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);

  Wire.begin(21, 22);  // SDA=21, SCL=22
  delay(200);

  i2cMutex = xSemaphoreCreateMutex();
  maxResultQueue = xQueueCreate(1, sizeof(MAX30102_Result));
  simMutex = xSemaphoreCreateMutex();
  simRequestQueue = xQueueCreate(SIM_QUEUE_LENGTH,
                                 sizeof(SimRequest));
  if (i2cMutex == nullptr || maxResultQueue == nullptr) {
    Serial.println("HỆ THỐNG: LỖI KHỞI TẠO TÀI NGUYÊN FREERTOS");
    return;
  }
  if (simMutex == nullptr || simRequestQueue == nullptr) {
    Serial.println("HỆ THỐNG: SIMTASK BỊ VÔ HIỆU HÓA");
  }

  MAX30102_SetI2CMutex(i2cMutex);
  PublishMAX30102Result({MAX30102_State::NOT_READY, 0, 0, 0, 0});

  environmentTaskCreated = xTaskCreatePinnedToCore(
                               EnvironmentTask,
                               "EnvironmentTask",
                               8192,
                               nullptr,
                               1,
                               nullptr,
                               1) == pdPASS;
  if (!environmentTaskCreated) {
    Serial.println("HỆ THỐNG: ENVIRONMENTTASK CHẠY Ở LOOP DỰ PHÒNG");
  }

  maxTaskCreated = xTaskCreatePinnedToCore(
                       MAX30102Task,
                       "MAX30102Task",
                       8192,
                       nullptr,
                       2,
                       nullptr,
                       1) == pdPASS;
  if (!maxTaskCreated) {
    Serial.println("HỆ THỐNG: MAX30102TASK CHẠY Ở LOOP DỰ PHÒNG");
  }

  if (simMutex != nullptr && simRequestQueue != nullptr) {
    simTaskCreated = xTaskCreatePinnedToCore(
                         SimTask,
                         "SimTask",
                         SIM_TASK_STACK_SIZE,
                         nullptr,
                         SIM_TASK_PRIORITY,
                         nullptr,
                         SIM_TASK_CORE) == pdPASS;
    if (!simTaskCreated) {
      Serial.println("HỆ THỐNG: KHÔNG THỂ TẠO SIMTASK");
    }
  }
}

void loop() {
  if (environmentTaskCreated && maxTaskCreated) {
    vTaskDelete(nullptr);
  }

  if (!environmentTaskCreated &&
      i2cMutex != nullptr &&
      maxResultQueue != nullptr) {
    EnvironmentTask(nullptr);
  }

  if (!maxTaskCreated &&
      i2cMutex != nullptr &&
      maxResultQueue != nullptr) {
    MAX30102Task(nullptr);
  }

  vTaskDelay(portMAX_DELAY);
}
