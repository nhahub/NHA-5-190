"""Tests for Milestone 4 Wardrobe Gap Analysis."""

from __future__ import annotations

from wardiq.compatibility.candidate_generator import CandidateItem
from wardiq.personalization import (
    analyze_wardrobe_gaps,
    load_gap_analysis_config,
)


def _make_item(
    item_id: str,
    category: str | None,
    *,
    split: str = "train",
) -> CandidateItem:
    return CandidateItem(
        item_id=item_id,
        common_category=category,
        mapping_status="direct",
        source_category_id=f"src_{category}",
        source_label=str(category),
        target_split=split,
        source_dataset="test_wardrobe",
        image_sha256=None,
    )


def test_missing_category_unlocks_combinations_and_ranks_deterministically() -> None:
    """Wardrobe with tops + bottoms but no footwear should rank footwear #1."""
    wardrobe = [
        _make_item("top_1", "top"),
        _make_item("top_2", "top"),
        _make_item("bottom_1", "bottom"),
        _make_item("bottom_2", "bottom"),
    ]

    result = analyze_wardrobe_gaps(wardrobe, wardrobe_ref="wardrobe_no_shoes")

    assert result.baseline_feasible_combinations == 0
    assert "footwear" in result.missing_categories
    assert result.has_meaningful_gap is True
    assert len(result.ranked_gaps) >= 1

    top_gap = result.ranked_gaps[0]
    assert top_gap.rank == 1
    assert top_gap.candidate_category == "footwear"
    assert top_gap.evidence.incremental_useful_combinations == 4
    assert "separates_core" in top_gap.evidence.unlocked_templates
    assert "footwear" in top_gap.explanation


def test_compatibility_evidence_with_embeddings_and_wus_handoff() -> None:
    """Simulated additions with embeddings compute M3 avg_ocs and WUS handoff."""
    wardrobe = [
        _make_item("top_1", "top"),
        _make_item("bottom_1", "bottom"),
        _make_item("shoe_1", "footwear"),
    ]
    candidates = [
        _make_item("outer_good", "outerwear"),
        _make_item("bag_low_compat", "bag"),
    ]
    embeddings = {
        "top_1": [1.0, 0.0, 0.0],
        "bottom_1": [0.95, 0.05, 0.0],
        "shoe_1": [0.9, 0.1, 0.0],
        "outer_good": [0.92, 0.08, 0.0],
        "bag_low_compat": [-1.0, 0.0, 0.0],
    }

    result = analyze_wardrobe_gaps(
        wardrobe,
        candidate_pool=candidates,
        item_embeddings=embeddings,
        wardrobe_ref="wardrobe_with_embeddings",
    )

    assert result.has_meaningful_gap is True
    assert len(result.ranked_gaps) == 1
    winner = result.ranked_gaps[0]
    assert winner.candidate_item_id == "outer_good"
    assert winner.evidence.scoring_mode == "m3_compatibility_ocs"
    assert winner.evidence.avg_ocs is not None
    assert winner.evidence.avg_ocs >= 0.5

    # Low-compatibility bag should be rejected for 0 useful combinations
    rejected_ids = {r.candidate_item_id: r.reasons for r in result.rejected_candidates}
    assert "bag_low_compat" in rejected_ids
    assert "zero_incremental_useful_combinations" in rejected_ids["bag_low_compat"]

    # Verify Hana's WUS handoff does not fabricate missing signals
    wus = winner.to_wus_handoff()
    assert wus["schema_version"] == "wardiq.wardrobe-utility.v1"
    assert wus["gain"] == float(winner.evidence.incremental_useful_combinations)
    assert wus["avg_ocs"] == winner.evidence.avg_ocs
    assert wus["preference"] is None
    assert wus["context"] is None
    assert wus["wus"] is None

    # Verify Asmaa/Hayat product-matching record
    pm_record = winner.to_product_matching_record()
    assert pm_record["schema_version"] == "wardiq.m4.gap-candidate-product-record.v1"
    assert pm_record["target_category"] == "outerwear"
    assert pm_record["rank"] == 1


