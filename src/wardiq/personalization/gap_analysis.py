"""Milestone 4: Wardrobe Gap Analysis via simulated candidate additions.

Identifies missing or underrepresented clothing categories/items, simulates
adding each candidate to the user's baseline wardrobe using M3 candidate
generation and compatibility scoring, filters redundant or invalid-category
candidates, and returns deterministically ranked, explainable gap records
ready for Hana's WUS calculation and Asmaa/Hayat's product-matching handoff.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from wardiq.compatibility.candidate_generator import (
    CandidateItem,
    CandidateOutfitRecord,
    generate_candidates,
    load_candidate_rules,
    normalize_item_record,
)
from wardiq.compatibility.scoring import (
    OutfitScoringResult,
    compute_pairwise_cosine_similarity,
    score_outfit_candidate,
)
from wardiq.contracts import WardrobeUtility

DEFAULT_GAP_CONFIG_PATH = (
    Path(__file__).resolve().parents[3] / "configs" / "m4" / "gap_analysis_v1.json"
)


def load_gap_analysis_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load the versioned M4 wardrobe gap analysis configuration."""
    config_path = Path(path) if path is not None else DEFAULT_GAP_CONFIG_PATH
    with config_path.open("r", encoding="utf-8") as handle:
        data: dict[str, Any] = json.load(handle)
        return data


@dataclass(frozen=True, slots=True)
class CompatibilityEvidence:
    """Supporting M3 compatibility and combination evidence for a gap candidate."""

    unlocked_outfit_ids: tuple[str, ...]
    unlocked_templates: tuple[str, ...]
    incremental_feasible_combinations: int
    incremental_useful_combinations: int
    avg_ocs: float | None
    min_ocs: float | None
    max_ocs: float | None
    scoring_mode: str


@dataclass(frozen=True, slots=True)
class RedundancyAssessment:
    """Redundancy check result against the baseline wardrobe."""

    is_redundant: bool
    redundancy_score: float
    existing_category_count: int
    max_embedding_similarity: float | None
    max_attribute_overlap: float | None
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RejectedGapCandidate:
    """Candidate rejected before or during gap simulation."""

    candidate_item_id: str
    candidate_category: str | None
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GapCandidateRecord:
    """Ranked, explainable wardrobe gap candidate."""

    rank: int | None
    candidate_item_id: str
    candidate_category: str
    is_synthetic_candidate: bool
    gap_score: float
    normalized_gain: float
    evidence: CompatibilityEvidence
    redundancy: RedundancyAssessment
    explanation: str
    wardrobe_ref: str
    config_ref: str

    def to_wus_handoff(self) -> WardrobeUtility:
        """Convert to contracts.WardrobeUtility for Hana's WUS calculation.

        Missing upstream signals (preference, context, wus) are explicitly left
        as None and never fabricated.
        """
        return WardrobeUtility(
            schema_version="wardiq.wardrobe-utility.v1",
            wardrobe_ref=self.wardrobe_ref,
            candidate_item_id=self.candidate_item_id,
            gain=float(self.evidence.incremental_useful_combinations),
            avg_ocs=self.evidence.avg_ocs,
            preference=None,
            context=None,
            redundancy=self.redundancy.redundancy_score,
            wus=None,
            config_ref=self.config_ref,
        )

    def to_product_matching_record(self) -> dict[str, Any]:
        """Convert to a product-matching-ready record for Asmaa/Hayat."""
        return {
            "schema_version": "wardiq.m4.gap-candidate-product-record.v1",
            "wardrobe_ref": self.wardrobe_ref,
            "config_ref": self.config_ref,
            "rank": self.rank,
            "candidate_item_id": self.candidate_item_id,
            "target_category": self.candidate_category,
            "is_synthetic_candidate": self.is_synthetic_candidate,
            "gap_score": self.gap_score,
            "incremental_useful_combinations": self.evidence.incremental_useful_combinations,
            "avg_ocs": self.evidence.avg_ocs,
            "unlocked_templates": list(self.evidence.unlocked_templates),
            "redundancy_score": self.redundancy.redundancy_score,
            "explanation": self.explanation,
        }


