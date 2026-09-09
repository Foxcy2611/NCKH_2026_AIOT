#include "Vitals_UI/PPG_Sensor.h"
#include <Wire.h>
#include <math.h>

/* =========================================================
 * MAX30102 INTERNAL CONFIGURATION
 * ========================================================= */
#define MAX30102_ADDR_REG              0x57

#define REG_INTER_STATUS_1             0x00
#define REG_INTER_STATUS_2             0x01
#define REG_INTER_ENABLE_1             0x02
#define REG_INTER_ENABLE_2             0x03
#define REG_WR_PTR_CONF                0x04
#define REG_OVF_COUNTER                0x05
#define REG_RD_PTR_CONF                0x06
#define REG_FIFO_DATA                  0x07
#define REG_FIFO_CONFIG                0x08
#define REG_MODE_CONFIG                0x09
#define REG_SP02_CONFIG                0x0A
#define REG_PULSE_AMP_1                0x0C
#define REG_PULSE_AMP_2                0x0D
#define REG_PART_ID                    0xFF

#define A_FULL_EN                      0x80
#define PPG_RDY_EN                     0x40
#define ERASER_POINTER                 0x00

#define FIFO_SMP_AVE_4                 (0b010 << 5)
#define FIFO_ROLLOVER_ENABLE           (1 << 4)
#define FIFO_A_FULL_15                 0x0F

#define MODE_RESET                     0x40
#define MODE_SP02                      0x03

#define SP02_ADC_RGE_4096              (0b01 << 5)
#define SP02_SR_100                    (0b001 << 2)
#define SP02_LED_PW_411                0x03

#define LED_CURRENT                    0x24
#define VALUE_PART_ID                  0x15

#define MAX30102_IR_FINGER_THRESHOLD   50000UL
#define MAX30102_HR_MIN_BPM            40
#define MAX30102_HR_MAX_BPM            180
#define MAX30102_SPO2_MIN_PCT          70
#define MAX30102_SPO2_MAX_PCT          100

#define MAX30102_BUFFER_SIZE           100
#define MAX30102_NEW_SAMPLES           25
#define MAX30102_ENABLE_BANDPASS_FILTER 1
#define MAX30102_FILTER_FS_HZ          25.0f

/*
 * Clone module tím: FIFO/ngắt thường không ổn định như bản chính hãng.
 * Timeout dùng để tự phục hồi nếu I2C/FIFO im lặng quá lâu, thay vì
 * treo mãi như bản blocking cũ.
 */
#define MAX30102_SAMPLE_TIMEOUT_MS     6000UL

