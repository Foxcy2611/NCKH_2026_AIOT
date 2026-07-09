"""
=========================================================
6. Train Model
Sử dụng kiến trúc mạng DS-CNN
Các ảnh Mel có thang đo dB giá trị âm khá lớn
=> Scale (Chuẩn hóa) về trong khoảng 0 1 cho đẹp
(Còn dùng ReLu)

- Load ma trận 4D (Mel-Spectrogram)
- Chuẩn hóa Min-Max Scaling [0, 1]
- Train mô hình siêu nhẹ (SeparableConv2D)
- Vẽ biểu đồ theo dõi quá trình học
- Xuất file model chuẩn Keras
=========================================================
"""

import os

os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
from keras import models, layers
from sklearn.model_selection import train_test_split

Dir_Features  = "5_Output_Features"
Dir_Out_Model = "6_Output_Model"

Epochs     = 100
Batch_Size = 32

os.makedirs(Dir_Out_Model, exist_ok=True)

# Hàm vẽ biểu đồ Loss và Accuracy sau khi train xong
def Plot_Training_History(history):
    plt.figure(figsize=(12, 5))

    # Biểu đồ Accuracy (Độ chính xác)
    plt.subplot(1, 2, 1)
    plt.plot(
        history.history['accuracy'], 
        label='Train Accuracy', 
        color='blue', 
        linewidth=2
    )
    plt.plot(
        history.history['val_accuracy'], 
        label='Validation Accuracy', 
        color='orange', 
        linewidth=2
    )
    plt.title('Độ chính xác qua các Epoch', fontweight='bold')
    plt.xlabel('Epochs')
    plt.ylabel('Accuracy')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)

    # Biểu đồ Loss (Độ lỗi)
    plt.subplot(1, 2, 2)
    plt.plot(
        history.history['loss'], 
        label='Train Loss', 
        color='red', 
        linewidth=2
    )
    plt.plot(
        history.history['val_loss'], 
        label='Validation Loss', 
        color='green', 
        linewidth=2
    )
    plt.title('Độ suy hao (Loss) qua các Epoch', fontweight='bold')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)

    plt.tight_layout()

    # Lưu biểu đồ vào thư mục Model
    plt.savefig(os.path.join(Dir_Out_Model, 'Training_History.png'), dpi=150)
    print("Đã lưu biểu đồ huấn luyện tại: Training_History.png")
    plt.show()

# Hàm dựng kiến trúc DS-CNN
def Build_and_Compile_Model(input_shape):
    model = models.Sequential([
        layers.Input(shape=input_shape),

        # 1. Trích xuất đặc trưng cơ bản
        layers.SeparableConv2D(
            16, (3, 3),
            activation='relu',
            padding='same'
        ),
        layers.BatchNormalization(),
        layers.MaxPool2D((2, 2)),

        # 2. Đào sâu đặc trưng bệnh lý
        layers.SeparableConv2D(
            32, (3, 3),
            activation='relu',
            padding='same'
        ),
        layers.BatchNormalization(),
        layers.MaxPool2D((2, 2)),

        # 3. Phân tích chi tiết vệt rít
        layers.SeparableConv2D(
            64, (3, 3),
            activation='relu',
            padding='same'
        ),
        layers.BatchNormalization(),
        layers.MaxPool2D((2, 2)),
        # => Output sẽ 8x16x64

        # 4. Duỗi phẳng và ra quyết định
        layers.Flatten(), # Duỗi thẳng = 8x16x64 = 8192
        layers.Dense(64, activation='relu'),
        layers.Dropout(0.3),
        layers.Dense(1, activation='sigmoid')
    ])

    model.compile(
        optimizer='adam',
        loss='binary_crossentropy',
        metrics=['accuracy']
    )

    print("\n--- MÔ HÌNH ĐÃ ĐƯỢC BIÊN DỊCH THÀNH CÔNG! ---")
    print(f"Optimizer đang dùng: {model.optimizer.name}")
    print(f"Hàm Loss đang dùng: {model.loss}")

    return model

