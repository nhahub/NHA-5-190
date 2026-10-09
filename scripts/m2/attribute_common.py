"""Shared I/O and validation for the provisional, validation-only attribute handoff."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from research_cli import protect_evidence  # noqa: E402

DEFAULT_MANIFEST = ROOT / "data/manifests/fashionpedia_validation_sample_manifest.csv"
DEFAULT_VOCABULARY = ROOT / "configs/m2/attribute_vocabulary_v1.json"
DEFAULT_TARGETS = ROOT / "data/processed/m2/attribute_targets_validation_sample.csv"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts/m2/attributes/v1"


def resolve_path(value):
    path = Path(value)
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def safe_output(value, *inputs):
    output = resolve_path(value)
    protect_evidence(output)
    reports = ROOT / "reports"
    if output == reports or reports in output.parents:
        raise ValueError("Output would overwrite committed report evidence; use artifacts/")
    if output in {resolve_path(path) for path in inputs}:
        raise ValueError("Output must not overwrite source inputs")
    return output


def load_vocabulary(path=DEFAULT_VOCABULARY):
    vocabulary = json.loads(resolve_path(path).read_text(encoding="utf-8-sig"))
    labels = vocabulary.get("labels")
    if not isinstance(labels, list) or not labels:
        raise ValueError("Vocabulary needs a nonempty label list")
    if type(vocabulary.get("vector_length")) is not int or vocabulary["vector_length"] != len(
        labels
    ):
        raise ValueError("Vocabulary vector_length does not match labels length")
    if (
        not isinstance(vocabulary.get("vocabulary_version"), str)
        or not vocabulary["vocabulary_version"]
    ):
        raise ValueError("Vocabulary version must be a nonempty string")
    if any(not isinstance(label, dict) for label in labels):
        raise ValueError("Each vocabulary label must be an object")
    if any(type(label.get("index")) is not int for label in labels) or [
        label.get("index") for label in labels
    ] != list(range(len(labels))):
        raise ValueError("Vocabulary indexes must follow vector order, starting at zero")
    ids = [label.get("attribute_id") for label in labels]
    if vocabulary.get("source_dataset") != "Fashionpedia":
        raise ValueError("Expected a Fashionpedia attribute vocabulary")
    if any(type(value) is not int or value < 0 for value in ids):
        raise ValueError("Vocabulary IDs must be nonnegative integers")
    if len(set(ids)) != len(ids):
        raise ValueError("Vocabulary contains duplicate attribute IDs")
    if vocabulary.get("ordering") != "ascending_attribute_id" or ids != sorted(ids):
        raise ValueError("Vocabulary IDs must follow the declared ascending order")
    if any(not isinstance(label.get("name"), str) or not label["name"] for label in labels):
        raise ValueError("Vocabulary labels need nonempty names")
    return vocabulary


def parse_attribute_ids(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if str(value).strip() in {"", "[]"}:
        return []
    parsed = value if isinstance(value, list) else ast.literal_eval(str(value))
    if not isinstance(parsed, list) or any(type(item) is not int or item < 0 for item in parsed):
        raise ValueError("Expected a list of nonnegative integer attribute IDs")
    return parsed


def build_target_and_mask(attribute_ids, vocabulary_ids):
    observed = set(attribute_ids)
    unknown_ids = observed - set(vocabulary_ids)
    if unknown_ids:
        raise ValueError(f"Observed attribute IDs are not in vocabulary: {sorted(unknown_ids)}")
    targets = [int(attribute_id in observed) for attribute_id in vocabulary_ids]
    return targets, targets.copy()


def read_manifest(path):
    frame = pd.read_csv(resolve_path(path), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    required = {"item_id", "source_dataset", "source_split", "attribute_ids"}
    if not required <= set(frame.columns):
        raise ValueError("Attribute source manifest is missing required columns")
    if frame.empty or frame.item_id.str.strip().eq("").any() or frame.item_id.duplicated().any():
        raise ValueError("Attribute manifest needs nonempty, unique stable item IDs")
    if not frame.source_dataset.eq("Fashionpedia").all():
        raise ValueError("This vocabulary describes Fashionpedia attributes only")
    return frame


def read_targets(path):
    frame = pd.read_csv(resolve_path(path), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    required = {
        "item_id",
        "source_dataset",
        "source_split",
        "attribute_target",
        "observation_mask",
        "observed_positive_count",
        "unknown_count",
        "negative_count",
        "vocabulary_version",
    }
    if not required <= set(frame.columns):
        raise ValueError("Attribute targets are missing required columns")
    if frame.empty or frame.item_id.str.strip().eq("").any() or frame.item_id.duplicated().any():
        raise ValueError("Target rows need nonempty, unique stable item IDs")
    return frame


def validate_targets(manifest, targets, vocabulary):
    source, output = read_manifest(manifest), read_targets(targets)
    if set(source.item_id) != set(output.item_id):
        raise ValueError("Target IDs must exactly match the source manifest")
    ids = [label["attribute_id"] for label in vocabulary["labels"]]
    indexed = output.set_index("item_id")
    for row in source.itertuples():
        result = indexed.loc[row.item_id]
        for field in ("source_dataset", "source_split"):
            if result[field] != getattr(row, field):
                raise ValueError(f"Source metadata mismatch for {row.item_id}")
        if result.vocabulary_version != vocabulary["vocabulary_version"]:
            raise ValueError(f"Vocabulary version mismatch for {row.item_id}")
        target, mask = json.loads(result.attribute_target), json.loads(result.observation_mask)
        for name, vector in (("target", target), ("mask", mask)):
            if not isinstance(vector, list) or len(vector) != len(ids):
                raise ValueError(f"{name} length mismatch for {row.item_id}")
            if any(type(value) is not int or value not in (0, 1) for value in vector):
                raise ValueError(f"{name} must contain binary integers for {row.item_id}")
        expected, expected_mask = build_target_and_mask(parse_attribute_ids(row.attribute_ids), ids)
        if target != expected or mask != expected_mask:
            raise ValueError(
                f"Target/mask mismatch for {row.item_id}; unknown labels must stay masked"
            )
        counts = {
            "observed_positive_count": sum(expected_mask),
            "unknown_count": len(ids) - sum(expected_mask),
            "negative_count": 0,
        }
        if any(int(result[field]) != count for field, count in counts.items()):
            raise ValueError(f"Target summary counts mismatch for {row.item_id}")
    return output


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def run(main):
    try:
        return main()
    except (OSError, ValueError, KeyError, TypeError, SyntaxError) as error:
        print(f"Attribute handoff failed: {error}", file=sys.stderr)
        return 1
