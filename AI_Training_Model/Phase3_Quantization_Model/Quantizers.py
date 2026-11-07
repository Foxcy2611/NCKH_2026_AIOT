import copy
import re

import numpy as np
import tensorflow as tf

from sklearn.utils.class_weight import compute_class_weight

from Config import (
    SEED,
    REPRESENTATIVE_PER_CLASS,

    QAT_MODEL_PATH,
    QAT_LOG_PATH,

    QAT_EPOCHS,
    QAT_BATCH_SIZE,
    QAT_LEARNING_RATE,
    QAT_PATIENCE,

    QAT_REDUCE_LR_FACTOR,
    QAT_REDUCE_LR_PATIENCE,
    QAT_MIN_LR,
)


# =============================================================================
# REPRESENTATIVE DATASET
# =============================================================================

def choose_representative_indices(
    y_train
):

    rng = np.random.default_rng(
        SEED
    )

    selected = []

    y_int = y_train.astype(int)

    classes = np.unique(
        y_int
    )

    for label in classes:

        indices = np.where(
            y_int == label
        )[0]

        amount = min(
            REPRESENTATIVE_PER_CLASS,
            len(indices)
        )

        chosen = rng.choice(
            indices,
            amount,
            replace=False
        )

        selected.extend(
            chosen
        )

    selected = np.asarray(
        selected,
        dtype=np.int64
    )

    rng.shuffle(
        selected
    )

    return selected


def make_representative_dataset(
    x_train,
    y_train
):

    indices = (
        choose_representative_indices(
            y_train
        )
    )

    def representative_dataset():

        for index in indices:

            yield [
                x_train[
                    index:index + 1
                ].astype(np.float32)
            ]

    return (
        representative_dataset,
        len(indices)
    )


# =============================================================================
# SAVE
# =============================================================================

def save_binary(
    data,
    path
):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        path,
        "wb"
    ) as file:

        file.write(
            data
        )


# =============================================================================
# FP32 TFLITE
# =============================================================================

def convert_fp32(
    model,
    output_path
):

    converter = (
        tf.lite.TFLiteConverter
        .from_keras_model(model)
    )

    data = converter.convert()

    save_binary(
        data,
        output_path
    )

    return data


# =============================================================================
# PTQ FULL INT8
# =============================================================================

def convert_ptq_int8(
    model,
    x_train,
    y_train,
    output_path
):

    (
        representative_dataset,
        representative_count

    ) = make_representative_dataset(
        x_train,
        y_train
    )

    converter = (
        tf.lite.TFLiteConverter
        .from_keras_model(model)
    )

    converter.optimizations = [
        tf.lite.Optimize.DEFAULT
    ]

    converter.representative_dataset = (
        representative_dataset
    )

    converter.target_spec.supported_ops = [
        tf.lite.OpsSet.TFLITE_BUILTINS_INT8
    ]

    converter.inference_input_type = (
        tf.int8
    )

    converter.inference_output_type = (
        tf.int8
    )

    data = converter.convert()

    save_binary(
        data,
        output_path
    )

    return (
        data,
        representative_count
    )


# =============================================================================
# PTQ INT16x8
#
# Activation : INT16
# Weight     : INT8
# =============================================================================

def convert_ptq_int16x8(
    model,
    x_train,
    y_train,
    output_path
):

    (
        representative_dataset,
        representative_count

    ) = make_representative_dataset(
        x_train,
        y_train
    )

    converter = (
        tf.lite.TFLiteConverter
        .from_keras_model(model)
    )

    converter.optimizations = [
        tf.lite.Optimize.DEFAULT
    ]

    converter.representative_dataset = (
        representative_dataset
    )

    converter.target_spec.supported_ops = [
        tf.lite.OpsSet
        .EXPERIMENTAL_TFLITE_BUILTINS_ACTIVATIONS_INT16_WEIGHTS_INT8
    ]

    # Full integer input/output.
    converter.inference_input_type = (
        tf.int16
    )

    converter.inference_output_type = (
        tf.int16
    )

    data = converter.convert()

    save_binary(
        data,
        output_path
    )

    return (
        data,
        representative_count
    )



