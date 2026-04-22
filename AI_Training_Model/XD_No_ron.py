import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
# Ép TensorFlow im lặng (Chỉ in ra Lỗi thực sự, giấu đi các Warning)


import tensorflow as tf
import numpy as np
from keras import layers, models

# Load lại nếu cần (sau khi restart kernel)
X_train = np.load("X_train.npy")
X_test  = np.load("X_test.npy")
y_train = np.load("y_train.npy")
y_test  = np.load("y_test.npy")

INPUT_DIM   = X_train.shape[1]   # 240
NUM_CLASSES = 3

def build_dnn_esp32(input_dim, num_classes):

    model = models.Sequential([
        layers.Input(shape=(input_dim,)),

        # Lớp 1
        layers.Dense(128, activation='relu'),
        layers.BatchNormalization(),    
        layers.Dropout(0.3),         

        # Lớp 2
        layers.Dense(64, activation='relu'),
        layers.BatchNormalization(),
        layers.Dropout(0.25),

        # Lớp 3
        layers.Dense(32, activation='relu'),
        layers.Dropout(0.2),

        # Output: 3 lớp (Asthma / Others / Background)
        layers.Dense(num_classes, activation='softmax')
    ])
    return model

model = build_dnn_esp32(INPUT_DIM, NUM_CLASSES)

# B3 — Compile
model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
    loss='sparse_categorical_crossentropy', 
    metrics=['accuracy']
)

model.summary()

params = model.count_params()
size_kb = params * 4 / 1024         
print(f"\nTổng tham số: {params:,}")
print(f"Kích thước ước tính (float32): {size_kb:.1f} KB")
print(f"Sau lượng tử hóa INT8: ~{size_kb/4:.1f} KB  ← ESP32 Flash OK")



callbacks_list = [
    tf.keras.callbacks.EarlyStopping(
        monitor='val_loss',
        patience=20,                  # dừng nếu val_loss không giảm 20 epoch
        restore_best_weights=True     # lấy lại weights tốt nhất
    ),
    tf.keras.callbacks.ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,                   # giảm LR xuống một nửa
        patience=10,
        min_lr=1e-6,
        verbose=1
    ),
    tf.keras.callbacks.ModelCheckpoint(
        "best_model.keras",
        monitor='val_accuracy',
        save_best_only=True,
        verbose=1
    )
]

history = model.fit(
    X_train, y_train,
    validation_split=0.15,            # 15% của train làm validation
    epochs=150,
    batch_size=32,
    callbacks=callbacks_list,
    verbose=1
)