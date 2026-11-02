"""Behavioral tests for the isolated Hayat implementation."""

import copy
import csv
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from wardiq.compatibility.rule_baseline import score_pair_features

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / "scripts/m3"))
import build_pair_features as cli  # noqa: E402
import extract_training_features as extraction  # noqa: E402

SPEC = importlib.util.spec_from_file_location(
    "hayat_pair_features", PACKAGE / "src/wardiq/compatibility/pair_features.py"
)
f = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(f)


def item(key, axis=0, split="train"):
    vector = np.eye(1, 512, axis, dtype=np.float32).ravel().tolist()
    return {
        "schema_version": "1.0.0",
        "item_id": key,
        "source_dataset": "Polyvore Outfits",
        "category": {
            "common_category": "top",
            "mapping_status": "direct",
            "category_schema_version": "1.0.0",
        },
        "embedding": {
            "model": f.MODEL,
            "model_version": f.REVISION,
            "dimension": 512,
            "vector": vector,
        },
        "attributes": {"scores": None, "mask": None},
        "color": {"model": None, "model_version": None, "palette": None},
        "split": {"target_split": split},
    }


def builder(records=None, names=None, split="train"):
    obj = f.PairFeatureBuilder(f.make_config(names or ["jeans"]), split)
    for row in records or [item("a"), item("b", 1)]:
        obj.add_item(row)
    return obj


def test_exact_symmetry_and_analytic_embedding_features():
    obj = builder()
    result = obj.transform_pair("a", "b")
    np.testing.assert_array_equal(result, obj.transform_pair("b", "a"))
    columns = obj.config["feature_names"]
    assert result.dtype == np.float32
    assert result.shape == (obj.config["dimension"],)
    assert result[columns.index("clip:cosine")] == 0
    assert result[columns.index("clip:abs_difference:0")] == 1
    assert result[columns.index("clip:abs_difference:1")] == 1
    assert np.isfinite(result).all()


def test_no_label_or_dataset_statistics_needed():
    first = builder().transform_pair("a", "b")
    obj = builder([item("b", 1), item("a"), item("unrelated", 20)])
    np.testing.assert_array_equal(first, obj.transform_pair("a", "b"))


def test_unknown_category_is_explicit_not_remapped():
    a = item("a")
    a["category"].update(common_category=None, mapping_status="unmapped")
    obj = builder([a, item("b")])
    values = obj.transform_pair("a", "b")
    names = obj.config["feature_names"]
    assert values[names.index("category:both_mapped")] == 0
    assert values[names.index("category:top|unknown")] == 1
    assert a["category"]["common_category"] is None


def test_color_missing_and_real_zero_distance_are_distinct():
    a, b = item("a"), item("b")
    obj = builder([a, b])
    index = obj.config["feature_names"].index("lab:both_available")
    assert obj.transform_pair("a", "b")[index] == 0
    palette = [{"L": 50, "a": 0, "b": 0, "proportion": 1}]
    for record in (a, b):
        record["color"] = {
            "model": "LAB_KMeans",
            "model_version": "wardiq.color.v1",
            "palette": palette,
        }
    obj = builder([a, b])
    values = obj.transform_pair("a", "b")
    assert values[index] == 1
    np.testing.assert_array_equal(values[index - 4 : index], np.zeros(4))


def test_weighted_lab_distance_analytic_and_symmetric():
    a, b = item("a"), item("b")
    for record, lightness in ((a, 20), (b, 70)):
        record["color"] = {
            "model": "LAB_KMeans",
            "model_version": "wardiq.color.v1",
            "palette": [{"L": lightness, "a": 0, "b": 0, "proportion": 1}],
        }
    obj = builder([a, b])
    values = obj.transform_pair("a", "b")
    assert values[obj.config["feature_names"].index("lab:expected_delta_e76_over_100")] == 0.5
    np.testing.assert_array_equal(values, obj.transform_pair("b", "a"))


def test_known_zero_attribute_is_not_missing():
    a, b = item("a"), item("b")
    for record in (a, b):
        record["attributes"] = {
            "vocabulary_source": "fashionpedia_v1_partial",
            "vocabulary_version": "1.0.0",
            "scores": {"jeans": 0.0},
            "mask": {"jeans": "present"},
        }
    obj = builder([a, b])
    mask = obj.config["feature_names"].index("attribute:jeans:both_observed")
    assert obj.transform_pair("a", "b")[mask] == 1
    b["attributes"]["scores"]["jeans"] = None
    b["attributes"]["mask"]["jeans"] = "not_annotated"
    obj = builder([a, b])
    assert obj.transform_pair("a", "b")[mask] == 0


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": "2.0.0"},
        {"split": {"target_split": "test"}},
        {
            "embedding": {
                "model": "other",
                "model_version": f.REVISION,
                "dimension": 512,
                "vector": [0] * 512,
            }
        },
        {
            "category": {
                "common_category": "invented",
                "mapping_status": "direct",
                "category_schema_version": "1.0.0",
            }
        },
        {"attributes": {"scores": {"jeans": 0}, "mask": {"jeans": "not_annotated"}}},
    ],
)
def test_reject_incompatible_records(change):
    record = item("a")
    record.update(change)
    with pytest.raises(ValueError):
        builder([record])


@pytest.mark.parametrize("bad", [[0] * 512, [1, 2], [float("nan")] * 512])
def test_reject_bad_embeddings(bad):
    record = item("a")
    record["embedding"]["vector"] = bad
    with pytest.raises(ValueError):
        builder([record])