namespace
{
static const int32_t FreqS = 25;
static const int32_t BUFFER_SIZE = FreqS * 4;
static const int32_t MA4_SIZE = 4;
static_assert(BUFFER_SIZE == MAX30102_BUFFER_SIZE, "MAX30102 algorithm requires 100 samples");

static const uint8_t uch_spo2_table[184] = {
    95, 95, 95, 96, 96, 96, 97, 97, 97, 97, 97, 98, 98, 98, 98, 98, 99, 99, 99, 99,
    99, 99, 99, 99, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100,
    100, 100, 100, 100, 99, 99, 99, 99, 99, 99, 99, 99, 98, 98, 98, 98, 98, 98, 97, 97,
    97, 97, 96, 96, 96, 96, 95, 95, 95, 94, 94, 94, 93, 93, 93, 92, 92, 92, 91, 91,
    90, 90, 89, 89, 89, 88, 88, 87, 87, 86, 86, 85, 85, 84, 84, 83, 82, 82, 81, 81,
    80, 80, 79, 78, 78, 77, 76, 76, 75, 74, 74, 73, 72, 72, 71, 70, 69, 69, 68, 67,
    66, 66, 65, 64, 63, 62, 62, 61, 60, 59, 58, 57, 56, 56, 55, 54, 53, 52, 51, 50,
    49, 48, 47, 46, 45, 44, 43, 42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 31, 30, 29,
    28, 27, 26, 25, 23, 22, 21, 20, 19, 17, 16, 15, 14, 12, 11, 10, 9, 7, 6, 5,
    3, 2, 1
};

static int32_t an_x[BUFFER_SIZE];
static int32_t an_y[BUFFER_SIZE];

/* =========================================================
 * BANDPASS 0.5 Hz - 4 Hz CHỈ DÙNG CHO PEAK DETECTION
 * (Không đổi so với bản gốc)
 * ========================================================= */

struct MAX30102_BiquadState
{
    float x1;
    float x2;
    float y1;
    float y2;
};

static float MAX30102_BiquadProcess(
    MAX30102_BiquadState *state,
    const float coeffs[5],
    float input
)
{
    float output =
        coeffs[0] * input +
        coeffs[1] * state->x1 +
        coeffs[2] * state->x2 -
        coeffs[3] * state->y1 -
        coeffs[4] * state->y2;

    state->x2 = state->x1;
    state->x1 = input;
    state->y2 = state->y1;
    state->y1 = output;

    return output;
}

static void MAX30102_BandpassFilter(int32_t *data, int32_t length)
{
    const float q = 0.707107f;
    const float pi = static_cast<float>(PI);

    float omega = 2.0f * pi * 0.5f / MAX30102_FILTER_FS_HZ;
    float alpha = sinf(omega) / (2.0f * q);
    float cosOmega = cosf(omega);
    float a0 = 1.0f + alpha;
    float highpassCoeffs[5] = {
        (1.0f + cosOmega) / 2.0f,
        -(1.0f + cosOmega),
        (1.0f + cosOmega) / 2.0f,
        -2.0f * cosOmega,
        1.0f - alpha
    };

    for (uint8_t i = 0; i < 5; i++)
    {
        highpassCoeffs[i] /= a0;
    }

    omega = 2.0f * pi * 4.0f / MAX30102_FILTER_FS_HZ;
    alpha = sinf(omega) / (2.0f * q);
    cosOmega = cosf(omega);
    a0 = 1.0f + alpha;
    float lowpassCoeffs[5] = {
        (1.0f - cosOmega) / 2.0f,
        1.0f - cosOmega,
        (1.0f - cosOmega) / 2.0f,
        -2.0f * cosOmega,
        1.0f - alpha
    };

    for (uint8_t i = 0; i < 5; i++)
    {
        lowpassCoeffs[i] /= a0;
    }

    /* Reset state cho từng buffer 100 mẫu. */
    MAX30102_BiquadState highpassState = {};
    MAX30102_BiquadState lowpassState = {};

    for (int32_t i = 0; i < length; i++)
    {
        float highpassOutput = MAX30102_BiquadProcess(
            &highpassState,
            highpassCoeffs,
            static_cast<float>(data[i])
        );
        float bandpassOutput = MAX30102_BiquadProcess(
            &lowpassState,
            lowpassCoeffs,
            highpassOutput
        );

        data[i] = static_cast<int32_t>(lroundf(bandpassOutput));
    }
}

static void maxim_find_peaks(
    int32_t *pn_locs,
    int32_t *n_npks,
    int32_t *pn_x,
    int32_t n_size,
    int32_t n_min_height,
    int32_t n_min_distance,
    int32_t n_max_num
);

static void maxim_peaks_above_min_height(
    int32_t *pn_locs,
    int32_t *n_npks,
    int32_t *pn_x,
    int32_t n_size,
    int32_t n_min_height
);

static void maxim_remove_close_peaks(
    int32_t *pn_locs,
    int32_t *pn_npks,
    int32_t *pn_x,
    int32_t n_min_distance
);

static void maxim_sort_ascend(int32_t *pn_x, int32_t n_size);

static void maxim_sort_indices_descend(
    int32_t *pn_x,
    int32_t *pn_indx,
    int32_t n_size
);

static void maxim_heart_rate_and_oxygen_saturation(
    uint32_t *pun_ir_buffer,
    int32_t n_ir_buffer_length,
    uint32_t *pun_red_buffer,
    int32_t *pn_spo2,
    int8_t *pch_spo2_valid,
    int32_t *pn_heart_rate,
    int8_t *pch_hr_valid
)
{
    uint32_t un_ir_mean;
    int32_t k;
    int32_t n_i_ratio_count;
    int32_t i;
    int32_t n_exact_ir_valley_locs_count;
    int32_t n_middle_idx;
    int32_t n_th1;
    int32_t n_npks;
    int32_t an_ir_valley_locs[15];
    int32_t n_peak_interval_sum;
    int32_t n_y_ac;
    int32_t n_x_ac;
    int32_t n_spo2_calc;
    int32_t n_y_dc_max;
    int32_t n_x_dc_max;
    int32_t n_y_dc_max_idx = 0;
    int32_t n_x_dc_max_idx = 0;
    int32_t an_ratio[5];
    int32_t n_ratio_average;
    int32_t n_nume;
    int32_t n_denom;
    float averagePeakInterval = 0.0f;

    un_ir_mean = 0;
    for (k = 0; k < n_ir_buffer_length; k++)
    {
        un_ir_mean += pun_ir_buffer[k];
    }
    un_ir_mean = un_ir_mean / n_ir_buffer_length;

    for (k = 0; k < n_ir_buffer_length; k++)
    {
        an_x[k] = -1 * (pun_ir_buffer[k] - un_ir_mean);
    }

    for (k = 0; k < BUFFER_SIZE - MA4_SIZE; k++)
    {
        an_x[k] = (an_x[k] + an_x[k + 1] + an_x[k + 2] + an_x[k + 3]) / 4;
    }

#if MAX30102_ENABLE_BANDPASS_FILTER
    /* Chỉ lọc bản sao an_x, không sửa dữ liệu IR/RED gốc. */
    MAX30102_BandpassFilter(an_x, n_ir_buffer_length);
#endif

    n_th1 = 0;
    for (k = 0; k < BUFFER_SIZE; k++)
    {
        n_th1 += an_x[k];
    }
    n_th1 = n_th1 / BUFFER_SIZE;
    if (n_th1 < 30)
    {
        n_th1 = 30;
    }
    if (n_th1 > 60)
    {
        n_th1 = 60;
    }

    for (k = 0; k < 15; k++)
    {
        an_ir_valley_locs[k] = 0;
    }

    maxim_find_peaks(
        an_ir_valley_locs,
        &n_npks,
        an_x,
        BUFFER_SIZE,
        n_th1,
        4,
        15
    );

    n_peak_interval_sum = 0;
    if (n_npks >= 2)
    {
        for (k = 1; k < n_npks; k++)
        {
            n_peak_interval_sum += an_ir_valley_locs[k] - an_ir_valley_locs[k - 1];
        }

        int32_t intervalCount = n_npks - 1;

        averagePeakInterval =
            static_cast<float>(n_peak_interval_sum) / intervalCount;
        *pn_heart_rate = static_cast<int32_t>(lroundf((FreqS * 60.0f) / averagePeakInterval));
        *pch_hr_valid = 1;
    }
    else
    {
        *pn_heart_rate = -999;
        *pch_hr_valid = 0;
    }

    for (k = 0; k < n_ir_buffer_length; k++)
    {
        an_x[k] = pun_ir_buffer[k];
        an_y[k] = pun_red_buffer[k];
    }

    n_exact_ir_valley_locs_count = n_npks;
    n_ratio_average = 0;
    n_i_ratio_count = 0;
    for (k = 0; k < 5; k++)
    {
        an_ratio[k] = 0;
    }

    for (k = 0; k < n_exact_ir_valley_locs_count; k++)
    {
        if (an_ir_valley_locs[k] > BUFFER_SIZE)
        {
            *pn_spo2 = -999;
            *pch_spo2_valid = 0;
            return;
        }
    }

    for (k = 0; k < n_exact_ir_valley_locs_count - 1; k++)
    {
        n_y_dc_max = -16777216;
        n_x_dc_max = -16777216;

        if (an_ir_valley_locs[k + 1] - an_ir_valley_locs[k] > 3)
        {
            for (i = an_ir_valley_locs[k]; i < an_ir_valley_locs[k + 1]; i++)
            {
                if (an_x[i] > n_x_dc_max)
                {
                    n_x_dc_max = an_x[i];
                    n_x_dc_max_idx = i;
                }
                if (an_y[i] > n_y_dc_max)
                {
                    n_y_dc_max = an_y[i];
                    n_y_dc_max_idx = i;
                }
            }

            n_y_ac =
                (an_y[an_ir_valley_locs[k + 1]] - an_y[an_ir_valley_locs[k]]) *
                (n_y_dc_max_idx - an_ir_valley_locs[k]);
            n_y_ac =
                an_y[an_ir_valley_locs[k]] +
                n_y_ac / (an_ir_valley_locs[k + 1] - an_ir_valley_locs[k]);
            n_y_ac = an_y[n_y_dc_max_idx] - n_y_ac;

            n_x_ac =
                (an_x[an_ir_valley_locs[k + 1]] - an_x[an_ir_valley_locs[k]]) *
                (n_x_dc_max_idx - an_ir_valley_locs[k]);
            n_x_ac =
                an_x[an_ir_valley_locs[k]] +
                n_x_ac / (an_ir_valley_locs[k + 1] - an_ir_valley_locs[k]);
            n_x_ac = an_x[n_y_dc_max_idx] - n_x_ac;

            n_nume = (n_y_ac * n_x_dc_max) >> 7;
            n_denom = (n_x_ac * n_y_dc_max) >> 7;

            if (n_denom > 0 && n_i_ratio_count < 5 && n_nume != 0)
            {
                an_ratio[n_i_ratio_count] = (n_nume * 100) / n_denom;
                n_i_ratio_count++;
            }
        }
    }

    maxim_sort_ascend(an_ratio, n_i_ratio_count);
    n_middle_idx = n_i_ratio_count / 2;

    if (n_middle_idx > 1)
    {
        n_ratio_average =
            (an_ratio[n_middle_idx - 1] + an_ratio[n_middle_idx]) / 2;
    }
    else
    {
        n_ratio_average = an_ratio[n_middle_idx];
    }

    if (n_ratio_average > 2 && n_ratio_average < 184)
    {
        n_spo2_calc = uch_spo2_table[n_ratio_average];
        *pn_spo2 = n_spo2_calc;
        *pch_spo2_valid = 1;
    }
    else
    {
        *pn_spo2 = -999;
        *pch_spo2_valid = 0;
    }
}

static void maxim_find_peaks(
    int32_t *pn_locs,
    int32_t *n_npks,
    int32_t *pn_x,
    int32_t n_size,
    int32_t n_min_height,
    int32_t n_min_distance,
    int32_t n_max_num
)
{
    maxim_peaks_above_min_height(
        pn_locs,
        n_npks,
        pn_x,
        n_size,
        n_min_height
    );
    maxim_remove_close_peaks(pn_locs, n_npks, pn_x, n_min_distance);
    *n_npks = min(*n_npks, n_max_num);
}

static void maxim_peaks_above_min_height(
    int32_t *pn_locs,
    int32_t *n_npks,
    int32_t *pn_x,
    int32_t n_size,
    int32_t n_min_height
)
{
    int32_t i = 1;
    int32_t n_width;

    *n_npks = 0;
    while (i < n_size - 1)
    {
        if (pn_x[i] > n_min_height && pn_x[i] > pn_x[i - 1])
        {
            n_width = 1;
            while (i + n_width < n_size && pn_x[i] == pn_x[i + n_width])
            {
                n_width++;
            }

            if (
                i + n_width < n_size &&
                pn_x[i] > pn_x[i + n_width] &&
                *n_npks < 15
            )
            {
                pn_locs[(*n_npks)++] = i;
                i += n_width + 1;
            }
            else
            {
                i += n_width;
            }
        }
        else
        {
            i++;
        }
    }
}

static void maxim_remove_close_peaks(
    int32_t *pn_locs,
    int32_t *pn_npks,
    int32_t *pn_x,
    int32_t n_min_distance
)
{
    int32_t i;
    int32_t j;
    int32_t n_old_npks;
    int32_t n_dist;

    maxim_sort_indices_descend(pn_x, pn_locs, *pn_npks);

    for (i = -1; i < *pn_npks; i++)
    {
        n_old_npks = *pn_npks;
        *pn_npks = i + 1;

        for (j = i + 1; j < n_old_npks; j++)
        {
            n_dist = pn_locs[j] - (i == -1 ? -1 : pn_locs[i]);
            if (n_dist > n_min_distance || n_dist < -n_min_distance)
            {
                pn_locs[(*pn_npks)++] = pn_locs[j];
            }
        }
    }

    maxim_sort_ascend(pn_locs, *pn_npks);
}

static void maxim_sort_ascend(int32_t *pn_x, int32_t n_size)
{
    int32_t i;
    int32_t j;
    int32_t n_temp;

    for (i = 1; i < n_size; i++)
    {
        n_temp = pn_x[i];
        for (j = i; j > 0 && n_temp < pn_x[j - 1]; j--)
        {
            pn_x[j] = pn_x[j - 1];
        }
        pn_x[j] = n_temp;
    }
}

static void maxim_sort_indices_descend(
    int32_t *pn_x,
    int32_t *pn_indx,
    int32_t n_size
)
{
    int32_t i;
    int32_t j;
    int32_t n_temp;

    for (i = 1; i < n_size; i++)
    {
        n_temp = pn_indx[i];
        for (
            j = i;
            j > 0 && pn_x[n_temp] > pn_x[pn_indx[j - 1]];
            j--
        )
        {
            pn_indx[j] = pn_indx[j - 1];
        }
        pn_indx[j] = n_temp;
    }
}
}


