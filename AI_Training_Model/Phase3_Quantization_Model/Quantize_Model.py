import os

os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"


import numpy as np
import tensorflow as tf


from Config import (
    SEED,
    MODEL_VERSION,

    MODEL_PATH,

    OUTPUT_DIR,
    MODEL_DIR,
    HEADER_DIR,
    QAT_DIR,

    FP32_TFLITE_PATH,

    PTQ_INT8_PATH,
    QAT_INT8_PATH,
    PTQ_INT16X8_PATH,

    PTQ_INT8_HEADER,
    QAT_INT8_HEADER,
    PTQ_INT16X8_HEADER,
)

from Data_Utils import (
    load_dataset,
)

from Quantizers import (
    convert_fp32,
    convert_ptq_int8,
    convert_qat_int8,
    convert_ptq_int16x8,
    convert_to_header,
)

from Inference import (
    run_keras,
    run_tflite,
)

from Report_Utils import (
    evaluate,
    save_predictions,
    write_report,
)


# =============================================================================
# MAIN
# =============================================================================

def main():

    tf.keras.utils.set_random_seed(
        SEED
    )

    np.random.seed(
        SEED
    )

    # =================================================================
    # OUTPUT DIRS
    # =================================================================

    for directory in [
        OUTPUT_DIR,
        MODEL_DIR,
        HEADER_DIR,
        QAT_DIR,
    ]:

        directory.mkdir(
            parents=True,
            exist_ok=True
        )

    # =================================================================
    # 1. LOAD
    # =================================================================

    print(
        "\n"
        "============================================================"
    )

    print(
        "1. LOAD MODEL + DATA"
    )

    print(
        "============================================================"
    )

    print(
        f"Model:\n{MODEL_PATH}"
    )

    model = (
        tf.keras.models.load_model(
            MODEL_PATH,
            compile=False
        )
    )

    data = load_dataset()

    print(
        f"\nTrain: "
        f"{data['x_train'].shape}"
    )

    print(
        f"Val:   "
        f"{data['x_val'].shape}"
    )

    print(
        f"Test:  "
        f"{data['x_test'].shape}"
    )

    print(
        f"\nTRAIN_MIN="
        f"{data['train_min']}"
    )

    print(
        f"TRAIN_MAX="
        f"{data['train_max']}"
    )

    # =================================================================
    # 2. FP32 TFLITE
    # =================================================================

    print(
        "\n"
        "============================================================"
    )

    print(
        "2. KERAS -> TFLITE FP32"
    )

    print(
        "============================================================"
    )

    convert_fp32(
        model,
        FP32_TFLITE_PATH
    )

    # =================================================================
    # 3. PTQ INT8
    # =================================================================

    print(
        "\n"
        "============================================================"
    )

    print(
        "3. PTQ FULL INT8"
    )

    print(
        "============================================================"
    )

    (
        ptq_int8_data,
        representative_count

    ) = convert_ptq_int8(

        model,

        data["x_train"],
        data["y_train"],

        PTQ_INT8_PATH
    )

    convert_to_header(
        ptq_int8_data,
        PTQ_INT8_HEADER,
        f"{MODEL_VERSION.lower()}_ptq_int8_model"
    )

    # =================================================================
    # 4. QAT INT8
    # =================================================================

    print(
        "\n"
        "============================================================"
    )

    print(
        "4. QAT INT8"
    )

    print(
        "============================================================"
    )

    (
        qat_int8_data,
        _,
        qat_history

    ) = convert_qat_int8(

        model,

        data["x_train"],
        data["y_train"],

        data["x_val"],
        data["y_val"],

        QAT_INT8_PATH
    )

    convert_to_header(
        qat_int8_data,
        QAT_INT8_HEADER,
        f"{MODEL_VERSION.lower()}_qat_int8_model"
    )

    # =================================================================
    # 5. PTQ INT16x8
    # =================================================================

    print(
        "\n"
        "============================================================"
    )

    print(
        "5. PTQ INT16x8"
    )

    print(
        "============================================================"
    )

    (
        int16x8_data,
        _

    ) = convert_ptq_int16x8(

        model,

        data["x_train"],
        data["y_train"],

        PTQ_INT16X8_PATH
    )

    convert_to_header(
        int16x8_data,
        PTQ_INT16X8_HEADER,
        f"{MODEL_VERSION.lower()}_ptq_int16x8_model"
    )

    # =================================================================
    # 6. TEST INFERENCE
    # =================================================================

    print(
        "\n"
        "============================================================"
    )

    print(
        "6. EVALUATE ALL MODELS"
    )

    print(
        "============================================================"
    )

    # -----------------------------------------------------------------
    # KERAS
    # -----------------------------------------------------------------

    keras_prob = run_keras(
        model,
        data["x_test"]
    )

    # -----------------------------------------------------------------
    # FP32 TFLITE
    # -----------------------------------------------------------------

    (
        fp32_prob,
        fp32_info

    ) = run_tflite(

        FP32_TFLITE_PATH,
        data["x_test"]
    )

    # -----------------------------------------------------------------
    # PTQ INT8
    # -----------------------------------------------------------------

    (
        ptq_int8_prob,
        ptq_info

    ) = run_tflite(

        PTQ_INT8_PATH,
        data["x_test"]
    )

    # -----------------------------------------------------------------
    # QAT INT8
    # -----------------------------------------------------------------

    (
        qat_int8_prob,
        qat_info

    ) = run_tflite(

        QAT_INT8_PATH,
        data["x_test"]
    )

    # -----------------------------------------------------------------
    # PTQ INT16x8
    # -----------------------------------------------------------------

    (
        int16x8_prob,
        int16_info

    ) = run_tflite(

        PTQ_INT16X8_PATH,
        data["x_test"]
    )

    # =================================================================
    # 7. METRICS
    # =================================================================

    y_test = data[
        "y_test"
    ]

    results = {

        "Keras_FP32":
            evaluate(
                y_test,
                keras_prob
            ),

        "TFLite_FP32":
            evaluate(
                y_test,
                fp32_prob
            ),

        "PTQ_INT8":
            evaluate(
                y_test,
                ptq_int8_prob
            ),

        "QAT_INT8":
            evaluate(
                y_test,
                qat_int8_prob
            ),

        "PTQ_INT16x8":
            evaluate(
                y_test,
                int16x8_prob
            ),
    }

    # =================================================================
    # 8. SAVE PREDICTIONS
    # =================================================================

    save_predictions(

        data["file_names"],

        y_test,

        results
    )

    # =================================================================
    # 9. REPORT
    # =================================================================

    model_paths = {

        "Keras_FP32":
            MODEL_PATH,

        "TFLite_FP32":
            FP32_TFLITE_PATH,

        "PTQ_INT8":
            PTQ_INT8_PATH,

        "QAT_INT8":
            QAT_INT8_PATH,

        "PTQ_INT16x8":
            PTQ_INT16X8_PATH,
    }

    report = write_report(

        results,

        model_paths,

        {
            "representative_count":
                representative_count,

            "train_min":
                data["train_min"],

            "train_max":
                data["train_max"],
        }
    )

    # =================================================================
    # TERMINAL SUMMARY
    # =================================================================

    print(
        "\n"
        "============================================================"
    )

    print(
        "FINAL RESULT"
    )

    print(
        "============================================================"
    )

    for name, result in results.items():

        print(
            f"{name:<16} : "
            f"{result['accuracy'] * 100:.2f}%"
        )

    print(
        "\n"
        f"{report}"
    )


if __name__ == "__main__":
    main()