"""Outfit Compatibility Score (OCS): the mean of pairwise compatibility probabilities.

Ziad's model supplies C(i, j), the probability that items i and j are compatible.
This module only aggregates those probabilities; it does not train or calibrate anything.
"""

from __future__ import annotations

import itertools
import json
import math
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "0.2.0"
REQUIRED_VERSIONS = ("model", "cache", "config")

# C(i, j): probability in [0, 1] that two items go together.
ProbFn = Callable[[str, str], float]
RelevantPairs = frozenset[frozenset[str]]


class ItemUnavailable(Exception):
    """Raise from the probability function when an item has no usable features."""


def pair_id(a: str, b: str) -> str:
    """Order-independent id, so (a, b) and (b, a) are the same pair."""
    first, second = sorted((a, b))
    return f"{first}|{second}"


def load_relevant_pairs(path: str | Path) -> RelevantPairs:
    """Read the category pairs that count towards OCS from the config file."""
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    return frozenset(frozenset(pair) for pair in config["relevant_category_pairs"])


def item_from_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Turn a frozen M2 item record into the two fields scoring needs."""
    return {"item_id": record["item_id"], "category": record["category"]["common_category"]}


def _require_versions(versions: Mapping[str, str]) -> None:
    missing = [key for key in REQUIRED_VERSIONS if not versions.get(key)]
    if missing:
        raise ValueError(f"versions missing: {missing}")


def _is_probability(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and 0.0 <= value <= 1.0
    )


def score_outfit(
    outfit_id: str,
    items: Sequence[Mapping[str, Any]],
    prob_fn: ProbFn,
    relevant_pairs: RelevantPairs,
    versions: Mapping[str, str],
) -> dict[str, Any]:
    """Score one outfit. Never drops anything silently: every skip has a reason."""
    _require_versions(versions)
    excluded: list[dict[str, str]] = []
    usable = []
    for item in items:
        if item.get("category") is None:
            excluded.append({"scope": "item", "id": item["item_id"], "reason": "item_unavailable"})
        else:
            usable.append(item)

    pairs: list[dict[str, Any]] = []
    for a, b in itertools.combinations(usable, 2):
        if frozenset((a["category"], b["category"])) not in relevant_pairs:
            continue  # not part of the agreed mean; not an error
        first, second = sorted((a["item_id"], b["item_id"]))  # fixed order => symmetric
        pid = pair_id(first, second)
        try:
            score = prob_fn(first, second)
        except ItemUnavailable:
            excluded.append({"scope": "pair", "id": pid, "reason": "item_unavailable"})
            continue
        if not _is_probability(score):
            excluded.append({"scope": "pair", "id": pid, "reason": "invalid_probability"})
            continue
        pairs.append({"pair_id": pid, "item_a": first, "item_b": second, "score": float(score)})

    pair_exclusions = [e for e in excluded if e["scope"] == "pair"]
    if pairs:
        ocs: float | None = math.fsum(p["score"] for p in pairs) / len(pairs)
        status = "partial" if excluded else "ok"
    else:
        ocs = None
        status = "failed" if pair_exclusions else "no_relevant_pairs"

    return {
        "outfit_id": outfit_id,
        "item_ids": [item["item_id"] for item in items],
        "ocs": ocs,
        "status": status,
        "pairs": pairs,
        "excluded": excluded,
    }


def top_k(outfits: Sequence[Mapping[str, Any]], k: int) -> list[dict[str, Any]]:
    """Highest OCS first; ties go to the smaller outfit_id. Takes already-scored outfits.

    If k is larger than the number of outfits, all of them are returned (no padding, no error).
    """
    if k < 1:
        raise ValueError("k must be at least 1")
    ranked = sorted(outfits, key=lambda o: (-o["ocs"], o["outfit_id"]))
    return [{"rank": rank, **o} for rank, o in enumerate(ranked[:k], start=1)]


def check_candidate(candidate: Mapping[str, Any], cache_ids: set[str]) -> str | None:
    """Return why a candidate is invalid, or None if it can be scored."""
    ids = [item["item_id"] for item in candidate["items"]]
    if len(ids) < 2:
        return "too_few_items"
    if len(set(ids)) < len(ids):
        return "repeated_item"
    if any(i not in cache_ids for i in ids):
        return "item_not_in_cache"
    return None


def recommend(
    candidates: Sequence[Mapping[str, Any]],
    prob_fn: ProbFn,
    relevant_pairs: RelevantPairs,
    versions: Mapping[str, str],
    cache_ids: set[str],
    k: int,
    calibration_evidence: str | None = None,
) -> dict[str, Any]:
    """Candidates -> pair scores -> mean OCS -> top-K outfits (the M3 -> M4 payload).

    Candidates are processed sorted by outfit_id, so input order never changes the result.
    Anything that is not returned is listed in `rejected` with a reason.
    """
    _require_versions(versions)
    scored: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    used_ids: set[str] = set()
    seen_sets: dict[frozenset[str], str] = {}

    for candidate in sorted(candidates, key=lambda c: c["outfit_id"]):
        outfit_id = candidate["outfit_id"]
        item_set = frozenset(item["item_id"] for item in candidate["items"])
        reason = check_candidate(candidate, cache_ids)
        if reason is None and outfit_id in used_ids:
            reason = "duplicate_outfit_id"
        if reason is None and item_set in seen_sets:
            reason = f"duplicate_of:{seen_sets[item_set]}"
        if reason is None:
            result = score_outfit(outfit_id, candidate["items"], prob_fn, relevant_pairs, versions)
            if result["ocs"] is None:
                reason = result["status"]
        if reason is not None:
            rejected.append({"outfit_id": outfit_id, "reason": reason})
            continue
        used_ids.add(outfit_id)
        seen_sets[item_set] = outfit_id
        scored.append(result)

    ranked = top_k(scored, k)
    return {
        "contract_version": CONTRACT_VERSION,
        "versions": dict(versions),
        "calibration": {
            "status": "evidence_attached" if calibration_evidence else "not_provided",
            "evidence": calibration_evidence,
        },
        "requested_k": k,
        "returned_k": len(ranked),
        "top_k": ranked,
        "rejected": rejected,
    }


def validate_output(output: Mapping[str, Any]) -> list[str]:
    """Return a list of problems; an empty list means the payload follows the contract."""
    problems: list[str] = []
    if output.get("contract_version") != CONTRACT_VERSION:
        problems.append("contract_version mismatch")
    for key in REQUIRED_VERSIONS:
        if not output.get("versions", {}).get(key):
            problems.append(f"versions.{key} missing")
    if output.get("calibration", {}).get("status") not in ("not_provided", "evidence_attached"):
        problems.append("calibration.status invalid")

    rows = output.get("top_k", [])
    if output.get("returned_k") != len(rows) or len(rows) > output.get("requested_k", 0):
        problems.append("returned_k / requested_k do not match top_k")
    ids = [row.get("outfit_id") for row in rows]
    if len(set(ids)) != len(ids):
        problems.append("duplicate outfit in top_k")
    if [row.get("rank") for row in rows] != list(range(1, len(rows) + 1)):
        problems.append("ranks are not 1..n")
    if any(not _is_probability(row.get("ocs")) for row in rows):
        problems.append("a top_k row has a missing or out-of-range ocs")
    elif [(-r["ocs"], r["outfit_id"]) for r in rows] != sorted(
        (-r["ocs"], r["outfit_id"]) for r in rows
    ):
        problems.append("top_k is not ordered by ocs, then outfit_id")
    if any(not row.get("pairs") for row in rows):
        problems.append("a top_k row has no pair scores")
    if any(not r.get("outfit_id") or not r.get("reason") for r in output.get("rejected", [])):
        problems.append("a rejected entry has no outfit_id or reason")
    return problems