/* =========================================================
 * ISR FLAG (vẫn giữ, dùng như gợi ý "có thể có dữ liệu",
 * KHÔNG dùng để chặn chờ nữa)
 * ========================================================= */

static volatile bool MAX30102_is_ready = false;


/* =========================================================
 * INTERNAL FUNCTION PROTOTYPES
 * ========================================================= */

static bool MAX30102_WriteReg(uint8_t reg, uint8_t value);
static bool MAX30102_ReadReg(uint8_t reg, uint8_t *value);
static bool MAX30102_ClearInterrupt(void);
static bool MAX30102_ReadFIFO(uint32_t *redLED, uint32_t *irLED);
static void MAX30102_RunAlgorithmAndCache(void);

static uint32_t MAX30102_irBuffer[MAX30102_BUFFER_SIZE];
static uint32_t MAX30102_redBuffer[MAX30102_BUFFER_SIZE];

/* ---- State machine non-blocking ---- */
static uint16_t MAX30102_writeIndex = 0;      // vị trí đang thu tiếp theo trong buffer
static bool MAX30102_bufferReady = false;     // đã từng thu đủ 100 mẫu lần đầu chưa
static uint32_t MAX30102_lastSampleMillis = 0;

/* ---- Cache kết quả gần nhất, đọc được bất cứ lúc nào ---- */
static int32_t MAX30102_lastHeartRate = -999;
static int8_t MAX30102_lastValidHR = 0;
static int32_t MAX30102_lastSpO2 = -999;
static int8_t MAX30102_lastValidSpO2 = 0;


