#ifndef ESP32_MAX30102_LIB_H
#define ESP32_MAX30102_LIB_H

#include <Arduino.h>
#include <Wire.h>
#include <freertos/semphr.h>

/* =========================================================
 * I2C ADDRESS
 * ========================================================= */
#define MAX30102_ADDR_REG 0x57


/* =========================================================
 * PINOUT - ESP32 DEVKIT
 * ========================================================= */
#define SDA_PIN 21
#define SCL_PIN 22
#define INT_PIN 27


/* =========================================================
 * REGISTER MAP
 * ========================================================= */

/* Interrupt Status */
#define REG_INTER_STATUS_1     0x00
#define REG_INTER_STATUS_2     0x01

/* Interrupt Enable */
#define REG_INTER_ENABLE_1     0x02
#define REG_INTER_ENABLE_2     0x03

/* FIFO */
#define REG_WR_PTR_CONF        0x04
#define REG_OVF_COUNTER        0x05
#define REG_RD_PTR_CONF        0x06
#define REG_FIFO_DATA          0x07
#define REG_FIFO_CONFIG        0x08

/* Configuration */
#define REG_MODE_CONFIG        0x09
#define REG_SP02_CONFIG        0x0A

/* LED */
#define REG_PULSE_AMP_1        0x0C
#define REG_PULSE_AMP_2        0x0D

/* Device ID */
#define REG_PART_ID            0xFF


/* =========================================================
 * INTERRUPT ENABLE
 * ========================================================= */

#define A_FULL_EN              0x80
#define PPG_RDY_EN             0x40


/* =========================================================
 * INTERRUPT STATUS
 * ========================================================= */

#define A_FULL_STATUS          0x80
#define PPG_RDY_STATUS         0x40


/* =========================================================
 * FIFO POINTER
 * ========================================================= */

#define ERASER_POINTER         0x00


/* =========================================================
 * FIFO CONFIG
 * ========================================================= */

/* Không average */
#define FIFO_SMP_AVE_1         (0b000 << 5)

/* Average 4 mẫu */
#define FIFO_SMP_AVE_4         (0b010 << 5)

/* Cho phép FIFO rollover */
#define FIFO_ROLLOVER_ENABLE   (1 << 4)

/* Almost Full threshold */
#define FIFO_A_FULL_15         0x0F


/* =========================================================
 * MODE CONFIG
 * ========================================================= */

#define MODE_RESET             0x40

/* Heart Rate: RED */
#define MODE_HR                0x02

/* SpO2: RED + IR */
#define MODE_SP02              0x03


/* =========================================================
 * SPO2 CONFIG
 * ========================================================= */

/* ADC range = 4096 nA */
#define SP02_ADC_RGE_4096      (0b01 << 5)

/* Sample rate = 100 SPS */
#define SP02_SR_100            (0b001 << 2)

/* Pulse width = 411 us, ADC 18-bit */
#define SP02_LED_PW_411        0x03


/* =========================================================
 * LED CURRENT
 * ========================================================= */

#define LED_CURRENT            0x24
#define MAX30102_IR_FINGER_THRESHOLD 50000UL
#define MAX30102_HR_MIN_BPM    40
#define MAX30102_HR_MAX_BPM    180
#define MAX30102_SPO2_MIN_PCT  70
#define MAX30102_SPO2_MAX_PCT  100


/* =========================================================
 * PART ID
 * ========================================================= */

#define VALUE_PART_ID          0x15
#define MAX30102_BUFFER_SIZE 100
#define MAX30102_NEW_SAMPLES 25

#if SENSOR_TIMING_DEBUG
struct MAX30102_TimingProfile {
    int64_t sampleUs;
    int64_t mutexWaitUs;
    int64_t fifoUs;
    int64_t filterUs;
    int64_t bpmUs;
    int64_t spo2Us;
};
#endif


/* =========================================================
 * FUNCTION PROTOTYPES
 * ========================================================= */

bool MAX30102_Init(void);

void MAX30102_SetI2CMutex(SemaphoreHandle_t mutex);

#if SENSOR_TIMING_DEBUG
void MAX30102_GetTimingProfile(MAX30102_TimingProfile *profile);
#endif

bool MAX30102_ClearInterrupt(void);

bool MAX30102_HasInterrupt(void);

bool MAX30102_ReadFIFO(
    uint32_t *redLED,
    uint32_t *irLED
);

uint8_t MAX30102_GetOverflowCounter(void);


/* =========================================================
 * INTERRUPT / TEST
 *
 * Giữ nguyên kiến trúc:
 * ISR vẫn nằm trong LIB.
 * ========================================================= */

void IRAM_ATTR MAX30102_ISR(void);

void MAX30102_TestSetup(void);

void MAX30102_TestLoop(void);
bool MAX30102_GetHeartRateSpO2(
    int32_t *heartRate,
    int8_t *validHeartRate,
    int32_t *spo2,
    int8_t *validSpO2,
    bool *fingerDetected
);

#endif
