#include "ESP32_MAX30102_Lib.h"
#include <math.h>
#include <stdio.h>

#if SENSOR_TIMING_DEBUG
#include <esp_timer.h>
#endif

#ifndef MAX30102_ENABLE_BANDPASS_FILTER
#define MAX30102_ENABLE_BANDPASS_FILTER 1
#endif
#ifndef DEBUG_MAX30102_HR
#define DEBUG_MAX30102_HR 1
#endif
#ifndef DEBUG_MAX30102_PEAK
#define DEBUG_MAX30102_PEAK 1
#endif
#if DEBUG_MAX30102_PEAK
#include <stdarg.h>
#include <string.h>
#endif
#define MAX30102_FILTER_FS_HZ 25.0f


/*******************************************************************************
 * Heart-rate and SpO2 algorithm from the Maxim MAXREFDES117 reference design.
 *
 * Copyright (C) 2015 Maxim Integrated Products, Inc., All Rights Reserved.
 * Copyright (C) 2016 Maxim Integrated Products, Inc., All Rights Reserved.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a
 * copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included
 * in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
 * OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 * DEALINGS IN THE SOFTWARE.
 ******************************************************************************/

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

#if DEBUG_MAX30102_HR || DEBUG_MAX30102_PEAK
static uint32_t MAX30102_hrWindowIndex = 0;
#endif

#if DEBUG_MAX30102_PEAK
static int32_t MAX30102_debugDc[BUFFER_SIZE];
static int32_t MAX30102_debugMa4[BUFFER_SIZE];
static int32_t MAX30102_debugCandidateLocs[15];
static int32_t MAX30102_debugCandidateCount = 0;
static uint32_t MAX30102_debugSession = 0;
static uint32_t MAX30102_debugSessionWindow = 0;
static char MAX30102_debugLine[512];
#endif

#if SENSOR_TIMING_DEBUG
static MAX30102_TimingProfile MAX30102_timingProfile = {};
#endif

/* =========================================================
 * BANDPASS 0.5 Hz - 4 Hz CHỈ DÙNG CHO PEAK DETECTION
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

#if DEBUG_MAX30102_PEAK
static void MAX30102_DebugLogSuspiciousWindow(
    uint32_t windowIndex,
    uint32_t session,
    uint32_t sessionWindow,
    int32_t *finalPeaks,
    int32_t finalPeakCount,
    int32_t thresholdMean,
    int32_t threshold
);
#endif

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
#if SENSOR_TIMING_DEBUG
    int64_t phaseStartUs = esp_timer_get_time();
#endif

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
    float calculatedHeartRate = -999.0f;
    int32_t legacyHeartRate = -999;

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

#if DEBUG_MAX30102_PEAK
    memcpy(MAX30102_debugDc, an_x, sizeof(MAX30102_debugDc));
#endif

    for (k = 0; k < BUFFER_SIZE - MA4_SIZE; k++)
    {
        an_x[k] = (an_x[k] + an_x[k + 1] + an_x[k + 2] + an_x[k + 3]) / 4;
    }

#if DEBUG_MAX30102_PEAK
    memcpy(MAX30102_debugMa4, an_x, sizeof(MAX30102_debugMa4));
#endif

#if MAX30102_ENABLE_BANDPASS_FILTER
    /* Chỉ lọc bản sao an_x, không sửa dữ liệu IR/RED gốc. */
    MAX30102_BandpassFilter(an_x, n_ir_buffer_length);
#endif

#if SENSOR_TIMING_DEBUG
    MAX30102_timingProfile.filterUs =
        esp_timer_get_time() - phaseStartUs;
    phaseStartUs = esp_timer_get_time();
#endif

    n_th1 = 0;
    for (k = 0; k < BUFFER_SIZE; k++)
    {
        n_th1 += an_x[k];
    }
    n_th1 = n_th1 / BUFFER_SIZE;
#if DEBUG_MAX30102_PEAK
    const int32_t debugThresholdMean = n_th1;
#endif
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
        int32_t legacyAverageInterval =
            n_peak_interval_sum / intervalCount;
        legacyHeartRate =
            (FreqS * 60) / legacyAverageInterval;

        averagePeakInterval =
            static_cast<float>(n_peak_interval_sum) / intervalCount;
        calculatedHeartRate =
            (FreqS * 60.0f) / averagePeakInterval;
        *pn_heart_rate = static_cast<int32_t>(lroundf(calculatedHeartRate));
        *pch_hr_valid = 1;
    }
    else
    {
        *pn_heart_rate = -999;
        *pch_hr_valid = 0;
    }

#if SENSOR_TIMING_DEBUG
    MAX30102_timingProfile.bpmUs =
        esp_timer_get_time() - phaseStartUs;
#endif

#if DEBUG_MAX30102_HR || DEBUG_MAX30102_PEAK
    const uint32_t debugWindowIndex = ++MAX30102_hrWindowIndex;
#endif

#if DEBUG_MAX30102_PEAK
    const uint32_t debugSession = MAX30102_debugSession;
    const uint32_t debugSessionWindow = ++MAX30102_debugSessionWindow;
#endif