# =============================================================================
# KERAS 3 -> LEGACY TF_KERAS BRIDGE FOR QAT
# =============================================================================

def _sanitize_layer_config(config):
    """
    Loại các field Keras 3 mà legacy tf_keras
    không hỗ trợ khi deserialize layer.
    """

    config = copy.deepcopy(config)

    # Keras 3 -> legacy tf_keras incompatibilities
    unsupported_keys = [
        "batch_shape",
        "optional",
        "quantization_config",
    ]

    for key in unsupported_keys:
        config.pop(
            key,
            None
        )

    # Keras 3 có thể serialize dtype thành dict.
    dtype = config.get(
        "dtype"
    )

    if isinstance(
        dtype,
        dict
    ):

        dtype_name = (dtype.get("config", {}).get("name"))

        if dtype_name is not None:
            config["dtype"] = dtype_name

    return config


def build_qat_compatible_model(source_model, qat_keras):
    """
    Rebuild một Sequential Keras 3 model bằng legacy tf_keras rồi copy weights.

    Không hard-code riêng V5. Nếu model tương lai dùng Functional API,
    skip connection hoặc custom layer thì bridge này cần được mở rộng.
    """

    if source_model.__class__.__name__ != "Sequential":
        raise NotImplementedError(
            "\nQAT bridge hiện hỗ trợ Sequential model.\n"
            "Model hiện tại không phải Sequential.\n"
            "Nếu model tương lai dùng Functional API / skip connection, "
            "cần mở rộng build_qat_compatible_model()."
        )

    input_shape = tuple(source_model.input_shape[1:])

    legacy_model = qat_keras.Sequential(
        name=f"{source_model.name}_qat_compatible"
    )

    legacy_model.add(
        qat_keras.layers.InputLayer(
            input_shape=input_shape,
            dtype="float32"
        )
    )

    for layer_index, layer in enumerate(source_model.layers):
        class_name = layer.__class__.__name__

        if class_name == "InputLayer":
            continue

        config = _sanitize_layer_config(layer.get_config())

        # TFMOT tách SeparableConv2D thành depthwise + pointwise Conv2D khi
        # quantize_apply(). Nếu model gốc đã có một Conv2D mang tên mặc định
        # "conv2d" (như V6), lớp pointwise do TFMOT sinh ra có thể trùng tên
        # và khiến Sequential từ chối dựng graph. Đổi tên lớp ở bản bridge
        # theo vị trí giữ nguyên hoàn toàn cấu trúc/trọng số nhưng bảo đảm mọi
        # tên đều duy nhất trước khi TFMOT thực hiện graph transform.
        original_name = str(config.get("name", layer.name))
        config["name"] = f"qat_bridge_{layer_index:02d}_{original_name}"

        try:
            legacy_layer = qat_keras.layers.deserialize(
                {
                    "class_name": class_name,
                    "config": config,
                }
            )
        except Exception as error:
            raise NotImplementedError(
                "\nKhông thể rebuild layer cho QAT bridge:\n"
                f"  name : {layer.name}\n"
                f"  type : {class_name}\n\n"
                "Layer/config này chưa tương thích với legacy tf_keras."
            ) from error

        legacy_model.add(legacy_layer)

    # Build weights.
    legacy_model(
        np.zeros((1, *input_shape), dtype=np.float32),
        training=False
    )

    source_weights = source_model.get_weights()
    legacy_weights = legacy_model.get_weights()

    if len(source_weights) != len(legacy_weights):
        raise ValueError(
            "\nSố weight tensor không khớp:\n"
            f"Keras 3 : {len(source_weights)}\n"
            f"tf_keras : {len(legacy_weights)}"
        )

    for index, (source_weight, legacy_weight) in enumerate(
        zip(source_weights, legacy_weights)
    ):
        if source_weight.shape != legacy_weight.shape:
            raise ValueError(
                "\nWeight shape không khớp:\n"
                f"Index   : {index}\n"
                f"Keras 3 : {source_weight.shape}\n"
                f"tf_keras: {legacy_weight.shape}"
            )

    legacy_model.set_weights(source_weights)

    print("\nKeras 3 -> legacy tf_keras bridge: OK")
    print(f"Model : {source_model.name}")
    print(f"Input : {input_shape}")

    return legacy_model


