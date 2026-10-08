"""Verify Omar's canonical M1 assignments and export the test-only evaluation inventory."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml
from research_cli import ROOT, protect_evidence

SPLIT_FIELDS = (
    "item_id",
    "source_dataset",
    "source_split",
    "target_split",
    "split_method",
    "random_seed",
    "group_id",
)


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    if len(fields) != len(set(fields)) or any(
        None in row or any(value is None for value in row.values()) for row in rows
    ):
        raise ValueError(f"Malformed CSV: {path}")
    return fields, rows


def load_assignments(path: Path) -> dict[str, dict[str, str]]:
    fields, rows = read_rows(path)
    if not set(SPLIT_FIELDS).issubset(fields):
        raise ValueError("Split manifest is missing required columns")
    assignments = {}
    for row in rows:
        key = row["item_id"]
        if not key or key in assignments:
            raise ValueError(f"Empty or duplicate split item_id: {key}")
        if row["target_split"] not in {"train", "validation", "test"}:
            raise ValueError(f"Invalid target split for {key}")
        assignments[key] = row
    return assignments


def outfit_groups(value: str) -> set[str]:
    """Outfit membership tokens contain an optional :item-position suffix."""
    return {token.split(":")[0] for token in value.split(";") if token}


def sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def verify(raw_path: Path, split_path: Path, config_path: Path) -> dict[str, object]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    fields, raw = read_rows(raw_path)
    assignments = load_assignments(split_path)
    raw_ids = [row["item_id"] for row in raw]
    if not all(raw_ids) or len(set(raw_ids)) != len(raw_ids):
        raise ValueError("Raw manifest contains empty or duplicate item IDs")
    if set(raw_ids) != assignments.keys():
        raise ValueError("Split assignments do not exactly cover the raw manifest")
    inventory = config["input_manifest"]
    if len(raw) != inventory["rows"] or len(fields) != inventory["columns"]:
        raise ValueError("Input dimensions differ from the split configuration")
    # Omar recorded the Windows checkout hash. Accept that byte representation
    # and the equivalent LF checkout, without accepting changed CSV content.
    lf = raw_path.read_bytes().replace(b"\r\n", b"\n")
    hashes = {
        hashlib.sha256(lf).hexdigest(),
        hashlib.sha256(lf.replace(b"\n", b"\r\n")).hexdigest(),
    }
    if inventory["sha256"] not in hashes:
        raise ValueError("Input manifest checksum differs from the split configuration")
    group_splits = defaultdict(set)
    counts = Counter()
    categories = Counter()
    mnist_training_categories = Counter()
    dataset_keys = {
        "Fashion-MNIST": "fashion_mnist",
        "Fashionpedia": "fashionpedia",
        "Polyvore Outfits": "polyvore_outfits",
    }
    for row in raw:
        item = row["item_id"]
        assignment = assignments[item]
        dataset, source, target = (
            row["source_dataset"],
            row["source_split"],
            assignment["target_split"],
        )
        if any(assignment[field] != row[field] for field in ("source_dataset", "source_split")):
            raise ValueError(f"Source metadata mismatch for {item}")
        if dataset not in dataset_keys:
            raise ValueError(f"Unsupported source dataset: {dataset}")
        settings = config[dataset_keys[dataset]]
        if assignment["split_method"] != settings["method"]:
            raise ValueError(f"Split method mismatch for {item}")
        counts[(dataset, target)] += 1
        if dataset == "Fashion-MNIST":
            if source == "test":
                if target != "test":
                    raise ValueError(f"Official test record reassigned: {item}")
            elif source != "train" or target not in {"train", "validation"}:
                raise ValueError(f"Official training record assigned to test: {item}")
            if assignment["random_seed"] != str(config["random_seed"]):
                raise ValueError(f"Random seed mismatch for {item}")
            groups = {item}
            categories[(row["category_ids"], target)] += 1
            if source == "train":
                mnist_training_categories[row["category_ids"]] += 1
        elif dataset == "Fashionpedia":
            if target != source or source not in settings["provided_splits"]:
                raise ValueError(f"Official Fashionpedia split changed: {item}")
            groups = {row["source_image_id"]}
            if assignment["group_id"] != row["source_image_id"]:
                raise ValueError(f"Source-image group mismatch for {item}")
        else:
            if source not in settings["provided_splits"] or target != "validation":
                raise ValueError(f"Official Polyvore split changed: {item}")
            groups = outfit_groups(row["outfit_ids"])
            if not groups or outfit_groups(assignment["group_id"]) != groups:
                raise ValueError(f"Outfit grouping mismatch for {item}")
        for group in groups:
            group_splits[(dataset, "group", group)].add(target)
        if row["source_image_id"]:
            # Fashion-MNIST index zero in official train and test denotes different images.
            namespace = source if dataset == "Fashion-MNIST" else ""
            group_splits[(dataset, "image", namespace, row["source_image_id"])].add(target)
    if any(len(splits) > 1 for splits in group_splits.values()):
        raise ValueError("An image or outfit group crosses target splits")
    for category, count in mnist_training_categories.items():
        expected = count * config["fashion_mnist"]["validation_fraction"]
        if abs(categories[(category, "validation")] - expected) > 1:
            raise ValueError(f"Fashion-MNIST validation stratification mismatch: {category}")
    test_rows = sum(row["target_split"] == "test" for row in assignments.values())
    if test_rows != config["evaluation_manifest"]["records"]:
        raise ValueError("Evaluation count differs from the split configuration")
    return {
        "schema_version": "wardiq.split-verification.v1",
        "rows": len(raw),
        "raw_sha256_lf": sha256_lf(raw_path),
        "split_sha256_lf": sha256_lf(split_path),
        "config_sha256_lf": sha256_lf(config_path),
        "counts": {f"{ds}/{split}": count for (ds, split), count in sorted(counts.items())},
        "duplicate_ids": 0,
        "missing_assignments": 0,
        "group_leakage": 0,
        "evaluation_rows": test_rows,
        "delivered_evaluation_manifest_present": (
            ROOT / config["evaluation_manifest"]["path"]
        ).is_file(),
        "scope": (
            "Manifest assignments only; full raw images are not present or decoded by this check."
        ),
    }


def generate(
    raw_path: Path, split_path: Path, config_path: Path, output_dir: Path
) -> dict[str, object]:
    protect_evidence(output_dir)
    report = verify(raw_path, split_path, config_path)
    fields, assignments = read_rows(split_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "evaluation_manifest.csv"
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(row for row in assignments if row["target_split"] == "test")
    report["generated_evaluation_sha256_lf"] = sha256_lf(output)
    report["evaluation_policy"] = "Final evaluation only; exclude from tuning and model selection."
    (output_dir / "split_verification.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=ROOT / "data/manifests/raw_manifest.csv")
    parser.add_argument("--splits", type=Path, default=ROOT / "data/manifests/split_manifest.csv")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/m1_splits.yaml")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/m1/splits")
    args = parser.parse_args()
    try:
        print(json.dumps(generate(args.raw, args.splits, args.config, args.output_dir), indent=2))
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
        print(f"Split validation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