#if DEBUG_MAX30102_HR
    char hrDebugLine[320];
    int debugLength = snprintf(
        hrDebugLine,
        sizeof(hrDebugLine),
        "[MAX-HR] window=%lu peaks=%ld locs=",
        (unsigned long)debugWindowIndex,
        (long)n_npks
    );

    for (k = 0; k < n_npks; k++)
    {
        debugLength += snprintf(
            hrDebugLine + debugLength,
            sizeof(hrDebugLine) - debugLength,
            "%s%ld",
            k == 0 ? "" : ",",
            (long)an_ir_valley_locs[k]
        );
    }

    debugLength += snprintf(
        hrDebugLine + debugLength,
        sizeof(hrDebugLine) - debugLength,
        " intervals="
    );
    for (k = 1; k < n_npks; k++)
    {
        debugLength += snprintf(
            hrDebugLine + debugLength,
            sizeof(hrDebugLine) - debugLength,
            "%s%ld",
            k == 1 ? "" : ",",
            (long)(an_ir_valley_locs[k] - an_ir_valley_locs[k - 1])
        );
    }

    snprintf(
        hrDebugLine + debugLength,
        sizeof(hrDebugLine) - debugLength,
        " total=%ld avg=%.2f hr=%.2f out=%ld legacy=%ld",
        (long)n_peak_interval_sum,
        averagePeakInterval,
        calculatedHeartRate,
        (long)*pn_heart_rate,
        (long)legacyHeartRate
    );
    Serial.println(hrDebugLine);
#endif

#if DEBUG_MAX30102_PEAK
    MAX30102_DebugLogSuspiciousWindow(
        debugWindowIndex,
        debugSession,
        debugSessionWindow,
        an_ir_valley_locs,
        n_npks,
        debugThresholdMean,
        n_th1
    );
#endif

#if SENSOR_TIMING_DEBUG
    phaseStartUs = esp_timer_get_time();
#endif

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
#if SENSOR_TIMING_DEBUG
            MAX30102_timingProfile.spo2Us =
                esp_timer_get_time() - phaseStartUs;
#endif
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


#if SENSOR_TIMING_DEBUG
    MAX30102_timingProfile.spo2Us =
        esp_timer_get_time() - phaseStartUs;
#endif
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
#if DEBUG_MAX30102_PEAK
    MAX30102_debugCandidateCount = *n_npks;
    for (int32_t i = 0; i < MAX30102_debugCandidateCount; i++)
    {
        MAX30102_debugCandidateLocs[i] = pn_locs[i];
    }
#endif
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

#if DEBUG_MAX30102_PEAK
static size_t MAX30102_DebugAppend(
    char *line,
    size_t capacity,
    size_t length,
    const char *format,
    ...
)
{
    if (length >= capacity)
    {
        return capacity - 1;
    }

    va_list arguments;
    va_start(arguments, format);
    int written = vsnprintf(
        line + length,
        capacity - length,
        format,
        arguments
    );
    va_end(arguments);

    if (written < 0)
    {
        return length;
    }

    size_t available = capacity - length;
    if (static_cast<size_t>(written) >= available)
    {
        return capacity - 1;
    }

    return length + static_cast<size_t>(written);
}

static bool MAX30102_DebugPeakIsKept(
    int32_t peak,
    int32_t *finalPeaks,
    int32_t finalPeakCount
)
{
    for (int32_t i = 0; i < finalPeakCount; i++)
    {
        if (finalPeaks[i] == peak)
        {
            return true;
        }
    }

    return false;
}

static int32_t MAX30102_DebugLocalProminence(int32_t peak)
{
    if (peak <= 0 || peak >= BUFFER_SIZE - 1)
    {
        return 0;
    }

    int32_t leftStart = peak > 3 ? peak - 3 : 0;
    int32_t rightEnd = peak + 3 < BUFFER_SIZE ? peak + 3 : BUFFER_SIZE - 1;
    int32_t leftMinimum = an_x[peak - 1];
    int32_t rightMinimum = an_x[peak + 1];

    for (int32_t i = peak - 2; i >= leftStart; i--)
    {
        if (an_x[i] < leftMinimum)
        {
            leftMinimum = an_x[i];
        }
    }

    for (int32_t i = peak + 2; i <= rightEnd; i++)
    {
        if (an_x[i] < rightMinimum)
        {
            rightMinimum = an_x[i];
        }
    }

    int32_t localBase = leftMinimum > rightMinimum
        ? leftMinimum
        : rightMinimum;
    return an_x[peak] - localBase;
}

