"""Huấn luyện các kiến trúc Phase 2 bằng tensor do Preprocess_Audio.py tạo.

Đây vẫn là script train chính của pipeline cũ: nạp Train/Validation/Test, chuẩn
hóa bằng min/max của Train, chọn checkpoint theo val_loss và chỉ dùng Test để
báo cáo sau huấn luyện. Danh sách kiến trúc cần chạy được đặt ngay đầu file để
người đọc chỉ cần chạy lại Preprocess_Audio.py rồi Training_Model.py.
"""

from __future__ import annotations

import csv
import gc
import importlib
import json
import os
import sys
from pathlib import Path

os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from keras import models
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.utils.class_weight import compute_class_weight


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


SEED = int(os.environ.get("TRAIN_SEED", "42"))
EPOCHS = 100
BATCH_SIZE = 32

ARCHITECTURE_CONFIG = {
    "V1_SepConv2D_Flatten": {
        "module": "Model_Architectures.V1_SepConv2D_Flatten",
        "output_dir": "Output_Train_V1_SepConv2D_Flatten",
    },
    "V2_SepConv2D_GAP": {
        "module": "Model_Architectures.V2_SepConv2D_GAP",
        "output_dir": "Output_Train_V2_SepConv2D_GAP",
    },
    "V3_HelloEdge": {
        "module": "Model_Architectures.V3_HelloEdge",
        "output_dir": "Output_Train_V3_HelloEdge",
    },
    "V4_0_MobileNet": {
        "module": "Model_Architectures.V4_0_MobileNet",
        "output_dir": "Output_Train_V4_0_MobileNet",
    },
    "V4_1_MobileNet": {
        "module": "Model_Architectures.V4_1_MobileNet",
        "output_dir": "Output_Train_V4_1_MobileNet",
    },
    "V5_ERespiNet": {
        "module": "Model_Architectures.V5_ERespiNet",
        "output_dir": "Output_Train_V5_ERespiNet",
    },
    "V6_Azizi_SepCNN_Adapted": {
        "module": "Model_Architectures.V6_Azizi_SepCNN_Adapted",
        "output_dir": "Output_Train_V6_Azizi_SepCNN_Adapted",
    },
}

# Sáu họ V1-V6 hiện tương ứng bảy implementation vì V4 có V4.0 và V4.1.
# Giữ toàn bộ danh sách để benchmark công bằng trên cùng tensor đầu vào.
# Nếu chỉ muốn train model cuối V1, thay danh sách bằng ["V1_SepConv2D_Flatten"].
MODEL_ARCHITECTURES_TO_TRAIN = list(ARCHITECTURE_CONFIG)

BASE_DIR = Path(__file__).resolve().parent
DIR_FEATURES = BASE_DIR / "Output_Preprocess"
PREPROCESS_METADATA = DIR_FEATURES / "Preprocess_Metadata.json"
SUMMARY_PATH = BASE_DIR / "Architecture_Training_Summary.csv"


def load_preprocess_metadata():
    if not PREPROCESS_METADATA.is_file():
        return {}
    return json.loads(PREPROCESS_METADATA.read_text(encoding="utf-8"))


def load_split(split):
    x_path = DIR_FEATURES / f"X_{split}_mel.npy"
    y_path = DIR_FEATURES / f"Y_{split}_mel.npy"
    if not x_path.is_file() or not y_path.is_file():
        raise FileNotFoundError(f"Thiếu X/Y của split {split} trong {DIR_FEATURES}")

    x_data = np.load(x_path)
    y_data = np.load(y_path)
    if len(x_data) != len(y_data):
        raise ValueError(f"Split {split} không khớp X={len(x_data)}, Y={len(y_data)}")
    if x_data.ndim != 4 or x_data.shape[-1] != 1:
        raise ValueError(f"X_{split} phải có dạng (N, Mel, Time, 1): {x_data.shape}")
    if not np.isfinite(x_data).all():
        raise ValueError(f"X_{split} có NaN hoặc Inf")
    if not set(np.unique(y_data)).issubset({0, 1}):
        raise ValueError(f"Y_{split} có nhãn ngoài 0 và 1")

    print(
        f"{split}: X={x_data.shape}, dtype={x_data.dtype}, "
        f"Asthma={int(np.sum(y_data == 0))}, "
        f"Non-Asthma={int(np.sum(y_data == 1))}"
    )
    return x_data, y_data


