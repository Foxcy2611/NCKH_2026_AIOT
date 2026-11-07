"""Đồng bộ kết quả Validation/Test của ma trận C vào hai summary chuẩn.

Phạm vi cố định:
- F0, pre_0, mel_40, fft_2048;
- C1, C2, C3, C4;
- mỗi cấu hình dùng ba seed 42, 43 và 44.

Script không tạo một bảng summary thứ hai. Nó dùng đúng pipeline của
02_Preprocess.py và 04_Evaluate.py, chỉ bỏ qua trial khi đồng thời có:
prediction, config SHA và model SHA khớp artifact hiện tại. Kết quả cuối
duy nhất là results/val_summary.csv, results/test_summary.csv cùng prediction
theo từng checkpoint.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

import numpy as np


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


SEEDS = (42, 43, 44)
ALL_VARIANTS = (
    "F0",
    "pre_0",
    "mel_40",
    "fft_2048",
    "combo_pre0_mel40",
    "combo_pre0_fft2048",
    "combo_mel40_fft2048",
    "combo_pre0_mel40_fft2048",
)


def find_frontend_root() -> Path:
    current = Path(__file__).resolve()
    for parent in (current.parent, *current.parents):
        if (
            (parent / "frontend_core.py").is_file()
            and (parent / "02_Preprocess.py").is_file()
            and (parent / "04_Evaluate.py").is_file()
        ):
            return parent
    raise FileNotFoundError("Không tìm thấy thư mục Frontend_Benchmarking")


def load_script(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Không thể nạp script: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def reconcile_dataset_fingerprints(
    root: Path,
    summary_path: Path,
    expected_trials: list[str],
    split: str,
) -> int:
    """Bổ sung fingerprint chỉ sau khi prediction khớp tuyệt đối tensor split.

    Hàm không inference và không thay metric. Nó kiểm tra tên WAV, nhãn, Accuracy,
    FN/FP, config SHA rồi mới sao chép fingerprint từ feature metadata vào summary.
    """
    rows = read_csv(summary_path)
    by_trial = {row["trial_id"]: row for row in rows}
    if len(by_trial) != len(rows):
        raise RuntimeError(f"{summary_path.name} có trial_id trùng lặp")

    changed = 0
    for trial in expected_trials:
        row = by_trial.get(trial)
        if row is None:
            raise RuntimeError(f"{summary_path.name} thiếu {trial}")

        variant = row["variant_id"]
        feature_dir = root / "artifacts" / "features" / variant
        feature_metadata = json.loads(
            (feature_dir / f"{split}_metadata.json").read_text(encoding="utf-8")
        )
        expected_files = np.load(
            feature_dir / f"Files_{split}.npy", allow_pickle=False
        ).astype(str)
        expected_labels = np.load(
            feature_dir / f"Y_{split}.npy", allow_pickle=False
        ).astype(int)
        prediction_path = (
            root / "artifacts" / "models" / trial / f"{split}_predictions.csv"
        )
        predictions = read_csv(prediction_path)

        actual_files = np.asarray(
            [record["file"].replace("\\", "/") for record in predictions],
            dtype=str,
        )
        actual_labels = np.asarray(
            [int(record["true_label"]) for record in predictions], dtype=int
        )
        predicted_labels = np.asarray(
            [int(record["predicted_label"]) for record in predictions], dtype=int
        )
        if not (
            len(predictions) == len(expected_files)
            and np.array_equal(actual_files, expected_files)
            and np.array_equal(actual_labels, expected_labels)
        ):
            raise RuntimeError(
                f"{trial}: {split}_predictions.csv không khớp Files/Y_{split}.npy"
            )

        accuracy = float(np.mean(actual_labels == predicted_labels))
        asthma_fn = int(np.sum((actual_labels == 0) & (predicted_labels == 1)))
        non_asthma_fp = int(np.sum((actual_labels == 1) & (predicted_labels == 0)))
        if not (
            abs(float(row["accuracy"]) - accuracy) < 1e-12
            and int(row["asthma_fn"]) == asthma_fn
            and int(row["non_asthma_fp"]) == non_asthma_fp
            and row["config_sha256"] == feature_metadata["config_sha256"]
        ):
            raise RuntimeError(f"{trial}: metric/config summary không khớp prediction")

        fingerprint = feature_metadata["dataset_fingerprint"]
        current = row.get("dataset_fingerprint", "")
        if current and current != fingerprint:
            raise RuntimeError(f"{trial}: dataset fingerprint xung đột")
        if not current:
            row["dataset_fingerprint"] = fingerprint
            changed += 1

    if changed:
        fields = list(rows[0])
        if "dataset_fingerprint" not in fields:
            fields.append("dataset_fingerprint")
        temp_path = summary_path.with_suffix(".csv.tmp")
        with temp_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        temp_path.replace(summary_path)
    return changed


def validate_canonical_summary(
    root: Path,
    summary_path: Path,
    expected_trials: list[str],
    split: str,
) -> None:
    rows = read_csv(summary_path)
    by_trial = {row["trial_id"]: row for row in rows}
    if len(by_trial) != len(rows):
        raise RuntimeError(f"{summary_path.name} có trial_id trùng lặp")

    missing = sorted(set(expected_trials) - set(by_trial))
    if missing:
        raise RuntimeError(
            f"{summary_path.name} chưa đủ ma trận 24 trial; missing={missing}"
        )

    for trial in expected_trials:
        row = by_trial[trial]
        model_path = root / "artifacts" / "models" / trial / "Model_Asthma.keras"
        metadata_path = model_path.parent / "training_metadata.json"
        prediction_path = model_path.parent / f"{split}_predictions.csv"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not prediction_path.is_file():
            raise RuntimeError(f"{trial}: thiếu {split}_predictions.csv")
        if row.get("config_sha256") != metadata.get("config_sha256"):
            raise RuntimeError(f"{trial}: config SHA trong {split} summary không khớp checkpoint")
        if row.get("model_sha256") != sha256(model_path):
            raise RuntimeError(f"{trial}: model SHA trong {split} summary không khớp checkpoint")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Đồng bộ Validation/Test của đủ 24 checkpoint C vào results/."
    )
    parser.add_argument(
        "--dataset-root",
        help="Tùy chọn đường dẫn Dataset_Chia_V2; để trống để frontend_core tự tìm.",
    )
    parser.add_argument(
        "--fingerprint-only",
        action="store_true",
        help=(
            "Chỉ xác minh prediction/metric rồi bổ sung dataset_fingerprint; "
            "không preprocess và không inference."
        ),
    )
    args = parser.parse_args()

    root = find_frontend_root()
    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    import frontend_core as fc

    preprocess = load_script(root / "02_Preprocess.py", "cd_preprocess")
    evaluate = load_script(root / "04_Evaluate.py", "cd_evaluate")

    plan_rows = {row["variant_id"]: row for row in fc.plans()}
    absent_plans = sorted(set(ALL_VARIANTS) - set(plan_rows))
    if absent_plans:
        raise RuntimeError(f"experiment_plan.csv thiếu variant: {absent_plans}")

    expected_trials = [
        fc.trial_id(variant, "V1", seed)
        for variant in ALL_VARIANTS
        for seed in SEEDS
    ]
    assert len(expected_trials) == 24

    for trial in expected_trials:
        model_dir = root / "artifacts" / "models" / trial
        missing_files = [
            path
            for path in (
                model_dir / "Model_Asthma.keras",
                model_dir / "training_metadata.json",
            )
            if not path.is_file()
        ]
        if missing_files:
            raise FileNotFoundError(
                f"Checkpoint {trial} chưa đầy đủ: "
                + ", ".join(str(path) for path in missing_files)
            )

        metadata = json.loads(
            (model_dir / "training_metadata.json").read_text(encoding="utf-8")
        )
        variant = metadata.get("variant_id")
        if variant not in plan_rows:
            raise RuntimeError(f"{trial}: variant_id không có trong experiment_plan.csv")
        if metadata.get("config_sha256") != plan_rows[variant]["config_sha256"]:
            raise RuntimeError(f"{trial}: config SHA không khớp experiment_plan.csv")

    if args.fingerprint_only:
        val_summary_path = root / "results" / "val_summary.csv"
        test_summary_path = root / "results" / "test_summary.csv"
        filled_val = reconcile_dataset_fingerprints(
            root, val_summary_path, expected_trials, "val"
        )
        filled_test = reconcile_dataset_fingerprints(
            root, test_summary_path, expected_trials, "test"
        )
        validate_canonical_summary(root, val_summary_path, expected_trials, "val")
        validate_canonical_summary(root, test_summary_path, expected_trials, "test")
        print("Fingerprint đã bổ sung - Validation:", filled_val)
        print("Fingerprint đã bổ sung - Test      :", filled_test)
        print("Không preprocess, không inference.")
        return

    dataset = fc.dataset_root(args.dataset_root)
    print("Frontend root:", root)
    print("Dataset root :", dataset)
    print("Mục tiêu     : đồng bộ đúng provenance cho đủ 24 checkpoint")

    # Tạo/kiểm tra tensor Validation và Test cho cả tám variant bằng pipeline chuẩn.
    # run_split tự bỏ qua artifact đã có nếu provenance còn hợp lệ.
    for variant in ALL_VARIANTS:
        for split in ("val", "test"):
            preprocess.run_split(dataset, plan_rows[variant], split, False)

    try:
        import tensorflow as tf
    except ImportError as exc:
        raise SystemExit("Cần TensorFlow trong môi trường Python hiện tại") from exc

    val_summary_path = root / "results" / "val_summary.csv"
    val_rows = {row["trial_id"]: row for row in read_csv(val_summary_path)}

    # Validation có thể chạy lại an toàn. Chỉ giữ dòng đã có đủ prediction và
    # hai SHA khớp artifact hiện tại; mọi dòng legacy/stale sẽ được thay tại chỗ.
    for variant in ALL_VARIANTS:
        row = plan_rows[variant]
        for seed in SEEDS:
            trial = fc.trial_id(variant, "V1", seed)
            model_path = root / "artifacts" / "models" / trial / "Model_Asthma.keras"
            prediction_path = model_path.parent / "val_predictions.csv"
            current = val_rows.get(trial)
            metadata = json.loads(
                (model_path.parent / "training_metadata.json").read_text(encoding="utf-8")
            )
            is_current = bool(
                current
                and prediction_path.is_file()
                and current.get("config_sha256") == metadata.get("config_sha256")
                and current.get("model_sha256") == sha256(model_path)
            )
            if is_current:
                print("SKIP Validation đúng provenance:", trial)
                continue
            evaluate.evaluate(row, trial, "val", True, tf)
            val_rows = {r["trial_id"]: r for r in read_csv(val_summary_path)}

    filled_val = reconcile_dataset_fingerprints(
        root, val_summary_path, expected_trials, "val"
    )
    validate_canonical_summary(root, val_summary_path, expected_trials, "val")

    summary_path = root / "results" / "test_summary.csv"
    summary_rows = {row["trial_id"] for row in read_csv(summary_path)}

    for variant in ALL_VARIANTS:
        row = plan_rows[variant]
        for seed in SEEDS:
            trial = fc.trial_id(variant, "V1", seed)
            prediction_path = (
                root / "artifacts" / "models" / trial / "test_predictions.csv"
            )
            has_summary = trial in summary_rows
            if prediction_path.is_file() and has_summary:
                current_rows = {row["trial_id"]: row for row in read_csv(summary_path)}
                current = current_rows[trial]
                model_path = root / "artifacts" / "models" / trial / "Model_Asthma.keras"
                metadata = json.loads(
                    (model_path.parent / "training_metadata.json").read_text(encoding="utf-8")
                )
                if (
                    current.get("config_sha256") == metadata.get("config_sha256")
                    and current.get("model_sha256") == sha256(model_path)
                ):
                    print("SKIP đã hoàn tất và đúng provenance:", trial)
                    continue
                raise RuntimeError(
                    f"{trial}: đã có prediction nhưng summary mang SHA cũ; "
                    "không tự ghi đè kết quả Test"
                )
            if prediction_path.is_file() and not has_summary:
                raise RuntimeError(
                    f"{trial}: test_predictions.csv và test_summary.csv không đồng bộ; "
                    "không tự ghi đè Test"
                )
            # Nếu summary cũ tồn tại nhưng prediction không còn, metric đó không
            # đủ bằng chứng provenance. evaluate() sẽ inference và thay đúng dòng.
            evaluate.evaluate(row, trial, "test", False, tf)
            summary_rows.add(trial)

    filled_test = reconcile_dataset_fingerprints(
        root, summary_path, expected_trials, "test"
    )
    validate_canonical_summary(root, summary_path, expected_trials, "test")
    print("HOÀN TẤT:", val_summary_path)
    print("HOÀN TẤT:", summary_path)
    print("Fingerprint đã bổ sung - Validation:", filled_val)
    print("Fingerprint đã bổ sung - Test      :", filled_test)
    print("Ma trận C Validation: 24 / 24")
    print("Ma trận C Test      : 24 / 24")


if __name__ == "__main__":
    main()
