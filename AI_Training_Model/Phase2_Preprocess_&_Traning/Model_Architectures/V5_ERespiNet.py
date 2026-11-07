"""V5 — CNN một nhánh Conv2D 16–32–64; mô hình đối chứng NCKH.

Nguồn tham khảo cho khối CNN: "E-RespiNet: An LLM-ELECTRA driven triple-stream
       CNN with feature fusion for asthma classification" (PLOS ONE, 2025).
       DOI: 10.1371/journal.pone.0334528.
Tương đồng: Các nhánh CNN âm học của bài báo dùng ba lớp Conv2D 16–32–64,
            BatchNormalization, MaxPool và Flatten.
Giới hạn: File này chỉ có MỘT nhánh CNN đơn giản; KHÔNG có ba nhánh
           MFCC/Wavelet/Mel, feature fusion hay ELECTRA.
           Không được gọi đây là bản tái hiện E-RespiNet đầy đủ.
Giữ tên file cũ để tương thích pipeline; nên gọi trong báo cáo là
"V5 — Single-stream CNN baseline (E-RespiNet-inspired)"."""

from keras import layers, models


def build_and_compile_model(input_shape):
    model = models.Sequential([
        layers.Input(shape=input_shape),

        layers.Conv2D(16, (3, 3), activation="relu", padding="same"),
        layers.BatchNormalization(),
        layers.MaxPool2D((2, 2)),

        layers.Conv2D(32, (3, 3), activation="relu", padding="same"),
        layers.BatchNormalization(),
        layers.MaxPool2D((2, 2)),

        layers.Conv2D(64, (3, 3), activation="relu", padding="same"),
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
