"""Small, transparent M3 rule baseline.

The baseline uses embedding, colour and category signals only. Attributes are
intentionally not used: training attribute values are masked and must never be
treated as negative evidence.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Final, Sequence

WEIGHTS: Final[dict[str, float]] = {
    "embedding": 0.25,
    "colour": 0.35,
    "category": 0.40,
}
MIN_WEIGHT_COVERAGE: Final[float] = 0.5

CATEGORY_RULES: Final[dict[str, float]] = {
    "complementary": 1.0,
    "accessory": 0.7,
    "same_or_conflicting": 0.3,
}

ACCESSORY_CATEGORIES: Final[frozenset[str]] = frozenset(
    {"accessory_other", "bag", "eyewear", "headwear", "jewellery", "scarf"}
)
KNOWN_CATEGORIES: Final[frozenset[str]] = frozenset(
    {
        "top",
        "bottom",
        "one_piece",
        "outerwear",
        "footwear",
        *ACCESSORY_CATEGORIES,
    }
)
COMPLEMENTARY_PAIRS: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        ("bottom", "top"),
        ("footwear", "top"),
        ("bottom", "footwear"),
        ("footwear", "one_piece"),
        ("outerwear", "top"),
        ("bottom", "outerwear"),
        ("one_piece", "outerwear"),
        ("footwear", "outerwear"),
    }
)


@dataclass(frozen=True)
class PairScore:
    """A heuristic score and the evidence used to calculate it."""

    score: float | None
    status: str
    signals_used: tuple[str, ...]
    weight_coverage: float


def _category_score(feature_names: Sequence[str], features: dict[str, float]) -> float:
    active_pairs: list[tuple[str, str]] = []
    for name in feature_names:
        if not name.startswith("category:") or name == "category:both_mapped":
            continue
        value = features[name]
        if value not in (0.0, 1.0):
            raise ValueError("Category pair features must be 0 or 1")
        if value == 1.0:
            pair_parts = name.removeprefix("category:").split("|")
            if len(pair_parts) != 2:
                raise ValueError(f"Invalid category pair feature: {name}")
            active_pairs.append((pair_parts[0], pair_parts[1]))

    if len(active_pairs) != 1:
        raise ValueError("Expected exactly one active category pair feature")

    left, right = active_pairs[0]
    if left not in KNOWN_CATEGORIES or right not in KNOWN_CATEGORIES:
        raise ValueError(f"Unknown mapped category pair: {left}|{right}")
    pair = (left, right) if left <= right else (right, left)

    if left in ACCESSORY_CATEGORIES or right in ACCESSORY_CATEGORIES:
        return CATEGORY_RULES["accessory"]
    if pair in COMPLEMENTARY_PAIRS:
        return CATEGORY_RULES["complementary"]
    if left == right or pair in {
        ("one_piece", "top"),
        ("bottom", "one_piece"),
    }:
        return CATEGORY_RULES["same_or_conflicting"]
    raise ValueError(f"No category rule for mapped pair: {left}|{right}")


def score_pair_features(
    *, feature_names: Sequence[str], feature_values: Sequence[float]
) -> PairScore:
    """Score one PairFeatureBuilder row using named signals, never attributes."""
    if len(feature_names) != len(feature_values):
        raise ValueError("Feature names and values must have equal lengths")
    if len(set(feature_names)) != len(feature_names):
        raise ValueError("Feature names must be unique")
    if any(not isfinite(value) for value in feature_values):
        raise ValueError("Feature values must be finite")

    features = dict(zip(feature_names, feature_values))
    required = {
        "clip:cosine",
        "lab:expected_delta_e76_over_100",
        "lab:both_available",
        "category:both_mapped",
    }
    if not required.issubset(features):
        raise ValueError("Required compatibility features are missing")

    cosine = features["clip:cosine"]
    if not -1.0 <= cosine <= 1.0:
        raise ValueError("clip:cosine must be in [-1, 1]")
    color_available = features["lab:both_available"]
    category_available = features["category:both_mapped"]
    if color_available not in (0.0, 1.0):
        raise ValueError("lab:both_available must be 0 or 1")
    if category_available not in (0.0, 1.0):
        raise ValueError("category:both_mapped must be 0 or 1")

    signals: list[tuple[str, float, float]] = [
        ("embedding", min(max(cosine, 0.0), 1.0), WEIGHTS["embedding"])
    ]

    if color_available == 1.0:
        distance = features["lab:expected_delta_e76_over_100"]
        if distance < 0.0:
            raise ValueError("LAB distance must be non-negative")
        color_score = 1.0 - min(distance, 1.0)
        signals.append(("colour", color_score, WEIGHTS["colour"]))

    if category_available == 1.0:
        category_score = _category_score(feature_names, features)
        signals.append(("category", category_score, WEIGHTS["category"]))

    coverage = sum(weight for _, _, weight in signals)
    used = tuple(name for name, _, _ in signals)
    if coverage < MIN_WEIGHT_COVERAGE:
        return PairScore(None, "insufficient_evidence", used, coverage)

    weighted_total = sum(value * weight for _, value, weight in signals)
    return PairScore(weighted_total / coverage, "scored", used, coverage)


def score_rows(feature_names: Sequence[str], matrix: Sequence[Sequence[float]]) -> list[PairScore]:
    """Score feature rows in their supplied order."""
    results: list[PairScore] = []
    for row in matrix:
        results.append(score_pair_features(feature_names=feature_names, feature_values=row))
    return results


def mean_ocs(pair_scores: Sequence[PairScore]) -> float | None:
    """Return the pair-score mean, or None if any pair lacks a score."""
    if not pair_scores or any(pair.score is None for pair in pair_scores):
        return None
    return sum(pair.score for pair in pair_scores if pair.score is not None) / len(pair_scores)
