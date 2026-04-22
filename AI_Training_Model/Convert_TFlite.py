import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import tensorflow as tf
import numpy as np

print("--- BẮT ĐẦU QUÁ TRÌNH ÉP CÂN (QUANTIZATION) ---")

# 1. Load lại mô hình đã train ngon lành và dữ liệu để làm mẫu
model = tf.keras.models.load_model("best_model.keras")
X_train = np.load("X_train.npy")

# 2. Cài đặt công cụ chuyển đổi sang TFLite
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]

# 3. Cung cấp dữ liệu đại diện để "cân chỉnh" thước đo INT8
def representative_data_gen():
    # Lấy 200 mẫu đầu tiên để AI đo đạc biên độ
    for i in range(min(200, len(X_train))):
        sample = X_train[i:i+1].astype(np.float32)
        yield [sample]

converter.representative_dataset = representative_data_gen

# 4. Ép buộc mọi thứ (Input, Ops, Output) về số nguyên 8-bit (INT8)
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type  = tf.int8
converter.inference_output_type = tf.int8

# 5. Tiến hành nén
tflite_model = converter.convert()

# Lưu file .tflite để backup
with open("asthma_model.tflite", "wb") as f:
    f.write(tflite_model)

size_kb = len(tflite_model) / 1024
print(f"=> Đã nén thành Model INT8: {size_kb:.1f} KB")

# 6. Dịch ra mã C++ (Mảng Hex) để nạp thẳng vào ESP32
print("\n--- XUẤT FILE C++ ---")
with open("asthma_model.h", "w") as f:
    f.write("// Auto-generated model by NgocChien VT01\n")
    f.write(f"const unsigned int model_len = {len(tflite_model)};\n")
    # alignas(8) cực kỳ quan trọng cho ESP32
    f.write("alignas(8) const unsigned char asthma_model[] = {\n  ")
    f.write(", ".join(f"0x{b:02x}" for b in tflite_model))
    f.write("\n};\n")

print("=> HOÀN TẤT! Đã sinh ra file 'asthma_model.h'.")