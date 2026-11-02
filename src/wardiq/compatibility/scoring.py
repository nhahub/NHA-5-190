"""Pairwise compatibility scoring and OCS aggregation for Milestone 3."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from wardiq.contracts import PairwiseScore


@dataclass(frozen=True)
class OutfitScoringResult:
    """Result of scoring pairwise interactions and OCS."""

    outfit_id: str
    item_ids: tuple[str, ...]
    pairwise_scores: tuple[PairwiseScore, ...]
    ocs: float | None
    structurally_valid: bool
    rejection_reasons: tuple[str, ...]


def compute_pairwise_cosine_similarity(
    left_vector: Sequence[float], right_vector: Sequence[float]
) -> float:
    """Compute normalized cosine similarity between two embeddings."""
    if not left_vector or not right_vector or len(left_vector) != len(right_vector):
        return 0.0
    dot_prod = sum(float(lv) * float(rv) for lv, rv in zip(left_vector, right_vector))
    norm_l = sum(float(lv) ** 2 for lv in left_vector) ** 0.5
    norm_r = sum(float(rv) ** 2 for rv in right_vector) ** 0.5
    if norm_l == 0.0 or norm_r == 0.0:
        return 0.0
    val: float = dot_prod / (norm_l * norm_r)
    return max(-1.0, min(1.0, val))


def score_outfit_candidate(
    item_ids: Sequence[str],
    item_embeddings: Mapping[str, Sequence[float]],
    relevant_pairs: Sequence[tuple[str, str]] | None = None,
) -> OutfitScoringResult:
    """Score all relevant pairs in an outfit and compute mean OCS."""
    clean_ids = tuple(str(i).strip() for i in item_ids)
    if len(clean_ids) < 2:
        return OutfitScoringResult(
            outfit_id="unknown",
            item_ids=clean_ids,
            pairwise_scores=(),
            ocs=None,
            structurally_valid=False,
            rejection_reasons=("too_few_items_for_scoring",),
        )

    pairs_to_score = list(relevant_pairs) if relevant_pairs is not None else []
    if not pairs_to_score:
        sorted_unique = sorted(set(clean_ids))
        for i in range(len(sorted_unique)):
            for j in range(i + 1, len(sorted_unique)):
                pairs_to_score.append((sorted_unique[i], sorted_unique[j]))

    pairwise_scores: list[PairwiseScore] = []
    probabilities: list[float] = []

    for left_id, right_id in pairs_to_score:
        l_vec = item_embeddings.get(left_id)
        r_vec = item_embeddings.get(right_id)
        if l_vec is not None and r_vec is not None:
            prob = float(compute_pairwise_cosine_similarity(l_vec, r_vec))
        else:
            prob = 0.5

        pairwise_scores.append(
            PairwiseScore(
                left_item_id=left_id,
                right_item_id=right_id,
                probability=round(prob, 4),
            )
        )
        probabilities.append(prob)

    ocs = round(sum(probabilities) / len(probabilities), 4) if probabilities else None

    return OutfitScoringResult(
        outfit_id="",
        item_ids=clean_ids,
        pairwise_scores=tuple(pairwise_scores),
        ocs=ocs,
        structurally_valid=True,
        rejection_reasons=(),
    )
