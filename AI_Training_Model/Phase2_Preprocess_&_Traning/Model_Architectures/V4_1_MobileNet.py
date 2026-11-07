"""V4.1 — Biến thể MobileNetV1-style rút gọn của NCKH.

Nguồn: Howard và cộng sự (2017), "MobileNets: Efficient Convolutional
       Neural Networks for Mobile Vision Applications", arXiv:1704.04861.
       https://arxiv.org/abs/1704.04861.
Kế thừa: Conv2D stem, Depthwise + Pointwise Conv, BN, ReLU6 và GAP.
Điều chỉnh: alpha=0.50, beta=8 (beta là tham số số khối của code NCKH),
            đầu vào Log-Mel và Dense(1, sigmoid).
Vai trò: Biến thể nhỏ hơn V4.0 để so sánh hiệu năng/tài nguyên.
Lưu ý: Không dùng trọng số pretrained; không phải MobileNetV1 nguyên bản."""

from keras import layers, models


def build_and_compile_model(input_shape):
    return _build_mobilenet(input_shape, alpha=0.50, beta=8)


def _build_mobilenet(input_shape, alpha, beta):
    def filters(base_filters):
        return int(base_filters * alpha)

    model = models.Sequential([
        layers.Input(shape=input_shape),
        layers.Conv2D(
            filters=filters(32),
            kernel_size=(3, 3),
            strides=(2, 2),
            padding="same",
            use_bias=False
        ),
        layers.BatchNormalization(),
        layers.ReLU(max_value=6.0),
    ])

    def add_ds_block(pointwise_filters, stride=1):
        if stride == 2:
            model.add(layers.ZeroPadding2D(padding=((0, 1), (0, 1))))

        model.add(layers.DepthwiseConv2D(
            kernel_size=(3, 3),
            strides=(stride, stride),
            padding="same" if stride == 1 else "valid",
            use_bias=False
        ))
        model.add(layers.BatchNormalization())
        model.add(layers.ReLU(max_value=6.0))
        model.add(layers.Conv2D(
            filters=filters(pointwise_filters),
            kernel_size=(1, 1),
            padding="same",
            use_bias=False
        ))
        model.add(layers.BatchNormalization())
        model.add(layers.ReLU(max_value=6.0))

    add_ds_block(64)
    add_ds_block(128, stride=2)
    add_ds_block(128)
    add_ds_block(256, stride=2)
    add_ds_block(256)
    add_ds_block(512, stride=2)

    for _ in range(beta - 8):
        add_ds_block(512)

    add_ds_block(1024, stride=2)
    add_ds_block(1024)
    model.add(layers.GlobalAveragePooling2D())
    model.add(layers.Dense(1, activation="sigmoid"))

    model.compile(
        optimizer="adam",
        loss="binary_crossentropy",
        metrics=["accuracy"]
    )
    return model