static void MAX30102_DebugLogSuspiciousWindow(
    uint32_t windowIndex,
    uint32_t session,
    uint32_t sessionWindow,
    int32_t *finalPeaks,
    int32_t finalPeakCount,
    int32_t thresholdMean,
    int32_t threshold
)
{
    bool suspiciousWindow = false;

    for (int32_t i = 1; i < finalPeakCount; i++)
    {
        int32_t interval = finalPeaks[i] - finalPeaks[i - 1];
        if (interval <= 10 || interval >= 25)
        {
            suspiciousWindow = true;
            break;
        }
    }

    if (!suspiciousWindow)
    {
        for (int32_t i = 0; i < finalPeakCount; i++)
        {
            if (finalPeaks[i] >= 94)
            {
                suspiciousWindow = true;
                break;
            }
        }
    }

    if (!suspiciousWindow)
    {
        return;
    }

    size_t length = MAX30102_DebugAppend(
        MAX30102_debugLine,
        sizeof(MAX30102_debugLine),
        0,
        "[MAX-P] window=%lu session=%lu session_window=%lu mean=%ld threshold=%ld candidates=",
        (unsigned long)windowIndex,
        (unsigned long)session,
        (unsigned long)sessionWindow,
        (long)thresholdMean,
        (long)threshold
    );

    if (MAX30102_debugCandidateCount == 0)
    {
        length = MAX30102_DebugAppend(
            MAX30102_debugLine,
            sizeof(MAX30102_debugLine),
            length,
            "none"
        );
    }
    else
    {
        for (int32_t i = 0; i < MAX30102_debugCandidateCount; i++)
        {
            int32_t peak = MAX30102_debugCandidateLocs[i];
            bool kept = MAX30102_DebugPeakIsKept(
                peak,
                finalPeaks,
                finalPeakCount
            );
            length = MAX30102_DebugAppend(
                MAX30102_debugLine,
                sizeof(MAX30102_debugLine),
                length,
                "%s%ld:%ld:%c",
                i == 0 ? "" : ",",
                (long)peak,
                (long)an_x[peak],
                kept ? 'K' : 'R'
            );
        }
    }

    length = MAX30102_DebugAppend(
        MAX30102_debugLine,
        sizeof(MAX30102_debugLine),
        length,
        " kept="
    );
    if (finalPeakCount == 0)
    {
        MAX30102_DebugAppend(
            MAX30102_debugLine,
            sizeof(MAX30102_debugLine),
            length,
            "none"
        );
    }
    else
    {
        for (int32_t i = 0; i < finalPeakCount; i++)
        {
            length = MAX30102_DebugAppend(
                MAX30102_debugLine,
                sizeof(MAX30102_debugLine),
                length,
                "%s%ld",
                i == 0 ? "" : ",",
                (long)finalPeaks[i]
            );
        }
    }
    Serial.println(MAX30102_debugLine);

    for (int32_t i = 0; i < MAX30102_debugCandidateCount; i++)
    {
        int32_t peak = MAX30102_debugCandidateLocs[i];
        if (peak > 3)
        {
            continue;
        }

        bool kept = MAX30102_DebugPeakIsKept(
            peak,
            finalPeaks,
            finalPeakCount
        );
        snprintf(
            MAX30102_debugLine,
            sizeof(MAX30102_debugLine),
            "[MAX-DIST] window=%lu session=%lu a=-1 amp=NA b=%ld amp=%ld distance=%ld result=%s",
            (unsigned long)windowIndex,
            (unsigned long)session,
            (long)peak,
            (long)an_x[peak],
            (long)(peak + 1),
            kept ? "KEEP_B" : "REMOVE_B"
        );
        Serial.println(MAX30102_debugLine);
    }

    for (int32_t i = 1; i < MAX30102_debugCandidateCount; i++)
    {
        int32_t peakA = MAX30102_debugCandidateLocs[i - 1];
        int32_t peakB = MAX30102_debugCandidateLocs[i];
        int32_t distance = peakB - peakA;
        if (distance > 10)
        {
            continue;
        }

        bool keepA = MAX30102_DebugPeakIsKept(
            peakA,
            finalPeaks,
            finalPeakCount
        );
        bool keepB = MAX30102_DebugPeakIsKept(
            peakB,
            finalPeaks,
            finalPeakCount
        );
        const char *result = keepA
            ? (keepB ? "KEEP_BOTH" : "REMOVE_B")
            : (keepB ? "REMOVE_A" : "REMOVE_BOTH");

        snprintf(
            MAX30102_debugLine,
            sizeof(MAX30102_debugLine),
            "[MAX-DIST] window=%lu session=%lu a=%ld amp=%ld b=%ld amp=%ld distance=%ld result=%s",
            (unsigned long)windowIndex,
            (unsigned long)session,
            (long)peakA,
            (long)an_x[peakA],
            (long)peakB,
            (long)an_x[peakB],
            (long)distance,
            result
        );
        Serial.println(MAX30102_debugLine);
    }

    for (int32_t i = 0; i < finalPeakCount; i++)
    {
        int32_t peak = finalPeaks[i];
        int32_t previousPeak = i > 0 ? finalPeaks[i - 1] : -1;
        int32_t nextPeak = i + 1 < finalPeakCount ? finalPeaks[i + 1] : -1;
        int32_t previousDistance = previousPeak >= 0 ? peak - previousPeak : -1;
        int32_t nextDistance = nextPeak >= 0 ? nextPeak - peak : -1;
        bool suspiciousPrevious =
            previousDistance >= 0 &&
            (previousDistance <= 10 || previousDistance >= 25);
        bool suspiciousNext =
            nextDistance >= 0 &&
            (nextDistance <= 10 || nextDistance >= 25);

        if (peak < 94 && !suspiciousPrevious && !suspiciousNext)
        {
            continue;
        }

        uint32_t absoluteSample =
            (sessionWindow - 1) * MAX30102_NEW_SAMPLES + peak;
        int32_t prominence = MAX30102_DebugLocalProminence(peak);
        snprintf(
            MAX30102_debugLine,
            sizeof(MAX30102_debugLine),
            "[MAX-PEAK] window=%lu session=%lu session_window=%lu peak=%ld abs=%lu prev=%ld next=%ld dprev=%ld dnext=%ld edge_start=%ld edge_end=%ld amp=%ld threshold=%ld prominence=%ld",
            (unsigned long)windowIndex,
            (unsigned long)session,
            (unsigned long)sessionWindow,
            (long)peak,
            (unsigned long)absoluteSample,
            (long)previousPeak,
            (long)nextPeak,
            (long)previousDistance,
            (long)nextDistance,
            (long)peak,
            (long)(BUFFER_SIZE - 1 - peak),
            (long)an_x[peak],
            (long)threshold,
            (long)prominence
        );
        Serial.println(MAX30102_debugLine);

        int32_t rangeStart = peak > 3 ? peak - 3 : 0;
        int32_t rangeEnd = peak + 3 < BUFFER_SIZE ? peak + 3 : BUFFER_SIZE - 1;
        length = MAX30102_DebugAppend(
            MAX30102_debugLine,
            sizeof(MAX30102_debugLine),
            0,
            "[MAX-SIG] window=%lu session=%lu peak=%ld abs=%lu range=%ld..%ld DC=",
            (unsigned long)windowIndex,
            (unsigned long)session,
            (long)peak,
            (unsigned long)absoluteSample,
            (long)rangeStart,
            (long)rangeEnd
        );
        for (int32_t sample = rangeStart; sample <= rangeEnd; sample++)
        {
            length = MAX30102_DebugAppend(
                MAX30102_debugLine,
                sizeof(MAX30102_debugLine),
                length,
                "%s%ld",
                sample == rangeStart ? "" : ",",
                (long)MAX30102_debugDc[sample]
            );
        }
        length = MAX30102_DebugAppend(
            MAX30102_debugLine,
            sizeof(MAX30102_debugLine),
            length,
            " MA4="
        );
        for (int32_t sample = rangeStart; sample <= rangeEnd; sample++)
        {
            length = MAX30102_DebugAppend(
                MAX30102_debugLine,
                sizeof(MAX30102_debugLine),
                length,
                "%s%ld",
                sample == rangeStart ? "" : ",",
                (long)MAX30102_debugMa4[sample]
            );
        }
        length = MAX30102_DebugAppend(
            MAX30102_debugLine,
            sizeof(MAX30102_debugLine),
            length,
            " BP="
        );
        for (int32_t sample = rangeStart; sample <= rangeEnd; sample++)
        {
            length = MAX30102_DebugAppend(
                MAX30102_debugLine,
                sizeof(MAX30102_debugLine),
                length,
                "%s%ld",
                sample == rangeStart ? "" : ",",
                (long)an_x[sample]
            );
        }
        Serial.println(MAX30102_debugLine);

        if (peak < 94)
        {
            continue;
        }

        length = MAX30102_DebugAppend(
            MAX30102_debugLine,
            sizeof(MAX30102_debugLine),
            0,
            "[MAX-TAIL] window=%lu session=%lu peak=%ld DC[93..99]=",
            (unsigned long)windowIndex,
            (unsigned long)session,
            (long)peak
        );
        for (int32_t sample = 93; sample < BUFFER_SIZE; sample++)
        {
            length = MAX30102_DebugAppend(
                MAX30102_debugLine,
                sizeof(MAX30102_debugLine),
                length,
                "%s%ld",
                sample == 93 ? "" : ",",
                (long)MAX30102_debugDc[sample]
            );
        }
        length = MAX30102_DebugAppend(
            MAX30102_debugLine,
            sizeof(MAX30102_debugLine),
            length,
            " MA4[93..99]="
        );
        for (int32_t sample = 93; sample < BUFFER_SIZE; sample++)
        {
            length = MAX30102_DebugAppend(
                MAX30102_debugLine,
                sizeof(MAX30102_debugLine),
                length,
                "%s%ld",
                sample == 93 ? "" : ",",
                (long)MAX30102_debugMa4[sample]
            );
        }
        length = MAX30102_DebugAppend(
            MAX30102_debugLine,
            sizeof(MAX30102_debugLine),
            length,
            " BP[93..99]="
        );
        for (int32_t sample = 93; sample < BUFFER_SIZE; sample++)
        {
            length = MAX30102_DebugAppend(
                MAX30102_debugLine,
                sizeof(MAX30102_debugLine),
                length,
                "%s%ld",
                sample == 93 ? "" : ",",
                (long)an_x[sample]
            );
        }
        Serial.println(MAX30102_debugLine);
    }
}
#endif
}


