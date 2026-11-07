"""V2 — Biến thể do nhóm NCKH phát triển từ V1.

Nguồn gốc: Thiết kế nội bộ; không tái hiện trực tiếp một mô hình công bố.
Cơ sở: SeparableConv2D theo nguyên lý MobileNet (Howard và cs., 2017),
        https://arxiv.org/abs/1704.04861; Global Average Pooling (GAP).
Điều chỉnh: Giữ ba khối 16–32–64 của V1 nhưng dùng GlobalAveragePooling2D
            thay cho Flatten để giảm số tham số trong phần phân loại.
Vai trò: Đối chứng Flatten/GAP với V1."""

from keras import layers, models


def build_and_compile_model(input_shape):
    model = models.Sequential([
        layers.Input(shape=input_shape),

        layers.SeparableConv2D(16, (3, 3), activation="relu", padding="same"),
        layers.BatchNormalization(),
        layers.MaxPool2D((2, 2)),

        layers.SeparableConv2D(32, (3, 3), activation="relu", padding="same"),
        layers.BatchNormalization(),
        layers.MaxPool2D((2, 2)),

        layers.SeparableConv2D(64, (3, 3), activation="relu", padding="same"),
        layers.BatchNormalization(),
        layers.MaxPool2D((2, 2)),

        layers.GlobalAveragePooling2D(),
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