static bool MAX30102_IsFingerDetected(uint32_t irSample)
{
    return irSample > MAX30102_IR_FINGER_THRESHOLD;
}


static void MAX30102_ApplyPhysiologicalSanityCheck(
    int32_t *heartRate,
    int8_t *validHeartRate,
    int32_t *spo2,
    int8_t *validSpO2
)
{
    if (
        *validHeartRate &&
        (*heartRate < MAX30102_HR_MIN_BPM ||
         *heartRate > MAX30102_HR_MAX_BPM)
    )
    {
        *validHeartRate = 0;
    }

    if (
        *validSpO2 &&
        (*spo2 < MAX30102_SPO2_MIN_PCT ||
         *spo2 > MAX30102_SPO2_MAX_PCT)
    )
    {
        *validSpO2 = 0;
    }
}



/* =========================================================
 * WRITE / READ REGISTER
 * ========================================================= */

static bool MAX30102_WriteReg(uint8_t reg, uint8_t value)
{
    Wire.beginTransmission(MAX30102_ADDR_REG);
    Wire.write(reg);
    Wire.write(value);

    return Wire.endTransmission() == 0;
}

static bool MAX30102_ReadReg(uint8_t reg, uint8_t *value)
{
    if (value == nullptr)
    {
        return false;
    }

    Wire.beginTransmission(MAX30102_ADDR_REG);
    Wire.write(reg);

    /* false: không STOP -> requestFrom() sẽ tạo REPEATED START */
    if (Wire.endTransmission(false) != 0)
    {
        return false;
    }

    size_t received = Wire.requestFrom((uint8_t)MAX30102_ADDR_REG, (size_t)1, true);

    if (received != 1 || !Wire.available())
    {
        return false;
    }

    *value = Wire.read();
    return true;
}


