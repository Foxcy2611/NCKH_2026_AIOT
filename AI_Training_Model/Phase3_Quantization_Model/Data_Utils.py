import numpy as np

from Config import (
    FEATURE_DIR,
    NORMALIZATION_PATH,
)


def load_normalization_params():

    if not NORMALIZATION_PATH.exists():
        raise FileNotFoundError(
            f"Không tìm thấy:\n"
            f"{NORMALIZATION_PATH}"
        )

    params = {}

    with open(
        NORMALIZATION_PATH,
        "r",
        encoding="utf-8"
    ) as file:

        for line in file:

            if "=" not in line:
                continue

            key, value = line.strip().split(
                "=",
                1
            )

            params[key] = float(value)

    if (
        "TRAIN_MIN" not in params
        or
        "TRAIN_MAX" not in params
    ):
        raise ValueError(
            "Thiếu TRAIN_MIN / TRAIN_MAX"
        )

    train_min = params["TRAIN_MIN"]
    train_max = params["TRAIN_MAX"]

    if train_max <= train_min:
        raise ValueError(
            "TRAIN_MIN / TRAIN_MAX không hợp lệ"
        )

    return train_min, train_max


def normalize(
    x,
    train_min,
    train_max
):

    x = x.astype(np.float32)

    return (
        (x - train_min)
        /
        (train_max - train_min)
    ).astype(np.float32)


def load_dataset():

    train_min, train_max = (
        load_normalization_params()
    )

    # =================================================================
    # TRAIN
    # =================================================================

    x_train = np.load(
        FEATURE_DIR / "X_train_mel.npy"
    )

    y_train = np.load(
        FEATURE_DIR / "Y_train_mel.npy"
    )

    # =================================================================
    # VALIDATION
    # =================================================================

    x_val = np.load(
        FEATURE_DIR / "X_val_mel.npy"
    )

    y_val = np.load(
        FEATURE_DIR / "Y_val_mel.npy"
    )

    # =================================================================
    # TEST
    # =================================================================

    x_test = np.load(
        FEATURE_DIR / "X_test_mel.npy"
    )

    y_test = np.load(
        FEATURE_DIR / "Y_test_mel.npy"
    )

    file_names = np.load(
        FEATURE_DIR / "Files_test.npy"
    )

    # =================================================================
    # CHECK
    # =================================================================

    if len(x_train) != len(y_train):
        raise ValueError(
            "Train X/Y không khớp"
        )

    if len(x_val) != len(y_val):
        raise ValueError(
            "Val X/Y không khớp"
        )

    if len(x_test) != len(y_test):
        raise ValueError(
            "Test X/Y không khớp"
        )

    if len(file_names) != len(y_test):
        raise ValueError(
            "Files_test không khớp Test"
        )

    # =================================================================
    # NORMALIZE
    # =================================================================

    x_train = normalize(
        x_train,
        train_min,
        train_max
    )

    x_val = normalize(
        x_val,
        train_min,
        train_max
    )

    x_test = normalize(
        x_test,
        train_min,
        train_max
    )

    return {
        "x_train": x_train,
        "y_train": y_train.astype(np.float32),

        "x_val": x_val,
        "y_val": y_val.astype(np.float32),

        "x_test": x_test,
        "y_test": y_test.astype(int),

        "file_names": file_names,

        "train_min": train_min,
        "train_max": train_max,
    }