"""Candidate generation, compatibility scoring, OCS, and ranking."""

from wardiq.compatibility.candidate_generator import (
    DEFAULT_RULES_PATH,
    CandidateGenerationResult,
    CandidateItem,
    CandidateOutfitRecord,
    ItemRejection,
    compute_stable_outfit_id,
    evaluate_candidate_combination,
    filter_eligible_items,
    generate_candidates,
    load_candidate_rules,
    normalize_item_record,
)
from wardiq.compatibility.pair_features import (
    VERSION,
    PairFeatureBuilder,
)

__all__ = [
    "VERSION",
    "DEFAULT_RULES_PATH",
    "CandidateGenerationResult",
    "CandidateItem",
    "CandidateOutfitRecord",
    "ItemRejection",
    "PairFeatureBuilder",
    "compute_stable_outfit_id",
    "evaluate_candidate_combination",
    "filter_eligible_items",
    "generate_candidates",
    "load_candidate_rules",
    "normalize_item_record",
]
