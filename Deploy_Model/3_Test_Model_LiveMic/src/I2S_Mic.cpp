#include "Audio_IO/I2S_Mic.h"
#include <string.h>

// ---------------------------------------------------------- //

// Thay lần lượt loạt mẫu sau được kết quả như sau
// Được chia làm 3 giai đoạn do quá trình phát sinh
// Xem kết quả interface ở log/s
/* // Phase 1
#include "Raw_Include_Phase_1/Raw_Asthma_Audio_1.h" // Limited
#include "Raw_Include_Phase_1/Raw_Asthma_Audio_2.h" // Limited
#include "Raw_Include_Phase_1/Raw_Asthma_Audio_3.h" // White Noise + Asthma
#include "Raw_Include_Phase_1/Raw_Asthma_Audio_4.h" // Silent + Asthma
#include "Raw_Include_Phase_1/Raw_Non_Asthma_Audio_1.h" // COPD 1
#include "Raw_Include_Phase_1/Raw_Non_Asthma_Audio_2.h" // COPD 2
#include "Raw_Include_Phase_1/Raw_Non_Asthma_Audio_3.h" // Bronchial
#include "Raw_Include_Phase_1/Raw_Non_Asthma_Audio_4.h" // Silent
*/

/* // Phase 2
#include "Raw_Include_Phase_2/Raw_Asthma_Audio_1.h" // Quạt + Asthma
#include "Raw_Include_Phase_2/Raw_Asthma_Audio_2.h" // Limited
#include "Raw_Include_Phase_2/Raw_Asthma_Audio_3.h" // White Noise + Asthma
#include "Raw_Include_Phase_2/Raw_Asthma_Audio_4.h" // Silent + Asthma
#include "Raw_Include_Phase_2/Raw_Non_Asthma_Audio_1.h" // COPD 1
#include "Raw_Include_Phase_2/Raw_Non_Asthma_Audio_2.h" // Tiếng podcast môi trường
#include "Raw_Include_Phase_2/Raw_Non_Asthma_Audio_3.h" // Pneumonia
#include "Raw_Include_Phase_2/Raw_Non_Asthma_Audio_4.h" // Silent
*/
 // Phase 3 
#include "Raw_Include_Phase_3/Raw_Asthma_Audio_1.h" // Quạt + Phím + Asthma
#include "Raw_Include_Phase_3/Raw_Asthma_Audio_2.h" // Tiếng đọc Podcast + Asthma
#include "Raw_Include_Phase_3/Raw_Asthma_Audio_3.h" // White Noise + Asthma
#include "Raw_Include_Phase_3/Raw_Asthma_Audio_4.h" // Pitch: Đổi cao độ nhịp thở gốc
#include "Raw_Include_Phase_3/Raw_Asthma_Audio_5.h" // Kéo giãn hoặc nén time
#include "Raw_Include_Phase_3/Raw_Asthma_Audio_6.h" // Dịch khung time 
#include "Raw_Include_Phase_3/Raw_Asthma_Audio_7.h" // Real từ Kaggle

#include "Raw_Include_Phase_3/Raw_Non_Asthma_Audio_1.h" // Bronchial
#include "Raw_Include_Phase_3/Raw_Non_Asthma_Audio_2.h" // COPD
#include "Raw_Include_Phase_3/Raw_Non_Asthma_Audio_3.h" // Healthy
#include "Raw_Include_Phase_3/Raw_Non_Asthma_Audio_4.h" // Pneumonia
#include "Raw_Include_Phase_3/Raw_Non_Asthma_Audio_5.h" // Im lặng
#include "Raw_Include_Phase_3/Raw_Non_Asthma_Audio_6.h" // Podcast
#include "Raw_Include_Phase_3/Raw_Non_Asthma_Audio_7.h" // Quạt/Phím
// ---------------------------------------------------------- //


#define Total_Samples 80000 // 5s cho 16 kHz
#define Val_Threshold 5000

#define Vote_Round 3 // Đo 3 lần ms ra quyết định
static uint8_t vote_asthma_count = 0;
static uint8_t vote_normal_count = 0;
static uint8_t vote_unsure_count = 0;
static uint8_t current_vote_round = 0;

// ==== THỐNG KÊ TỔNG (không reset theo vòng đo, chạy suốt phiên hoạt động) ====
static uint32_t total_tests = 0;
static uint32_t total_asthma_alerts = 0;

// System_State curr_state = STATE_LISTENING;

// ***** Khi test file Asthma Raw
// Thay biến trạng thái như sau
System_State curr_state = STATE_RECORDING;

