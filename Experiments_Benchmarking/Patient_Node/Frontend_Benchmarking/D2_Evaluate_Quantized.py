"""D2 - đánh giá FP32 và các model lượng tử trên Validation/Test.

Đầu ra gồm prediction từng file, accuracy, confusion matrix, classification
report từng method và báo cáo riêng cho mỗi split. Test là historical Test đã
được dùng tại bước C; kết quả Test không được dùng để chọn lại model/method.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from d_quantization_core import (
    D_ARTIFACTS, D_RESULTS, METHOD_SPECS, PLAN_PATH, atomic_json,
    binary_metrics, load_d_plan, load_split, run_tflite, sha256_file,
    trial_paths, utc_now, verify_trial_against_plan, write_csv,
)
from frontend_core import read_json, read_rows

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

SUMMARY_FIELDS = [
    'plan_sha256', 'split', 'priority_rank', 'model_role', 'trial_id', 'variant_id',
    'seed', 'method_id', 'training_mode',
    'integer_mode', 'experimental', 'accuracy', 'balanced_accuracy',
    'macro_f1', 'asthma_precision', 'asthma_recall', 'asthma_f1',
    'non_asthma_precision', 'non_asthma_recall', 'non_asthma_f1',
    'asthma_fn', 'non_asthma_fp', 'prediction_changes_vs_fp32',
    'mean_abs_probability_delta', 'max_abs_probability_delta',
    'model_size_bytes', 'input_dtype', 'output_dtype', 'model_sha256',
]


def _metric(value) -> str:
    return f'{float(value):.4f}'


def classification_rows(summary: dict, confusion: list[list[int]]) -> list[dict]:
    """Tạo classification report hai lớp từ metrics và confusion matrix."""
    asthma_support = int(confusion[0][0]) + int(confusion[0][1])
    non_support = int(confusion[1][0]) + int(confusion[1][1])
    total = asthma_support + non_support
    class_rows = [
        {
            'class_name': 'Asthma',
            'label': 0,
            'precision': float(summary['asthma_precision']),
            'recall': float(summary['asthma_recall']),
            'f1_score': float(summary['asthma_f1']),
            'support': asthma_support,
        },
        {
            'class_name': 'Non-Asthma',
            'label': 1,
            'precision': float(summary['non_asthma_precision']),
            'recall': float(summary['non_asthma_recall']),
            'f1_score': float(summary['non_asthma_f1']),
            'support': non_support,
        },
    ]
    class_rows.extend([
        {
            'class_name': 'accuracy',
            'label': '',
            'precision': '',
            'recall': '',
            'f1_score': float(summary['accuracy']),
            'support': total,
        },
        {
            'class_name': 'macro avg',
            'label': '',
            'precision': sum(float(row['precision']) for row in class_rows) / 2.0,
            'recall': sum(float(row['recall']) for row in class_rows) / 2.0,
            'f1_score': float(summary['macro_f1']),
            'support': total,
        },
        {
            'class_name': 'weighted avg',
            'label': '',
            'precision': sum(
                float(row['precision']) * int(row['support']) for row in class_rows[:2]
            ) / total,
            'recall': sum(
                float(row['recall']) * int(row['support']) for row in class_rows[:2]
            ) / total,
            'f1_score': sum(
                float(row['f1_score']) * int(row['support']) for row in class_rows[:2]
            ) / total,
            'support': total,
        },
    ])
    return class_rows


def write_detail_reports(
    result_dir: Path,
    summary: dict,
    confusion: list[list[int]],
    split: str,
) -> list[dict]:
    """Xuất confusion matrix và classification report cạnh prediction của model."""
    rows = classification_rows(summary, confusion)
    write_csv(
        result_dir / f'{split}_confusion_matrix.csv',
        [
            {
                'actual_class': 'Asthma',
                'predicted_asthma': int(confusion[0][0]),
                'predicted_non_asthma': int(confusion[0][1]),
            },
            {
                'actual_class': 'Non-Asthma',
                'predicted_asthma': int(confusion[1][0]),
                'predicted_non_asthma': int(confusion[1][1]),
            },
        ],
        ['actual_class', 'predicted_asthma', 'predicted_non_asthma'],
    )
    write_csv(
        result_dir / f'{split}_classification_report.csv',
        rows,
        ['class_name', 'label', 'precision', 'recall', 'f1_score', 'support'],
    )
    text_lines = [
        f'Accuracy: {float(summary["accuracy"]):.6f}',
        '',
        f'{"Class":<16}{"Precision":>12}{"Recall":>12}{"F1-score":>12}{"Support":>10}',
    ]
    for row in rows:
        precision = '' if row['precision'] == '' else f'{float(row["precision"]):.4f}'
        recall = '' if row['recall'] == '' else f'{float(row["recall"]):.4f}'
        text_lines.append(
            f'{row["class_name"]:<16}{precision:>12}{recall:>12}'
            f'{float(row["f1_score"]):>12.4f}{int(row["support"]):>10}'
        )
    text_lines.extend([
        '',
        'Confusion matrix (actual rows × predicted columns):',
        '                       Pred Asthma  Pred Non-Asthma',
        f'Actual Asthma        {int(confusion[0][0]):>12}  {int(confusion[0][1]):>16}',
        f'Actual Non-Asthma    {int(confusion[1][0]):>12}  {int(confusion[1][1]):>16}',
        '',
    ])
    path = result_dir / f'{split}_classification_report.txt'
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + '.pending')
    pending.write_text('\n'.join(text_lines), encoding='utf-8')
    pending.replace(path)
    return rows


def write_split_report(rows: list[dict], plan: dict, split: str) -> None:
    """Tạo CSV/report riêng cho Validation hoặc historical Test."""
    if split not in ('val', 'test'):
        raise ValueError(split)
    split_title = 'Validation' if split == 'val' else 'Historical Test'
    split_dir = D_RESULTS / ('Validation' if split == 'val' else 'Test')
    trial_order = {
        row['trial_id']: int(row['priority_rank']) for row in plan['trials']
    }
    method_order = {
        'KERAS_FP32': 0,
        **{
            row['method_id']: index
            for index, row in enumerate(plan['methods'], start=1)
        },
    }
    current = [
        row for row in rows
        if row.get('plan_sha256') == plan['plan_sha256']
        and row.get('split') == split
        and row.get('trial_id') in trial_order
        and row.get('method_id') in method_order
    ]
    current.sort(key=lambda row: (
        trial_order[row['trial_id']], method_order[row['method_id']]
    ))

    lines = [
        f'# Báo cáo lượng tử hóa Frontend — {split_title}',
        '',
        f'- Plan SHA256: `{plan["plan_sha256"]}`',
        f'- Split đánh giá: **{split_title}**',
        f'- Test accessed: **{str(split == "test").lower()}**',
        '- Thứ tự checkpoint được bàn giao từ phân tích bước C.',
        '',
        '## Phạm vi checkpoint',
        '',
        '| Ưu tiên | Vai trò | Trial | Variant | Input |',
        '|---:|---|---|---|---|',
    ]
    for trial in sorted(plan['trials'], key=lambda row: row['priority_rank']):
        shape = ' × '.join(str(value) for value in trial['input_shape'])
        lines.append(
            f'| {trial["priority_rank"]} | {trial["model_role"]} | '
            f'`{trial["trial_id"]}` | `{trial["variant_id"]}` | `{shape}` |'
        )

    lines.extend([
        '',
        f'## Kết quả {split_title}',
        '',
        '| Ưu tiên | Trial | Method | Accuracy | Macro F1 | Asthma Recall | Non-Asthma Recall | Đổi nhãn so với FP32 | Kích thước (byte) | I/O |',
        '|---:|---|---|---:|---:|---:|---:|---:|---:|---|',
    ])
    for row in current:
        lines.append(
            f'| {row["priority_rank"]} | `{row["trial_id"]}` | '
            f'`{row["method_id"]}` | {_metric(row["accuracy"])} | '
            f'{_metric(row["macro_f1"])} | {_metric(row["asthma_recall"])} | '
            f'{_metric(row["non_asthma_recall"])} | '
            f'{int(float(row["prediction_changes_vs_fp32"]))} | '
            f'{int(float(row["model_size_bytes"]))} | '
            f'{row["input_dtype"]} → {row["output_dtype"]} |'
        )

    classification_summary = []
    confusion_summary = []
    combined_predictions = []
    combined_text = [
        f'COMBINED {split_title.upper()} CLASSIFICATION REPORT',
        f'Plan SHA256: {plan["plan_sha256"]}',
        f'Total expected entries: {len(plan["trials"]) * (len(plan["methods"]) + 1)}',
        'Labels: Asthma=0, Non-Asthma=1',
        '',
    ]
    lines.extend([
        '',
        '## Confusion matrix và classification report',
        '',
        'Quy ước: nhãn `0 = Asthma`, nhãn `1 = Non-Asthma`, hàng là nhãn thật và cột là nhãn dự đoán.',
    ])
    for row in current:
        result_dir = (
            D_ARTIFACTS / row['trial_id'] / 'evaluation' / row['method_id']
        )
        metrics_path = result_dir / f'{split}_metrics.json'
        if not metrics_path.is_file():
            continue
        payload = read_json(metrics_path)
        if payload.get('plan_sha256') != plan['plan_sha256']:
            continue
        confusion = payload['confusion_matrix']
        class_rows = write_detail_reports(result_dir, row, confusion, split)
        predictions_path = result_dir / f'{split}_predictions.csv'
        for sample_index, prediction in enumerate(read_rows(predictions_path)):
            combined_predictions.append({
                'split': split,
                'priority_rank': row['priority_rank'],
                'model_role': row['model_role'],
                'trial_id': row['trial_id'],
                'method_id': row['method_id'],
                'sample_index': sample_index,
                **prediction,
            })
        for class_row in class_rows:
            classification_summary.append({
                'priority_rank': row['priority_rank'],
                'model_role': row['model_role'],
                'trial_id': row['trial_id'],
                'method_id': row['method_id'],
                **class_row,
            })
        confusion_summary.append({
            'priority_rank': row['priority_rank'],
            'model_role': row['model_role'],
            'trial_id': row['trial_id'],
            'method_id': row['method_id'],
            'actual_asthma_pred_asthma': int(confusion[0][0]),
            'actual_asthma_pred_non_asthma': int(confusion[0][1]),
            'actual_non_asthma_pred_asthma': int(confusion[1][0]),
            'actual_non_asthma_pred_non_asthma': int(confusion[1][1]),
        })

        combined_text.extend([
            '=' * 88,
            f'Priority   : {row["priority_rank"]}',
            f'Model role: {row["model_role"]}',
            f'Trial      : {row["trial_id"]}',
            f'Method     : {row["method_id"]}',
            f'Accuracy   : {float(row["accuracy"]):.6f}',
            '',
            f'{"Class":<16}{"Precision":>12}{"Recall":>12}{"F1-score":>12}{"Support":>10}',
        ])
        for class_row in class_rows:
            precision = (
                '' if class_row['precision'] == ''
                else f'{float(class_row["precision"]):.4f}'
            )
            recall = (
                '' if class_row['recall'] == ''
                else f'{float(class_row["recall"]):.4f}'
            )
            combined_text.append(
                f'{class_row["class_name"]:<16}{precision:>12}{recall:>12}'
                f'{float(class_row["f1_score"]):>12.4f}'
                f'{int(class_row["support"]):>10}'
            )
        combined_text.extend([
            '',
            'Confusion matrix (actual rows × predicted columns):',
            '                       Pred Asthma  Pred Non-Asthma',
            f'Actual Asthma        {int(confusion[0][0]):>12}  {int(confusion[0][1]):>16}',
            f'Actual Non-Asthma    {int(confusion[1][0]):>12}  {int(confusion[1][1]):>16}',
            '',
        ])

        lines.extend([
            '',
            f'### {row["priority_rank"]}. `{row["trial_id"]}` — `{row["method_id"]}`',
            '',
            f'- Accuracy: **{_metric(row["accuracy"])}**',
            f'- Balanced accuracy: **{_metric(row["balanced_accuracy"])}**',
            '',
            '| Actual \\ Predicted | Asthma | Non-Asthma |',
            '|---|---:|---:|',
            f'| Asthma | {int(confusion[0][0])} | {int(confusion[0][1])} |',
            f'| Non-Asthma | {int(confusion[1][0])} | {int(confusion[1][1])} |',
            '',
            '| Class | Precision | Recall | F1-score | Support |',
            '|---|---:|---:|---:|---:|',
        ])
        for class_row in class_rows:
            precision = (
                '—' if class_row['precision'] == ''
                else _metric(class_row['precision'])
            )
            recall = (
                '—' if class_row['recall'] == ''
                else _metric(class_row['recall'])
            )
            lines.append(
                f'| {class_row["class_name"]} | {precision} | {recall} | '
                f'{_metric(class_row["f1_score"])} | {class_row["support"]} |'
            )

    write_csv(
        split_dir / 'classification_report_summary.csv',
        classification_summary,
        [
            'priority_rank', 'model_role', 'trial_id', 'method_id',
            'class_name', 'label', 'precision', 'recall', 'f1_score', 'support',
        ],
    )
    write_csv(
        split_dir / 'confusion_matrix_summary.csv',
        confusion_summary,
        [
            'priority_rank', 'model_role', 'trial_id', 'method_id',
            'actual_asthma_pred_asthma', 'actual_asthma_pred_non_asthma',
            'actual_non_asthma_pred_asthma',
            'actual_non_asthma_pred_non_asthma',
        ],
    )

    combined_dir = D_ARTIFACTS / 'Combined_Evaluation'
    combined_path = combined_dir / (
        'Validation_All_Models_Report.txt'
        if split == 'val' else 'Test_All_Models_Report.txt'
    )
    combined_dir.mkdir(parents=True, exist_ok=True)
    pending_combined = combined_path.with_suffix(combined_path.suffix + '.pending')
    pending_combined.write_text('\n'.join(combined_text), encoding='utf-8')
    pending_combined.replace(combined_path)
    combined_predictions_path = combined_dir / (
        'Validation_All_Models_Predictions.csv'
        if split == 'val' else 'Test_All_Models_Predictions.csv'
    )
    write_csv(
        combined_predictions_path,
        combined_predictions,
        [
            'split', 'priority_rank', 'model_role', 'trial_id', 'method_id',
            'sample_index', 'file', 'true_label', 'p_non_asthma',
            'predicted_label', 'fp32_p_non_asthma', 'abs_delta_vs_fp32',
        ],
    )

    expected = len(plan['trials']) * (len(plan['methods']) + 1)
    lines.extend([
        '',
        '## Trạng thái',
        '',
        f'- Đã có kết quả: **{len(current)}/{expected}** tổ hợp, bao gồm FP32 đối chứng.',
        '- Báo cáo không tự thay đổi thứ tự ưu tiên checkpoint đã chuyển giao từ bước C.',
        (
            '- Validation có thể dùng để so sánh method lượng tử; historical Test '
            'chỉ dùng báo cáo sau khi phạm vi đã khóa.'
        ),
        '- INT16x8 cần đường inference `int16_t`; không thay trực tiếp model INT8 hiện tại.',
        '',
    ])
    if split == 'test':
        lines.insert(6, '- Cảnh báo: Test 159 WAV đã được xem ở bước C; đây không phải holdout mới hoàn toàn độc lập.')
    path = split_dir / (
        'D_Validation_Report.md' if split == 'val' else 'D_Test_Report.md'
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + '.pending')
    pending.write_text('\n'.join(lines), encoding='utf-8')
    pending.replace(path)


def split_result_dir(split: str) -> Path:
    return D_RESULTS / ('Validation' if split == 'val' else 'Test')


def summary_path(split: str) -> Path:
    return split_result_dir(split) / (
        'validation_summary.csv' if split == 'val' else 'test_summary.csv'
    )


def _evaluated_model_path(trial: str, method_id: str) -> Path:
    if method_id == 'KERAS_FP32':
        return trial_paths(trial)['model']
    return D_ARTIFACTS / trial / 'methods' / method_id / f'{method_id}.tflite'


def read_current_metrics(
    plan: dict,
    entry: dict,
    method_id: str,
    split: str,
) -> dict | None:
    """Chỉ nhận metrics còn khớp plan, split và đúng hash model hiện tại."""
    metrics_path = (
        D_ARTIFACTS / entry['trial_id'] / 'evaluation'
        / method_id / f'{split}_metrics.json'
    )
    if not metrics_path.is_file():
        return None
    payload = read_json(metrics_path)
    if payload.get('plan_sha256') != plan['plan_sha256']:
        return None
    # Metrics Validation cũ chưa có trường split; chỉ tương thích ngược cho val.
    if payload.get('split', 'val') != split:
        return None
    model_path = _evaluated_model_path(entry['trial_id'], method_id)
    if not model_path.is_file():
        return None
    summary = payload.get('summary_row', {})
    if summary.get('model_sha256') != sha256_file(model_path):
        return None
    return payload


def collect_completed_rows(plan: dict, split: str) -> list[dict]:
    """Đọc lại metrics hiện có để dựng report mà không inference lần nữa."""
    rows = []
    method_ids = ['KERAS_FP32', *[row['method_id'] for row in plan['methods']]]
    for entry in plan['trials']:
        for method_id in method_ids:
            payload = read_current_metrics(plan, entry, method_id, split)
            if payload is None:
                continue
            summary = dict(payload['summary_row'])
            summary['plan_sha256'] = plan['plan_sha256']
            summary['split'] = split
            summary['priority_rank'] = entry['priority_rank']
            summary['model_role'] = entry['model_role']
            rows.append(summary)
    return rows


def sort_summary_rows(rows: list[dict], plan: dict) -> None:
    trial_order = {
        row['trial_id']: int(row['priority_rank']) for row in plan['trials']
    }
    method_order = {
        'KERAS_FP32': 0,
        **{
            row['method_id']: index
            for index, row in enumerate(plan['methods'], start=1)
        },
    }
    rows.sort(key=lambda row: (
        trial_order.get(row['trial_id'], 999),
        method_order.get(row['method_id'], 999),
    ))


def write_summary_outputs(rows: list[dict], plan: dict, split: str) -> None:
    sort_summary_rows(rows, plan)
    write_csv(summary_path(split), rows, SUMMARY_FIELDS)
    write_split_report(rows, plan, split)


def prediction_rows(files, labels, probability, predicted, fp32_probability):
    return [
        {
            'file': str(file),
            'true_label': int(label),
            'p_non_asthma': float(prob),
            'predicted_label': int(pred),
            'fp32_p_non_asthma': float(fp_prob),
            'abs_delta_vs_fp32': float(abs(prob - fp_prob)),
        }
        for file, label, prob, pred, fp_prob in zip(
            files, labels, probability, predicted, fp32_probability
        )
    ]


def evaluate_trial(
    entry: dict,
    methods: list[str],
    plan: dict,
    force: bool,
    tf,
    split: str,
) -> list[dict]:
    current = verify_trial_against_plan(entry)
    trial = entry['trial_id']
    paths = trial_paths(trial)
    method_list = ['KERAS_FP32', *methods]

    # Nếu toàn bộ output của split đã đúng plan thì không load model/features.
    if not force:
        existing_rows = []
        all_current = True
        for method in method_list:
            old = read_current_metrics(plan, entry, method, split)
            if old is None:
                all_current = False
                break
            previous = dict(old['summary_row'])
            previous['plan_sha256'] = plan['plan_sha256']
            previous['split'] = split
            previous['priority_rank'] = entry['priority_rank']
            previous['model_role'] = entry['model_role']
            existing_rows.append(previous)
        if all_current:
            print(f'  BỎ QUA {trial}/{split}: toàn bộ kết quả đã tồn tại')
            return existing_rows

    features, labels, files = load_split(trial, split)
    model = tf.keras.models.load_model(paths['model'], compile=False)
    fp32_probability = np.asarray(
        model.predict(features, batch_size=32, verbose=0)
    ).reshape(-1).astype(np.float32)
    if len(fp32_probability) != len(labels) or not np.isfinite(fp32_probability).all():
        raise ValueError(f'{trial}: FP32 prediction không hợp lệ')
    fp32_metrics, fp32_predicted = binary_metrics(labels, fp32_probability)
    output_rows = []
    for method in method_list:
        result_dir = D_ARTIFACTS / trial / 'evaluation' / method
        metrics_path = result_dir / f'{split}_metrics.json'
        if metrics_path.is_file() and not force:
            old = read_json(metrics_path)
            current_metrics = read_current_metrics(plan, entry, method, split)
            if current_metrics is not None:
                print(f'  BỎ QUA {trial}/{method}/{split}: đã đánh giá')
                previous = dict(current_metrics['summary_row'])
                previous['plan_sha256'] = plan['plan_sha256']
                previous['split'] = split
                previous['priority_rank'] = entry['priority_rank']
                previous['model_role'] = entry['model_role']
                output_rows.append(previous)
                continue
            if old.get('plan_sha256') != plan['plan_sha256']:
                raise RuntimeError(
                    f'{metrics_path} thuộc kế hoạch cũ; kiểm tra rồi dùng --force'
                )
            print(
                f'  TÍNH LẠI {trial}/{method}/{split}: '
                'hash model đã đổi sau lần đánh giá trước'
            )

        if method == 'KERAS_FP32':
            probability = fp32_probability
            predicted = fp32_predicted
            metrics = fp32_metrics
            io = {'input': {'dtype': 'float32'}, 'output': {'dtype': 'float32'}}
            model_path = paths['model']
            spec = {'training_mode': 'FP32', 'integer_mode': 'FP32', 'experimental': False}
        else:
            method_model = D_ARTIFACTS / trial / 'methods' / method / f'{method}.tflite'
            conversion_metadata = D_ARTIFACTS / trial / 'methods' / method / 'conversion_metadata.json'
            if not method_model.is_file() or not conversion_metadata.is_file():
                raise FileNotFoundError(f'{trial}/{method}: chưa có output D1')
            converted = read_json(conversion_metadata)
            if converted.get('plan_sha256') != plan['plan_sha256']:
                raise RuntimeError(f'{trial}/{method}: conversion metadata thuộc plan khác')
            if converted.get('tflite_sha256') != sha256_file(method_model):
                raise RuntimeError(f'{trial}/{method}: TFLite hash không khớp metadata')
            probability, io = run_tflite(method_model, features)
            metrics, predicted = binary_metrics(labels, probability)
            model_path = method_model
            spec = METHOD_SPECS[method]

        delta = np.abs(probability - fp32_probability)
        summary_row = {
            'plan_sha256': plan['plan_sha256'],
            'split': split,
            'priority_rank': entry['priority_rank'],
            'model_role': entry['model_role'],
            'trial_id': trial,
            'variant_id': current['variant_id'],
            'seed': current['seed'],
            'method_id': method,
            **spec,
            **{key: value for key, value in metrics.items() if key != 'confusion_matrix'},
            'prediction_changes_vs_fp32': int(np.sum(predicted != fp32_predicted)),
            'mean_abs_probability_delta': float(np.mean(delta)),
            'max_abs_probability_delta': float(np.max(delta)),
            'model_size_bytes': model_path.stat().st_size,
            'input_dtype': io['input']['dtype'],
            'output_dtype': io['output']['dtype'],
            'model_sha256': sha256_file(model_path),
        }
        rows = prediction_rows(files, labels, probability, predicted, fp32_probability)
        write_csv(
            result_dir / f'{split}_predictions.csv', rows,
            ['file', 'true_label', 'p_non_asthma', 'predicted_label',
             'fp32_p_non_asthma', 'abs_delta_vs_fp32'],
        )
        atomic_json(metrics_path, {
            'status': f'{split.upper()}_EVALUATION_COMPLETE',
            'generated_utc': utc_now(),
            'split': split,
            'test_accessed': split == 'test',
            'historical_test_previously_inspected': split == 'test',
            'plan_path': str(PLAN_PATH.resolve()),
            'plan_sha256': plan['plan_sha256'],
            'confusion_matrix_labels': ['Asthma=0', 'Non-Asthma=1'],
            'confusion_matrix': metrics['confusion_matrix'],
            'io': io,
            'summary_row': summary_row,
        })
        output_rows.append(summary_row)
        print(
            f'  {trial}/{method}: Acc={summary_row["accuracy"]:.2%}, '
            f'Asthma Recall={summary_row["asthma_recall"]:.2%}, '
            f'changes={summary_row["prediction_changes_vs_fp32"]}'
        )
    del model, features
    tf.keras.backend.clear_session()
    return output_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial-id', help='Chỉ đánh giá một trial đã đăng ký')
    parser.add_argument('--method', choices=tuple(METHOD_SPECS), help='Chỉ đánh giá một method đã đăng ký')
    parser.add_argument(
        '--split', choices=('val', 'test', 'both'), default='both',
        help='Mặc định chạy Validation trước rồi historical Test',
    )
    parser.add_argument('--force', action='store_true', help='Tính lại output split đã tồn tại')
    parser.add_argument(
        '--report-only', action='store_true',
        help=(
            'Không load TensorFlow/inference; chỉ đọc metrics JSON hiện có '
            'để tái tạo report cho split được chọn'
        ),
    )
    args = parser.parse_args()

    plan = load_d_plan()
    selected_splits = ['val', 'test'] if args.split == 'both' else [args.split]
    if args.report_only:
        if args.force or args.trial_id or args.method:
            parser.error(
                '--report-only dùng toàn bộ kết quả hoàn tất trong plan; '
                'không đi kèm --force/--trial-id/--method'
            )
        generated = 0
        for split in selected_splits:
            completed = collect_completed_rows(plan, split)
            if not completed:
                print(f'BỎ QUA REPORT {split}: chưa có metrics hợp lệ')
                continue
            write_summary_outputs(completed, plan, split)
            directory = split_result_dir(split)
            print(f'{split.upper()} SUMMARY : {summary_path(split)}')
            print(f'{split.upper()} CONFUSION: {directory / "confusion_matrix_summary.csv"}')
            print(f'{split.upper()} CLASSIFY : {directory / "classification_report_summary.csv"}')
            generated += 1
        if not generated:
            raise FileNotFoundError('Chưa có metrics JSON hợp lệ để tạo report')
        print('Report được dựng từ kết quả D2 hiện có; không chạy inference.')
        return

    try:
        import tensorflow as tf
    except ImportError as exc:
        raise SystemExit('Thiếu TensorFlow trong môi trường đánh giá') from exc

    registered_methods = [row['method_id'] for row in plan['methods']]
    if args.method and args.method not in registered_methods:
        parser.error(f'{args.method} chưa được đăng ký trong kế hoạch D0')
    methods = [args.method] if args.method else registered_methods
    trials = [
        row for row in plan['trials']
        if args.trial_id is None or row['trial_id'] == args.trial_id
    ]
    if not trials:
        parser.error(f'Không tìm thấy trial đã đăng ký: {args.trial_id}')

    for split in selected_splits:
        split_name = 'VALIDATION' if split == 'val' else 'HISTORICAL TEST'
        new_rows = []
        for entry in trials:
            print(f'\nĐÁNH GIÁ {split_name}: {entry["trial_id"]}')
            new_rows.extend(
                evaluate_trial(entry, methods, plan, args.force, tf, split)
            )

        # Dựng summary từ metrics đã xác minh hash thay vì ghép CSV cũ. Nhờ đó
        # D1 --force không thể để lại các dòng đánh giá của model cũ trong report.
        completed = collect_completed_rows(plan, split)
        if not completed:
            raise RuntimeError(f'Không có metrics {split} hợp lệ sau đánh giá')
        write_summary_outputs(completed, plan, split)
        directory = split_result_dir(split)
        print(f'\n{split_name} SUMMARY : {summary_path(split)}')
        print(f'{split_name} CONFUSION: {directory / "confusion_matrix_summary.csv"}')
        print(f'{split_name} CLASSIFY : {directory / "classification_report_summary.csv"}')
        print(
            f'{split_name} REPORT   : '
            f'{directory / ("D_Validation_Report.md" if split == "val" else "D_Test_Report.md")}'
        )

    print('\nD2 HOÀN TẤT. Validation và historical Test được báo cáo độc lập.')
    print('Không dùng historical Test để chọn lại checkpoint hoặc method lượng tử.')


if __name__ == '__main__':
    main()
