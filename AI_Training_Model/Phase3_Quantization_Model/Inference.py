import numpy as np
import tensorflow as tf


def run_keras(
    model,
    x_test
):

    probabilities = (
        model.predict(
            x_test,
            verbose=0
        )
        .reshape(-1)
    )

    return probabilities.astype(
        np.float32
    )


def quantize_input(
    sample,
    dtype,
    scale,
    zero_point
):

    q = np.round(
        sample / scale
        + zero_point
    )

    limits = np.iinfo(
        dtype
    )

    q = np.clip(
        q,
        limits.min,
        limits.max
    )

    return q.astype(
        dtype
    )


def dequantize_output(
    output,
    scale,
    zero_point
):

    return (
        output.astype(np.float32)
        - zero_point
    ) * scale


def run_tflite(
    model_path,
    x_test
):

    interpreter = tf.lite.Interpreter(
        model_path=str(model_path)
    )

    interpreter.allocate_tensors()

    input_detail = (
        interpreter
        .get_input_details()[0]
    )

    output_detail = (
        interpreter
        .get_output_details()[0]
    )

    input_dtype = (
        input_detail["dtype"]
    )

    output_dtype = (
        output_detail["dtype"]
    )

    probabilities = []

    for sample in x_test:

        # =============================================================
        # INPUT
        # =============================================================

        if input_dtype == np.float32:

            model_input = (
                sample
                .astype(np.float32)
            )

        elif input_dtype in (
            np.int8,
            np.int16
        ):

            (
                input_scale,
                input_zero
            ) = input_detail[
                "quantization"
            ]

            if input_scale <= 0:
                raise ValueError(
                    "Input scale không hợp lệ"
                )

            model_input = quantize_input(
                sample,
                input_dtype,
                input_scale,
                input_zero
            )

        else:

            raise TypeError(
                f"Không hỗ trợ input dtype: "
                f"{input_dtype}"
            )

        model_input = model_input[
            np.newaxis,
            ...
        ]

        interpreter.set_tensor(
            input_detail["index"],
            model_input
        )

        interpreter.invoke()

        output = interpreter.get_tensor(
            output_detail["index"]
        )

        # =============================================================
        # OUTPUT
        # =============================================================

        if output_dtype == np.float32:

            output_float = output

        elif output_dtype in (
            np.int8,
            np.int16
        ):

            (
                output_scale,
                output_zero
            ) = output_detail[
                "quantization"
            ]

            output_float = (
                dequantize_output(
                    output,
                    output_scale,
                    output_zero
                )
            )

        else:

            raise TypeError(
                f"Không hỗ trợ output dtype: "
                f"{output_dtype}"
            )

        probabilities.append(
            float(
                output_float
                .reshape(-1)[0]
            )
        )

    info = {

        "input_shape":
            input_detail["shape"].tolist(),

        "input_dtype":
            str(input_dtype),

        "input_quantization":
            input_detail["quantization"],

        "output_shape":
            output_detail["shape"].tolist(),

        "output_dtype":
            str(output_dtype),

        "output_quantization":
            output_detail["quantization"],
    }

    return (
        np.asarray(
            probabilities,
            dtype=np.float32
        ),
        info
    )