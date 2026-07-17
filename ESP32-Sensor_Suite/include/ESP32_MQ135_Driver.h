#ifndef ESP32_MQ135_DRIVER_H
#define ESP32_MQ135_DRIVER_H

#include <Arduino.h>
#include <math.h>

// Yêu cầu: MQ135 Cần 
// + VH: Nhiệt độ nung nấu Sn02
// + VC: Cấp nguồn

// Lưu ý: Mạch bắt buộc sử dụng nguồn 5V, nhưng nếu cấp 5V thì A0 sẽ
// xuất ra tín hiệu từ 0-5V > 3.3V của GPIO ESP32
// => Cháy GPIO
// => Cần cầu phân áp (2 Điện trở) để hạ áp từ chân A0 xuống

/* Cầu phân áp: Cần 2R1 = R2 = 20kOhm
- A0 nối vào R1
- R1 nối vào R2
- R2 nối xuống GND
- ADC nối 2 cái R1 và R2
A0 - R1 - ADC - R2 - GND

ĐL nối tiếp điện trở
+ Cường độ dòng điện chạy qua 2 R là: V_A0 / (R1+R2)
+ ADC sẽ đo mức điện áp đc nối vs GND: V_esp = I . R2
=> V_A0 = V_esp . 1,5
*/

/*
// Fig 3 theo datasheet
Trục Y: Tỉ lệ Rs/R0 vs đơn vị là thang đo loga (Y = Rs/R0)
Trục X: Nồng đồ khí đo bằng đvi ppm (Cũng là thang đo loga) (X = ppm)

- Và đây là pt điểm trên 1 đồ thị 2 trục loga, phương trình 1 điểm
    log(Y) = m.log(X) + log(a)
+ log(a): Điểm cắt trục tung
+ m: Độ dốc
Loga 2 vế đưa về đc dạng
    Rs/R0 = a.(ppm)^m và 
    + Với (1/a)^(1/m) = A
    + Với 1/m = B
    => ppm = A . (Rs/R0)^B

- Xét NH3 có 
+ Độ dốc m
x1 = 10 -> y1 ~ 0.8
x2 = 100 -> y2 ~ 0.3
=> Độ dốc m = [log(y2) - log(y1)] / [log(x2) - log(x1)] = -0.426

+ Điểm cắt
Có x1, y1, m
=> a ~ 2.138

Tips: Có nhiều loại khí nên a, m sẽ thay đổi
*/

#define MQ135_PIN 34

// Điện trở tải RL trên module
#define MQ135_RL_kOhm 4.7f

// Điện áp cấp mạch là 5V
#define MQ135_VC_Volts 5.0f

// ADC độ phân giải 12-bit
#define ESP32_ADC_MAX 4095.0f
#define ESP32_ADC_REF_VOLTS 3.3f

// Hệ số phân cầu áp
#define VOLTAGE_DIVIDER_RATIO 1.5f

typedef enum {
MQ135_GAS_CO2 = 0,
    MQ135_GAS_CO,
    MQ135_GAS_ALCOHOL,
    MQ135_GAS_NH3,
    MQ135_GAS_TOLUENE,
    MQ135_GAS_ACETONE
} MQ135_GasType_t;

/* ==== NGUYÊN MẪU HÀM ==== */
void MQ135_Init(uint8_t pin);
float MQ135_ReadRs();
float MQ135_CalibrateR0();

float MQ135_GetPPM(float r0, MQ135_GasType_t gasType);

// ==== TEST MAIN ====
void MQ135_TestSetup(void);
void MQ135_TestLoop(void);

#endif

/*
- SGP30 đóng vai trò "Bác sĩ" (Đo đạc chi tiết):
+ Dùng để cập nhật UI/Dashboard liên tục về chất lượng không khí trong phòng 
+ (Ví dụ: "eCO2 đang là 800ppm, TVOC là 120ppb, không khí bình thường").
+ Thông số này mang tính chất theo dõi sức khỏe dài hạn.

- MQ135 đóng vai trò "Lính gác" (Trigger Cảnh báo nguy hiểm):
+ Vì MQ135 nhạy với bất kỳ khí lạ nào (đặc biệt là Khói cháy, Rò rỉ Gas, Amoniac nồng độ cao), 
+ ta sẽ không bắt nó đo CO2 nữa (vì đã có SGP30 làm quá tốt rồi).
+ Hãy thiết lập MQ135 làm Máy phát hiện Hỏa hoạn hoặc Khí độc rò rỉ.
+ Cách lập trình: Không cần đo chính xác số ppm của nó nữa. Chỉ cần theo dõi sự sụt giảm điện trở R_s. 
+ Nếu R_s đột ngột rớt thê thảm (điện áp ADC vọt lên cao ngưỡng quá mức bình thường), lập tức kích hoạt luồng cảnh báo:
*/