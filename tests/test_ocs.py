import math
from pathlib import Path

import pytest

from wardiq.compatibility.ocs import (
    ItemUnavailable,
    build_m3_output,
    item_from_record,
    load_relevant_pairs,
    pair_id,
    score_outfit,
    top_k,
    validate_output,
)

VERSIONS = {"model": "stub-0", "cache": "stub-0", "config": "0.1.0"}
PAIRS = frozenset({frozenset(("top", "bottom")), frozenset(("top", "footwear"))})
ITEMS = [
    {"item_id": "t1", "category": "top"},
    {"item_id": "b1", "category": "bottom"},
    {"item_id": "f1", "category": "footwear"},
]


def fake(scores):
    def prob(a, b):
        value = scores[pair_id(a, b)]
        if value == "missing":
            raise ItemUnavailable
        return value

    return prob


def score(items=ITEMS, scores=None, pairs=PAIRS):
    return score_outfit("o1", items, fake(scores or {}), pairs, VERSIONS)


def test_ocs_is_exact_mean_of_relevant_pairs():
    # bottom-footwear is not in PAIRS, so its score must not enter the mean
    result = score(scores={"b1|t1": 0.2, "f1|t1": 0.8, "b1|f1": 0.0})
    assert result["ocs"] == 0.5
    assert result["status"] == "ok"
    assert [p["pair_id"] for p in result["pairs"]] == ["b1|t1", "f1|t1"]


def test_pair_order_does_not_change_the_score():
    scores = {"b1|t1": 0.3, "f1|t1": 0.9}
    forward = score(scores=scores)
    backward = score(items=list(reversed(ITEMS)), scores=scores)
    assert forward["ocs"] == backward["ocs"]


def test_no_relevant_pair():
    result = score(items=[ITEMS[1], ITEMS[2]], scores={})  # bottom + footwear only
    assert result["ocs"] is None
    assert result["status"] == "no_relevant_pairs"


def test_unavailable_item_is_listed_not_dropped():
    items = ITEMS + [{"item_id": "x1", "category": None}]
    result = score(items=items, scores={"b1|t1": 0.2, "f1|t1": 0.8})
    assert result["ocs"] == 0.5
    assert result["status"] == "partial"
    assert result["excluded"] == [{"scope": "item", "id": "x1", "reason": "item_unavailable"}]
    assert "x1" in result["item_ids"]


def test_pair_whose_features_are_missing_is_excluded():
    result = score(scores={"b1|t1": 0.4, "f1|t1": "missing"})
    assert result["ocs"] == 0.4
    assert result["excluded"][0]["reason"] == "item_unavailable"


@pytest.mark.parametrize("bad", [1.2, -0.1, math.nan, math.inf, None, "0.5", True])
def test_invalid_probability_is_excluded(bad):
    result = score(scores={"b1|t1": 0.6, "f1|t1": bad})
    assert result["ocs"] == 0.6
    assert result["excluded"] == [{"scope": "pair", "id": "f1|t1", "reason": "invalid_probability"}]


def test_all_pairs_invalid_gives_failed_not_zero():
    result = score(scores={"b1|t1": math.nan, "f1|t1": 2.0})
    assert result["ocs"] is None
    assert result["status"] == "failed"


def test_versions_are_required():
    with pytest.raises(ValueError):
        score_outfit("o1", ITEMS, fake({}), PAIRS, {"model": "stub-0"})


def test_top_k_orders_by_ocs_then_outfit_id():
    outfits = [
        {"outfit_id": "b", "ocs": 0.7},
        {"outfit_id": "a", "ocs": 0.7},
        {"outfit_id": "c", "ocs": 0.9},
        {"outfit_id": "d", "ocs": None},
    ]
    assert [r["outfit_id"] for r in top_k(outfits, 3)] == ["c", "a", "b"]
    with pytest.raises(ValueError):
        top_k(outfits, 0)


def test_output_contract_passes_and_bad_output_fails():
    outfit = score(scores={"b1|t1": 0.2, "f1|t1": 0.8})
    output = build_m3_output([outfit], k=1, versions=VERSIONS)
    assert validate_output(output) == []
    assert output["calibration"]["status"] == "not_provided"

    output["outfits"][0]["ocs"] = 1.5
    output["versions"]["model"] = ""
    problems = validate_output(output)
    assert "o1: ocs out of range" in problems
    assert "versions.model missing" in problems


def test_item_from_m2_record_and_config_load():
    record = {"item_id": "t1", "category": {"common_category": "top"}}
    assert item_from_record(record) == {"item_id": "t1", "category": "top"}
    config = Path(__file__).parents[1] / "configs" / "m3" / "ocs.json"
    assert frozenset(("top", "bottom")) in load_relevant_pairs(config)
