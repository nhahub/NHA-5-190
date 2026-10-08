"""Canonical split isolation, immutable inventory and garment join regressions."""

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_m1_splits as splits  # noqa: E402


@pytest.fixture
def inventory(tmp_path):
    raw = []
    assignments = []
    for index in range(11):
        source = "test" if index == 10 else "train"
        target = "test" if index == 10 else "validation" if index == 9 else "train"
        raw.append(
            dict(
                item_id=f"item-{index}",
                source_dataset="Fashion-MNIST",
                source_split=source,
                source_image_id=str(index),
                category_ids="0",
            )
        )
        assignments.append(
            dict(
                item_id=f"item-{index}",
                source_dataset="Fashion-MNIST",
                source_split=source,
                target_split=target,
                split_method="stratified_random_split",
                random_seed="42",
                group_id="",
            )
        )
    raw_path, assignment_path, config_path = [
        tmp_path / name for name in ("raw.csv", "split.csv", "config.yaml")
    ]
    write_csv(raw_path, raw)
    write_csv(assignment_path, assignments)
    config = dict(
        input_manifest=dict(
            rows=len(raw),
            columns=len(raw[0]),
            sha256=hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        ),
        fashion_mnist=dict(method="stratified_random_split", validation_fraction=0.1),
        random_seed=42,
        evaluation_manifest=dict(records=1, path="data/manifests/not-delivered.csv"),
    )
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return raw_path, assignment_path, config_path, assignments


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_exact_inventory_and_evaluation_export_repeat(inventory, tmp_path):
    raw, assignments, config, _ = inventory
    output = tmp_path / "outputs"
    report = splits.generate(raw, assignments, config, output)
    assert report["rows"] == 11 and report["group_leakage"] == 0
    assert report["delivered_evaluation_manifest_present"] is False
    fields, evaluation = splits.read_rows(output / "evaluation_manifest.csv")
    assert fields == list(splits.SPLIT_FIELDS)
    assert [row["item_id"] for row in evaluation] == ["item-10"]
    original = (output / "evaluation_manifest.csv").read_bytes()
    assert splits.generate(raw, assignments, config, output) == report
    assert (output / "evaluation_manifest.csv").read_bytes() == original
    # Git LF and Windows CRLF checkouts identify the same input and assignments.
    raw.write_bytes(raw.read_bytes().replace(b"\n", b"\r\n"))
    assignments.write_bytes(assignments.read_bytes().replace(b"\n", b"\r\n"))
    assert splits.generate(raw, assignments, config, output) == report


@pytest.mark.parametrize(
    "mutation, message",
    [
        ("duplicate", "duplicate"),
        ("missing", "exactly cover"),
        ("test_to_train", "test record reassigned"),
        ("train_to_test", "training record"),
        ("dataset", "metadata mismatch"),
        ("seed", "seed mismatch"),
        ("method", "method mismatch"),
        ("invalid", "Invalid target"),
        ("unstratified", "stratification mismatch"),
    ],
)
def test_rejects_bad_assignments_before_writing(inventory, tmp_path, mutation, message):
    raw, path, config, rows = inventory
    if mutation == "duplicate":
        rows.append(rows[0].copy())
    elif mutation == "missing":
        rows.pop()
    elif mutation == "test_to_train":
        rows[-1]["target_split"] = "train"
    elif mutation == "train_to_test":
        rows[0]["target_split"] = "test"
    elif mutation == "dataset":
        rows[0]["source_dataset"] = "Fashionpedia"
    elif mutation == "seed":
        rows[0]["random_seed"] = "0"
    elif mutation == "method":
        rows[0]["split_method"] = "random"
    elif mutation == "invalid":
        rows[0]["target_split"] = "val"
    else:
        for row in rows[:9]:
            row["target_split"] = "validation"
    write_csv(path, rows)
    output = tmp_path / "outputs"
    with pytest.raises(ValueError, match=message):
        splits.generate(raw, path, config, output)
    assert not output.exists()


def test_duplicate_source_image_cannot_cross_splits(inventory):
    raw, path, config_path, _ = inventory
    _, rows = splits.read_rows(raw)
    rows[9]["source_image_id"] = rows[0]["source_image_id"]
    write_csv(raw, rows)
    config = yaml.safe_load(config_path.read_text())
    config["input_manifest"]["sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    config_path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match="crosses target splits"):
        splits.verify(raw, path, config_path)


def test_committed_full_inventory_and_cli_from_other_directory(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/validate_m1_splits.py"),
            "--output-dir",
            str(tmp_path),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    report = json.loads(result.stdout)
    assert report["rows"] == 85815
    assert report["counts"] == {
        "Fashion-MNIST/train": 54000,
        "Fashion-MNIST/validation": 6000,
        "Fashion-MNIST/test": 10000,
        "Fashionpedia/validation": 1158,
        "Polyvore Outfits/validation": 14657,
    }
    _, evaluation = splits.read_rows(tmp_path / "evaluation_manifest.csv")
    assert len(evaluation) == 10000
    assert all(row["source_split"] == row["target_split"] == "test" for row in evaluation)


def test_garments_follow_canonical_splits_and_keep_all_outfit_groups(tmp_path):
    config = yaml.safe_load((ROOT / "configs/m1/garment_preparation.yaml").read_text())
    _, rows = splits.read_rows(ROOT / config["canonical_split_manifest"])
    # Contradict the historical sample assignment to prove canonical authority.
    next(row for row in rows if row["item_id"] == "fashion_mnist_train_000000")["target_split"] = (
        "validation"
    )
    assignment_path = tmp_path / "assignments.csv"
    write_csv(assignment_path, rows)
    config["canonical_split_manifest"] = str(assignment_path)
    config["output"] = {
        "manifest_path": str(tmp_path / "garments.csv"),
        "image_manifest_path": str(tmp_path / "images.csv"),
        "crops_root": str(tmp_path / "crops"),
    }
    config_path = tmp_path / "garments.yaml"
    config_path.write_text(yaml.safe_dump(config))
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/prepare_garment_crops.py"),
            "--config",
            str(config_path),
        ],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    garments = pd.read_csv(tmp_path / "garments.csv")
    images = pd.read_csv(tmp_path / "images.csv")
    assert (
        garments.loc[garments.item_id == "fashion_mnist_train_000000", "target_split"].item()
        == "validation"
    )
    assert (
        images.loc[images.item_id == "fashion_mnist_train_000000", "target_split"].item()
        == "validation"
    )
    groups = garments.loc[garments.source_item_id.astype(str) == "213366441", "group_id"].item()
    assert groups == "224931182;225010218"
    assert splits.outfit_groups("42:1;42:3;99:1") == {"42", "99"}
