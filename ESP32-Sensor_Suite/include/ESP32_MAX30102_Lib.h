#ifndef ESP32_MAX30102_LIB_H
#define ESP32_MAX30102_LIB_H

#include <Arduino.h>
#include <Wire.h>

/* Địa chỉ */
#define MAX30102_ADDR_REG 0x57

/* Sơ đồ PINOUT */
#define INT_PIN 12 
#define SCL_PIN 23
#define SDA_PIN 33

/* Define thanh ghi */

#define REG_INTER_STTUS 0x00
#define REG_INTER_ENABL 0x02
#define REG_WR_PTR_CONF 0x04
#define REG_OVF_COUNTER 0x05
#define REG_RD_PTR_CONF 0x06
#define REG_FIFO_CONFIG 0x08
#define REG_MODE_CONFIG 0x09
#define REG_SP02_CONFIG 0x0A
#define REG_PULSE_AMP_1 0x0C
#define REG_PULSE_AMP_2 0x0D

/* Giá trị cấu hình thanh ghi */

// REG_INTER_ENABL: Cho phép ngắt khi đầy dữ liệu
#define A_FULL_EN 0x80 // Kích hoạt khi FIFO sắp đầy
#define PPG_RDY_EN 0x40 // Kích hoạt khi có 1 mẫu dữ liệu sẵn sàng

// REG_WR_PTR v REG_RD_PTR
#define ERASER_POINTER 0x00

// REG_FIFO_CONFIG
#define FIFO_SMP_AVE_4 (0b010 << 5) // Lấy trung bình 4 mẫu
#define FIFO_ROLLOVER_ENABLE (1 << 4) // Cho phép ghi đè khi full
#define FIFO_A_FULL_15 0x0F // Ngắt khi còn 15 mẫu trống

// REG_MODE_CONFIG
#define MODE_RESET 0x40 // Reset module (1 << 6)
#define MODE_SP02 0x03 // Chế độ Sp02: RED + IR
#define MODE_HR 0x02 // Chế độ Heart Rate: Chỉ đo nhịp tim (RED)

// REG_SP02_CONFIG
#define SP02_ADC_RGE_4096 (0b01 << 5) // Dải đo của ADC (Độ nhạy: full)
#define SP02_SR_100 (0b001 << 2) // Tốc độ lấy mẫu = 100 mẫu/s
#define SP02_LED_PW_411 0x03 // Độ rộng xung 411 us

// REG_PULSE_AMP1 v 2
#define LED_CURRENT 0x24 // Độ sáng trung bình ~ 7mA

/* Thanh ghi doc du lieu */
#define REG_FIFO_DATA 0x07

/* Kiểm tra thanh ghi */
#define REG_PART_ID 0xFF
#define VALUE_PART_ID 0x15

/* ==== NGUYÊN MẪU HÀM ==== */
bool MAX30102_Init(void);
void MAX30102_ClearInterrupt();
bool MAX30102_HasInterrupt();
bool MAX30102_ReadFIFO(uint32_t* redLED, uint32_t* irLED);

// ==== TEST MAIN ====

// Hàm này phục vụ ngắt, éo lưu vào RAM thay vì FLASH
// => Giúp thực thi nhanh
void IRAM_ATTR MAX30102_ISR(void);
void MAX30102_TestSetup(void);
void MAX30102_TestLoop(void);

#endif