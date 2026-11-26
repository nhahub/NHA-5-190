"""Compare the rule baseline with the Logistic Regression model on the SAME validation pairs.

    python scripts/m3/compare_rule_vs_lr.py --features-dir <build_pair_features.py output> \
        --lr-predictions <validation_predictions.csv> --output <new directory>

The rule scores come from the exported feature rows; the LR scores come from the prediction file
written by train_m3_logistic_regression.py. Both must describe exactly the same pairs. Results are
validation-only. The test split is refused unless --allow-test and --rule-threshold are given.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from wardiq.compatibility.rule_baseline import (  # noqa: E402
    MIN_WEIGHT_COVERAGE,
    WEIGHTS,
    score_rows,
)

Array = NDArray[Any]
CHUNK = 5000
LIMITATIONS = [
    "Validation only. The held-out test split was not used.",
    "Positives are source-outfit co-occurrence; negatives are assumed, not human judgments.",
    "Near-duplicate products across pairs have not been ruled out.",
    "The rule score is a heuristic, not a probability: no calibration claim is made for it.",
    "Ranking metrics are not reported: there are no relevance labels or candidate universe.",
]


def roc_auc(labels: Array, scores: Array) -> float | None:
    """Tie-aware ROC-AUC; None if only one class is present."""
    y = labels.astype(int)
    pos, neg = int((y == 1).sum()), int((y == 0).sum())
    if pos == 0 or neg == 0:
        return None
    _, inverse, counts = np.unique(scores, return_inverse=True, return_counts=True)
    ranks = (np.cumsum(counts) - (counts - 1) / 2.0)[inverse]
    return float((ranks[y == 1].sum() - pos * (pos + 1) / 2.0) / (pos * neg))


def at_threshold(labels: Array, scores: Array, threshold: float) -> dict[str, float]:
    """Accuracy, precision, recall and F1 when score >= threshold predicts a compatible pair."""
    y = labels.astype(int)
    predicted = (scores >= threshold).astype(int)
    tp = int(((predicted == 1) & (y == 1)).sum())
    fp = int(((predicted == 1) & (y == 0)).sum())
    fn = int(((predicted == 0) & (y == 1)).sum())
    return {
        "threshold": float(threshold),
        "accuracy": float((predicted == y).mean()),
        "precision": tp / (tp + fp) if tp + fp else 0.0,
        "recall": tp / (tp + fn) if tp + fn else 0.0,
        "f1": 2 * tp / (2 * tp + fp + fn) if tp else 0.0,
    }


def best_f1_threshold(labels: Array, scores: Array) -> float:
    """Threshold with the highest F1 on these (validation) rows; ties keep the highest score."""
    y = labels.astype(int)
    order = np.argsort(-scores, kind="mergesort")
    s, y_sorted = scores[order], y[order]
    tp = np.cumsum(y_sorted)
    fp = np.cumsum(1 - y_sorted)
    last = np.append(s[1:] != s[:-1], True)  # the end of each run of equal scores
    f1 = 2 * tp[last] / (2 * tp[last] + fp[last] + (y.sum() - tp[last]))
    return float(s[last][int(np.argmax(f1))])


def reliability(labels: Array, probabilities: Array, bins: int = 10) -> dict[str, Any]:
    """Brier score and a reliability table (predicted vs observed rate per probability bin)."""
    y = labels.astype(float)
    which = np.minimum((probabilities * bins).astype(int), bins - 1)
    table = []
    for b in range(bins):
        inside = which == b
        if inside.any():
            table.append(
                {
                    "bin": f"{b / bins:.1f}-{(b + 1) / bins:.1f}",
                    "count": int(inside.sum()),
                    "mean_predicted": float(probabilities[inside].mean()),
                    "observed_positive_rate": float(y[inside].mean()),
                }
            )
    return {"brier": float(np.mean((probabilities - y) ** 2)), "bins": table}


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            sha.update(block)
    return sha.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:  # accepts files with a BOM
        return list(csv.DictReader(stream))


def rule_scores(features_dir: Path) -> Array:
    """Score the exported rows with the rule baseline; NaN where there is too little evidence."""
    names = json.loads((features_dir / "feature_schema.json").read_text(encoding="utf-8"))[
        "feature_names"
    ]
    matrix = np.load(features_dir / "features.npy", mmap_mode="r")
    out = np.full(len(matrix), np.nan)
    for start in range(0, len(matrix), CHUNK):
        block = np.asarray(matrix[start : start + CHUNK]).tolist()
        for i, result in enumerate(score_rows(names, block)):
            if result.score is not None:
                out[start + i] = result.score
    return out


def failure_rows(
    method: str, rows: list[dict[str, str]], labels: Array, scores: Array
) -> list[Any]:
    """The 10 most confident wrong pairs of each kind."""
    found: list[Any] = []
    wrong_pos = np.flatnonzero(labels == 0)  # false positives: negatives with the highest scores
    wrong_neg = np.flatnonzero(labels == 1)  # false negatives: positives with the lowest scores
    for kind, pool, sign in (("false_positive", wrong_pos, -1), ("false_negative", wrong_neg, 1)):
        for i in pool[np.argsort(sign * scores[pool], kind="mergesort")][:10]:
            row = rows[i]
            found.append(
                [method, kind, row["left_item_id"], row["right_item_id"], int(labels[i]), scores[i]]
            )
    return found


def compare(
    features_dir: Path, lr_path: Path, output: Path, allow_test: bool, rule_threshold: float | None
) -> dict[str, Any]:
    inventory = read_csv(features_dir / "pair_inventory.csv")
    lr_rows = read_csv(lr_path)
    if len(inventory) != len(lr_rows):
        raise ValueError("Feature rows and LR predictions have different lengths")
    for mine, theirs in zip(inventory, lr_rows):
        same = (mine["left_item_id"], mine["right_item_id"], mine["split"], mine["label"]) == (
            theirs["left_item_id"],
            theirs["right_item_id"],
            theirs["split"],
            theirs["actual_label"],
        )
        if not same:
            raise ValueError(f"Not the same population at row {mine['row_index']}")
    splits = {r["split"] for r in inventory}
    split = splits.pop() if len(splits) == 1 else "mixed"
    if split != "validation" and not (split == "test" and allow_test and rule_threshold):
        raise ValueError(
            "Only validation is compared. Test needs --allow-test and --rule-threshold"
        )

    labels = np.array([int(r["label"]) for r in inventory])
    lr = np.array([float(r["compatibility_probability"]) for r in lr_rows])
    lr_threshold = float(lr_rows[0]["threshold"])
    rule = rule_scores(features_dir)
    common = ~np.isnan(rule)  # rows the rule baseline could score
    y, r, p = labels[common], rule[common], lr[common]
    chosen = rule_threshold if rule_threshold else best_f1_threshold(y, r)
    rule_right = (r >= chosen).astype(int) == y
    lr_right = (p >= lr_threshold).astype(int) == y

    output.mkdir(parents=True)
    all_rows = {"rows": len(labels), "positives": int(labels.sum())}
    all_rows["negatives"] = len(labels) - all_rows["positives"]
    summary: dict[str, Any] = {
        "split": split,
        "status": "validation-only comparison, not a final evaluation",
        "population_all_rows": all_rows,
        "population_scored_by_both": {
            "rows": int(common.sum()),
            "positives": int(y.sum()),
            "negatives": int((y == 0).sum()),
        },
        "excluded_rule_insufficient_evidence": int((~common).sum()),
        "rule_baseline": {
            "weights": WEIGHTS,
            "min_weight_coverage": MIN_WEIGHT_COVERAGE,
            "roc_auc": roc_auc(y, r),
            "threshold_source": "supplied" if rule_threshold else "max F1 on these validation rows",
            "at_threshold": at_threshold(y, r, chosen),
            "calibration": "not applicable: the score is not a probability",
        },
        "logistic_regression": {
            "roc_auc": roc_auc(y, p),
            "threshold_source": "from the LR prediction file (chosen on validation)",
            "at_threshold": at_threshold(y, p, lr_threshold),
            "roc_auc_all_rows": roc_auc(labels, lr),
            "calibration": reliability(y, p),
        },
        "agreement_at_thresholds": {
            "both_right": int((rule_right & lr_right).sum()),
            "only_rule_right": int((rule_right & ~lr_right).sum()),
            "only_lr_right": int((~rule_right & lr_right).sum()),
            "both_wrong": int((~rule_right & ~lr_right).sum()),
        },
        "inputs_sha256": {
            "features.npy": digest(features_dir / "features.npy"),
            "pair_inventory.csv": digest(features_dir / "pair_inventory.csv"),
            "feature_schema.json": digest(features_dir / "feature_schema.json"),
            "lr_predictions.csv": digest(lr_path),
        },
        "limitations": LIMITATIONS,
    }
    kept = [inventory[i] for i in np.flatnonzero(common)]
    failures = failure_rows("rule", kept, y, r) + failure_rows("logistic_regression", kept, y, p)
    with (output / "failure_cases.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["method", "kind", "left_item_id", "right_item_id", "label", "score"])
        writer.writerows(failures)
    (output / "comparison_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features-dir", type=Path, required=True)
    parser.add_argument("--lr-predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new directory, not overwritten")
    parser.add_argument("--allow-test", action="store_true")
    parser.add_argument("--rule-threshold", type=float, default=None)
    args = parser.parse_args()
    result = compare(
        args.features_dir, args.lr_predictions, args.output, args.allow_test, args.rule_threshold
    )
    print(json.dumps(result, indent=2, sort_keys=True))
