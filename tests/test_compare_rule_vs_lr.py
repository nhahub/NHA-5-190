"""Tests for the rule-versus-Logistic-Regression comparison (validation only)."""

import csv
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from wardiq.compatibility.pair_features import make_config

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/m3/compare_rule_vs_lr.py"
spec = importlib.util.spec_from_file_location("compare_rule_vs_lr", SCRIPT)
assert spec is not None and spec.loader is not None
compare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compare)

CONFIG = make_config(["jeans"])
NAMES = CONFIG["feature_names"]


def row(pair: tuple[str, str], mapped: int, cosine: float, color: float | None) -> list[float]:
    """One feature row; color None means no palette."""
    values = np.zeros(len(NAMES), dtype=np.float32)
    values[NAMES.index("category:" + "|".join(sorted(pair)))] = 1.0
    values[NAMES.index("category:both_mapped")] = mapped
    values[NAMES.index("clip:cosine")] = cosine
    if color is not None:
        values[NAMES.index("lab:both_available")] = 1.0
        values[NAMES.index("lab:expected_delta_e76_over_100")] = color
    return values.tolist()


GOOD = ("top", "bottom")  # complementary
BAD = ("top", "top")  # same category twice
LR_PROBABILITIES = [0.9, 0.8, 0.6, 0.4, 0.7, 0.5, 0.3, 0.1, 0.45, 0.55]
LABELS = [1, 1, 1, 1, 0, 0, 0, 0, 1, 0]  # the last two rows cannot be scored by the rule


def write_inputs(tmp_path: Path, split: str = "validation") -> tuple[Path, Path]:
    rows = [row(GOOD, 1, 0.9, 0.1) for _ in range(4)] + [row(BAD, 1, 0.5, 0.8) for _ in range(4)]
    rows += [row(("top", "unknown"), 0, 0.5, None)] * 2  # unknown category and no palette
    directory = tmp_path / "features"
    directory.mkdir()
    np.save(directory / "features.npy", np.array(rows, dtype=np.float32))
    (directory / "feature_schema.json").write_text(json.dumps(CONFIG), encoding="utf-8")
    inventory, predictions = [], []
    for i, label in enumerate(LABELS):
        base = {"row_index": i, "left_item_id": f"a{i}", "right_item_id": f"b{i}"}
        base |= {"split": split, "label": label}
        inventory.append(base)
        predictions.append(
            base
            | {
                "actual_label": label,
                "compatibility_probability": LR_PROBABILITIES[i],
                "predicted_label": int(LR_PROBABILITIES[i] >= 0.45),
                "threshold": 0.45,
            }
        )
    for name, data in (("pair_inventory.csv", inventory), ("lr.csv", predictions)):
        target = directory / name if name.startswith("pair") else tmp_path / name
        with target.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)
    return directory, tmp_path / "lr.csv"


def cli_args(features: Path, lr: Path, output: Path) -> list[str]:
    return ["--features-dir", str(features), "--lr-predictions", str(lr), "--output", str(output)]


def run(*args: str) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(SCRIPT), *args]
    return subprocess.run(command, capture_output=True, text=True, check=False)


def test_metric_helpers_match_hand_calculations() -> None:
    labels = np.array([1, 1, 1, 1, 0, 0, 0, 0])
    scores = np.array([0.9, 0.8, 0.6, 0.4, 0.7, 0.5, 0.3, 0.1])
    assert compare.roc_auc(labels, scores) == pytest.approx(13 / 16)  # 13 of 16 pairs ordered
    assert compare.roc_auc(labels, np.full(8, 0.5)) == 0.5
    assert compare.roc_auc(np.ones(3), np.array([0.1, 0.2, 0.3])) is None
    metrics = compare.at_threshold(labels, scores, 0.45)
    assert metrics["precision"] == pytest.approx(3 / 5)
    assert metrics["recall"] == pytest.approx(3 / 4)
    assert metrics["f1"] == pytest.approx(2 * 3 / (6 + 2 + 1))
    assert compare.best_f1_threshold(np.array([0, 0, 1, 1]), np.array([0.1, 0.4, 0.6, 0.9])) == 0.6
    table = compare.reliability(np.array([1, 0, 1, 0]), np.array([0.9, 0.1, 0.6, 0.4]))
    assert sum(b["count"] for b in table["bins"]) == 4
    assert table["brier"] == pytest.approx((0.01 + 0.01 + 0.16 + 0.16) / 4)