def build_selective_qat_model(base_model, tfmot, qat_keras):
    """
    Chỉ QAT các layer có weight cần lượng tử.

    TFMOT 0.8.x không hỗ trợ gọi quantize_model() trực tiếp với một số layer
    độc lập như BatchNormalization. Các layer không được annotate vẫn được giữ
    trong graph và sẽ được TFLite converter xử lý khi xuất model thật.
    """

    quantizable_layer_names = {
        "Conv2D",
        "DepthwiseConv2D",
        "SeparableConv2D",
        "Dense",
    }

    annotated_names = []
    skipped_names = []

    def annotate_layer(layer):
        class_name = layer.__class__.__name__

        if class_name in quantizable_layer_names:
            annotated_names.append(
                f"{layer.name} ({class_name})"
            )
            return tfmot.quantization.keras.quantize_annotate_layer(
                layer
            )

        skipped_names.append(
            f"{layer.name} ({class_name})"
        )
        return layer

    annotated_model = qat_keras.models.clone_model(
        base_model,
        clone_function=annotate_layer
    )

    # clone_model tạo graph mới. Khôi phục đúng trọng số model FP32 đã train
    # trước khi quantize_apply chèn các fake-quantization wrapper.
    annotated_model.set_weights(
        base_model.get_weights()
    )

    qat_model = tfmot.quantization.keras.quantize_apply(
        annotated_model
    )

    print("\nSelective QAT annotation: OK")
    print("Quantized layers:")
    for name in annotated_names:
        print(f"  + {name}")

    print("Float/pass-through layers:")
    for name in skipped_names:
        print(f"  - {name}")

    return qat_model

def verify_qat_bridge(
    source_model,
    legacy_model,
    x_data
):
    """
    Kiểm tra Keras 3 model và legacy tf_keras model
    có cho cùng output sau khi copy weights hay không.

    Đây là sanity check trước QAT.
    """

    source_prob = (
        source_model.predict(
            x_data,
            verbose=0
        )
        .reshape(-1)
    )

    legacy_prob = (
        legacy_model.predict(
            x_data,
            verbose=0
        )
        .reshape(-1)
    )

    abs_diff = np.abs(
        source_prob
        - legacy_prob
    )

    max_diff = float(
        np.max(abs_diff)
    )

    mean_diff = float(
        np.mean(abs_diff)
    )

    source_pred = (
        source_prob >= 0.5
    ).astype(int)

    legacy_pred = (
        legacy_prob >= 0.5
    ).astype(int)

    changed = int(
        np.sum(
            source_pred
            != legacy_pred
        )
    )

    print(
        "\n"
        "============================================================"
    )

    print(
        "QAT BRIDGE SANITY CHECK"
    )

    print(
        "============================================================"
    )

    print(
        f"Samples              : {len(x_data)}"
    )

    print(
        f"Mean abs difference  : {mean_diff:.10f}"
    )

    print(
        f"Max abs difference   : {max_diff:.10f}"
    )

    print(
        f"Prediction changed   : "
        f"{changed}/{len(x_data)}"
    )

    if changed != 0:

        raise ValueError(
            "\nQAT bridge làm thay đổi prediction "
            "trước khi QAT bắt đầu."
        )

    if max_diff > 1e-5:

        raise ValueError(
            "\nQAT bridge output lệch quá lớn.\n"
            f"Max abs difference = {max_diff}"
        )

    print(
        "QAT bridge verification: PASS"
    )

# =============================================================================
# QAT INT8
# =============================================================================