/* =========================================================
 * INTERRUPT FLAG
 * ========================================================= */

volatile bool MAX30102_is_ready = false;


/* =========================================================
 * INTERNAL FUNCTION PROTOTYPES
 * ========================================================= */

static bool MAX30102_WriteReg(
    uint8_t reg,
    uint8_t value
);

static bool MAX30102_ReadReg(
    uint8_t reg,
    uint8_t *value
);

static uint8_t MAX30102_I2CPing(void);
static uint32_t MAX30102_irBuffer[MAX30102_BUFFER_SIZE];
static uint32_t MAX30102_redBuffer[MAX30102_BUFFER_SIZE];

static bool MAX30102_bufferReady = false;
static const uint32_t MAX30102_SAMPLE_TIMEOUT_MS = 6000;
static SemaphoreHandle_t MAX30102_i2cMutex = nullptr;


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


static bool MAX30102_LockI2C(void)
{
    return MAX30102_i2cMutex == nullptr ||
           xSemaphoreTake(MAX30102_i2cMutex, portMAX_DELAY) == pdTRUE;
}


static void MAX30102_UnlockI2C(void)
{
    if (MAX30102_i2cMutex != nullptr)
    {
        xSemaphoreGive(MAX30102_i2cMutex);
    }
}


/* =========================================================
 * I2C PING
 *
 * Chỉ kiểm tra xem thiết bị địa chỉ 0x57 có ACK hay không.
 * ========================================================= */

