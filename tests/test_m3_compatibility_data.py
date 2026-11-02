"""M3 data protocol regressions with small synthetic source parquets."""

import copy
import importlib.util
import io
import json
from argparse import Namespace
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "compatibility_data", ROOT / "scripts/m3/prepare_compatibility_data.py"
)
assert SPEC is not None and SPEC.loader is not None
data = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(data)


def synthetic_item(split, key, category, image_hash=None):
    return {
        "item_id": f"{split}_{key}",
        "source_item_id": key,
        "source_split": split,
        "image_sha256": image_hash or split + key,
        "common_category": category,
        "source_category_id": category,
        "category_supported": True,
    }


def outfit(group, *keys):
    return {
        "set_id": group,
        "items": [{"item_id": key, "index": i + 1} for i, key in enumerate(keys)],
    }


def test_split_policy_removes_ids_and_byte_aliases_but_preserves_test():
    items = {
        "test": {"t": synthetic_item("test", "t", "top", "same")},
        "validation": {
            "v": synthetic_item("validation", "v", "top", "same"),
            "u": synthetic_item("validation", "u", "top"),
        },
        "train": {
            "v": synthetic_item("train", "v", "top"),
            "a": synthetic_item("train", "a", "top"),
            "b": synthetic_item("train", "b", "top", "validationu"),
        },
    }
    preserved = copy.deepcopy(items)
    eligible, excluded = data.split_eligibility(items)
    assert eligible == {"test": {"t"}, "validation": {"u"}, "train": {"a"}}
    assert len(excluded) == 3 and items == preserved


def test_negative_pairs_are_split_local_category_preserving_and_not_known_positive():
    items = {
        k: synthetic_item("train", k, category)
        for k, category in [("a", "top"), ("b", "footwear"), ("c", "top"), ("d", "footwear")]
    }
    outfits = [outfit("one", "a", "b"), outfit("two", "c", "d")]
    pairs, report = data.make_pairs(items, outfits, outfits, "train", 42)
    assert report["positive_pairs"] == report["negative_pairs"] == 2
    assert pairs == data.make_pairs(items, outfits, outfits, "train", 42)[0]
    known = {tuple(sorted(("train_a", "train_b"))), tuple(sorted(("train_c", "train_d")))}
    by_id = {item["item_id"]: item for item in items.values()}
    for pair in pairs:
        assert pair["split"] == "train"
        if not pair["label"]:
            assert tuple(sorted((pair["left_item_id"], pair["right_item_id"]))) not in known
            assert (
                by_id[pair["right_item_id"]]["common_category"]
                == by_id[pair["replaced_item_id"]]["common_category"]
            )
            assert pair["label_origin"].startswith("assumed_")


def test_known_positive_image_alias_is_not_a_negative():
    items = {
        k: synthetic_item("train", k, category, image_hash)
        for k, category, image_hash in [
            ("a", "top", "A"),
            ("b", "footwear", "B"),
            ("c", "top", "C"),
            ("d", "footwear", "B"),
        ]
    }
    outfits = [outfit("one", "a", "b"), outfit("two", "c", "d")]
    pairs, report = data.make_pairs(items, outfits, outfits, "train", 42)
    assert all(pair["label"] == 1 for pair in pairs)
    assert report["positives_without_negative"] == 2


def test_repeated_source_item_positions_are_preserved_without_self_pairs(tmp_path):
    items = {
        "a": synthetic_item("train", "a", "top"),
        "b": synthetic_item("train", "b", "footwear"),
    }
    original = [outfit("one", "a", "a", "b")]
    path = tmp_path / "outfits.json"
    data.write_json(path, original)
    loaded, refs, _ = data.load_outfits(path, items)
    assert loaded == original and refs["one_1"] == refs["one_2"] == "a"
    pairs, report = data.make_pairs(items, loaded, loaded, "train", 42)
    assert report["positive_pairs"] == 1
    assert all(row["left_item_id"] != row["right_item_id"] for row in pairs)


