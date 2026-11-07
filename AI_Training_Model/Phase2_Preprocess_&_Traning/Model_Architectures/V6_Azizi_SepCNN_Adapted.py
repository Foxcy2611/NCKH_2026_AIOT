"""V6 — Separable CNN tham khảo Azizi, điều chỉnh cho âm thanh hô hấp NCKH.

Nguồn: Azizi, Sayahi & Nejabat (2025), "Convolutional Neural Network
       Classifier for Unmanned Aerial Vehicles Detection and Identification
       Using Mel-Frequency Spectrograms", The Journal of Engineering.
       DOI: 10.1049/tje2.70135 (Bảng 1).
Kế thừa: Conv2D mở đầu, SeparableConv2D 16-32-64, BN, Pooling, Dropout,
         GlobalAveragePooling2D và Dense(64).
Điều chỉnh: Log-Mel 64x129x1 (gốc 64x89x1), Dense(1, sigmoid) cho
            Asthma=0 / Non-Asthma=1 thay vì Softmax 2/3 lớp của bài báo.
Lưu ý: Đây là bản điều chỉnh theo nghiên cứu về UAV, không phải bản gốc."""

from keras import layers, models


def build_and_compile_model(input_shape):
    """Build an independent V6 trial without changing the V1 baseline."""
    model = models.Sequential([
        layers.Input(shape=input_shape),

        # Block 1: standard Conv2D stem, followed by separable convolution.
        layers.Conv2D(16, (3, 3), padding="same", activation="relu"),
        layers.BatchNormalization(),
        layers.SeparableConv2D(16, (3, 3), padding="same", activation="relu"),
        layers.BatchNormalization(),
        layers.MaxPooling2D(pool_size=(2, 2)),
        layers.Dropout(0.2),

        # Block 2.
        layers.SeparableConv2D(32, (3, 3), padding="same", activation="relu"),
        layers.BatchNormalization(),
        layers.MaxPooling2D(pool_size=(2, 2)),
        layers.Dropout(0.3),

        # Block 3.
        layers.SeparableConv2D(64, (3, 3), padding="same", activation="relu"),
        layers.BatchNormalization(),
        layers.MaxPooling2D(pool_size=(2, 2)),
        layers.Dropout(0.4),

        # GAP keeps the classifier small compared with Flatten -> Dense(64).
        layers.GlobalAveragePooling2D(),
        layers.Dense(64, activation="relu"),
        layers.Dropout(0.4),
        layers.Dense(1, activation="sigmoid"),
    ], name="V6_Azizi_SeparableCNN_Adapted")

    model.compile(
        optimizer="adam",
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )
    return model


if __name__ == "__main__":
    # Standalone architectural smoke test (not a training entry point).
    model = build_and_compile_model((64, 129, 1))
    model.summary()
