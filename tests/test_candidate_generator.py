"""Unit and fixture tests for deterministic candidate generation (M3)."""

from __future__ import annotations

from wardiq.compatibility.candidate_generator import (
    compute_stable_outfit_id,
    filter_eligible_items,
    generate_candidates,
    load_candidate_rules,
    normalize_item_record,
)


def test_load_candidate_rules():
    rules = load_candidate_rules()
    assert rules["schema_version"] == "wardiq.m3.candidate-rules.v1"
    assert "top" in rules["category_vocabulary"]
    assert len(rules["outfit_templates"]) >= 1


def test_stable_outfit_id():
    id1 = compute_stable_outfit_id(["item_a", "item_b"], "1.0.0")
    id2 = compute_stable_outfit_id(["item_b", "item_a"], "1.0.0")
    id3 = compute_stable_outfit_id(["item_a", "item_c"], "1.0.0")
    assert id1 == id2
    assert id1 != id3
    assert id1.startswith("cand_")


def test_normalize_item_record():
    raw = {
        "item_id": "test_1",
        "category": {
            "common_category": "top",
            "mapping_status": "direct",
            "source_category_id": 1,
            "source_label": "shirt",
        },
        "split": {"target_split": "train"},
        "provenance": {"source_image_sha256": "abc123hash"},
    }
    item = normalize_item_record(raw)
    assert item.item_id == "test_1"
    assert item.common_category == "top"
    assert item.mapping_status == "direct"
    assert item.target_split == "train"
    assert item.image_sha256 == "abc123hash"


def test_filter_eligible_items():
    rules = load_candidate_rules()
    records = [
        {
            "item_id": "item_valid",
            "common_category": "top",
            "mapping_status": "direct",
            "target_split": "train",
            "image_sha256": "hash_1",
        },
        {
            "item_id": "item_invalid_status",
            "common_category": "top",
            "mapping_status": "unmapped",
            "target_split": "train",
        },
        {
            "item_id": "item_missing_cat",
            "common_category": None,
            "mapping_status": "direct",
            "target_split": "train",
        },
        {
            "item_id": "item_valid",
            "common_category": "bottom",
            "mapping_status": "direct",
            "target_split": "train",
        },
    ]
    eligible, rejections, _ = filter_eligible_items(
        records, rules, target_split="train"
    )
    assert "item_valid" in eligible
    assert "item_invalid_status" not in eligible
    assert "item_missing_cat" not in eligible
    assert len(rejections) >= 2


def test_generate_candidates_synthetic():
    rules = load_candidate_rules()
    records = [
        {
            "item_id": "t1",
            "common_category": "top",
            "mapping_status": "direct",
            "target_split": "train",
            "image_sha256": "h_t1",
        },
        {
            "item_id": "b1",
            "common_category": "bottom",
            "mapping_status": "direct",
            "target_split": "train",
            "image_sha256": "h_b1",
        },
        {
            "item_id": "f1",
            "common_category": "footwear",
            "mapping_status": "direct",
            "target_split": "train",
            "image_sha256": "h_f1",
        },
        {
            "item_id": "s1",
            "common_category": "sneaker",
            "mapping_status": "unmapped",
            "target_split": "train",
        },
    ]
    result = generate_candidates(
        records,
        rules=rules,
        target_split="train",
        seed=42,
        max_candidates=10,
    )
    assert result.input_item_count == 4
    assert result.eligible_item_count == 3
    assert result.candidates_emitted >= 1
    cand = result.valid_candidates[0]
    assert cand.structurally_valid is True
    assert cand.template_id == "separates_core"
    assert len(cand.relevant_pairs) >= 1