def test_source_category_matching_retains_items_with_unmapped_common_category():
    items = {
        key: synthetic_item("train", key, category)
        for key, category in [("a", "15"), ("b", "343"), ("c", "15"), ("d", "343")]
    }
    for item in items.values():
        item["common_category"] = ""
        item["category_supported"] = False
    outfits = [outfit("one", "a", "b"), outfit("two", "c", "d")]
    pairs, report = data.make_pairs(items, outfits, outfits, "train", 42)
    assert report["positive_pairs"] == report["negative_pairs"] == 2
    by_id = {row["item_id"]: row for row in items.values()}
    for row in pairs:
        if row["label"] == 0:
            assert (
                by_id[row["right_item_id"]]["source_category_id"]
                == by_id[row["replaced_item_id"]]["source_category_id"]
            )
    assert all(item["common_category"] == "" for item in items.values())


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "source"
    (root / "disjoint").mkdir(parents=True)
    (root / "data/disjoint").mkdir(parents=True)
    metadata = {}
    for si, split in enumerate(data.SPLITS):
        short = data.SOURCE_NAMES[split]
        keys = [str(si * 10 + i + 1) for i in range(4)]
        images = []
        for i, key in enumerate(keys):
            payload = io.BytesIO()
            Image.new("RGB", (4, 4), (si * 70, i * 60, 40)).save(payload, format="PNG")
            images.append(
                {"item_id": key, "image": {"bytes": payload.getvalue(), "path": key + ".png"}}
            )
            metadata[key] = {
                "category_id": "15" if i % 2 == 0 else "46",
                "semantic_category": "tops" if i % 2 == 0 else "shoes",
            }
        path = (
            root / "disjoint/validation-00000-of-00001.parquet"
            if split == "validation"
            else root / f"data/disjoint/{split}.parquet"
        )
        pq.write_table(pa.Table.from_pylist(images), path)
        groups = [outfit(f"{si}A", *keys[:2]), outfit(f"{si}B", *keys[2:])]
        data.write_json(root / f"disjoint/{short}.json", groups)
        (root / f"disjoint/compatibility_{short}.txt").write_text(
            f"1 {si}A_1 {si}A_2\n0 {si}A_1 {si}B_2\n", encoding="utf-8"
        )
        data.write_json(
            root / f"disjoint/fill_in_blank_{short}.json",
            [{"question": [f"{si}A_1"], "blank_position": 2, "answers": [f"{si}A_2", f"{si}B_2"]}],
        )
    data.write_json(root / "polyvore_item_metadata.json", metadata)
    (root / "categories.csv").write_text("15,tunic,tops\n46,sandals,shoes\n", encoding="utf-8")
    return Namespace(
        source_root=root,
        taxonomy=ROOT / "configs/m1/taxonomy.json",
        output=tmp_path / "output",
        seed=42,
        stage="audit",
        cache_records=tmp_path / "missing.jsonl",
    )


def test_audit_only_does_not_make_a_category_decision(source):
    report = data.build(source)
    assert report["training_ready"] is False and report["source_files_unchanged"] is True
    assert report["scope"] == "split_inventory_audit_only"
    assert not list(source.output.rglob("pairs.jsonl"))
    assert all(report["split_summary"][s]["eligible_items"] == 4 for s in data.SPLITS)


@pytest.mark.parametrize("keep_legacy", [False, True])
def test_audit_accepts_recovered_validation_layout(source, keep_legacy):
    legacy = source.source_root / "disjoint/validation-00000-of-00001.parquet"
    recovered = source.source_root / "data/disjoint/validation.parquet"
    recovered.write_bytes(legacy.read_bytes())
    if not keep_legacy:
        legacy.unlink()
    assert data.source_paths(source.source_root)["validation_images"] == recovered
    report = data.build(source)
    assert report["source_files_unchanged"] is True
    assert all(report["split_summary"][s]["eligible_items"] == 4 for s in data.SPLITS)


def test_real_pipeline_reports_missing_training_cache_and_is_repeatable(source):
    source.stage = "pairs"
    first = data.build(source)
    assert first["training_ready"] is False and first["handoff_ready"] is False
    assert first["cache_coverage"]["train"]["missing_items"] == 4
    assert first["pair_summary"]["train"]["negative_pairs"] == 2
    first_pairs = (source.output / "train/pairs.jsonl").read_bytes()
    source.output = source.output.parent / "repeat"
    data.build(source)
    assert (source.output / "train/pairs.jsonl").read_bytes() == first_pairs


def test_output_may_not_replace_original_sources_or_existing_results(source):
    target = source.output
    source.output = source.source_root
    with pytest.raises(ValueError, match="overlaps"):
        data.build(source)
    source.output = target
    data.build(source)
    with pytest.raises(ValueError, match="already exists"):
        data.build(source)


