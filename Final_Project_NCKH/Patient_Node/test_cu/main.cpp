#include <Arduino.h>

#include "State_Machine/state_machine.h"
#include "Audio_IO/I2S_Mic.h"
#include "board_pinout.h"

#include "State_Machine/quality_check.h"

#include "DSP_Preprocessing/DSP_Filter.h"
#include "DSP_Preprocessing/Mel_Scale.h"
#include "Model_AI/Interface_Asthma.h"

static void OnEnter_ManualCheck(void) {
    if (!I2S_RecordSamples()) {
        // Bị SLEEP abort giữa chừng — HandleAbortIfNeeded() bên trong
        // StateMachine_Run() (lần gọi kế tiếp) sẽ tự đưa về STANDBY.
        // Không làm gì thêm ở đây.
        return;
    }

    const int16_t* buffer = I2S_GetRecordedBuffer();
    const uint32_t sample_count = I2S_GetRecordedSampleCount();

    // Chuyển sang PROCESSING TRƯỚC khi chạy Quality/DSP/AI — để mọi nút
    // bấm lỡ tay trong lúc tính toán (dù đồng bộ) bị Handle_Processing
    // ignore đúng theo thiết kế, không lọt vào AUDIO_RESULT sai ngữ cảnh.
    StateMachine_NotifyCaptureDone();

    // TODO(Phase 3 - Audio_Quality): gọi AudioQuality_CheckQuality(buffer,
    // sample_count) ở đây trước khi cho DSP/AI chạy. Nếu FAIL -> gọi
    // StateMachine_SubmitAudioResult(quality, INTERFACE_UNCERTAIN, 0.0f)
    // và return, KHÔNG chạy tiếp xuống dưới.
    Audio_Quality_Metrics_t metrics;
    Audio_Quality_t quality = AudioQuality_Check(buffer, sample_count, &metrics);

    if(quality == AUDIO_INACTIVE){
        Serial.println("[ERR] Audio INPUT quá bé, không hợp lệ !");
        return;
    } else if(quality == AUDIO_TOO_LOUD){
        Serial.println("[ERR] Audio INPUT quá nhiễu, không hợp lệ !");
        return;
    } else if(quality == AUDIO_TOO_WEAK){
        Serial.println("[ERR] Audio INPUT quá yếu, không hợp lệ !");
        return;
    } else {
        Serial.println("[OK] Audio INPUT hợp lệ !!");
    }

    // Buffer trung gian TÁI DÙNG từ Audio_IO (đã cấp phát sẵn trong
    // I2S_Mic_Init) — không cấp phát PSRAM riêng ở đây.
    float* audio_float_buffer = I2S_GetFloatBuffer();
    auto mel_buffer = I2S_GetMelBuffer();

    Normalize_To_Float(const_cast<int16_t*>(buffer), audio_float_buffer, sample_count);
    Butterworth_Reset();
    Butterworth_Process_Buffer(audio_float_buffer, sample_count);
    Apply_Pre_Emphasis(audio_float_buffer, sample_count);

    const int frame_count = Compute_Mel_Power_Spectrogram(
        audio_float_buffer,
        sample_count,
        mel_buffer,
        MAX_FRAMES
    );
    if (frame_count != MAX_FRAMES) {
        Serial.printf("[ERR] So khung Mel=%d, can %d.\n", frame_count, MAX_FRAMES);
        StateMachine_SubmitAudioResult(AUDIO_INACTIVE, INTERFACE_UNCERTAIN, 0.0f);
        return;
    }

    Power_To_dB_RefMax(mel_buffer, mel_buffer, frame_count);

    Asthma_Result result = Run_Asthma_Interface(mel_buffer);
    Interface_TinyML_t classification = (result.Predicted_Class == 0) ? INTERFACE_ASTHMA_LIKE : INTERFACE_NON_ASTHMA;
    const float score = (result.Predicted_Class == 0) ? result.Asthma_Prob : result.Non_Asthma_Prob;

    StateMachine_SubmitAudioResult(AUDIO_OK, classification, score);
}

void setup(void) {
    Serial.begin(115200);
    delay(3000);

    Serial.println("\n=== HỆ THỐNG TINYML HỖ TRỢ SÀNG LỌC ASTHMA ===");
    
    if(!Init_Mel_Filterbank()){
        Serial.println("[ERR] Không khởi tạo được Mel Filterbank !");
        while(1);
    } else {
        Serial.println("--> [STATE] 1.Khởi tạo Mel Filterbank thành công !!");
    }

    if(!Init_Asthma_Model()){
        Serial.println("[ERR] Không khởi tạo được mô hình.");
        while(1);
    } else {
        Serial.println("--> [STATE] 2. Khởi tạo mô hình TFLite thành công !!");
    }

    I2S_Mic_Init(PIN_I2S_SCK, PIN_I2S_WS, PIN_I2S_SD);
    Serial.println("--> [STATE] 3. Khởi tạo Micro thành công !!");

    StateMachine_Init();
    Serial.println("--> [STATE] 4. Khởi tạo STATE MACHINE thành công !!");




    Serial.println("\n=== HỆ THỐNG TINYML ASTHMA SẴN SÀNG ===");
}

void loop(void) {
    static Patient_State_t last_state = STATE_STANDBY;

    // 1. Chạy state machine trước — xử lý abort/transition từ event
    //    của vòng loop trước.
    StateMachine_Run();

    // 2. Phát hiện "vừa mới vào state nào đó" để chạy entry-action
    //    tương ứng — đây là cách duy nhất Audio_IO được gọi, không để
    //    State_Machine tự gọi ngược lại Audio_IO.
    Patient_State_t current = StateMachine_GetCurrentState();
    if (current != last_state) {
        if (current == STATE_MANUAL_CHECK) {
            OnEnter_ManualCheck();
            
            
        } else if(current == STATE_AUTO_MONITOR){
            Process_Audio_Stream();
        }
        // TODO: entry-action cho STATE_AUTO_MONITOR (Phase 7), gọi
        // Process_Audio_Stream() liên tục thay vì 1 lần như Manual Check.

        last_state = current;
    }
}