# Callbacks cho Fit
callbacks_list = [
    # 1. Dừng sớm nếu val_loss ko giảm sau 10 vòng
    tf.keras.callbacks.EarlyStopping(
        monitor='val_loss',
        patience=10,
        restore_best_weights=True
    ),
    # 2. Giảm tốc độ học LR đi 1 nửa sau 10 vòng nếu bị chững
    tf.keras.callbacks.ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        min_lr=1e-6,
        patience=10,
        verbose=1
    ),
    # 3. Lưu lại bộ não xuất sắc ra từng vòng ra file cứng
    tf.keras.callbacks.ModelCheckpoint(
        filepath=os.path.join(Dir_Out_Model, 'Bin_Asthma.keras'),
        monitor='val_loss',
        save_best_only=True,
        verbose=1
    ),
    # 4. Xuất toàn bộ điểm số ra từng vòng ra file CSV
    tf.keras.callbacks.CSVLogger(
        filename=os.path.join(Dir_Out_Model,'training_log.csv'),
        separator=',',
        append=False
    ),
    # 5. Ghi log để xem trực tuyến trên trình duyệt
    tf.keras.callbacks.TensorBoard(
        log_dir=os.path.join(Dir_Out_Model,'logs'),
        histogram_freq=1 
    ),
    # 6. Dừng khẩn cấp nếu xảy ra lỗi về giá trị
    tf.keras.callbacks.TerminateOnNaN()
]

def main():
    print("1. ĐỌC DỮ LIỆU TỪ MA TRẬN .NPY...")
    x_path = os.path.join(Dir_Features, "X_data_mel.npy")
    y_path = os.path.join(Dir_Features, "Y_labels_mel.npy")

    X_data   = np.load(x_path)
    Y_labels = np.load(y_path)
    print(f"Đã tải xong! Kích thước X: {X_data.shape} | Kích thước Y: {Y_labels.shape}")

    print("\n2. CHIA TẬP TRAIN & TEST...")
    X_train_np, X_temp, Y_train_np, Y_temp = train_test_split(
        X_data,
        Y_labels,
        test_size=0.2,
        random_state=42,
        stratify=Y_labels
    )

    X_valid_np, X_test_np, Y_valid_np, Y_test_np = train_test_split(
        X_temp,
        Y_temp,
        test_size=0.5,
        random_state=42,
        stratify=Y_temp
    )

    print("\n--- KẾT QUẢ CHIA TẬP (Sklearn) ---")
    print(f"Tập Train (Học):        {len(X_train_np)} mẫu")
    print(f"Tập Validation (Chỉnh): {len(X_valid_np)} mẫu")
    print(f"Tập Test (Thi):         {len(X_test_np)} mẫu")
    
    print("\n3. CHUẨN HÓA DỮ LIỆU VỀ [0, 1]...")
    min_val = np.min(X_train_np)
    max_val = np.max(X_train_np)

    X_train_np = (X_train_np - min_val) / (max_val - min_val)
    X_valid_np = (X_valid_np - min_val) / (max_val - min_val)
    X_test_np  = (X_test_np  - min_val) / (max_val - min_val)
    print(f"\nĐã chuẩn hóa xong về [0 1]")

    print("\n4. BẮT ĐẦU CHUYỂN ĐỔI TENSOR...")
    X_train = tf.convert_to_tensor(X_train_np, dtype=tf.float32)
    Y_train = tf.convert_to_tensor(Y_train_np, dtype=tf.float32)

    X_valid = tf.convert_to_tensor(X_valid_np, dtype=tf.float32)
    Y_valid = tf.convert_to_tensor(Y_valid_np, dtype=tf.float32)

    X_test = tf.convert_to_tensor(X_test_np, dtype=tf.float32)
    Y_test = tf.convert_to_tensor(Y_test_np, dtype=tf.float32)

    print("\n--- THÔNG TIN TENSOR ĐẦU VÀO ---")
    print(f"Shape: {X_train.shape}")
    print(f"Dtype: {X_train.dtype}")

    print(f"\n5. KHỞI TẠO MÔ HÌNH...")
    # Bỏ chiều đầu tiên (Số lượng mẫu) 
    # Input sẽ là 1 ảnh 64x129x1
    input_shape = X_train.shape[1:]
    model = Build_and_Compile_Model(input_shape)
    print("\n--- BẢNG TÓM TẮT KIẾN TRÚC MÔ HÌNH ---")
    model.summary()

    print(f"\n6. BẮT ĐẦU TRAINING...")
    history = model.fit(
        X_train,
        Y_train,
        epochs=Epochs,
        batch_size=Batch_Size,
        validation_data=(X_valid, Y_valid),
        callbacks=callbacks_list,
        verbose=1
    )

    print("\n-> Đã huấn luyện xong và lưu bản gốc Bin_Asthma.keras!")

    print(f"\n7. ĐÁNH GIÁ EVALUATION...")
    loss, acc = model.evaluate(
        X_test, 
        Y_test, 
        verbose=1
    )
    print(f"Test Loss    : {loss:.4f}")
    print(f"Test Accuracy: {acc:.4f} ({acc*100:.2f}%)")
    Plot_Training_History(history)

if __name__ == "__main__":
    main()