"""Unknown-label semantics and executable validation for Ziad's attribute handoff."""

import ast
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/m2"))
import attribute_common as attributes  # noqa: E402


def command(script, *args, cwd):
    return subprocess.run(
        [sys.executable, str(ROOT / script), *map(str, args)],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def test_unknown_attribute_positions_do_not_become_known_negatives():
    target, mask = attributes.build_target_and_mask([219], [0, 20, 219])
    assert target == [0, 0, 1] and mask == [0, 0, 1]
    assert attributes.build_target_and_mask([], [0, 20]) == ([0, 0], [0, 0])
    with pytest.raises(ValueError, match="not in vocabulary"):
        attributes.build_target_and_mask([999], [0, 20])


@pytest.mark.parametrize("value", ["[True]", "[1.5]", "[-1]", '["20"]', "not a list"])
def test_malformed_annotation_ids_are_rejected(value):
    with pytest.raises((ValueError, SyntaxError)):
        attributes.parse_attribute_ids(value)


@pytest.mark.parametrize("mutation", ["index", "duplicate", "order", "length", "source"])
def test_invalid_vocabulary_order_or_shape_is_rejected(tmp_path, mutation):
    vocabulary = attributes.load_vocabulary()
    if mutation == "index":
        vocabulary["labels"][0]["index"] = 1
    elif mutation == "duplicate":
        vocabulary["labels"][1]["attribute_id"] = 0
    elif mutation == "order":
        vocabulary["labels"][0]["attribute_id"] = 999
    elif mutation == "length":
        vocabulary["vector_length"] = 1
    else:
        vocabulary["source_dataset"] = "Polyvore Outfits"
    path = tmp_path / "vocabulary.json"
    path.write_text(json.dumps(vocabulary))
    with pytest.raises(ValueError):
        attributes.load_vocabulary(path)


def test_full_attribute_handoff_is_portable_and_repeatable(tmp_path):
    outputs = [tmp_path / "first", tmp_path / "second"]
    committed = [
        ROOT / "reports/m2/sample_prediction_v1.json",
        ROOT / "reports/m2/supported_attribute_coverage_v1.csv",
    ]
    before = [path.read_bytes() for path in committed]
    for output in outputs:
        result = command(
            "scripts/m2/run_attribute_handoff.py", "--output-dir", output, cwd=tmp_path
        )
        assert result.returncode == 0, result.stderr
        assert "training remains blocked" in result.stdout
    for name in (
        "attribute_targets_validation_sample.csv",
        "attribute_support_v1.csv",
        "supported_attribute_coverage_v1.csv",
        "sample_prediction_v1.json",
        "model_inference_config_v1.json",
        "attribute_handoff_report.json",
    ):
        assert (outputs[0] / name).read_bytes() == (outputs[1] / name).read_bytes()
    assert before == [path.read_bytes() for path in committed]
    report = json.loads((outputs[0] / "attribute_handoff_report.json").read_text())
    assert (report["source_rows"], report["vector_length"]) == (46, 35)
    assert (
        report["observed_positive_positions"],
        report["unknown_positions"],
        report["known_negative_positions"],
    ) == (87, 1523, 0)
    assert report["training_supported_labels"] == 0 and report["model_checkpoint"] is None
    prediction = json.loads((outputs[0] / "sample_prediction_v1.json").read_text())
    assert prediction["scores"] is None
    assert prediction["support_mask"] == [0] * 35
    assert len(prediction["observation_mask"]) == 35
    assert (
        json.loads(
            (ROOT / "configs/m2/attribute_prediction_schema_v1.json").read_text(
                encoding="utf-8-sig"
            )
        )["scores"]["nullable"]
        is True
    )
    # Independently reconcile the published ID/name pairs against delivered annotations.
    vocabulary = attributes.load_vocabulary()
    names = {label["attribute_id"]: label["name"] for label in vocabulary["labels"]}
    source = attributes.read_manifest(attributes.DEFAULT_MANIFEST)
    observed = set()
    for row in source.itertuples():
        ids, labels = ast.literal_eval(row.attribute_ids), ast.literal_eval(row.attribute_labels)
        assert [names[attribute_id] for attribute_id in ids] == labels
        observed.update(ids)
    assert observed == set(names)


@pytest.fixture(scope="module")
def valid_targets(tmp_path_factory):
    directory = tmp_path_factory.mktemp("attributes")
    path = directory / "targets.csv"
    result = command("scripts/m2/build_attribute_targets.py", "--output", path, cwd=directory)
    assert result.returncode == 0, result.stderr
    return path


@pytest.mark.parametrize(
    "mutation",
    [
        "mask",
        "target",
        "short",
        "nonbinary",
        "version",
        "split",
        "counts",
        "duplicate",
        "missing",
    ],
)
def test_invalid_targets_return_failure_without_a_traceback(tmp_path, valid_targets, mutation):
    frame = pd.read_csv(valid_targets, dtype=str, keep_default_na=False)
    if mutation in {"mask", "target", "short", "nonbinary"}:
        field = "attribute_target" if mutation in {"target", "short"} else "observation_mask"
        values = json.loads(frame.at[0, field])
        if mutation == "short":
            values = []
        elif mutation == "nonbinary":
            values[0] = 0.0
        elif mutation == "mask":
            values[values.index(1)] = 0
        else:
            values[values.index(0)] = 1
        frame.at[0, field] = json.dumps(values)
    elif mutation == "version":
        frame.at[0, "vocabulary_version"] = "wrong-version"
    elif mutation == "split":
        frame.at[0, "source_split"] = "train"
    elif mutation == "counts":
        frame.at[0, "unknown_count"] = "0"
    elif mutation == "duplicate":
        frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    else:
        frame = frame.iloc[1:]
    path = tmp_path / "bad.csv"
    frame.to_csv(path, index=False)
    result = command("scripts/m2/validate_attribute_targets.py", "--targets", path, cwd=tmp_path)
    assert result.returncode == 1
    assert "Attribute handoff failed:" in result.stderr
    assert "Traceback" not in result.stderr


def test_attribute_outputs_cannot_replace_committed_evidence_or_inputs(tmp_path):
    for path in (
        ROOT / "reports/m2/sample_prediction_v1.json",
        ROOT / "configs/m2/attribute_vocabulary_v1.json",
        ROOT / "data/manifests/fashionpedia_validation_sample_manifest.csv",
    ):
        before = path.read_bytes()
        with pytest.raises(ValueError):
            attributes.safe_output(path)
        assert path.read_bytes() == before
    with pytest.raises(ValueError, match="source inputs"):
        attributes.safe_output(tmp_path / "input.csv", tmp_path / "input.csv")