@pytest.mark.parametrize("kind", ["compatibility", "fitb", "duplicate_position"])
def test_bad_source_references_fail_before_success_report(source, kind):
    if kind == "compatibility":
        (source.source_root / "disjoint/compatibility_train.txt").write_text("1 bad_1 bad_2\n")
    elif kind == "fitb":
        data.write_json(
            source.source_root / "disjoint/fill_in_blank_train.json",
            [{"question": ["0A_1"], "blank_position": 2, "answers": ["0B_2"]}],
        )
    else:
        path = source.source_root / "disjoint/train.json"
        outfits = data.read_json(path)
        outfits[0]["items"][1]["index"] = 1
        data.write_json(path, outfits)
    with pytest.raises(ValueError):
        data.build(source)
    assert not (source.output / "report.json").exists()


def test_filtering_removes_whole_fitb_questions_without_changing_answers(source):
    paths = data.source_paths(source.source_root)
    items = data.scan_items(paths, data.load_taxonomy(source.taxonomy))
    eligible, _ = data.split_eligibility(items)
    eligible["train"].remove("4")
    source.output.mkdir()
    _, _, report = data.filter_examples(paths, items, eligible, source.output)
    assert report["train"]["eligible_outfits"] == 1
    assert report["train"]["eligible_fitb_questions"] == 0
    original = data.read_json(paths["train_fitb"])
    assert len(original[0]["answers"]) == 2


def test_cache_split_mismatch_is_rejected(source):
    items = {s: {"x": synthetic_item(s, "x", "top")} for s in data.SPLITS}
    pairs = {s: [] for s in data.SPLITS}
    pairs["train"] = [{"left_item_id": "train_x", "right_item_id": "train_x"}]
    source.cache_records.write_text(
        json.dumps({"item_id": "train_x", "split": {"target_split": "validation"}}) + "\n"
    )
    with pytest.raises(ValueError, match="split mismatch"):
        data.cache_coverage(source.cache_records, items, pairs)


def test_jsonl_exports_have_platform_independent_bytes(tmp_path):
    path = tmp_path / "pairs.jsonl"
    data.write_jsonl(path, [{"label": 1, "item_id": "001"}])
    assert path.read_bytes() == b'{"item_id": "001", "label": 1}\n'


def training_request(source):
    paths = data.source_paths(source.source_root)
    items = data.scan_items(paths, data.load_taxonomy(source.taxonomy))["train"]
    directory = source.output.parent / "request"
    directory.mkdir()
    inventory = directory / "train_required_items.csv"
    data.write_csv(inventory, items.values())
    request = {
        "version": "wardiq.m3.training-feature-request.v1",
        "items_file": inventory.name,
        "items_sha256": data.sha256(inventory),
        "item_count": len(items),
        "source_parquet_sha256": data.sha256(paths["train_images"]),
    }
    path = directory / "training_request.json"
    data.write_json(path, request)
    return path


def test_training_input_export_resolves_for_hayats_existing_extractor(source):
    from wardiq.representation.clip_embeddings import load_usable_manifest

    request = training_request(source)
    report = data.prepare_training_images(request, source.source_root, source.output)
    frame = load_usable_manifest(source.output / "garment_manifest.csv")
    assert report["item_count"] == len(frame) == 4
    assert frame.target_split.eq("train").all()
    assert set(frame.item_id) == {f"polyvore_outfits_disjoint_train_{i}" for i in range(1, 5)}
    assert report["features_extracted"] is False
    for row in frame.itertuples():
        assert data.sha256(row.image_path) == row.image_sha256
        assert data.sha256(row.source_image_path) == row.source_image_sha256
    with pytest.raises(ValueError, match="exists"):
        data.prepare_training_images(request, source.source_root, source.output)


@pytest.mark.parametrize("problem", ["inventory", "parquet", "test_item"])
def test_training_export_rejects_changed_or_heldout_inputs(source, problem):
    import csv

    request = training_request(source)
    if problem == "parquet":
        with (source.source_root / "data/disjoint/train.parquet").open("ab") as stream:
            stream.write(b"changed")
    else:
        config = data.read_json(request)
        inventory = request.parent / config["items_file"]
        if problem == "inventory":
            with inventory.open("a") as stream:
                stream.write("changed")
        else:
            with inventory.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            rows[0]["source_split"] = "test"
            data.write_csv(inventory, rows)
            config["items_sha256"] = data.sha256(inventory)
            data.write_json(request, config)
    with pytest.raises(ValueError):
        data.prepare_training_images(request, source.source_root, source.output)
    assert not source.output.exists()
