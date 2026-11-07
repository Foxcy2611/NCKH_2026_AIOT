

"""V1 — DS-CNN baseline do nhóm NCKH tự thiết kế.

Nguồn gốc: Cấu hình do nhóm đề xuất, không sao chép nguyên mẫu từ bài báo.
Cơ sở: Depthwise Separable Convolution trong MobileNet (Howard và cs., 2017),
        https://arxiv.org/abs/1704.04861.
Đặc điểm: Ba khối SeparableConv2D (16–32–64), BN, MaxPool,
          Flatten → Dense(64) → Dropout → Sigmoid.
Vai trò: Kiến trúc tham chiếu chính của các thí nghiệm NCKH."""

from keras import layers, models


def build_and_compile_model(input_shape):
    """Tạo và compile kiến trúc V1 baseline."""
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