/* =========================================================
 * INITIALIZE MAX30102
 * ========================================================= */

bool MAX30102_Init(void)
{
    uint8_t configValue = 0;
    uint8_t registerValue = 0;

    MAX30102_is_ready = false;
    MAX30102_bufferReady = false;
    MAX30102_writeIndex = 0;
    MAX30102_lastSampleMillis = millis();

    pinMode(INT_PIN, INPUT_PULLUP);

    /* CHECK PART ID */
    if (!MAX30102_ReadReg(REG_PART_ID, &registerValue))
    {
        return false;
    }
    if (registerValue != VALUE_PART_ID)
    {
        return false;
    }

    /* RESET */
    if (!MAX30102_WriteReg(REG_MODE_CONFIG, MODE_RESET))
    {
        return false;
    }

    uint32_t resetStart = millis();
    while (1)
    {
        if (!MAX30102_ReadReg(REG_MODE_CONFIG, &registerValue))
        {
            return false;
        }
        if ((registerValue & MODE_RESET) == 0)
        {
            break;
        }
        if ((millis() - resetStart) > 100)
        {
            return false;
        }
        delay(1);
    }
    /* Lưu ý: vòng chờ reset ở trên chỉ chạy 1 lần trong Init(), tối đa
     * 100ms, không phải phần lặp đọc dữ liệu nên không ảnh hưởng tới
     * tính non-blocking của Poll(). */

    /* DISABLE INTERRUPTS */
    if (!MAX30102_WriteReg(REG_INTER_ENABLE_1, 0x00)) return false;
    if (!MAX30102_WriteReg(REG_INTER_ENABLE_2, 0x00)) return false;

    /* RESET FIFO POINTERS */
    if (!MAX30102_WriteReg(REG_WR_PTR_CONF, ERASER_POINTER)) return false;
    if (!MAX30102_WriteReg(REG_OVF_COUNTER, ERASER_POINTER)) return false;
    if (!MAX30102_WriteReg(REG_RD_PTR_CONF, ERASER_POINTER)) return false;

    /* FIFO CONFIG: average 4, rollover, almost full 15 */
    configValue = FIFO_SMP_AVE_4 | FIFO_ROLLOVER_ENABLE | FIFO_A_FULL_15;
    if (!MAX30102_WriteReg(REG_FIFO_CONFIG, configValue)) return false;

    /* SPO2 CONFIG: ADC 4096nA, 100SPS, pulse width 411us */
    configValue = SP02_ADC_RGE_4096 | SP02_SR_100 | SP02_LED_PW_411;
    if (!MAX30102_WriteReg(REG_SP02_CONFIG, configValue)) return false;

    /* LED CURRENT */
    if (!MAX30102_WriteReg(REG_PULSE_AMP_1, LED_CURRENT)) return false; /* RED */
    if (!MAX30102_WriteReg(REG_PULSE_AMP_2, LED_CURRENT)) return false; /* IR */

    /* RESET INTERRUPT STATUS */
    if (!MAX30102_ClearInterrupt())
    {
        return false;
    }

    /* START SPO2 MODE (RED + IR) */
    if (!MAX30102_WriteReg(REG_MODE_CONFIG, MODE_SP02))
    {
        return false;
    }

    /* ENABLE INTERRUPT */
    configValue = PPG_RDY_EN | A_FULL_EN;
    if (!MAX30102_WriteReg(REG_INTER_ENABLE_1, configValue)) return false;
    if (!MAX30102_WriteReg(REG_INTER_ENABLE_2, 0x00)) return false;

    return true;
}


