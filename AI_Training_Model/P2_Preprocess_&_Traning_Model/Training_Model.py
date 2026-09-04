"""
===============================================================================
Tên script: Training_Model.py

Tác dụng:
- Nạp ba bộ X/Y train, val và test đã tạo sẵn, sau đó huấn luyện mạng DS-CNN
  phân loại 0=Asthma và 1=Non-Asthma.
- Chọn model tốt nhất theo val_loss, dừng sớm, giảm learning rate và lưu báo
  cáo/ma trận nhầm lẫn trên test.

Điểm tinh chỉnh so với model ban đầu:
- Không gọi train_test_split trên folder đã chứa file tăng cường.
- Min/max chuẩn hóa chỉ lấy từ train rồi áp dụng nguyên vẹn cho val/test.
- Val dùng để chọn model; test chỉ dùng để lập báo cáo sau khi model đã chốt.
===============================================================================
"""

import os
import sys

os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from keras import layers, models
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.utils.class_weight import compute_class_weight


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


SEED = 42
EPOCHS = 100
BATCH_SIZE = 32

# Chạy script từ thư mục gốc NCKH_2026_AIOT.
DIR_FEATURES = os.path.join(
    "AI_Training_Model",
    "P2_Preprocess_&_Traning_Model",
    "Output_Preprocess"
)
DIR_OUT_MODEL = os.path.join(
    "AI_Training_Model",
    "P2_Preprocess_&_Traning_Model",
    "Output_Train"
)
MODEL_PATH = os.path.join(DIR_OUT_MODEL, "Bin_Asthma.keras")

os.makedirs(DIR_OUT_MODEL, exist_ok=True)

tf.keras.utils.set_random_seed(SEED)
np.random.seed(SEED)


def load_split(split):
    x_path = os.path.join(DIR_FEATURES, f"X_{split}_mel.npy")
    y_path = os.path.join(DIR_FEATURES, f"Y_{split}_mel.npy")

    if not os.path.exists(x_path) or not os.path.exists(y_path):
        raise FileNotFoundError(
            f"Thiếu X/Y của tập {split} trong: {DIR_FEATURES}"
        )

    x_data = np.load(x_path)
    y_data = np.load(y_path)

    if len(x_data) != len(y_data):
        raise ValueError(
            f"Tập {split} không khớp: X={len(x_data)}, Y={len(y_data)}"
        )

    if x_data.shape[1:] != (64, 129, 1):
        raise ValueError(f"Sai kích thước X_{split}: {x_data.shape}")

    if np.isnan(x_data).any() or np.isinf(x_data).any():
        raise ValueError(f"X_{split} có NaN hoặc Inf")

    if not set(np.unique(y_data)).issubset({0, 1}):
        raise ValueError(f"Y_{split} có nhãn ngoài 0 và 1")

    print(
        f"{split}: X={x_data.shape}, Y={y_data.shape}, "
        f"Asthma={np.sum(y_data == 0)}, "
        f"Non_Asthma={np.sum(y_data == 1)}"
    )

    return x_data, y_data


def build_and_compile_model(input_shape):
    # Giữ nguyên kiến trúc DS-CNN của file train cũ.
    model = models.Sequential([
        layers.Input(shape=input_shape),

        layers.SeparableConv2D(
            16, (3, 3), 
            activation="relu", 
            padding="same"
        ),
        layers.BatchNormalization(),
        layers.MaxPool2D((2, 2)),

        layers.SeparableConv2D(
            32, (3, 3), 
            activation="relu", 
            padding="same"
        ),
        layers.BatchNormalization(),
        layers.MaxPool2D((2, 2)),

        layers.SeparableConv2D(
            64, (3, 3), 
            activation="relu", 
            padding="same"
        ),
        layers.BatchNormalization(),
        layers.MaxPool2D((2, 2)),

        layers.Flatten(),
        layers.Dense(64, activation="relu"),
        layers.Dropout(0.3),
        layers.Dense(1, activation="sigmoid")
    ])

    model.compile(
        optimizer="adam",
        loss="binary_crossentropy",
        metrics=["accuracy"]
    )

    return model


def create_callbacks():
    return [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            mode="min",
            patience=10,
            restore_best_weights=True
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            mode="min",
            factor=0.5,
            min_lr=1e-6,
            patience=5,
            verbose=1
        ),
        tf.keras.callbacks.ModelCheckpoint(
            filepath=MODEL_PATH,
            monitor="val_loss",
            mode="min",
            save_best_only=True,
            verbose=1
        ),
        tf.keras.callbacks.CSVLogger(
            filename=os.path.join(DIR_OUT_MODEL, "training_log.csv"),
            separator=",",
            append=False
        ),
        tf.keras.callbacks.TensorBoard(
            log_dir=os.path.join(DIR_OUT_MODEL, "logs"),
            histogram_freq=1
        ),
        tf.keras.callbacks.TerminateOnNaN()
    ]


