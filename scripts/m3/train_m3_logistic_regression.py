"""Train and evaluate the M3 Logistic Regression compatibility model.

Expected input directory per split (produced by build_pair_features.py):
  features.npy, labels.npy, pair_inventory.csv

Fit uses train only. The validation split selects the classification threshold.
Test evaluation is opt-in (--evaluate-test) and uses that frozen threshold.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def load_split(
    directory: Path, expected_split: str
) -> tuple[np.ndarray, np.ndarray, list[dict[str, str]]]:
    directory = directory.resolve()
    features_path = directory / "features.npy"
    labels_path = directory / "labels.npy"
    inventory_path = directory / "pair_inventory.csv"

    for path in (features_path, labels_path, inventory_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required {expected_split} artifact is missing: {path}")

    features = np.load(features_path, allow_pickle=False)
    labels = np.load(labels_path, allow_pickle=False)

    if features.ndim != 2 or features.shape[0] == 0:
        raise ValueError(f"{expected_split}: features must be a nonempty 2D array")
    if labels.ndim != 1 or len(labels) != features.shape[0]:
        raise ValueError(f"{expected_split}: labels must align with feature rows")
    if not np.isfinite(features).all():
        raise ValueError(f"{expected_split}: features contain NaN or infinity")
    if not np.isin(labels, [0, 1]).all():
        raise ValueError(f"{expected_split}: labels must be binary 0/1")

    with inventory_path.open(encoding="utf-8-sig", newline="") as stream:
        inventory = list(csv.DictReader(stream))

    if len(inventory) != len(labels):
        raise ValueError(f"{expected_split}: inventory row count does not match labels")
    if "split" not in (inventory[0].keys() if inventory else []):
        raise ValueError(f"{expected_split}: pair_inventory.csv needs a 'split' column")
    if any(row.get("split") != expected_split for row in inventory):
        raise ValueError(f"{expected_split}: inventory contains a different split identity")

    return features.astype(np.float32, copy=False), labels.astype(np.int8, copy=False), inventory


def choose_f1_threshold(y_true: np.ndarray, probabilities: np.ndarray) -> tuple[float, float]:
    candidates = np.unique(np.concatenate(([0.0, 0.5, 1.0], probabilities)))
    best_threshold = 0.5
    best_f1 = -1.0
    for threshold in candidates:
        predicted = (probabilities >= threshold).astype(np.int8)
        score = f1_score(y_true, predicted, zero_division=0)
        # In a tie, prefer the threshold closer to the conventional 0.5.
        if score > best_f1 or (
            score == best_f1 and abs(float(threshold) - 0.5) < abs(best_threshold - 0.5)
        ):
            best_threshold = float(threshold)
            best_f1 = float(score)
    return best_threshold, best_f1


def calculate_metrics(
    y_true: np.ndarray, probabilities: np.ndarray, threshold: float
) -> dict[str, Any]:
    predicted = (probabilities >= threshold).astype(np.int8)
    metrics: dict[str, Any] = {
        "examples": int(len(y_true)),
        "positive_count": int(np.sum(y_true == 1)),
        "negative_count": int(np.sum(y_true == 0)),
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, predicted)),
        "precision": float(precision_score(y_true, predicted, zero_division=0)),
        "recall": float(recall_score(y_true, predicted, zero_division=0)),
        "f1": float(f1_score(y_true, predicted, zero_division=0)),
        "log_loss": float(log_loss(y_true, probabilities, labels=[0, 1])),
        "brier_score": float(brier_score_loss(y_true, probabilities)),
    }
    if len(np.unique(y_true)) == 2:
        metrics["roc_auc"] = float(roc_auc_score(y_true, probabilities))
        metrics["average_precision"] = float(average_precision_score(y_true, probabilities))
    else:
        metrics["roc_auc"] = None
        metrics["average_precision"] = None
    return metrics


def write_predictions(
    path: Path,
    inventory: list[dict[str, str]],
    labels: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(inventory[0].keys()) if inventory else []
    fields += ["actual_label", "compatibility_probability", "predicted_label", "threshold"]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row, actual, probability in zip(inventory, labels, probabilities):
            writer.writerow(
                {
                    **row,
                    "actual_label": int(actual),
                    "compatibility_probability": repr(float(probability)),
                    "predicted_label": int(probability >= threshold),
                    "threshold": f"{threshold:.10f}",
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-dir", type=Path, required=True)
    parser.add_argument("--validation-dir", type=Path, required=True)
    parser.add_argument("--test-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--c", type=float, default=1.0, help="Inverse regularization strength")
    parser.add_argument("--max-iter", type=int, default=1000)
    parser.add_argument(
        "--evaluate-test",
        action="store_true",
        help=(
            "Evaluate test using the threshold selected on validation; "
            "do this only after protocol lock."
        ),
    )
    args = parser.parse_args()

    if args.c <= 0 or args.max_iter < 1:
        parser.error("--c and --max-iter must be positive")
    if args.evaluate_test and args.test_dir is None:
        parser.error("--test-dir is required with --evaluate-test")

    train_x, train_y, train_inventory = load_split(args.train_dir, "train")
    val_x, val_y, val_inventory = load_split(args.validation_dir, "validation")
    if train_x.shape[1] != val_x.shape[1]:
        raise ValueError("Train and validation feature dimensions differ")
    if len(np.unique(train_y)) != 2:
        raise ValueError("Training split must contain both classes")
    if len(np.unique(val_y)) != 2:
        raise ValueError("Validation split must contain both classes")

    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "logistic_regression",
                LogisticRegression(
                    C=args.c,
                    max_iter=args.max_iter,
                    solver="lbfgs",
                    random_state=42,
                ),
            ),
        ]
    )
    model.fit(train_x, train_y)

    val_probabilities = model.predict_proba(val_x)[:, 1]
    threshold, validation_f1 = choose_f1_threshold(val_y, val_probabilities)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, output_dir / "logistic_regression.joblib")
    write_predictions(
        output_dir / "validation_predictions.csv",
        val_inventory,
        val_y,
        val_probabilities,
        threshold,
    )

    report: dict[str, Any] = {
        "schema_version": "wardiq.m3.logistic-regression-report.v1",
        "model": "sklearn.pipeline.Pipeline(StandardScaler, LogisticRegression)",
        "model_parameters": {"C": args.c, "max_iter": args.max_iter, "solver": "lbfgs"},
        "feature_dimension": int(train_x.shape[1]),
        "training": {
            "examples": int(len(train_y)),
            "positive_count": int(np.sum(train_y == 1)),
            "negative_count": int(np.sum(train_y == 0)),
            "split": "train",
        },
        "validation": calculate_metrics(val_y, val_probabilities, threshold),
        "threshold_selection": {
            "method": "maximum validation F1",
            "selected_threshold": threshold,
            "validation_f1": validation_f1,
            "test_used_for_selection": False,
        },
        "probability_interpretation": (
            "The model's estimated probability of label 1 under the training examples and "
            "sampling process; not a verified human judgment of outfit compatibility."
        ),
        "test_evaluation": None,
    }

    if args.evaluate_test:
        test_x, test_y, test_inventory = load_split(args.test_dir, "test")
        if test_x.shape[1] != train_x.shape[1]:
            raise ValueError("Train and test feature dimensions differ")
        test_probabilities = model.predict_proba(test_x)[:, 1]
        report["test_evaluation"] = calculate_metrics(test_y, test_probabilities, threshold)
        report["test_evaluation"]["threshold_source"] = "validation"
        write_predictions(
            output_dir / "test_predictions.csv",
            test_inventory,
            test_y,
            test_probabilities,
            threshold,
        )

    (output_dir / "metrics.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