def load_architecture_builder(architecture):
    module_name = ARCHITECTURE_CONFIG[architecture]["module"]
    module = importlib.import_module(module_name)
    builder = getattr(module, "build_and_compile_model", None)
    if not callable(builder):
        raise AttributeError(
            f"Module {module_name} thiếu build_and_compile_model(input_shape)"
        )
    return builder


def create_callbacks(output_dir, model_path):
    return [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            mode="min",
            patience=10,
            restore_best_weights=True,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            mode="min",
            factor=0.5,
            min_lr=1e-6,
            patience=5,
            verbose=1,
        ),
        tf.keras.callbacks.ModelCheckpoint(
            filepath=model_path,
            monitor="val_loss",
            mode="min",
            save_best_only=True,
            verbose=1,
        ),
        tf.keras.callbacks.CSVLogger(
            filename=output_dir / "training_log.csv",
            separator=",",
            append=False,
        ),
        tf.keras.callbacks.TensorBoard(
            log_dir=output_dir / "logs",
            histogram_freq=1,
        ),
        tf.keras.callbacks.TerminateOnNaN(),
    ]


def plot_training_history(history, output_dir):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].plot(history.history["accuracy"], label="Train Accuracy")
    axes[0].plot(history.history["val_accuracy"], label="Validation Accuracy")
    axes[0].set_title("Độ chính xác qua các epoch")
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Accuracy")
    axes[0].legend()
    axes[0].grid(True, linestyle="--", alpha=0.6)

    axes[1].plot(history.history["loss"], label="Train Loss")
    axes[1].plot(history.history["val_loss"], label="Validation Loss")
    axes[1].set_title("Loss qua các epoch")
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("Loss")
    axes[1].legend()
    axes[1].grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()
    fig.savefig(output_dir / "Training_History.png", dpi=150)
    plt.close(fig)


