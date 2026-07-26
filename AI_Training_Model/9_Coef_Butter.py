"""
=========================================================
9. TRÍCH XUẤT HỆ SỐ
- Lấy các hệ số của bộ lọc Butterworth
- Làm nguyên liệu cho quá trình xây dựng tiền xử lý bằng C++
=========================================================
"""


from scipy.signal import butter

def Butter_Bandpass_SOS(lowcut, highcut, fs, order):
    nyq = 0.5 * fs
    sos = butter(order, [lowcut/nyq, highcut/nyq], btype='band', output='sos')
    return sos

sos = Butter_Bandpass_SOS(100, 2000, 16000, 5)
print("Số sections:", sos.shape[0])
print(repr(sos))