def test_comparison_uses_the_same_pairs_and_reports_exclusions(tmp_path: Path) -> None:
    features, lr = write_inputs(tmp_path)
    result = run(*cli_args(features, lr, tmp_path / "o"))
    assert result.returncode == 0, result.stderr
    summary = json.loads((tmp_path / "o/comparison_summary.json").read_text())
    assert summary["population_all_rows"] == {"rows": 10, "positives": 5, "negatives": 5}
    assert summary["population_scored_by_both"] == {"rows": 8, "positives": 4, "negatives": 4}
    assert summary["excluded_rule_insufficient_evidence"] == 2
    assert summary["rule_baseline"]["roc_auc"] == 1.0  # the rule separates this toy data
    assert summary["rule_baseline"]["at_threshold"]["f1"] == 1.0
    assert summary["logistic_regression"]["roc_auc"] == pytest.approx(13 / 16)
    assert summary["logistic_regression"]["at_threshold"]["f1"] == pytest.approx(2 / 3)
    assert summary["agreement_at_thresholds"] == {
        "both_right": 5,
        "only_rule_right": 3,
        "only_lr_right": 0,
        "both_wrong": 0,
    }
    assert "not applicable" in summary["rule_baseline"]["calibration"]
    cases = list(csv.DictReader((tmp_path / "o/failure_cases.csv").open(encoding="utf-8")))
    assert {c["method"] for c in cases} == {"rule", "logistic_regression"}
    assert all(c["left_item_id"] not in {"a8", "a9"} for c in cases)  # unscored rows are excluded


def test_runs_are_repeatable_and_never_overwrite(tmp_path: Path) -> None:
    features, lr = write_inputs(tmp_path)
    assert run(*cli_args(features, lr, tmp_path / "one")).returncode == 0
    assert run(*cli_args(features, lr, tmp_path / "two")).returncode == 0
    for name in ("comparison_summary.json", "failure_cases.csv"):
        assert (tmp_path / "one" / name).read_bytes() == (tmp_path / "two" / name).read_bytes()
    assert run(*cli_args(features, lr, tmp_path / "one")).returncode != 0


def test_refuses_a_different_population_and_the_test_split(tmp_path: Path) -> None:
    features, lr = write_inputs(tmp_path)
    lines = lr.read_text(encoding="utf-8").splitlines()
    lines[1] = lines[1].replace("a0", "zzz")
    lr.write_text("\n".join(lines) + "\n", encoding="utf-8")
    different = run(*cli_args(features, lr, tmp_path / "x"))
    assert different.returncode != 0 and "Not the same population" in different.stderr

    test_root = tmp_path / "test_split"
    test_root.mkdir()
    test_features, test_lr = write_inputs(test_root, "test")
    refused = run(*cli_args(test_features, test_lr, tmp_path / "y"))
    assert refused.returncode != 0 and "Only validation is compared" in refused.stderr


def test_files_with_a_byte_order_mark_are_read(tmp_path: Path) -> None:
    features, lr = write_inputs(tmp_path)
    inventory = features / "pair_inventory.csv"
    inventory.write_bytes(b"\xef\xbb\xbf" + inventory.read_bytes())
    lr.write_bytes(b"\xef\xbb\xbf" + lr.read_bytes())
    assert run(*cli_args(features, lr, tmp_path / "bom")).returncode == 0