static uint8_t MAX30102_I2CPing(void)
{
    Wire.beginTransmission(MAX30102_ADDR_REG);

    return Wire.endTransmission();
}


/* =========================================================
 * WRITE REGISTER
 * ========================================================= */

static bool MAX30102_WriteReg(
    uint8_t reg,
    uint8_t value
)
{
    Wire.beginTransmission(MAX30102_ADDR_REG);

    Wire.write(reg);
    Wire.write(value);


    uint8_t error = Wire.endTransmission();


    if (error != 0)
    {
        return false;
    }


    return true;
}


/* =========================================================
 * READ REGISTER
 * ========================================================= */

static bool MAX30102_ReadReg(
    uint8_t reg,
    uint8_t *value
)
{
    if (value == nullptr)
    {
        return false;
    }


    /* -----------------------------------------------------
     * Gửi địa chỉ register muốn đọc
     * ----------------------------------------------------- */

    Wire.beginTransmission(MAX30102_ADDR_REG);

    Wire.write(reg);


    /*
     * false:
     *
     * Không STOP.
     * Sau đó Wire.requestFrom() sẽ tạo
     * REPEATED START.
     */
    uint8_t error =
        Wire.endTransmission(false);


    if (error != 0)
    {
        return false;
    }


    /* -----------------------------------------------------
     * Đọc 1 byte
     * ----------------------------------------------------- */

    size_t received =
        Wire.requestFrom(
            (uint8_t)MAX30102_ADDR_REG,
            (size_t)1,
            true
        );


    if (received != 1)
    {
        return false;
    }


    if (!Wire.available())
    {
        return false;
    }


    *value = Wire.read();


    return true;
}


/* =========================================================
 * INITIALIZE MAX30102
 * ========================================================= */

void MAX30102_SetI2CMutex(SemaphoreHandle_t mutex)
{
    MAX30102_i2cMutex = mutex;
}


#if SENSOR_TIMING_DEBUG
void MAX30102_GetTimingProfile(MAX30102_TimingProfile *profile)
{
    if (profile != nullptr)
    {
        *profile = MAX30102_timingProfile;
    }
}
#endif


