"""
=========================================================
13. BÀI KIỂM TRA TFLITE INT8 VỚI TÁC NHÂN THẬT
- Tương tự script 12 nhưng test với các mẫu dataset sau khi
chúng đi qua tiền xử bằng python
- Mục đích các mẫu dataset đi đúng quy trình và model nhận
diện chuẩn để làm bàn so sánh vs các thuật toán deploy C++
=========================================================
"""

import tensorflow as tf
import numpy as np
import librosa
from scipy.signal import butter, lfilter

Sr = 16000
Samples = 80000
Low_Cut, High_Cut, Order = 100.0, 2000.0, 5
Pre_Coef = 0.97
N_Mels, Hop_Length, N_FFT = 64, 625, 1024

def Butter_Bandpass(lowcut, highcut, fs, order):
    nyq = 0.5 * fs
    b, a = butter(order, [lowcut/nyq, highcut/nyq], btype='band')
    return b, a

def Pre_Emphasis(signal, coef=0.97):
    return np.append(signal[0], signal[1:] - coef * signal[:-1])

def Apply_Bandpass_Filter(data, lowcut, highcut, fs, order):
    b, a = Butter_Bandpass(lowcut, highcut, fs, order)
    return lfilter(b, a, data)

def Process_Audio_File(file_path):
    y, _ = librosa.load(file_path, sr=Sr)
    y = librosa.util.fix_length(y, size=Samples)
    y_norm = librosa.util.normalize(y)
    y_bandpass = Apply_Bandpass_Filter(y_norm, Low_Cut, High_Cut, Sr, Order)
    y_pre = Pre_Emphasis(y_bandpass, Pre_Coef)
    mel_spec = librosa.feature.melspectrogram(
        y=y_pre, sr=Sr, n_fft=N_FFT, hop_length=Hop_Length,
        n_mels=N_Mels, fmin=Low_Cut, fmax=High_Cut
    )
    return librosa.power_to_db(mel_spec, ref=np.max)

# ==== Dùng ĐÚNG global min/max cố định từ lúc train (-80, 0) ====
TRAIN_MIN, TRAIN_MAX = -80.0, 0.0

def To_Int8(mel_db):
    normalized = (mel_db - TRAIN_MIN) / (TRAIN_MAX - TRAIN_MIN)
    normalized = np.clip(normalized, 0, 1)
    return np.clip((normalized * 255.0) - 128.0, -128, 127).astype(np.int8)

interpreter = tf.lite.Interpreter(model_path="Training_Model_Phase_2/7_Output_TFLite/Asthma_Model_Int8.tflite")
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Nhớ thay tên các file nhằm test 
# ==== TEST FILE ASTHMA THẬT ====
mel_asthma = Process_Audio_File("Dataset/0_Asthma/Aug_Fan_Key_gen_0033.wav")
input_asthma = To_Int8(mel_asthma)[np.newaxis, ..., np.newaxis]
interpreter.set_tensor(input_details[0]['index'], input_asthma)
interpreter.invoke()
out_asthma = interpreter.get_tensor(output_details[0]['index'])
print("Output file ASTHMA THAT:", out_asthma)

mel_asthma = Process_Audio_File("Dataset/0_Asthma/Orig_P18WheezingIE_89.wav")
input_asthma = To_Int8(mel_asthma)[np.newaxis, ..., np.newaxis]
interpreter.set_tensor(input_details[0]['index'], input_asthma)
interpreter.invoke()
out_asthma = interpreter.get_tensor(output_details[0]['index'])
print("Output file ASTHMA THAT:", out_asthma)

mel_asthma = Process_Audio_File("Dataset/0_Asthma/Aug_WNoise_gen_0121.wav")
input_asthma = To_Int8(mel_asthma)[np.newaxis, ..., np.newaxis]
interpreter.set_tensor(input_details[0]['index'], input_asthma)
interpreter.invoke()
out_asthma = interpreter.get_tensor(output_details[0]['index'])
print("Output file ASTHMA THAT:", out_asthma)

mel_asthma = Process_Audio_File("Dataset/0_Asthma/Aug_Sil_gen_0242.wav")
input_asthma = To_Int8(mel_asthma)[np.newaxis, ..., np.newaxis]
interpreter.set_tensor(input_details[0]['index'], input_asthma)
interpreter.invoke()
out_asthma = interpreter.get_tensor(output_details[0]['index'])
print("Output file ASTHMA THAT:", out_asthma)


# --------------------------------------------------------- #


# ==== TEST FILE NON-ASTHMA THẬT ====
mel_non = Process_Audio_File("Dataset/1_Non_Asthma/Kaggle_P5COPDMc_40.wav")
input_non = To_Int8(mel_non)[np.newaxis, ..., np.newaxis]
interpreter.set_tensor(input_details[0]['index'], input_non)
interpreter.invoke()
out_non = interpreter.get_tensor(output_details[0]['index'])
print("Output file NON-ASTHMA THAT:", out_non)

mel_non = Process_Audio_File("Dataset/1_Non_Asthma/Noise_postcard_024.wav")
input_non = To_Int8(mel_non)[np.newaxis, ..., np.newaxis]
interpreter.set_tensor(input_details[0]['index'], input_non)
interpreter.invoke()
out_non = interpreter.get_tensor(output_details[0]['index'])
print("Output file NON-ASTHMA THAT:", out_non)

mel_non = Process_Audio_File("Dataset/1_Non_Asthma/Kaggle_P28Pneumonia56Y.wav")
input_non = To_Int8(mel_non)[np.newaxis, ..., np.newaxis]
interpreter.set_tensor(input_details[0]['index'], input_non)
interpreter.invoke()
out_non = interpreter.get_tensor(output_details[0]['index'])
print("Output file NON-ASTHMA THAT:", out_non)

mel_non = Process_Audio_File("Dataset/1_Non_Asthma/Noise_im_lang_013.wav")
input_non = To_Int8(mel_non)[np.newaxis, ..., np.newaxis]
interpreter.set_tensor(input_details[0]['index'], input_non)
interpreter.invoke()
out_non = interpreter.get_tensor(output_details[0]['index'])
print("Output file NON-ASTHMA THAT:", out_non)

"""
Output file ASTHMA THAT: [[-128]]
Output file ASTHMA THAT: [[-128]]
Output file ASTHMA THAT: [[-116]]
Output file ASTHMA THAT: [[-128]]
Output file NON-ASTHMA THAT: [[127]]
Output file NON-ASTHMA THAT: [[127]]
Output file NON-ASTHMA THAT: [[125]]
Output file NON-ASTHMA THAT: [[125]]

=> OK
"""