def test_training_and_wardrobe_inference_are_identical():
    train = builder()
    inference = builder([item("a", split=None), item("b", 1, split=None)], split="inference")
    np.testing.assert_array_equal(
        train.transform_pair("a", "b"), inference.transform_pair("a", "b")
    )


def test_reject_duplicate_self_missing_and_tampered_config():
    obj = builder()
    with pytest.raises(ValueError):
        obj.add_item(item("a"))
    for pair in [("a", "a"), ("a", "missing")]:
        with pytest.raises(ValueError):
            obj.transform_pair(*pair)
    config = f.make_config(["jeans"])
    config["dimension"] += 1
    with pytest.raises(ValueError):
        f.PairFeatureBuilder(config, "train")


def write_fixture(tmp_path, pairs=None, records=None):
    config = tmp_path / "config.json"
    config.write_text(json.dumps(f.make_config(["jeans"])))
    cache = tmp_path / "records.jsonl"
    cache.write_text("".join(json.dumps(r) + "\n" for r in records or [item("a"), item("b", 1)]))
    pair_file = tmp_path / "pairs.jsonl"
    pairs = (
        pairs
        if pairs is not None
        else [
            {
                "left_item_id": "a",
                "right_item_id": "b",
                "split": "train",
                "label": 1,
                "label_origin": "fixture",
            }
        ]
    )
    pair_file.write_text("".join(json.dumps(r) + "\n" for r in pairs))
    return cache, pair_file, config


def test_cli_alignment_reproducibility_and_output_protection(tmp_path):
    args = write_fixture(tmp_path)
    before = [p.read_bytes() for p in args]
    for name in ("v1", "v2"):
        cli.build(*args, tmp_path / name, "train")
    np.testing.assert_array_equal(
        np.load(tmp_path / "v1/features.npy"), np.load(tmp_path / "v2/features.npy")
    )
    assert np.load(tmp_path / "v1/labels.npy").tolist() == [1]
    assert [p.read_bytes() for p in args] == before
    with pytest.raises(ValueError):
        cli.build(*args, tmp_path / "v1", "train")
    with (tmp_path / "v1/pair_inventory.csv").open() as stream:
        assert list(csv.DictReader(stream))[0]["left_item_id"] == "a"


@pytest.mark.parametrize("case", ["missing", "duplicate", "split", "label", "empty"])
def test_bad_pair_population_fails_before_outputs(tmp_path, case):
    pair = {"left_item_id": "a", "right_item_id": "b", "split": "train", "label": 1}
    pairs = [copy.deepcopy(pair)]
    if case == "missing":
        pairs[0]["right_item_id"] = "absent"
    elif case == "duplicate":
        pairs.append({**pair, "left_item_id": "b", "right_item_id": "a"})
    elif case == "split":
        pairs[0]["split"] = "validation"
    elif case == "label":
        pairs[0]["label"] = True
    elif case == "empty":
        pairs = []
    args = write_fixture(tmp_path, pairs)
    with pytest.raises(ValueError):
        cli.build(*args, tmp_path / "out", "train")
    assert not (tmp_path / "out").exists()


def test_checkpoint_resume_and_tamper_detection(tmp_path, monkeypatch):
    """Exercise orchestration without substituting fake outputs in real extraction."""
    import pandas as pd

    import wardiq.representation.clip_embeddings as clip

    image = tmp_path / "image.jpg"
    image.write_bytes(b"fixture")
    manifest = tmp_path / "manifest.csv"
    pd.DataFrame(
        [
            {
                "item_id": key,
                "source_dataset": "Polyvore Outfits",
                "image_path": str(image),
                "target_split": "train",
                "usable_derivative": True,
                "image_sha256": extraction.digest(image),
            }
            for key in ("a", "b", "c")
        ]
    ).to_csv(manifest, index=False)
    calls = []

    def fake_extract(source, destination, **kwargs):
        calls.append(source)
        rows = pd.read_csv(source)
        vectors = np.zeros((len(rows), 512), dtype=np.float32)
        vectors[:, 0] = 1
        np.save(destination / "clip_embeddings.npy", vectors)
        rows.insert(0, "embedding_row_index", np.arange(len(rows)))
        rows.to_csv(destination / "clip_inventory.csv", index=False)
        (destination / "metadata.json").write_text(
            json.dumps({"model_id": f.MODEL, "model_revision": f.REVISION})
        )

    monkeypatch.setattr(clip, "extract_clip_embeddings", fake_extract)
    out = tmp_path / "extraction"
    extraction.extract(manifest, out, chunk_size=2)
    assert len(calls) == 2
    assert np.load(out / "clip_embeddings.npy").shape == (3, 512)
    extraction.extract(manifest, out, chunk_size=2, resume=True)
    assert len(calls) == 2
    (out / "chunks/000000/clip_embeddings.npy").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="Changed completed chunk"):
        extraction.extract(manifest, out, chunk_size=2, resume=True)

    unrelated = tmp_path / "unrelated_existing_directory"
    unrelated.mkdir()
    with pytest.raises(ValueError, match="original run.json"):
        extraction.extract(manifest, unrelated, resume=True)
    with pytest.raises(ValueError, match="configuration differs"):
        extraction.extract(manifest, out, chunk_size=3, resume=True)


def test_rule_baseline_integrates_with_real_pair_feature_builder():
    obj = builder()
    values = obj.transform_pair("a", "b")
    names = obj.config["feature_names"]

    pair_score = score_pair_features(
        feature_names=names,
        feature_values=values.tolist(),
    )

    assert pair_score.status == "scored"
    assert pair_score.score is not None
    assert 0.0 <= pair_score.score <= 1.0
