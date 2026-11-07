"""V3 — DS-CNN tham khảo Hello Edge, điều chỉnh cho NCKH.

Nguồn: Zhang, Suda, Lai & Chandra (2017),
       "Hello Edge: Keyword Spotting on Microcontrollers", arXiv:1711.07128.
       https://arxiv.org/abs/1711.07128.
Kế thừa: Conv2D mở đầu; các khối Depthwise + Pointwise; GAP.
Điều chỉnh: Đầu vào (frequency, time), kernel (4,10), bốn khối DS-CNN,
            64 kênh và đầu ra Sigmoid cho bài toán nhị phân.
Lưu ý: Đây là biến thể tham khảo, không phải tái hiện nguyên bản Hello Edge."""

from keras import layers, models


def build_and_compile_model(input_shape):
    model = models.Sequential([
        layers.Input(shape=input_shape),

        # Tensor dự án là (frequency, time), vì vậy kernel tham khảo 10x4
        # theo (time, frequency) được biểu diễn thành (4, 10).
        layers.Conv2D(
            filters=64,
            kernel_size=(4, 10),
            strides=(2, 2),
            padding="same",
            use_bias=False
        ),
        layers.BatchNormalization(),
        layers.ReLU(),

        layers.DepthwiseConv2D(
            kernel_size=(3, 3), padding="same", use_bias=False
        ),
        layers.BatchNormalization(),
        layers.ReLU(),
        layers.Conv2D(64, (1, 1), padding="same", use_bias=False),
        layers.BatchNormalization(),
        layers.ReLU(),

        layers.DepthwiseConv2D(
            kernel_size=(3, 3), padding="same", use_bias=False
        ),
        layers.BatchNormalization(),
        layers.ReLU(),
        layers.Conv2D(64, (1, 1), padding="same", use_bias=False),
        layers.BatchNormalization(),
        layers.ReLU(),

        layers.DepthwiseConv2D(
            kernel_size=(3, 3), padding="same", use_bias=False
        ),
        layers.BatchNormalization(),
        layers.ReLU(),
        layers.Conv2D(64, (1, 1), padding="same", use_bias=False),
        layers.BatchNormalization(),
        layers.ReLU(),

        layers.DepthwiseConv2D(
            kernel_size=(3, 3), padding="same", use_bias=False
        ),
        layers.BatchNormalization(),
        layers.ReLU(),
        layers.Conv2D(64, (1, 1), padding="same", use_bias=False),
        layers.BatchNormalization(),
        layers.ReLU(),

        layers.GlobalAveragePooling2D(),
        layers.Dense(1, activation="sigmoid")
    ])

    model.compile(
        optimizer="adam",
        loss="binary_crossentropy",
        metrics=["accuracy"]
    )
    return model