def convert_qat_int8(
    source_model,

    x_train,
    y_train,

    x_val,
    y_val,

    output_path
):

    try:
        import tensorflow_model_optimization as tfmot

        from tensorflow_model_optimization.python.core.keras.compat import (
            keras as qat_keras
        )

    except ImportError as error:
        raise ImportError(
            "\nQAT cần:\n"
            "pip install tensorflow-model-optimization tf_keras\n"
        ) from error

    # Không load file .keras bằng legacy tf_keras.
    # Model nguồn đã được load thành công bằng Keras 3 ở Quantize_Model.py.
    base_model = build_qat_compatible_model(
        source_model,
        qat_keras
    )

    # =============================================================
    # SANITY CHECK:
    # Keras 3 source vs legacy tf_keras bridge
    # =============================================================

    verify_qat_bridge(
        source_model,
        base_model,
        x_val
    )

    # Insert fake quantization có chọn lọc. Không gọi quantize_model() cho toàn
    # mạng vì BatchNormalization độc lập không nằm trong registry mặc định.
    qat_model = build_selective_qat_model(
        base_model,
        tfmot,
        qat_keras
    )

    qat_model.compile(
        optimizer=qat_keras.optimizers.Adam(
            learning_rate=QAT_LEARNING_RATE
        ),
        loss="binary_crossentropy",
        metrics=["accuracy"]
    )

    QAT_LOG_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    callbacks = [
        qat_keras.callbacks.EarlyStopping(
            monitor="val_loss",
            mode="min",
            patience=QAT_PATIENCE,
            restore_best_weights=True,
            verbose=1
        ),

        qat_keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            mode="min",
            factor=QAT_REDUCE_LR_FACTOR,
            patience=QAT_REDUCE_LR_PATIENCE,
            min_lr=QAT_MIN_LR,
            verbose=1
        ),

        qat_keras.callbacks.CSVLogger(
            str(QAT_LOG_PATH),
            append=False
        ),
    ]

    classes = np.unique(
        y_train.astype(int)
    )

    weights = compute_class_weight(
        class_weight="balanced",
        classes=classes,
        y=y_train.astype(int)
    )

    class_weight_dict = dict(
        zip(
            classes,
            weights
        )
    )

    print(
        "QAT class weights:",
        class_weight_dict
    )

    history = qat_model.fit(
        x_train,
        y_train,
        validation_data=(x_val, y_val),
        epochs=QAT_EPOCHS,
        batch_size=QAT_BATCH_SIZE,
        callbacks=callbacks,
        class_weight=class_weight_dict,
        shuffle=True,
        verbose=1
    )

    QAT_MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    try:
        qat_model.save(str(QAT_MODEL_PATH))
    except Exception as error:
        print("\nWARNING: Không lưu được QAT .keras artifact.")
        print(f"Chi tiết: {error}")

    # QAT -> real Full INT8 TFLite.
    (
        representative_dataset,
        representative_count
    ) = make_representative_dataset(
        x_train,
        y_train
    )

    converter = (
        tf.lite.TFLiteConverter
        .from_keras_model(qat_model)
    )

    converter.optimizations = [
        tf.lite.Optimize.DEFAULT
    ]

    converter.representative_dataset = representative_dataset

    converter.target_spec.supported_ops = [
        tf.lite.OpsSet.TFLITE_BUILTINS_INT8
    ]

    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8

    data = converter.convert()

    save_binary(
        data,
        output_path
    )

    return (
        data,
        representative_count,
        history
    )


# =============================================================================
# TFLITE -> C HEADER
# =============================================================================

def convert_to_header(
    tflite_data,
    output_path,
    array_name
):

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    safe_name = re.sub(
        r"[^A-Za-z0-9_]",
        "_",
        array_name
    )

    guard = (
        safe_name.upper()
        + "_H"
    )

    rows = []

    for start in range(
        0,
        len(tflite_data),
        12
    ):

        chunk = tflite_data[
            start:start + 12
        ]

        rows.append(
            "    "
            +
            ", ".join(
                f"0x{byte:02x}"
                for byte in chunk
            )
        )

    array_text = ",\n".join(
        rows
    )

    text = f"""#ifndef {guard}
#define {guard}

#include <stdint.h>

// Generated from TFLite.
// Size: {len(tflite_data)} bytes.

const unsigned int {safe_name}_len = {len(tflite_data)};

const unsigned char {safe_name}[]
__attribute__((aligned(16))) = {{
{array_text}
}};

#endif
"""

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            text
        )
