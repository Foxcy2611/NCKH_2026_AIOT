"""
=========================================================
7. LƯỢNG TỬ HÓA (QUANTIZATION) & XUẤT C ARRAY
- Tải mô hình .keras
- Dùng Representative Dataset ép chuẩn về Int8
- Chuyển đổi thành TensorFlow Lite (.tflite)
- Dịch file .tflite thành mảng C/C++ (.h) cho TinyML
=========================================================
"""
import os
import numpy as np
import tensorflow as tf

# === Link dẫn file ===
Dir_Features  = "Training_Model_Phase_2/5_Output_Features"
Dir_Out_Model = "Training_Model_Phase_2/6_Output_Model"

Dir_TFLite    = "Training_Model_Phase_2/7_Output_TFLite"

os.makedirs(Dir_TFLite, exist_ok=True)

# Hàm đọc file .tflite và ghi ra mảng C/C++ Header
def Convert_to_C_Array(tflite_path, c_file_path):
    with open(tflite_path, "rb") as f:
        bytedata = f.read()

    hex_array = ""
    for i, b in enumerate(bytedata):
        hex_array += f"0x{b:02x}, "
        if (i + 1) % 12 == 0:
            hex_array += "\n        "
            
    print("\n=== 4. TẠO FILE HEADER (.h) ===")
    
    header_content = f"""#ifndef ASTHMA_MODEL_H
#define ASTHMA_MODEL_H

// Kich thuoc model: {len(bytedata)} bytes
const int model_data_len = {len(bytedata)};

const unsigned char model_data[] __attribute__((aligned(4))) = {{
        {hex_array}
}};

#endif // ASTHMA_MODEL_H
"""

    with open(c_file_path, "w") as f:
        f.write(header_content)
    print(f"-> Đã xuất mảng C array tại: {c_file_path}")

# MAIN
def main():
    print("1. TẢI MÔ HÌNH VÀ DỮ LIỆU ĐẠI DIỆN...")

    model_path = os.path.join(Dir_Out_Model, "Bin_Asthma.keras")
    model = tf.keras.models.load_model(model_path)

    # Load dữ liệu tập chia để làm thước đo
    X_train = np.load(os.path.join(Dir_Features, "X_data_mel.npy"))
    Y_labels = np.load(os.path.join(Dir_Features, "Y_labels_mel.npy")) # Ms thêm

    # Normalize về [0 1] vì các giá trị dB đều -80 < đvi <= 0
    X_min = np.min(X_train)
    X_max = np.max(X_train)
    X_train = (X_train - X_min) / (X_max - X_min)

    # Đưa về dtype float32 để TFLite đọc được
    X_train = X_train.astype(np.float32)

    # ==== SỬA: Lấy đều cả 2 lớp, xáo trộn ngẫu nhiên ====
    np.random.seed(42)
    idx_class0 = np.where(Y_labels == 0)[0]   # tất cả index của Asthma
    idx_class1 = np.where(Y_labels == 1)[0]   # tất cả index của Non-Asthma

    # Lấy 50 mẫu ngẫu nhiên từ mỗi lớp, tổng 100 mẫu cân bằng
    sample_idx = np.concatenate([
        np.random.choice(idx_class0, 50, replace=False),
        np.random.choice(idx_class1, 50, replace=False)
    ])
    np.random.shuffle(sample_idx)   # xáo trộn để tránh thứ tự theo khối

    # Hàm tạo gen làm thước đo
    def Rep_Data_Gen():
        for i in sample_idx:
            yield [X_train[i:i+1]]
            
    print("\n2. CẤU HÌNH CONVERTER (INT8)...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = Rep_Data_Gen
    
    # Bắt buộc thuật toán ép toán bộ phép tính về Int8
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    # Bắt buộc Inp/Out là INT8
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8

    print("\n3. TIẾN HÀNH ÉP CÂN (QUANTIZATION)...")
    tflite_model = converter.convert()
    
    tflite_path = os.path.join(Dir_TFLite, "Asthma_Model_Int8.tflite")
    with open(tflite_path, "wb") as f:
        f.write(tflite_model)
        
    c_file_path = os.path.join(Dir_TFLite, "Asthma_Model.h")
    Convert_to_C_Array(tflite_path, c_file_path)

    print("\n=== 5. BÁO CÁO ÉP CÂN ===")
    keras_size = os.path.getsize(model_path)
    tflite_size = os.path.getsize(tflite_path)
    
    print(f"Dung lượng file gốc (.keras):   {keras_size} Bytes")
    print(f"Dung lượng file nén (.tflite):  {tflite_size} Bytes")
    print(f"Tỷ lệ nén: Giảm {100 - (tflite_size/keras_size)*100:.1f}% dung lượng!")

if __name__ == "__main__":
    main()