def test_redundancy_handling_exact_embedding_attribute_and_saturation() -> None:
    """Redundant candidates are separated and never ranked as gaps."""
    wardrobe = [
        _make_item("top_1", "top"),
        _make_item("top_2", "top"),
        _make_item("top_3", "top"),
        _make_item("bottom_1", "bottom"),
        _make_item("shoe_1", "footwear"),
    ]
    candidates = [
        _make_item("top_1", "top"),  # exact item_id match
        _make_item("top_4", "top"),  # category saturated (3 >= 3)
        _make_item("bottom_dup", "bottom"),  # high embedding + attribute overlap
    ]
    embeddings = {
        "top_1": [1.0, 0.0],
        "top_2": [0.8, 0.2],
        "top_3": [0.7, 0.3],
        "bottom_1": [0.0, 1.0],
        "shoe_1": [0.5, 0.5],
        "top_4": [0.6, 0.4],
        "bottom_dup": [0.01, 0.99],
    }
    attributes = {
        "bottom_1": ["denim", "blue", "straight"],
        "bottom_dup": ["denim", "blue", "straight"],
    }

    result = analyze_wardrobe_gaps(
        wardrobe,
        candidate_pool=candidates,
        item_embeddings=embeddings,
        item_attributes=attributes,
        wardrobe_ref="wardrobe_redundancy",
    )

    assert result.has_meaningful_gap is False
    assert len(result.ranked_gaps) == 0

    red_by_id = {r.candidate_item_id: r.redundancy.reasons for r in result.redundant_candidates}
    assert "exact_item_id_match" in red_by_id["top_1"]
    assert "category_saturated" in red_by_id["top_4"]
    assert "high_embedding_similarity" in red_by_id["bottom_dup"]
    assert "high_attribute_overlap" in red_by_id["bottom_dup"]


def test_invalid_category_is_rejected() -> None:
    """Candidates outside M3 category_vocabulary are explicitly rejected."""
    wardrobe = [
        _make_item("top_1", "top"),
        _make_item("bottom_1", "bottom"),
        _make_item("shoe_1", "footwear"),
    ]
    candidates = [
        _make_item("bad_1", "spacesuit"),
        _make_item("bad_2", None),
    ]

    result = analyze_wardrobe_gaps(wardrobe, candidate_pool=candidates)

    assert result.has_meaningful_gap is False
    rejected_map = {r.candidate_item_id: r.reasons for r in result.rejected_candidates}
    assert rejected_map["bad_1"] == ("invalid_category",)
    assert rejected_map["bad_2"] == ("invalid_category",)


def test_complete_wardrobe_has_no_meaningful_gap() -> None:
    """A wardrobe covering all template-active categories has no missing-category gaps."""
    wardrobe = [
        _make_item("top_1", "top"),
        _make_item("bottom_1", "bottom"),
        _make_item("one_piece_1", "one_piece"),
        _make_item("outer_1", "outerwear"),
        _make_item("shoe_1", "footwear"),
        _make_item("bag_1", "bag"),
    ]

    result = analyze_wardrobe_gaps(wardrobe, wardrobe_ref="wardrobe_complete")

    assert result.missing_categories == ()
    assert result.has_meaningful_gap is False
    assert result.ranked_gaps == ()
    assert result.baseline_feasible_combinations > 0


def test_reproducibility_and_serialization() -> None:
    """Repeated runs on the same wardrobe produce identical serialized outputs."""
    wardrobe = [
        _make_item("top_1", "top"),
        _make_item("bottom_1", "bottom"),
        _make_item("shoe_1", "footwear"),
    ]

    res_a = analyze_wardrobe_gaps(wardrobe, wardrobe_ref="wardrobe_repro", seed=42)
    res_b = analyze_wardrobe_gaps(wardrobe, wardrobe_ref="wardrobe_repro", seed=42)

    assert res_a.to_dict() == res_b.to_dict()
    assert load_gap_analysis_config()["config_version"] == res_a.config_version