/* =========================================================
 * CLEAR INTERRUPT
 * ========================================================= */

static bool MAX30102_ClearInterrupt(void)
{
    uint8_t status1 = 0;
    uint8_t status2 = 0;

    if (!MAX30102_ReadReg(REG_INTER_STATUS_1, &status1))
    {
        return false;
    }

    return MAX30102_ReadReg(REG_INTER_STATUS_2, &status2);
}



/* =========================================================
 * ĐỌC 1 MẪU TỪ FIFO (RED 3 byte + IR 3 byte)
 * Trả về false ngay nếu FIFO rỗng - không có vòng chờ nào ở đây,
 * đúng nghĩa "thử đọc, không có thì thôi".
 * ========================================================= */

static bool MAX30102_ReadFIFO(uint32_t *redLED, uint32_t *irLED)
{
    if (redLED == nullptr || irLED == nullptr)
    {
        return false;
    }

    uint8_t wrPtr = 0;
    uint8_t rdPtr = 0;

    if (!MAX30102_ReadReg(REG_WR_PTR_CONF, &wrPtr)) return false;
    if (!MAX30102_ReadReg(REG_RD_PTR_CONF, &rdPtr)) return false;

    wrPtr &= 0x1F;
    rdPtr &= 0x1F;

    if (wrPtr == rdPtr)
    {
        /* FIFO không còn dữ liệu ngay lúc này */
        return false;
    }

    Wire.beginTransmission(MAX30102_ADDR_REG);
    Wire.write(REG_FIFO_DATA);
    if (Wire.endTransmission() != 0)
    {
        return false;
    }

    size_t received = Wire.requestFrom((uint8_t)MAX30102_ADDR_REG, (size_t)6, true);
    if (received != 6)
    {
        return false;
    }

    uint8_t data[6];
    for (uint8_t i = 0; i < 6; i++)
    {
        if (!Wire.available())
        {
            return false;
        }
        data[i] = Wire.read();
    }

    *redLED = (((uint32_t)data[0] << 16) | ((uint32_t)data[1] << 8) | (uint32_t)data[2]) & 0x03FFFF;
    *irLED  = (((uint32_t)data[3] << 16) | ((uint32_t)data[4] << 8) | (uint32_t)data[5]) & 0x03FFFF;

    return true;
}


