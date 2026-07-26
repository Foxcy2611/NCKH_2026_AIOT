"""
=========================================================
12. BÀI KIỂM TRA TFLITE INT8 VỚI TÁC NHÂN RANDOM
Mục đích đảm bảo mô hình INT8 sau lượng tử hoạt động tốt
với các test mẫu ngẫu nhiên mô phỏng dataset thật
=========================================================
"""

import tensorflow as tf
import numpy as np

# Load model TFLITE INT8
interpreter = tf.lite.Interpreter(model_path="Training_Model_Phase_2/7_Output_TFLite/Asthma_Model_Int8.tflite")
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

print("Input details:", input_details)
print("Output details:", output_details)

# ==== Test với random input để xem model có "sống" hay không ====
np.random.seed(1)
random_input = np.random.randint(-128, 127, size=input_details[0]['shape'], dtype=np.int8)
interpreter.set_tensor(input_details[0]['index'], random_input)
interpreter.invoke()
print("Output voi input NGAU NHIEN:", interpreter.get_tensor(output_details[0]['index']))

# ==== Test với toàn bộ giá trị = -128 (giống dữ liệu "im lặng tuyệt đối") ====
silence_input = np.full(input_details[0]['shape'], -128, dtype=np.int8)
interpreter.set_tensor(input_details[0]['index'], silence_input)
interpreter.invoke()
print("Output voi TOAN BO -128:", interpreter.get_tensor(output_details[0]['index']))

# ==== Test với toàn bộ giá trị = 127 ====
max_input = np.full(input_details[0]['shape'], 127, dtype=np.int8)
interpreter.set_tensor(input_details[0]['index'], max_input)
interpreter.invoke()
print("Output voi TOAN BO 127:", interpreter.get_tensor(output_details[0]['index']))

"""
Output voi input NGAU NHIEN: [[127]]
Output voi TOAN BO -128: [[0]]
Output voi TOAN BO 127: [[127]]

"""