def train_architecture(
    architecture,
    x_train,
    y_train,
    x_val,
    y_val,
    x_test,
    y_test,
    train_min,
    train_max,
    input_shape,
    preprocess_metadata,
):
    print("\n" + "=" * 78)
    print(f"BẮT ĐẦU: {architecture} | seed={SEED} | input={input_shape}")
    print("=" * 78)

    tf.keras.backend.clear_session()
    tf.keras.utils.set_random_seed(SEED)
    np.random.seed(SEED)

    output_dir = BASE_DIR / ARCHITECTURE_CONFIG[architecture]["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "Model_Asthma.keras"

    (output_dir / "Normalization_Params.txt").write_text(
        f"TRAIN_MIN={train_min}\nTRAIN_MAX={train_max}\n",
        encoding="utf-8",
    )

    build_model = load_architecture_builder(architecture)
    model = build_model(input_shape)
    model.summary()

    classes = np.unique(y_train).astype(int)
    weights = compute_class_weight(
        class_weight="balanced",
        classes=classes,
        y=y_train.astype(int),
    )
    class_weight_dict = {
        int(label): float(weight) for label, weight in zip(classes, weights)
    }
    print("Class weights:", class_weight_dict)

    history = model.fit(
        x_train,
        y_train,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        validation_data=(x_val, y_val),
        callbacks=create_callbacks(output_dir, model_path),
        class_weight=class_weight_dict,
        shuffle=True,
        verbose=1,
    )

    # Đánh giá đúng checkpoint có val_loss tốt nhất; Test không tham gia fit.
    model = models.load_model(model_path)
    test_loss, test_accuracy = model.evaluate(x_test, y_test, verbose=1)
    probabilities = model.predict(x_test, verbose=0).reshape(-1)
    predictions = (probabilities >= 0.5).astype(np.int64)
    matrix = confusion_matrix(y_test.astype(int), predictions, labels=[0, 1])
    report = classification_report(
        y_test.astype(int),
        predictions,
        labels=[0, 1],
        target_names=["Asthma", "Non_Asthma"],
        digits=4,
        zero_division=0,
    )

    (output_dir / "Test_Report.txt").write_text(
        f"Pipeline: {preprocess_metadata.get('pipeline_name', 'unspecified')}\n"
        f"Input shape: {input_shape}\n"
        f"Training seed: {SEED}\n"
        f"Test Loss: {test_loss:.6f}\n"
        f"Test Accuracy: {test_accuracy:.6f}\n\n"
        f"Confusion Matrix [Asthma, Non_Asthma]:\n{matrix}\n\n"
        f"Classification Report:\n{report}",
        encoding="utf-8",
    )
    plot_training_history(history, output_dir)

    best_epoch = int(np.argmin(history.history["val_loss"]) + 1)
    best_val_loss = float(np.min(history.history["val_loss"]))
    best_val_accuracy = float(history.history["val_accuracy"][best_epoch - 1])
    metadata = {
        "pipeline_name": preprocess_metadata.get("pipeline_name", "unspecified"),
        "preprocess_config": preprocess_metadata.get("preprocess_config", {}),
        "architecture": architecture,
        "seed": SEED,
        "input_shape": list(input_shape),
        "epochs_requested": EPOCHS,
        "epochs_completed": len(history.history["loss"]),
        "best_epoch": best_epoch,
        "best_val_loss": best_val_loss,
        "best_val_accuracy": best_val_accuracy,
        "test_accuracy": float(test_accuracy),
        "parameter_count": int(model.count_params()),
        "test_used_for_training": False,
    }
    (output_dir / "Training_Metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Hoàn thành {architecture}: val={best_val_accuracy:.4f}, "
        f"test={test_accuracy:.4f}"
    )
    return metadata


def save_summary(rows):
    fields = [
        "pipeline_name",
        "architecture",
        "seed",
        "input_shape",
        "epochs_requested",
        "epochs_completed",
        "best_epoch",
        "best_val_loss",
        "best_val_accuracy",
        "test_accuracy",
        "parameter_count",
        "test_used_for_training",
    ]
    with SUMMARY_PATH.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            normalized = dict(row)
            normalized["input_shape"] = "x".join(map(str, row["input_shape"]))
            writer.writerow(normalized)


def main():
    preprocess_metadata = load_preprocess_metadata()
    unknown = set(MODEL_ARCHITECTURES_TO_TRAIN) - set(ARCHITECTURE_CONFIG)
    if unknown:
        raise ValueError(f"Kiến trúc không hợp lệ: {sorted(unknown)}")

    print("1. ĐỌC BA SPLIT ĐÃ PREPROCESS")
    x_train, y_train = load_split("train")
    x_val, y_val = load_split("val")
    x_test, y_test = load_split("test")

    input_shape = tuple(int(value) for value in x_train.shape[1:])
    if tuple(x_val.shape[1:]) != input_shape or tuple(x_test.shape[1:]) != input_shape:
        raise ValueError("Train/Validation/Test không có cùng input shape")
    metadata_shape = tuple(preprocess_metadata.get("input_shape", []))
    if metadata_shape and metadata_shape != input_shape:
        raise ValueError(
            f"Metadata shape {metadata_shape} không khớp tensor {input_shape}"
        )

    print("\n2. CHUẨN HÓA [0, 1] BẰNG MIN/MAX CỦA TRAIN")
    train_min = float(np.min(x_train))
    train_max = float(np.max(x_train))
    if train_max <= train_min:
        raise ValueError("Min/max của Train không hợp lệ")
    print(f"TRAIN_MIN={train_min}, TRAIN_MAX={train_max}")

    scale = train_max - train_min
    x_train = ((x_train - train_min) / scale).astype(np.float32)
    x_val = ((x_val - train_min) / scale).astype(np.float32)
    x_test = ((x_test - train_min) / scale).astype(np.float32)
    y_train = y_train.astype(np.float32)
    y_val = y_val.astype(np.float32)
    y_test = y_test.astype(np.float32)

    print(
        f"\n3. TRAIN {len(MODEL_ARCHITECTURES_TO_TRAIN)} IMPLEMENTATION: "
        f"{MODEL_ARCHITECTURES_TO_TRAIN}"
    )
    summary_rows = []
    for architecture in MODEL_ARCHITECTURES_TO_TRAIN:
        summary_rows.append(
            train_architecture(
                architecture,
                x_train,
                y_train,
                x_val,
                y_val,
                x_test,
                y_test,
                train_min,
                train_max,
                input_shape,
                preprocess_metadata,
            )
        )
        tf.keras.backend.clear_session()
        gc.collect()

    save_summary(summary_rows)
    print(f"\nHoàn thành. Bảng tổng hợp: {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