/* =========================================================
 * ISR - CHỈ SET FLAG, KHÔNG I2C/DELAY/SERIAL
 * (Với clone tím, ngắt có thể không đáng tin -> Poll() không phụ
 * thuộc hoàn toàn vào flag này, chỉ dùng để log/debug nếu cần.)
 * ========================================================= */

void IRAM_ATTR MAX30102_ISR(void)
{
    MAX30102_is_ready = true;
}


/* =========================================================
 * CHẠY THUẬT TOÁN HR/SPO2 TRÊN BUFFER HIỆN TẠI VÀ CACHE KẾT QUẢ,
 * SAU ĐÓ TRƯỢT CỬA SỔ (GIỮ 75 MẪU CŨ) ĐỂ CHUẨN BỊ CHU KỲ TIẾP THEO.
 * ========================================================= */

static void MAX30102_RunAlgorithmAndCache(void)
{
    int32_t heartRate = -999;
    int8_t validHeartRate = 0;
    int32_t spo2 = -999;
    int8_t validSpO2 = 0;

    maxim_heart_rate_and_oxygen_saturation(
        MAX30102_irBuffer,
        MAX30102_BUFFER_SIZE,
        MAX30102_redBuffer,
        &spo2,
        &validSpO2,
        &heartRate,
        &validHeartRate
    );

    MAX30102_ApplyPhysiologicalSanityCheck(
        &heartRate,
        &validHeartRate,
        &spo2,
        &validSpO2
    );

    MAX30102_lastHeartRate = heartRate;
    MAX30102_lastValidHR = validHeartRate;
    MAX30102_lastSpO2 = spo2;
    MAX30102_lastValidSpO2 = validSpO2;

    /* GIỮ LẠI 75 MẪU CŨ, dồn về đầu buffer */
    for (uint16_t i = MAX30102_NEW_SAMPLES; i < MAX30102_BUFFER_SIZE; i++)
    {
        MAX30102_redBuffer[i - MAX30102_NEW_SAMPLES] = MAX30102_redBuffer[i];
        MAX30102_irBuffer[i - MAX30102_NEW_SAMPLES]  = MAX30102_irBuffer[i];
    }

    MAX30102_writeIndex = MAX30102_BUFFER_SIZE - MAX30102_NEW_SAMPLES;
    MAX30102_bufferReady = true;
}


