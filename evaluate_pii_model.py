#!/usr/bin/env python3
import argparse
import ast
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

from gliner import GLiNER


DEFAULT_CANONICAL_LABEL_MAP = {
    "NAME_STUDENT": "person name",
    "EMAIL": "email address",
    "USERNAME": "username",
    "ID_NUM": "id number",
    "PHONE_NUM": "phone number",
    "URL_PERSONAL": "url",
    "STREET_ADDRESS": "address",
}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def load_rows(csv_path: Path, text_col: str, labels_col: str, max_rows: int | None):
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            if max_rows is not None and idx >= max_rows:
                break
            text = row.get(text_col, "")
            raw_labels = row.get(labels_col, "{}")
            if not text:
                continue
            try:
                labels_dict = ast.literal_eval(raw_labels)
                if not isinstance(labels_dict, dict):
                    continue
            except Exception:
                continue
            yield text, labels_dict


def evaluate(
    csv_path: Path,
    model_id: str,
    text_col: str,
    labels_col: str,
    max_rows: int | None,
    threshold: float,
    canonical_label_map: dict[str, str],
):
    model = GLiNER.from_pretrained(
        model_id,
        proxies=None,
        resume_download=False,
    )

    counts = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    rows_used = 0

    for text, gold_dict in load_rows(csv_path, text_col, labels_col, max_rows):
        dataset_labels = sorted(gold_dict.keys())
        if not dataset_labels:
            continue

        dataset_to_canonical = {
            label: canonical_label_map.get(label, label)
            for label in dataset_labels
        }
        canonical_labels = sorted(set(dataset_to_canonical.values()))

        predicted_entities = model.predict_entities(text, canonical_labels, threshold=threshold)

        pred_by_canonical = defaultdict(set)
        for ent in predicted_entities:
            label = ent.get("label")
            token = ent.get("text", "")
            if label and token:
                pred_by_canonical[label].add(normalize_text(token))

        for label in dataset_labels:
            gold_values = gold_dict.get(label, []) or []
            gold_set = {
                normalize_text(v)
                for v in gold_values
                if isinstance(v, str) and v.strip()
            }
            canonical_label = dataset_to_canonical[label]
            pred_set = pred_by_canonical.get(canonical_label, set())

            tp = len(gold_set & pred_set)
            fp = len(pred_set - gold_set)
            fn = len(gold_set - pred_set)

            counts[label]["tp"] += tp
            counts[label]["fp"] += fp
            counts[label]["fn"] += fn

        rows_used += 1

    per_label = {}
    total_tp = total_fp = total_fn = 0
    for label, c in sorted(counts.items()):
        tp, fp, fn = c["tp"], c["fp"], c["fn"]
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        per_label[label] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }
        total_tp += tp
        total_fp += fp
        total_fn += fn

    micro_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0.0
    micro_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0.0
    micro_f1 = (
        2 * micro_precision * micro_recall / (micro_precision + micro_recall)
        if (micro_precision + micro_recall)
        else 0.0
    )

    result = {
        "model": model_id,
        "dataset": str(csv_path),
        "rows_used": rows_used,
        "threshold": threshold,
        "canonical_label_map": canonical_label_map,
        "overall_micro": {
            "tp": total_tp,
            "fp": total_fp,
            "fn": total_fn,
            "precision": round(micro_precision, 4),
            "recall": round(micro_recall, 4),
            "f1": round(micro_f1, 4),
        },
        "per_label": per_label,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="Evaluate GLiNER PII model against CSV gold labels.")
    parser.add_argument(
        "--csv",
        default="pii_dataset/ai_data.csv",
        help="Path to CSV dataset (default: pii_dataset/ai_data.csv)",
    )
    parser.add_argument(
        "--model",
        default="urchade/gliner_multi_pii-v1",
        help="Hugging Face model id",
    )
    parser.add_argument("--text-col", default="0", help="Text column name")
    parser.add_argument("--labels-col", default="1", help="Labels column name containing dict-like string")
    parser.add_argument("--max-rows", type=int, default=None, help="Limit rows for quick tests")
    parser.add_argument("--threshold", type=float, default=0.5, help="Prediction threshold")
    parser.add_argument("--output-json", default=None, help="Optional output file path for metrics JSON")
    parser.add_argument(
        "--label-map-json",
        default=None,
        help="Optional JSON string to override/add canonical label mapping",
    )
    args = parser.parse_args()

    canonical_label_map = dict(DEFAULT_CANONICAL_LABEL_MAP)
    if args.label_map_json:
        user_map = json.loads(args.label_map_json)
        if not isinstance(user_map, dict):
            raise ValueError("--label-map-json must decode to an object/dict")
        canonical_label_map.update({str(k): str(v) for k, v in user_map.items()})

    result = evaluate(
        csv_path=Path(args.csv),
        model_id=args.model,
        text_col=args.text_col,
        labels_col=args.labels_col,
        max_rows=args.max_rows,
        threshold=args.threshold,
        canonical_label_map=canonical_label_map,
    )

    print(json.dumps(result, indent=2))
    if args.output_json:
        Path(args.output_json).write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