int16_t* audio_buffer = nullptr;
float* audio_float_buff = nullptr;
int sample_cnt = 0;

uint8_t warmup_chunk = 100;

static float mel_power_buff[N_MELS][MAX_FRAMES];
static float mel_db_buff[N_MELS][MAX_FRAMES];

static int chkpnt = 1;

void Process_Audio_Stream(void){
    // 1. Đọc 256 mẫu thô từ DMA
    int32_t raw_samples[Buffer_Samples];
    size_t bytes_read = 0;

    i2s_read(I2S_Port, raw_samples, sizeof(int32_t) * Buffer_Samples, &bytes_read, portMAX_DELAY);
    int samples_read = bytes_read / sizeof(int32_t);

    if (samples_read == 0) return; 

    // 2. Chuyển đổi về PCM 16-bit chuẩn
    int16_t chunk[Buffer_Samples];
    for (int i = 0; i < samples_read; i++) {
        int32_t amplified = (raw_samples[i] >> 16) * Amplify_Factor;
        
        if(amplified > 32767) amplified = 32767;
        if(amplified < -32768) amplified = -32768;

        chunk[i] = (int16_t)amplified;
    }

    // 3. Chuyển đổi trạng thái
    if(curr_state == STATE_LISTENING){
        // Tính năng lượng WAV của 256 mẫu hiện tại
        uint32_t sum_energy = 0;
        for(int i = 0 ; i < samples_read ; i++){
            sum_energy += abs(chunk[i]);
        } 
        uint32_t avg_enegry = sum_energy / samples_read;

        if(avg_enegry > Val_Threshold){
            Serial.printf("[VAD] Phát hiện tiếng động! - Năng lượng: %d\n", avg_enegry);
            Serial.println("Bắt đầu ghi !!");
            curr_state = STATE_RECORDING;
            sample_cnt = 0;

            // Nhét luôn chukn vào kẻo lỡ mất dữ liệu đầu
            for(int i = 0 ; i < samples_read ; i++){
                audio_buffer[sample_cnt] = chunk[i];
                sample_cnt++;
            }
        } 

    } else if(curr_state == STATE_RECORDING){
        // ******** Khi test vs file Asthma Raw
        // Note đoạn này đến ---
               // Nạp đủ mẫu
        for(int i = 0 ; i < samples_read ; i++){
            if(sample_cnt < Total_Samples){
                audio_buffer[sample_cnt] = chunk[i];
                sample_cnt++;
            }
        }

        if (sample_cnt >= Total_Samples) {
            Serial.println("[MIC] Đã thu đủ 5 giây âm thanh! Chuyển sang AI ...");
            curr_state = STATE_PROCESSING;
        }
            // --- đoạn này
        
        
        /*
        Serial.println("[*] BYPASS MODE: Đang nạp dữ liệu Asthma giả lập...");

        if(chkpnt > 8) chkpnt = 1;
        
        // TEST PHASE 2
        if (chkpnt == 1) {
            memcpy(audio_buffer, raw_asthma_audio_1, sizeof(raw_asthma_audio_1));
        } else if (chkpnt == 2) {
            memcpy(audio_buffer, raw_asthma_audio_2, sizeof(raw_asthma_audio_2));
        } else if (chkpnt == 3) {
            memcpy(audio_buffer, raw_asthma_audio_3, sizeof(raw_asthma_audio_3));
        } else if (chkpnt == 4) {
            memcpy(audio_buffer, raw_asthma_audio_4, sizeof(raw_asthma_audio_4));
        } else if (chkpnt == 5) {
            memcpy(audio_buffer, raw_non_asthma_audio_1, sizeof(raw_non_asthma_audio_1));
        } else if (chkpnt == 6) {
            memcpy(audio_buffer, raw_non_asthma_audio_2, sizeof(raw_non_asthma_audio_2));
        } else if (chkpnt == 7) {
            memcpy(audio_buffer, raw_non_asthma_audio_3, sizeof(raw_non_asthma_audio_3));
        } else if (chkpnt == 8) {
            memcpy(audio_buffer, raw_non_asthma_audio_4, sizeof(raw_non_asthma_audio_4));
        }
        */

        /*
        if(chkpnt > 14) chkpnt = 1;

        if (chkpnt == 1) {
            Serial.printf("-> Đến mẫu thứ %d\n", chkpnt);
            memcpy(audio_buffer, raw_asthma_audio_1, sizeof(raw_asthma_audio_1));
        } else if (chkpnt == 2) {
            Serial.printf("-> Đến mẫu thứ %d\n", chkpnt);
            memcpy(audio_buffer, raw_asthma_audio_2, sizeof(raw_asthma_audio_2));
        } else if (chkpnt == 3) {
            Serial.printf("-> Đến mẫu thứ %d\n", chkpnt);
            memcpy(audio_buffer, raw_asthma_audio_3, sizeof(raw_asthma_audio_3));
        } else if (chkpnt == 4) {
            Serial.printf("-> Đến mẫu thứ %d\n", chkpnt);
            memcpy(audio_buffer, raw_asthma_audio_4, sizeof(raw_asthma_audio_4));
        } else if (chkpnt == 5) {
            Serial.printf("-> Đến mẫu thứ %d\n", chkpnt);
            memcpy(audio_buffer, raw_asthma_audio_5, sizeof(raw_asthma_audio_5));
        } else if (chkpnt == 6) {
            Serial.printf("-> Đến mẫu thứ %d\n", chkpnt);
            memcpy(audio_buffer, raw_asthma_audio_6, sizeof(raw_asthma_audio_6));
        } else if (chkpnt == 7) {
            Serial.printf("-> Đến mẫu thứ %d\n", chkpnt);
            memcpy(audio_buffer, raw_asthma_audio_7, sizeof(raw_asthma_audio_7));
        } else if (chkpnt == 8) {
            Serial.printf("-> Đến mẫu thứ %d\n", chkpnt);
            memcpy(audio_buffer, raw_non_asthma_audio_1, sizeof(raw_non_asthma_audio_1));
        } else if (chkpnt == 9) {
            Serial.printf("-> Đến mẫu thứ %d\n", chkpnt);
            memcpy(audio_buffer, raw_non_asthma_audio_2, sizeof(raw_non_asthma_audio_2));
        } else if (chkpnt == 10) {
            Serial.printf("-> Đến mẫu thứ %d\n", chkpnt);
            memcpy(audio_buffer, raw_non_asthma_audio_3, sizeof(raw_non_asthma_audio_3));
        } else if (chkpnt == 11) {
            Serial.printf("-> Đến mẫu thứ %d\n", chkpnt);
            memcpy(audio_buffer, raw_non_asthma_audio_4, sizeof(raw_non_asthma_audio_4));
        } else if (chkpnt == 12) {
            Serial.printf("-> Đến mẫu thứ %d\n", chkpnt);
            memcpy(audio_buffer, raw_non_asthma_audio_5, sizeof(raw_non_asthma_audio_5));
        } else if (chkpnt == 13) {
            Serial.printf("-> Đến mẫu thứ %d\n", chkpnt);
            memcpy(audio_buffer, raw_non_asthma_audio_6, sizeof(raw_non_asthma_audio_6));
        } else if (chkpnt == 14) {
            Serial.printf("-> Đến mẫu thứ %d\n", chkpnt);
            memcpy(audio_buffer, raw_non_asthma_audio_7, sizeof(raw_non_asthma_audio_7));
        }


        chkpnt++;

        // Ép hệ thống tin rằng đã thu âm xong đủ 5s
        Serial.println("[*] Đã nạp xong 80,000 mẫu. Chuyển sang xử lý DSP & AI...");
        
        // Chuyển state sang bước tính toán Mel-Spectrogram / Inference
        curr_state = STATE_PROCESSING;
        */

    } else if(curr_state == STATE_PROCESSING){
        Serial.println("\n--- BẮT ĐẦU TIỀN XỬ LÝ ---\n");

        // 1. Chuẩn hóa về [-1, 1] TRƯỚC (int16 -> float)
        Normalize_To_Float(audio_buffer, audio_float_buff, Total_Samples);
        Serial.println("1. Hoàn thành chuẩn hóa về Float [-1.0, 1.0]");

        // 2. Reset + Lọc Butterworth TRÊN FLOAT
        Butterworth_Reset();
        Butterworth_Process_Buffer(audio_float_buff, Total_Samples);   
        Serial.println("2. Hoàn thành bộ lọc Butterworth.");

        // 3. Pre-emphasis TRÊN FLOAT
        Apply_Pre_Emphasis(audio_float_buff, Total_Samples);            
        Serial.println("3. Hoàn thành bộ lọc Pre-Emphasis.");

        // 4. Chạy STFT và năng lượng Mel
        int num_frames = Compute_Mel_Power_Spectrogram(
            audio_float_buff, Total_Samples, 
            mel_power_buff, 129
        );
        Serial.println("4. Hoàn thành trích xuất năng lượng Mel.");

        // 5. Chuyển đổi sang đơn vị dB
        Power_To_dB_RefMax(mel_power_buff, mel_db_buff, num_frames);
        Serial.println("5. Hoàn thành ma trận Mel-Spectrogram dB!");
        Serial.println("------------------------------");

        //
        Serial.println("[DEBUG] mel_db_buff frame 0, 10 gia tri mel dau:");
        for (int m = 0; m < 10; m++) {
            Serial.printf("%.4f ", mel_db_buff[m][0]);
        }
        Serial.println();
        
        Serial.println("[DEBUG] mel_db_buff FRAME 64, 10 gia tri mel dau:");
        for (int m = 0; m < 10; m++) Serial.printf("%.4f ", mel_db_buff[m][64]);
        Serial.println();

        curr_state = STATE_INTERFACE;

    } else if(curr_state == STATE_INTERFACE){
        Asthma_Result result = Run_Asthma_Interface(mel_db_buff);
    
        // Đếm vote
        if (result.Predicted_Class == 0) vote_asthma_count++;
        else if (result.Predicted_Class == 1) vote_normal_count++;
        else vote_unsure_count++;
        
        current_vote_round++;
        
        Serial.printf("[VOTE] Lan %d/%d - Asthma:%d Normal:%d Unsure:%d\n",
            current_vote_round, Vote_Round, vote_asthma_count, vote_normal_count, vote_unsure_count);

        if (current_vote_round >= Vote_Round) {
            // Đủ 3 lần -> đưa ra kết luận cuối
            Serial.println("\n========== KẾT LUẬN SAU 3 LẦN ĐO ==========");
            if (vote_asthma_count > vote_normal_count) {
                Serial.println(">>> KẾT LUẬN CUỐI: CẢNH BÁO HEN SUYỄN");
            } else if (vote_normal_count > vote_asthma_count) {
                Serial.println(">>> KẾT LUẬN CUỐI: BÌNH THƯỜNG");
            } else {
                Serial.println(">>> KẾT LUẬN CUỐI: KHÔNG CHẮC CHẮN, ĐỀ NGHỊ ĐO LẠI");
            }
            Serial.println("=============================================\n");

            // Reset để bắt đầu vòng đo mới
            vote_asthma_count = 0;
            vote_normal_count = 0;
            vote_unsure_count = 0;
            current_vote_round = 0;
        }

        // ==== THÊM: cộng dồn thống kê ====
        total_tests++;
        if (result.Predicted_Class == 0) total_asthma_alerts++;

        if (total_tests % 10 == 0) {   // cứ mỗi 10 lần đo thì in ra 1 lần
            Serial.printf("[THONG KE] Tong %lu lan do, %lu lan bao Asthma (%.1f%%)\n",
                total_tests, total_asthma_alerts,
                (float)total_asthma_alerts / total_tests * 100.0f);
        }

        curr_state = STATE_LISTENING;
        sample_cnt = 0;
        Serial.println("\n[CAI DAT] HE THONG SAN SANG! Dang lang nghe...");

    }
}