bool MAX30102_Init(void)
{
    uint8_t configValue = 0;
    uint8_t registerValue = 0;

    MAX30102_is_ready = false;
    MAX30102_bufferReady = false;


    /* =====================================================
     * 1. CONFIG INT PIN
     * ===================================================== */

    pinMode(INT_PIN, INPUT_PULLUP);


    /* =====================================================
     * 2. CHECK PART ID
     * ===================================================== */

    if (!MAX30102_ReadReg(
            REG_PART_ID,
            &registerValue))
    {
        return false;
    }


    if (registerValue != VALUE_PART_ID)
    {
        return false;
    }


    /* =====================================================
     * 3. RESET
     * ===================================================== */

    if (!MAX30102_WriteReg(
            REG_MODE_CONFIG,
            MODE_RESET))
    {
        return false;
    }


    /*
     * Cho MAX30102 tự clear bit RESET.
     */
    uint32_t resetStart = millis();


    while (1)
    {
        if (!MAX30102_ReadReg(
                REG_MODE_CONFIG,
                &registerValue))
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


    /* =====================================================
     * 4. DISABLE INTERRUPTS
     * ===================================================== */

    if (!MAX30102_WriteReg(
            REG_INTER_ENABLE_1,
            0x00))
    {
        return false;
    }


    if (!MAX30102_WriteReg(
            REG_INTER_ENABLE_2,
            0x00))
    {
        return false;
    }


    /* =====================================================
     * 5. RESET FIFO POINTERS
     * ===================================================== */

    if (!MAX30102_WriteReg(
            REG_WR_PTR_CONF,
            ERASER_POINTER))
    {
        return false;
    }


    if (!MAX30102_WriteReg(
            REG_OVF_COUNTER,
            ERASER_POINTER))
    {
        return false;
    }


    if (!MAX30102_WriteReg(
            REG_RD_PTR_CONF,
            ERASER_POINTER))
    {
        return false;
    }


    /* =====================================================
     * 6. FIFO CONFIG
     *
     * Average 4
     * Rollover enable
     * Almost Full threshold
     * ===================================================== */

    configValue =
        FIFO_SMP_AVE_4 |
        FIFO_ROLLOVER_ENABLE |
        FIFO_A_FULL_15;


    if (!MAX30102_WriteReg(
            REG_FIFO_CONFIG,
            configValue))
    {
        return false;
    }


    /* =====================================================
     * 7. SPO2 CONFIG
     *
     * ADC = 4096 nA
     * Sample rate = 100 SPS
     * Pulse width = 411 us
     * ===================================================== */

    configValue =
        SP02_ADC_RGE_4096 |
        SP02_SR_100 |
        SP02_LED_PW_411;


    if (!MAX30102_WriteReg(
            REG_SP02_CONFIG,
            configValue))
    {
        return false;
    }


    /* =====================================================
     * 8. LED CURRENT
     * ===================================================== */

    /* RED LED */
    if (!MAX30102_WriteReg(
            REG_PULSE_AMP_1,
            LED_CURRENT))
    {
        return false;
    }


    /* IR LED */
    if (!MAX30102_WriteReg(
            REG_PULSE_AMP_2,
            LED_CURRENT))
    {
        return false;
    }


    /* =====================================================
     * 9. RESET INTERRUPT STATUS
     * ===================================================== */

    if (!MAX30102_ClearInterrupt())
    {
        return false;
    }


    /* =====================================================
     * 10. START SPO2 MODE
     *
     * RED + IR
     * ===================================================== */

    if (!MAX30102_WriteReg(
            REG_MODE_CONFIG,
            MODE_SP02))
    {
        return false;
    }


    /* =====================================================
     * 11. ENABLE INTERRUPT
     * ===================================================== */

    configValue =
        PPG_RDY_EN |
        A_FULL_EN;


    if (!MAX30102_WriteReg(
            REG_INTER_ENABLE_1,
            configValue))
    {
        return false;
    }


    /*
     * Không dùng interrupt ở Status 2.
     */
    if (!MAX30102_WriteReg(
            REG_INTER_ENABLE_2,
            0x00))
    {
        return false;
    }


    return true;
}


/* =========================================================
 * CLEAR INTERRUPT
 * ========================================================= */

bool MAX30102_ClearInterrupt(void)
{
    uint8_t status1 = 0;
    uint8_t status2 = 0;


    if (!MAX30102_ReadReg(
            REG_INTER_STATUS_1,
            &status1))
    {
        return false;
    }


    return MAX30102_ReadReg(
        REG_INTER_STATUS_2,
        &status2
    );
}


/* =========================================================
 * CHECK INT PIN
 * ========================================================= */

bool MAX30102_HasInterrupt(void)
{
    return (
        digitalRead(INT_PIN) == LOW
    );
}


/* =========================================================
 * READ ONE FIFO SAMPLE
 *
 * SPO2 Mode:
 *
 * RED = 3 byte
 * IR  = 3 byte
 *
 * Total = 6 byte
 * ========================================================= */

bool MAX30102_ReadFIFO(
    uint32_t *redLED,
    uint32_t *irLED
)
{
    if (
        redLED == nullptr ||
        irLED == nullptr
    )
    {
        return false;
    }


    uint8_t wrPtr = 0;
    uint8_t rdPtr = 0;


    /* =====================================================
     * READ WRITE POINTER
     * ===================================================== */

    if (!MAX30102_ReadReg(
            REG_WR_PTR_CONF,
            &wrPtr))
    {
        return false;
    }


    /* =====================================================
     * READ READ POINTER
     * ===================================================== */

    if (!MAX30102_ReadReg(
            REG_RD_PTR_CONF,
            &rdPtr))
    {
        return false;
    }


    /*
     * Pointer là 5-bit.
     */
    wrPtr &= 0x1F;
    rdPtr &= 0x1F;


    /*
     * FIFO không còn dữ liệu.
     */
    if (wrPtr == rdPtr)
    {
        return false;
    }


    /* =====================================================
     * CHỌN FIFO DATA REGISTER
     * ===================================================== */

    Wire.beginTransmission(MAX30102_ADDR_REG);

    Wire.write(REG_FIFO_DATA);


    /*
     * Ở FIFO burst read, dùng STOP sau khi
     * chọn FIFO_DATA.
     *
     * SparkFun cũng sử dụng kiểu này khi
     * đọc FIFO.
     */
    if (Wire.endTransmission() != 0)
    {
        return false;
    }


    /* =====================================================
     * READ 6 BYTES
     * ===================================================== */

    size_t received =
        Wire.requestFrom(
            (uint8_t)MAX30102_ADDR_REG,
            (size_t)6,
            true
        );


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


    /* =====================================================
     * RED
     * ===================================================== */

    *redLED =
        (
            ((uint32_t)data[0] << 16) |
            ((uint32_t)data[1] << 8)  |
            ((uint32_t)data[2])
        )
        & 0x03FFFF;


    /* =====================================================
     * IR
     * ===================================================== */

    *irLED =
        (
            ((uint32_t)data[3] << 16) |
            ((uint32_t)data[4] << 8)  |
            ((uint32_t)data[5])
        )
        & 0x03FFFF;


    return true;
}


/* =========================================================
 * FIFO OVERFLOW COUNTER
 * ========================================================= */

uint8_t MAX30102_GetOverflowCounter(void)
{
    uint8_t overflow = 0;


    if (!MAX30102_ReadReg(
            REG_OVF_COUNTER,
            &overflow))
    {
        return 0;
    }


    return overflow & 0x1F;
}


/* =========================================================
 * ISR
 *
 * ISR VẪN NẰM TRONG LIB.
 * ========================================================= */

void IRAM_ATTR MAX30102_ISR(void)
{
    /*
     * ISR chỉ set flag.
     *
     * Không Wire.
     * Không Serial.
     * Không delay.
     */
    MAX30102_is_ready = true;
}


/* =========================================================
 * TEST SETUP
 *
 * VẪN NẰM TRONG LIB.
 * ========================================================= */

void MAX30102_TestSetup(void)
{
    Serial.begin(115200);


    delay(500);


    Serial.println();
    Serial.println(
        "--- MAX30102 Hardware Interrupt Test ---"
    );


    Serial.printf(
        "[INFO] SDA=%d | SCL=%d | INT=%d\n",
        SDA_PIN,
        SCL_PIN,
        INT_PIN
    );


    /* =====================================================
     * I2C INIT
     * ===================================================== */

    Wire.begin(
        SDA_PIN,
        SCL_PIN
    );


    /*
     * Tạm dùng 100 kHz để debug.
     *
     * Khi chạy ổn có thể đổi lại:
     *
     * Wire.setClock(400000);
     */
    Wire.setClock(100000);


    delay(100);


    /* =====================================================
     * TEST I2C ADDRESS 0x57
     * ===================================================== */

    uint8_t pingError =
        MAX30102_I2CPing();


    if (pingError != 0)
    {
        Serial.printf(
            "[ERR] Khong tim thay I2C device tai 0x57! Error=%u\n",
            pingError
        );


        Serial.println(
            "[ERR] Kiem tra lai VCC, GND, SDA=21, SCL=22."
        );


        while (1)
        {
            delay(1000);
        }
    }


    Serial.println(
        "[OK] I2C device 0x57 ACK."
    );


    /* =====================================================
     * INIT MAX30102
     * ===================================================== */

    if (!MAX30102_Init())
    {
        Serial.println(
            "[ERR] Khoi tao MAX30102 that bai!"
        );


        while (1)
        {
            delay(1000);
        }
    }


    Serial.println(
        "[OK] Khoi tao MAX30102 thanh cong!"
    );


    /* =====================================================
     * ATTACH INTERRUPT
     * ===================================================== */

    attachInterrupt(
        digitalPinToInterrupt(INT_PIN),
        MAX30102_ISR,
        FALLING
    );


    /*
     * Tránh trường hợp INT đã LOW
     * trước khi attachInterrupt().
     *
     * Clear trạng thái cũ để INT về HIGH,
     * sample tiếp theo sẽ tạo FALLING mới.
     */
    if (!MAX30102_ClearInterrupt())
    {
        detachInterrupt(digitalPinToInterrupt(INT_PIN));
        Serial.println("[ERR] Clear interrupt failed!");
        return;
    }

    MAX30102_is_ready = false;


    Serial.println(
        "[OK] Interrupt attached!"
    );


    Serial.println(
        "RED,IR"
    );
}


/* =========================================================
 * TEST LOOP
 *
 * VẪN NẰM TRONG LIB.
 * ========================================================= */

void MAX30102_TestLoop(void)
{
    int32_t heartRate = -999;
    int8_t validHeartRate = 0;

    int32_t spo2 = -999;
    int8_t validSpO2 = 0;
    bool fingerDetected = false;


    bool success = MAX30102_GetHeartRateSpO2(
        &heartRate,
        &validHeartRate,
        &spo2,
        &validSpO2,
        &fingerDetected
    );


    Serial.println(
        "--------------------------"
    );


    if (!success)
    {
        Serial.println(
            fingerDetected
                ? "Dang thu thap du lieu..."
                : "Khong phat hien ngon tay"
        );
        return;
    }


    Serial.print("Heart Rate: ");

    if (validHeartRate)
    {
        Serial.print(heartRate);
        Serial.println(" BPM");
    }
    else
    {
        Serial.println("Invalid");
    }


    Serial.print("SpO2      : ");

    if (validSpO2)
    {
        Serial.print(spo2);
        Serial.println(" %");
    }
    else
    {
        Serial.println("Invalid");
    }
}

bool MAX30102_GetHeartRateSpO2(
    int32_t *heartRate,
    int8_t *validHeartRate,
    int32_t *spo2,
    int8_t *validSpO2,
    bool *fingerDetected
)
{
    if (
        heartRate == nullptr ||
        validHeartRate == nullptr ||
        spo2 == nullptr ||
        validSpO2 == nullptr ||
        fingerDetected == nullptr
    )
    {
        return false;
    }

#if SENSOR_TIMING_DEBUG
    MAX30102_timingProfile = {};
#endif

    *heartRate = -999;
    *validHeartRate = 0;
    *spo2 = -999;
    *validSpO2 = 0;
    *fingerDetected = true;

    int32_t calculatedHeartRate = -999;
    int8_t calculatedValidHeartRate = 0;
    int32_t calculatedSpO2 = -999;
    int8_t calculatedValidSpO2 = 0;
    uint32_t red;
    uint32_t ir;


    /* =========================================
     * LẦN ĐẦU: THU 100 MẪU
     * ========================================= */
    if (!MAX30102_bufferReady)
    {
#if SENSOR_TIMING_DEBUG
        int64_t initialSampleStartUs = esp_timer_get_time();
#endif
        uint16_t index = 0;
        uint32_t waitStart = millis();


        while (index < MAX30102_BUFFER_SIZE)
        {
            /*
             * Chờ interrupt báo có dữ liệu.
             */
            if (!MAX30102_is_ready)
            {
                if ((millis() - waitStart) >= MAX30102_SAMPLE_TIMEOUT_MS)
                {
                    return false;
                }


                delay(1);
                continue;
            }


#if SENSOR_TIMING_DEBUG
            int64_t mutexWaitStartUs = esp_timer_get_time();
#endif
            if (!MAX30102_LockI2C())
            {
                return false;
            }
#if SENSOR_TIMING_DEBUG
            MAX30102_timingProfile.mutexWaitUs +=
                esp_timer_get_time() - mutexWaitStartUs;
            int64_t fifoStartUs = esp_timer_get_time();
#endif


            MAX30102_is_ready = false;

            if (!MAX30102_ClearInterrupt())
            {
                MAX30102_UnlockI2C();
                return false;
            }


            /*
             * Đọc hết sample hiện có trong FIFO.
             */
            while (
                MAX30102_ReadFIFO(&red, &ir) &&
                index < MAX30102_BUFFER_SIZE
            )
            {
                if (!MAX30102_IsFingerDetected(ir))
                {
                    *fingerDetected = false;
                    MAX30102_bufferReady = false;
                    MAX30102_UnlockI2C();
                    return false;
                }

                MAX30102_redBuffer[index] = red;
                MAX30102_irBuffer[index]  = ir;

                index++;
            }


            MAX30102_UnlockI2C();
#if SENSOR_TIMING_DEBUG
            MAX30102_timingProfile.fifoUs +=
                esp_timer_get_time() - fifoStartUs;
#endif
        }


        MAX30102_bufferReady = true;
#if DEBUG_MAX30102_PEAK
        MAX30102_debugSession++;
        MAX30102_debugSessionWindow = 0;
#endif
#if SENSOR_TIMING_DEBUG
        MAX30102_timingProfile.sampleUs +=
            esp_timer_get_time() - initialSampleStartUs;
#endif
    }


    /* =========================================
     * TÍNH HR + SPO2
     * ========================================= */
    maxim_heart_rate_and_oxygen_saturation(
        MAX30102_irBuffer,
        MAX30102_BUFFER_SIZE,

        MAX30102_redBuffer,

        &calculatedSpO2,
        &calculatedValidSpO2,

        &calculatedHeartRate,
        &calculatedValidHeartRate
    );

    MAX30102_ApplyPhysiologicalSanityCheck(
        &calculatedHeartRate,
        &calculatedValidHeartRate,
        &calculatedSpO2,
        &calculatedValidSpO2
    );


    /* =========================================
     * GIỮ LẠI 75 MẪU CŨ
     * ========================================= */
    for (
        uint16_t i = MAX30102_NEW_SAMPLES;
        i < MAX30102_BUFFER_SIZE;
        i++
    )
    {
        MAX30102_redBuffer[
            i - MAX30102_NEW_SAMPLES
        ] = MAX30102_redBuffer[i];


        MAX30102_irBuffer[
            i - MAX30102_NEW_SAMPLES
        ] = MAX30102_irBuffer[i];
    }


    /* =========================================
     * THU THÊM 25 MẪU MỚI
     * ========================================= */
    uint16_t index =
        MAX30102_BUFFER_SIZE -
        MAX30102_NEW_SAMPLES;
    uint32_t waitStart = millis();
#if SENSOR_TIMING_DEBUG
    int64_t newSampleStartUs = esp_timer_get_time();
#endif


    while (index < MAX30102_BUFFER_SIZE)
    {
        if (!MAX30102_is_ready)
        {
            if ((millis() - waitStart) >= MAX30102_SAMPLE_TIMEOUT_MS)
            {
                MAX30102_bufferReady = false;
                return false;
            }


            delay(1);
            continue;
        }


#if SENSOR_TIMING_DEBUG
        int64_t mutexWaitStartUs = esp_timer_get_time();
#endif
        if (!MAX30102_LockI2C())
        {
            MAX30102_bufferReady = false;
            return false;
        }
#if SENSOR_TIMING_DEBUG
        MAX30102_timingProfile.mutexWaitUs +=
            esp_timer_get_time() - mutexWaitStartUs;
        int64_t fifoStartUs = esp_timer_get_time();
#endif


        MAX30102_is_ready = false;

        if (!MAX30102_ClearInterrupt())
        {
            MAX30102_UnlockI2C();
            MAX30102_bufferReady = false;
            return false;
        }


        while (
            MAX30102_ReadFIFO(&red, &ir) &&
            index < MAX30102_BUFFER_SIZE
        )
        {
            if (!MAX30102_IsFingerDetected(ir))
            {
                *fingerDetected = false;
                MAX30102_bufferReady = false;
                MAX30102_UnlockI2C();
                return false;
            }

            MAX30102_redBuffer[index] = red;
            MAX30102_irBuffer[index]  = ir;

            index++;
        }


        MAX30102_UnlockI2C();
#if SENSOR_TIMING_DEBUG
        MAX30102_timingProfile.fifoUs +=
            esp_timer_get_time() - fifoStartUs;
#endif
    }

#if SENSOR_TIMING_DEBUG
    MAX30102_timingProfile.sampleUs +=
        esp_timer_get_time() - newSampleStartUs;
#endif


    *heartRate = calculatedHeartRate;
    *validHeartRate = calculatedValidHeartRate;
    *spo2 = calculatedSpO2;
    *validSpO2 = calculatedValidSpO2;

    return true;
}