/* =========================================================
 * RESET BUFFER (gọi khi mất ngón tay hoặc timeout)
 * ========================================================= */

void MAX30102_ResetBuffer(void)
{
    MAX30102_writeIndex = 0;
    MAX30102_bufferReady = false;
    MAX30102_lastSampleMillis = millis();
    /* Không xoá cache kết quả cũ - UI vẫn có thể hiển thị giá trị gần
     * nhất trong lúc chờ đo lại, tuỳ bạn muốn giữ hay clear ở lớp gọi. */
}


/* =========================================================
 * POLL - HÀM CHÍNH, GỌI LIÊN TỤC TRONG loop() HOẶC 1 TASK.
 * KHÔNG CÓ delay()/while CHỜ NÀO Ở ĐÂY -> non-blocking thật sự.
 *
 * Mỗi lần gọi: rút cạn các mẫu ĐANG CÓ SẴN trong FIFO (thường 1-4 mẫu
 * tuỳ tốc độ gọi Poll), rồi return ngay lập tức, không đợi mẫu tiếp theo.
 * ========================================================= */

MAX30102_State MAX30102_Poll(void)
{
    bool gotAnySampleThisCall = false;

    uint32_t red;
    uint32_t ir;

    while (MAX30102_writeIndex < MAX30102_BUFFER_SIZE)
    {
        if (!MAX30102_ReadFIFO(&red, &ir))
        {
            /* FIFO rỗng ngay lúc này -> dừng vòng rút mẫu, KHÔNG chờ */
            break;
        }

        MAX30102_is_ready = false; // đã tiêu thụ dữ liệu, coi như xử lý xong "sự kiện" ngắt

        if (!MAX30102_IsFingerDetected(ir))
        {
            MAX30102_ResetBuffer();
            return MAX30102_STATE_NO_FINGER;
        }

        MAX30102_redBuffer[MAX30102_writeIndex] = red;
        MAX30102_irBuffer[MAX30102_writeIndex] = ir;
        MAX30102_writeIndex++;

        gotAnySampleThisCall = true;
        MAX30102_lastSampleMillis = millis();
    }

    if (gotAnySampleThisCall)
    {
        /* Dọn cờ ngắt để tránh tràn REG_INTER_STATUS, không bắt buộc
         * phải thành công mỗi lần - lỗi ở đây không chặn flow. */
        MAX30102_ClearInterrupt();
    }

    if (MAX30102_writeIndex >= MAX30102_BUFFER_SIZE)
    {
        MAX30102_RunAlgorithmAndCache();
        return MAX30102_STATE_RESULT_READY;
    }

    if (!gotAnySampleThisCall &&
        (millis() - MAX30102_lastSampleMillis) >= MAX30102_SAMPLE_TIMEOUT_MS)
    {
        MAX30102_ResetBuffer();
        return MAX30102_STATE_TIMEOUT;
    }

    return MAX30102_STATE_COLLECTING;
}


/* =========================================================
 * LẤY KẾT QUẢ CACHE GẦN NHẤT
 * ========================================================= */

void MAX30102_GetLastResult(
    int32_t *heartRate,
    int8_t *validHeartRate,
    int32_t *spo2,
    int8_t *validSpO2
)
{
    if (heartRate) *heartRate = MAX30102_lastHeartRate;
    if (validHeartRate) *validHeartRate = MAX30102_lastValidHR;
    if (spo2) *spo2 = MAX30102_lastSpO2;
    if (validSpO2) *validSpO2 = MAX30102_lastValidSpO2;
}