void I2S_Mic_Init(int SCK_Pin, int WS_Pin, int SD_Pin){
    // Cấp phát bộ nhớ
    audio_buffer = (int16_t*)heap_caps_malloc(
        Total_Samples * sizeof(int16_t),
        MALLOC_CAP_SPIRAM
    );
    audio_float_buff = (float*)heap_caps_malloc(
        Total_Samples * sizeof(float),
        MALLOC_CAP_SPIRAM
    );

    if (audio_buffer == nullptr || audio_float_buff == nullptr) {
        Serial.println("[LỖI CRITICAL] Không đủ PSRAM để cấp phát mảng âm thanh!");
        while(1); // Treo mạch ở đây luôn để dễ debug
    }

    const i2s_config_t i2s_config = {
        .mode = i2s_mode_t(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = (uint32_t)Sample_Rate,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_RIGHT,
        .communication_format = i2s_comm_format_t(I2S_COMM_FORMAT_STAND_I2S),
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,
        .dma_buf_len = Buffer_Samples,
        .use_apll = false,
        .tx_desc_auto_clear = false,
        .fixed_mclk = 0 
    };

    const i2s_pin_config_t pin_config = {
        .bck_io_num = SCK_Pin,
        .ws_io_num = WS_Pin,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num = SD_Pin
    };

    i2s_driver_install(I2S_Port, &i2s_config, 0, NULL);
    i2s_set_pin(I2S_Port, &pin_config);
}