@dataclass(frozen=True, slots=True)
class WardrobeGapAnalysisResult:
    """Complete structured output of Wardrobe Gap Analysis."""

    schema_version: str
    config_version: str
    config_ref: str
    wardrobe_ref: str
    baseline_item_count: int
    baseline_feasible_combinations: int
    baseline_useful_combinations: int
    missing_categories: tuple[str, ...]
    has_meaningful_gap: bool
    ranked_gaps: tuple[GapCandidateRecord, ...]
    redundant_candidates: tuple[GapCandidateRecord, ...]
    rejected_candidates: tuple[RejectedGapCandidate, ...]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full result to a JSON-compatible dictionary."""
        return {
            "schema_version": self.schema_version,
            "config_version": self.config_version,
            "config_ref": self.config_ref,
            "wardrobe_ref": self.wardrobe_ref,
            "baseline_item_count": self.baseline_item_count,
            "baseline_feasible_combinations": self.baseline_feasible_combinations,
            "baseline_useful_combinations": self.baseline_useful_combinations,
            "missing_categories": list(self.missing_categories),
            "has_meaningful_gap": self.has_meaningful_gap,
            "ranked_gaps": [asdict(item) for item in self.ranked_gaps],
            "redundant_candidates": [asdict(item) for item in self.redundant_candidates],
            "rejected_candidates": [asdict(item) for item in self.rejected_candidates],
            "wus_handoff": [item.to_wus_handoff() for item in self.ranked_gaps],
            "product_matching_records": [
                item.to_product_matching_record() for item in self.ranked_gaps
            ],
        }


def _jaccard_overlap(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def _assess_redundancy(
    candidate: CandidateItem,
    wardrobe_items: Sequence[CandidateItem],
    item_embeddings: Mapping[str, Sequence[float]] | None,
    item_attributes: Mapping[str, Sequence[str] | set[str]] | None,
    redundancy_policy: Mapping[str, Any],
) -> RedundancyAssessment:
    """Check whether a candidate is redundant with existing wardrobe items."""
    reasons: list[str] = []
    flag_exact = bool(redundancy_policy.get("flag_exact_item_id_match", True))
    emb_threshold = float(redundancy_policy.get("embedding_similarity_threshold", 0.85))
    attr_threshold = float(redundancy_policy.get("attribute_overlap_threshold", 0.8))
    max_saturation = int(redundancy_policy.get("max_category_saturation", 3))

    existing_ids = {item.item_id for item in wardrobe_items}
    same_cat_items = [
        item for item in wardrobe_items if item.common_category == candidate.common_category
    ]
    existing_cat_count = len(same_cat_items)

    if flag_exact and candidate.item_id in existing_ids:
        reasons.append("exact_item_id_match")
        return RedundancyAssessment(
            is_redundant=True,
            redundancy_score=1.0,
            existing_category_count=existing_cat_count,
            max_embedding_similarity=1.0,
            max_attribute_overlap=1.0,
            reasons=tuple(reasons),
        )

    max_emb_sim: float | None = None
    if item_embeddings and candidate.item_id in item_embeddings and same_cat_items:
        cand_emb = item_embeddings[candidate.item_id]
        sims = [
            compute_pairwise_cosine_similarity(cand_emb, item_embeddings[item.item_id])
            for item in same_cat_items
            if item.item_id in item_embeddings
        ]
        if sims:
            max_emb_sim = round(max(sims), 6)
            if max_emb_sim >= emb_threshold:
                reasons.append("high_embedding_similarity")

    max_attr_ov: float | None = None
    if item_attributes and candidate.item_id in item_attributes and same_cat_items:
        cand_attrs = set(item_attributes[candidate.item_id])
        overlaps = [
            _jaccard_overlap(cand_attrs, set(item_attributes[item.item_id]))
            for item in same_cat_items
            if item.item_id in item_attributes
        ]
        if overlaps:
            max_attr_ov = round(max(overlaps), 6)
            if max_attr_ov >= attr_threshold:
                reasons.append("high_attribute_overlap")

    if existing_cat_count >= max_saturation:
        reasons.append("category_saturated")

    saturation_ratio = min(1.0, existing_cat_count / max_saturation) if max_saturation > 0 else 0.0
    signals = [saturation_ratio]
    if max_emb_sim is not None:
        signals.append(max(0.0, min(1.0, max_emb_sim)))
    if max_attr_ov is not None:
        signals.append(max(0.0, min(1.0, max_attr_ov)))

    redundancy_score = round(max(signals), 6)
    return RedundancyAssessment(
        is_redundant=bool(reasons),
        redundancy_score=redundancy_score,
        existing_category_count=existing_cat_count,
        max_embedding_similarity=max_emb_sim,
        max_attribute_overlap=max_attr_ov,
        reasons=tuple(reasons),
    )


def _score_outfits(
    outfits: Sequence[CandidateOutfitRecord],
    item_embeddings: Mapping[str, Sequence[float]] | None,
) -> tuple[dict[str, OutfitScoringResult | None], str]:
    """Score feasible outfits with M3 compatibility scorer when embeddings exist."""
    if not item_embeddings:
        return {outfit.outfit_id: None for outfit in outfits}, "structural_only"

    scored: dict[str, OutfitScoringResult | None] = {}
    any_scored = False
    for outfit in outfits:
        if all(item_id in item_embeddings for item_id in outfit.item_ids):
            scored[outfit.outfit_id] = score_outfit_candidate(
                item_ids=outfit.item_ids,
                item_embeddings=item_embeddings,
                relevant_pairs=outfit.relevant_pairs,
            )
            any_scored = True
        else:
            scored[outfit.outfit_id] = None
    return scored, ("m3_compatibility_ocs" if any_scored else "structural_only")


def _build_explanation(
    category: str,
    evidence: CompatibilityEvidence,
    redundancy: RedundancyAssessment,
) -> str:
    """Build a concise, auditable explanation for a gap candidate."""
    if redundancy.is_redundant:
        reason_text = ", ".join(redundancy.reasons)
        return (
            f"Candidate '{category}' flagged as redundant ({reason_text}); "
            f"wardrobe already contains {redundancy.existing_category_count} "
            "item(s) in this category."
        )
    templates = ", ".join(evidence.unlocked_templates) if evidence.unlocked_templates else "none"
    ocs_part = (
        f"mean OCS {evidence.avg_ocs:.3f}"
        if evidence.avg_ocs is not None
        else "structural feasibility only (no embeddings provided)"
    )
    return (
        f"Adding '{category}' unlocks {evidence.incremental_useful_combinations} useful "
        f"combination(s) across template(s) [{templates}] with {ocs_part}."
    )


def analyze_wardrobe_gaps(
    wardrobe_records: Sequence[Mapping[str, Any] | CandidateItem],
    *,
    candidate_pool: Sequence[Mapping[str, Any] | CandidateItem] | None = None,
    item_embeddings: Mapping[str, Sequence[float]] | None = None,
    item_attributes: Mapping[str, Sequence[str] | set[str]] | None = None,
    wardrobe_ref: str = "wardrobe_default",
    gap_config: Mapping[str, Any] | None = None,
    m3_rules: Mapping[str, Any] | None = None,
    seed: int | None = None,
    max_candidates: int | None = None,
) -> WardrobeGapAnalysisResult:
    """Run Wardrobe Gap Analysis over a structured wardrobe.

    Parameters
    ----------
    wardrobe_records:
        Structured wardrobe items (CandidateItem or M3-compatible dicts).
    candidate_pool:
        Optional explicit candidate items to simulate adding. If omitted, one
        synthetic candidate is generated for each missing template-active category.
    item_embeddings:
        Optional mapping of item_id -> embedding vector for M3 OCS scoring and
        embedding-based redundancy checks.
    item_attributes:
        Optional mapping of item_id -> attribute labels for attribute-overlap
        redundancy checks.
    wardrobe_ref:
        Identifier for the baseline wardrobe being analyzed.
    gap_config:
        Optional override for configs/m4/gap_analysis_v1.json.
    m3_rules:
        Optional override for configs/m3/candidate_generation_v1.json.
    """
    cfg = dict(gap_config) if gap_config is not None else load_gap_analysis_config()
    rules = dict(m3_rules) if m3_rules is not None else load_candidate_rules()

    valid_vocab = set(rules.get("category_vocabulary", []))
    template_active = list(cfg.get("template_active_categories", []))
    usefulness_policy = cfg.get("usefulness_policy", {})
    min_useful_ocs = float(usefulness_policy.get("min_useful_ocs", 0.5))
    redundancy_policy = cfg.get("redundancy_policy", {})
    ranking_policy = cfg.get("ranking_policy", {})
    weights = ranking_policy.get("weights", {"normalized_gain": 0.6, "avg_ocs": 0.4})
    w_gain = float(weights.get("normalized_gain", 0.6))
    w_ocs = float(weights.get("avg_ocs", 0.4))
    w_red = float(ranking_policy.get("redundancy_penalty_weight", 0.5))

    config_version = str(cfg.get("config_version", "1.0.0"))
    config_ref = f"configs/m4/gap_analysis_v1.json@{config_version}"

    # Normalize baseline wardrobe items
    wardrobe_items: list[CandidateItem] = [
        rec if isinstance(rec, CandidateItem) else normalize_item_record(rec)
        for rec in wardrobe_records
    ]
    baseline_split = wardrobe_items[0].target_split if wardrobe_items else "train"

    # Baseline feasible outfits from M3
    baseline_gen = generate_candidates(
        wardrobe_items,
        rules=rules,
        target_split=baseline_split,
        seed=seed,
        max_candidates=max_candidates,
    )
    baseline_outfit_ids = {c.outfit_id for c in baseline_gen.valid_candidates}
    baseline_scores, _ = _score_outfits(baseline_gen.valid_candidates, item_embeddings)
    baseline_useful = 0
    for outfit in baseline_gen.valid_candidates:
        score = baseline_scores[outfit.outfit_id]
        if score is None or (score.ocs is not None and score.ocs >= min_useful_ocs):
            baseline_useful += 1

    present_categories = {
        item.common_category for item in wardrobe_items if item.common_category in valid_vocab
    }
    missing_categories = tuple(cat for cat in template_active if cat not in present_categories)

    # Build candidate list to simulate
    candidates_to_eval: list[tuple[CandidateItem, bool]] = []
    rejected_candidates: list[RejectedGapCandidate] = []

    if candidate_pool is not None:
        for raw_cand in candidate_pool:
            cand = (
                raw_cand if isinstance(raw_cand, CandidateItem) else normalize_item_record(raw_cand)
            )
            if cand.common_category not in valid_vocab:
                rejected_candidates.append(
                    RejectedGapCandidate(
                        candidate_item_id=cand.item_id,
                        candidate_category=cand.common_category,
                        reasons=("invalid_category",),
                    )
                )
                continue
            candidates_to_eval.append((cand, False))
    else:
        for cat in missing_categories:
            synth = CandidateItem(
                item_id=f"gap_candidate_{cat}",
                common_category=cat,
                mapping_status="direct",
                source_category_id=f"synthetic_{cat}",
                source_label=cat,
                target_split=baseline_split,
                source_dataset="wardiq_gap_synthesis",
                image_sha256=None,
            )
            candidates_to_eval.append((synth, True))

    # Simulate each candidate addition
    preliminary_non_redundant: list[
        tuple[CandidateItem, bool, CompatibilityEvidence, RedundancyAssessment]
    ] = []
    redundant_records: list[GapCandidateRecord] = []

    for cand, is_synth in candidates_to_eval:
        redundancy = _assess_redundancy(
            cand,
            wardrobe_items,
            item_embeddings=item_embeddings,
            item_attributes=item_attributes,
            redundancy_policy=redundancy_policy,
        )

        # Simulate adding candidate (skip simulation if exact item_id already exists)
        if "exact_item_id_match" in redundancy.reasons:
            evidence = CompatibilityEvidence(
                unlocked_outfit_ids=(),
                unlocked_templates=(),
                incremental_feasible_combinations=0,
                incremental_useful_combinations=0,
                avg_ocs=None,
                min_ocs=None,
                max_ocs=None,
                scoring_mode="skipped_exact_duplicate",
            )
        else:
            sim_gen = generate_candidates(
                [*wardrobe_items, cand],
                rules=rules,
                target_split=baseline_split,
                seed=seed,
                max_candidates=max_candidates,
            )
            new_outfits = [
                outfit
                for outfit in sim_gen.valid_candidates
                if cand.item_id in outfit.item_ids and outfit.outfit_id not in baseline_outfit_ids
            ]
            scored_map, scoring_mode = _score_outfits(new_outfits, item_embeddings)

            useful_outfits: list[CandidateOutfitRecord] = []
            useful_ocs_values: list[float] = []
            for outfit in new_outfits:
                score_res = scored_map[outfit.outfit_id]
                if score_res is None:
                    useful_outfits.append(outfit)
                elif score_res.ocs is not None and score_res.ocs >= min_useful_ocs:
                    useful_outfits.append(outfit)
                    useful_ocs_values.append(float(score_res.ocs))

            avg_ocs = (
                round(sum(useful_ocs_values) / len(useful_ocs_values), 6)
                if useful_ocs_values
                else None
            )
            min_ocs = round(min(useful_ocs_values), 6) if useful_ocs_values else None
            max_ocs = round(max(useful_ocs_values), 6) if useful_ocs_values else None

            unlocked_templates = tuple(
                sorted(
                    {
                        outfit.template_id
                        for outfit in useful_outfits
                        if outfit.template_id is not None
                    }
                )
            )
            evidence = CompatibilityEvidence(
                unlocked_outfit_ids=tuple(sorted(outfit.outfit_id for outfit in useful_outfits)),
                unlocked_templates=unlocked_templates,
                incremental_feasible_combinations=len(new_outfits),
                incremental_useful_combinations=len(useful_outfits),
                avg_ocs=avg_ocs,
                min_ocs=min_ocs,
                max_ocs=max_ocs,
                scoring_mode=scoring_mode,
            )

        if redundancy.is_redundant:
            redundant_records.append(
                GapCandidateRecord(
                    rank=None,
                    candidate_item_id=cand.item_id,
                    candidate_category=str(cand.common_category),
                    is_synthetic_candidate=is_synth,
                    gap_score=0.0,
                    normalized_gain=0.0,
                    evidence=evidence,
                    redundancy=redundancy,
                    explanation=_build_explanation(str(cand.common_category), evidence, redundancy),
                    wardrobe_ref=wardrobe_ref,
                    config_ref=config_ref,
                )
            )
            continue

        if evidence.incremental_useful_combinations <= 0:
            rejected_candidates.append(
                RejectedGapCandidate(
                    candidate_item_id=cand.item_id,
                    candidate_category=cand.common_category,
                    reasons=("zero_incremental_useful_combinations",),
                )
            )
            continue

        preliminary_non_redundant.append((cand, is_synth, evidence, redundancy))

    # Score and deterministically rank non-redundant candidates with positive gain
    max_gain = max(
        (ev.incremental_useful_combinations for _, _, ev, _ in preliminary_non_redundant),
        default=0,
    )

    scored_records: list[GapCandidateRecord] = []
    for cand, is_synth, evidence, redundancy in preliminary_non_redundant:
        norm_gain = (
            round(evidence.incremental_useful_combinations / max_gain, 6) if max_gain > 0 else 0.0
        )
        if evidence.avg_ocs is not None and not math.isnan(evidence.avg_ocs):
            raw_score = (
                (w_gain * norm_gain)
                + (w_ocs * evidence.avg_ocs)
                - (w_red * redundancy.redundancy_score)
            )
        else:
            raw_score = norm_gain - (w_red * redundancy.redundancy_score)

        scored_records.append(
            GapCandidateRecord(
                rank=None,
                candidate_item_id=cand.item_id,
                candidate_category=str(cand.common_category),
                is_synthetic_candidate=is_synth,
                gap_score=round(raw_score, 6),
                normalized_gain=norm_gain,
                evidence=evidence,
                redundancy=redundancy,
                explanation=_build_explanation(str(cand.common_category), evidence, redundancy),
                wardrobe_ref=wardrobe_ref,
                config_ref=config_ref,
            )
        )

    # Deterministic sort matching configs/m4/gap_analysis_v1.json tie_breakers
    scored_records.sort(
        key=lambda rec: (
            -rec.gap_score,
            -rec.evidence.incremental_useful_combinations,
            -(rec.evidence.avg_ocs if rec.evidence.avg_ocs is not None else -1.0),
            rec.redundancy.redundancy_score,
            rec.candidate_category,
            rec.candidate_item_id,
        )
    )

    ranked_gaps = tuple(
        GapCandidateRecord(
            rank=idx,
            candidate_item_id=rec.candidate_item_id,
            candidate_category=rec.candidate_category,
            is_synthetic_candidate=rec.is_synthetic_candidate,
            gap_score=rec.gap_score,
            normalized_gain=rec.normalized_gain,
            evidence=rec.evidence,
            redundancy=rec.redundancy,
            explanation=rec.explanation,
            wardrobe_ref=rec.wardrobe_ref,
            config_ref=rec.config_ref,
        )
        for idx, rec in enumerate(scored_records, start=1)
    )

    return WardrobeGapAnalysisResult(
        schema_version="wardiq.m4.gap-analysis-result.v1",
        config_version=config_version,
        config_ref=config_ref,
        wardrobe_ref=wardrobe_ref,
        baseline_item_count=len(wardrobe_items),
        baseline_feasible_combinations=len(baseline_gen.valid_candidates),
        baseline_useful_combinations=baseline_useful,
        missing_categories=missing_categories,
        has_meaningful_gap=len(ranked_gaps) > 0,
        ranked_gaps=ranked_gaps,
        redundant_candidates=tuple(redundant_records),
        rejected_candidates=tuple(rejected_candidates),
    )
