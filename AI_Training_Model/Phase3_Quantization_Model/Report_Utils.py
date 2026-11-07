import csv
import os

import numpy as np

from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    classification_report,
)

from Config import (
    THRESHOLD,
    CLASS_NAMES,
    PREDICTION_PATH,
    REPORT_PATH,
)


def evaluate(
    y_true,
    probabilities
):

    predictions = (
        probabilities
        >= THRESHOLD
    ).astype(int)

    accuracy = accuracy_score(
        y_true,
        predictions
    )

    matrix = confusion_matrix(
        y_true,
        predictions,
        labels=[0, 1]
    )

    report = classification_report(
        y_true,
        predictions,
        labels=[0, 1],
        target_names=CLASS_NAMES,
        digits=4,
        zero_division=0
    )

    return {
        "probabilities": probabilities,
        "predictions": predictions,
        "accuracy": accuracy,
        "matrix": matrix,
        "report": report,
    }


def save_predictions(
    file_names,
    y_test,
    results
):

    PREDICTION_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    model_names = list(
        results.keys()
    )

    with open(
        PREDICTION_PATH,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.writer(
            file
        )

        header = [
            "file_name",
            "true_label",
        ]

        for name in model_names:

            header.extend([
                f"{name}_probability_non_asthma",
                f"{name}_prediction",
            ])

        writer.writerow(
            header
        )

        for index in range(
            len(y_test)
        ):

            row = [
                file_names[index],
                int(y_test[index]),
            ]

            for name in model_names:

                row.extend([
                    float(
                        results[name][
                            "probabilities"
                        ][index]
                    ),

                    int(
                        results[name][
                            "predictions"
                        ][index]
                    ),
                ])

            writer.writerow(
                row
            )


def write_report(
    results,
    model_paths,
    extra_info
):

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fp32_size = os.path.getsize(
        model_paths["TFLite_FP32"]
    )

    lines = []

    lines.append(
        "============================================================"
    )

    lines.append(
        "QUANTIZATION COMPARISON"
    )

    lines.append(
        "============================================================\n"
    )

    lines.append(
        f"Representative samples: "
        f"{extra_info['representative_count']}"
    )

    lines.append(
        f"TRAIN_MIN: "
        f"{extra_info['train_min']}"
    )

    lines.append(
        f"TRAIN_MAX: "
        f"{extra_info['train_max']}"
    )

    lines.append(
        f"Threshold: {THRESHOLD}\n"
    )

    # =================================================================
    # SIZE
    # =================================================================

    lines.append(
        "MODEL SIZE"
    )

    lines.append(
        "------------------------------------------------------------"
    )

    for name, path in model_paths.items():

        size = os.path.getsize(
            path
        )

        lines.append(
            f"{name}: "
            f"{size} bytes"
        )

        if name != "TFLite_FP32":

            reduction = (
                100.0
                *
                (
                    1.0
                    - size / fp32_size
                )
            )

            lines.append(
                f"  Reduction vs FP32 TFLite: "
                f"{reduction:.2f}%"
            )

    # =================================================================
    # RESULTS
    # =================================================================

    for name, result in results.items():

        lines.append(
            "\n"
            "============================================================"
        )

        lines.append(
            name
        )

        lines.append(
            "============================================================"
        )

        lines.append(
            f"Accuracy: "
            f"{result['accuracy']:.6f}\n"
        )

        lines.append(
            "Confusion Matrix:"
        )

        lines.append(
            np.array2string(
                result["matrix"]
            )
        )

        lines.append(
            "\nClassification Report:"
        )

        lines.append(
            result["report"]
        )

    # =================================================================
    # PREDICTION CHANGES
    # =================================================================

    fp32_predictions = (
        results["TFLite_FP32"][
            "predictions"
        ]
    )

    lines.append(
        "\n"
        "============================================================"
    )

    lines.append(
        "PREDICTION CHANGES VS FP32"
    )

    lines.append(
        "============================================================"
    )

    for name, result in results.items():

        if name == "TFLite_FP32":
            continue

        changed = int(
            np.sum(
                fp32_predictions
                != result["predictions"]
            )
        )

        lines.append(
            f"{name}: "
            f"{changed}/{len(fp32_predictions)}"
        )

    # PTQ vs QAT specifically.
    ptq = results[
        "PTQ_INT8"
    ]["predictions"]

    qat = results[
        "QAT_INT8"
    ]["predictions"]

    changed = int(
        np.sum(
            ptq != qat
        )
    )

    lines.append(
        "\nPTQ_INT8 vs QAT_INT8: "
        f"{changed}/{len(ptq)} changed"
    )

    # PTQ INT8 vs INT16x8.
    int16 = results[
        "PTQ_INT16x8"
    ]["predictions"]

    changed = int(
        np.sum(
            ptq != int16
        )
    )

    lines.append(
        "PTQ_INT8 vs PTQ_INT16x8: "
        f"{changed}/{len(ptq)} changed"
    )

    text = "\n".join(
        lines
    )

    with open(
        REPORT_PATH,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            text
        )

    return text