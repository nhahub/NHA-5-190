import math
from pathlib import Path

import pytest

from wardiq.compatibility.ocs import (
    ItemUnavailable,
    item_from_record,
    load_relevant_pairs,
    pair_id,
    recommend,
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


def outfit(outfit_id, ids, cats=("top", "bottom", "footwear")):
    return {
        "outfit_id": outfit_id,
        "items": [{"item_id": i, "category": c} for i, c in zip(ids, cats)],
    }


CACHE = {"t1", "b1", "f1", "t2", "b2", "f2"}
SCORES = {
    "b1|t1": 0.8,
    "f1|t1": 0.6,
    "b1|f1": 0.7,  # outfit a -> 0.7
    "b2|t2": 0.4,
    "f2|t2": 0.5,
    "b2|f2": 0.6,  # outfit b -> 0.5
}
ALL_PAIRS = frozenset(
    frozenset(p) for p in [("top", "bottom"), ("top", "footwear"), ("bottom", "footwear")]
)


def run(candidates, k=5, scores=SCORES):
    return recommend(candidates, fake(scores), ALL_PAIRS, VERSIONS, CACHE, k)


A = outfit("a", ["t1", "b1", "f1"])
B = outfit("b", ["t2", "b2", "f2"])


def test_ranking_and_pair_scores_are_kept():
    out = run([B, A])
    assert [r["outfit_id"] for r in out["top_k"]] == ["a", "b"]
    assert [r["rank"] for r in out["top_k"]] == [1, 2]
    assert len(out["top_k"][0]["pairs"]) == 3
    assert out["versions"] == VERSIONS
    assert validate_output(out) == []


def test_ties_go_to_smaller_outfit_id():
    rows = [
        {"outfit_id": "b", "ocs": 0.7},
        {"outfit_id": "a", "ocs": 0.7},
        {"outfit_id": "c", "ocs": 0.9},
    ]
    assert [r["outfit_id"] for r in top_k(rows, 3)] == ["c", "a", "b"]


def test_k_larger_than_available_returns_all_without_error():
    out = run([A, B], k=10)
    assert (out["requested_k"], out["returned_k"]) == (10, 2)
    assert validate_output(out) == []


def test_k_smaller_cuts_the_list_and_k_must_be_positive():
    assert run([A, B], k=1)["returned_k"] == 1
    with pytest.raises(ValueError):
        run([A, B], k=0)


def test_empty_input():
    out = run([])
    assert out["top_k"] == [] and out["rejected"] == [] and out["returned_k"] == 0
    assert validate_output(out) == []


def test_duplicate_candidates_are_rejected_once_each():
    same_items_other_order = outfit("a2", ["f1", "t1", "b1"], ("footwear", "top", "bottom"))
    same_id_again = outfit("a", ["t2", "b2", "f2"])
    out = run([A, same_items_other_order, same_id_again])
    assert [r["outfit_id"] for r in out["top_k"]] == ["a"]
    reasons = {r["outfit_id"]: r["reason"] for r in out["rejected"]}
    assert reasons == {"a": "duplicate_outfit_id", "a2": "duplicate_of:a"}


def test_invalid_and_unscorable_candidates_get_reasons():
    out = run(
        [
            A,
            outfit("one", ["t1"], ("top",)),
            outfit("rep", ["t1", "t1"], ("top", "top")),
            outfit("nocache", ["t1", "zz"], ("top", "bottom")),
            outfit("norel", ["t1", "t2"], ("top", "top")),
            outfit("nan", ["t2", "b2"], ("top", "bottom")),
        ],
        scores={**SCORES, "b2|t2": math.nan},
    )
    reasons = {r["outfit_id"]: r["reason"] for r in out["rejected"]}
    assert reasons == {
        "one": "too_few_items",
        "rep": "repeated_item",
        "nocache": "item_not_in_cache",
        "norel": "no_relevant_pairs",
        "nan": "failed",
    }
    assert [r["outfit_id"] for r in out["top_k"]] == ["a"]


def test_same_result_on_repeat_and_for_any_input_order():
    first = run([A, B])
    assert run([A, B]) == first
    assert run([B, A]) == first


def test_bad_output_fails_validation_with_reasons():
    out = run([A, B])
    out["top_k"][0]["ocs"] = 0.1  # now lower than rank 2
    out["versions"]["model"] = ""
    problems = validate_output(out)
    assert "top_k is not ordered by ocs, then outfit_id" in problems
    assert "versions.model missing" in problems


def test_calibration_is_only_claimed_with_evidence():
    assert run([A])["calibration"]["status"] == "not_provided"
    out = recommend([A], fake(SCORES), ALL_PAIRS, VERSIONS, CACHE, 1, "reports/calibration.md")
    assert out["calibration"]["status"] == "evidence_attached"


def test_item_from_m2_record_and_config_load():
    record = {"item_id": "t1", "category": {"common_category": "top"}}
    assert item_from_record(record) == {"item_id": "t1", "category": "top"}
    config = Path(__file__).parents[1] / "configs" / "m3" / "ocs.json"
    assert frozenset(("top", "bottom")) in load_relevant_pairs(config)
