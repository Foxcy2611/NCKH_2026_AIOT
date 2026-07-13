import scipy.signal as signal

def generate_cpp_coefficients(lowcut, highcut, fs, order):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    # Lấy hệ số
    b, a = signal.butter(order, [low, high], btype='band')
    
    # In ra định dạng mảng C++
    print(f"const float b[{len(b)}] = {{ {', '.join([f'{x:.8f}f' for x in b])} }};")
    print(f"const float a[{len(a)}] = {{ {', '.join([f'{x:.8f}f' for x in a])} }};")

# Chạy thử với dải 100Hz - 2000Hz, Sample Rate 16kHz, Bậc 5
generate_cpp_coefficients(100, 2000, 16000, 5)