def plot_training_history(history):
    plt.figure(figsize=(12, 5))

    plt.subplot(1, 2, 1)
    plt.plot(history.history["accuracy"], label="Train Accuracy")
    plt.plot(history.history["val_accuracy"], label="Validation Accuracy")
    plt.title("Độ chính xác qua các vòng học")
    plt.xlabel("Vòng học")
    plt.ylabel("Accuracy")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.6)

    plt.subplot(1, 2, 2)
    plt.plot(history.history["loss"], label="Train Loss")
    plt.plot(history.history["val_loss"], label="Validation Loss")
    plt.title("Độ lỗi qua các vòng học")
    plt.xlabel("Vòng học")
    plt.ylabel("Loss")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.6)

    plt.tight_layout()
    plt.savefig(
        os.path.join(DIR_OUT_MODEL, "Training_History.png"),
        dpi=150
    )
    plt.close()


def main():
    print("1. ĐỌC BA TẬP DỮ LIỆU ĐÃ CHIA SẴN")
    x_train_np, y_train_np = load_split("train")
    x_val_np, y_val_np = load_split("val")
    x_test_np, y_test_np = load_split("test")

    print("\n2. CHUẨN HÓA VỀ [0, 1]")
    # Chỉ lấy min/max từ tập học để tránh nhìn trước val/test.
    train_min = float(np.min(x_train_np))
    train_max = float(np.max(x_train_np))

    if train_max <= train_min:
        raise ValueError("Min/max tập học không hợp lệ")

    print(f"TRAIN_MIN={train_min}, TRAIN_MAX={train_max}")

    with open(
        os.path.join(DIR_OUT_MODEL, "Normalization_Params.txt"),
        "w",
        encoding="utf-8"
    ) as file:
        file.write(f"TRAIN_MIN={train_min}\n")
        file.write(f"TRAIN_MAX={train_max}\n")

    x_train_np = ((x_train_np - train_min) / (train_max - train_min)).astype(np.float32)
    x_val_np = ((x_val_np - train_min) / (train_max - train_min)).astype(np.float32)
    x_test_np = ((x_test_np - train_min) / (train_max - train_min)).astype(np.float32)

    y_train_np = y_train_np.astype(np.float32)
    y_val_np = y_val_np.astype(np.float32)
    y_test_np = y_test_np.astype(np.float32)

    print("\n3. KHỞI TẠO MÔ HÌNH")
    model = build_and_compile_model(x_train_np.shape[1:])
    model.summary()

    classes = np.unique(y_train_np).astype(int)
    weights = compute_class_weight(
        class_weight="balanced",
        classes=classes,
        y=y_train_np.astype(int)
    )
    class_weight_dict = dict(zip(classes, weights))
    print("Class weights:", class_weight_dict)

    print("\n4. BẮT ĐẦU HUẤN LUYỆN")
    history = model.fit(
        x_train_np,
        y_train_np,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        validation_data=(x_val_np, y_val_np),
        callbacks=create_callbacks(),
        class_weight=class_weight_dict,
        shuffle=True,
        verbose=1
    )

    print("\n5. ĐÁNH GIÁ TẬP TEST")
    # Luôn đánh giá đúng model tốt nhất đã chọn từ tập val.
    model = models.load_model(MODEL_PATH)
    test_loss, test_accuracy = model.evaluate(
        x_test_np,
        y_test_np,
        verbose=1
    )
    print(f"Test Loss: {test_loss:.4f}")
    print(f"Test Accuracy: {test_accuracy:.4f} ({test_accuracy * 100:.2f}%)")

    probabilities = model.predict(x_test_np, verbose=0).reshape(-1)
    predictions = (probabilities >= 0.5).astype(np.int64)

    matrix = confusion_matrix(
        y_test_np.astype(int),
        predictions,
        labels=[0, 1]
    )
    report = classification_report(
        y_test_np.astype(int),
        predictions,
        labels=[0, 1],
        target_names=["Asthma", "Non_Asthma"],
        digits=4,
        zero_division=0
    )

    print("\nMa trận nhầm lẫn [Asthma, Non_Asthma]:")
    print(matrix)
    print("\nBáo cáo phân loại:")
    print(report)

    with open(
        os.path.join(DIR_OUT_MODEL, "Test_Report.txt"),
        "w",
        encoding="utf-8"
    ) as file:
        file.write(f"Test Loss: {test_loss:.6f}\n")
        file.write(f"Test Accuracy: {test_accuracy:.6f}\n\n")
        file.write("Confusion Matrix [Asthma, Non_Asthma]:\n")
        file.write(np.array2string(matrix))
        file.write("\n\nClassification Report:\n")
        file.write(report)

    plot_training_history(history)
    print(f"\nHoàn thành. Model và báo cáo nằm tại: {DIR_OUT_MODEL}")


if __name__ == "__main__":
    main()
