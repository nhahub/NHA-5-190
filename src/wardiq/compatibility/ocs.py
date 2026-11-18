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

CONTRACT_VERSION = "0.1.0"
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
    missing = [key for key in REQUIRED_VERSIONS if not versions.get(key)]
    if missing:
        raise ValueError(f"versions missing: {missing}")

    excluded: list[dict[str, str]] = []
    usable = []
    for item in items:
        if item.get("category") is None:
            excluded.append(
                {"scope": "item", "id": item["item_id"], "reason": "item_unavailable"}
            )
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
    """Highest OCS first. Ties go to the smaller outfit_id. Outfits without an OCS are skipped."""
    if k < 1:
        raise ValueError("k must be at least 1")
    scored = [o for o in outfits if o["ocs"] is not None]
    scored.sort(key=lambda o: (-o["ocs"], o["outfit_id"]))
    return [
        {"rank": rank, "outfit_id": o["outfit_id"], "ocs": o["ocs"]}
        for rank, o in enumerate(scored[:k], start=1)
    ]


def build_m3_output(
    outfits: Sequence[Mapping[str, Any]],
    k: int,
    versions: Mapping[str, str],
    calibration_evidence: str | None = None,
) -> dict[str, Any]:
    """The M3 -> M4 payload. Calibration is only claimed when evidence is attached."""
    return {
        "contract_version": CONTRACT_VERSION,
        "versions": dict(versions),
        "calibration": {
            "status": "evidence_attached" if calibration_evidence else "not_provided",
            "evidence": calibration_evidence,
        },
        "outfits": [dict(o) for o in outfits],
        "top_k": top_k(outfits, k),
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

    ids = set()
    for outfit in output.get("outfits", []):
        ids.add(outfit.get("outfit_id"))
        ocs = outfit.get("ocs")
        if ocs is not None and not _is_probability(ocs):
            problems.append(f"{outfit.get('outfit_id')}: ocs out of range")
        if outfit.get("status") not in ("ok", "partial", "no_relevant_pairs", "failed"):
            problems.append(f"{outfit.get('outfit_id')}: bad status")
        if (ocs is None) != (outfit.get("status") in ("no_relevant_pairs", "failed")):
            problems.append(f"{outfit.get('outfit_id')}: ocs and status disagree")

    ranked = output.get("top_k", [])
    if any(row["outfit_id"] not in ids for row in ranked):
        problems.append("top_k refers to an unknown outfit")
    if [row["ocs"] for row in ranked] != sorted((row["ocs"] for row in ranked), reverse=True):
        problems.append("top_k is not sorted by ocs")
    return problems
