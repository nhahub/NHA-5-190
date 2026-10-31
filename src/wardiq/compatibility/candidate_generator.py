"""Deterministic candidate generation and structural filtering for Milestone 3."""

from __future__ import annotations

import hashlib
import itertools
import json
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from wardiq.contracts import RankedOutfit, RunIdentity

DEFAULT_RULES_PATH = (
    Path(__file__).resolve().parents[3] / "configs" / "m3" / "candidate_generation_v1.json"
)


@dataclass(frozen=True)
class CandidateItem:
    """Normalized item view for structural candidate generation."""

    item_id: str
    common_category: str | None
    mapping_status: str | None
    source_category_id: str | None = None
    source_label: str | None = None
    target_split: str | None = None
    source_dataset: str | None = None
    image_sha256: str | None = None


@dataclass(frozen=True)
class ItemRejection:
    """Explicit item-level exclusion record with ordered rejection reasons."""

    item_id: str
    reasons: tuple[str, ...]
    common_category: str | None = None
    mapping_status: str | None = None
    target_split: str | None = None


@dataclass(frozen=True)
class CandidateOutfitRecord:
    """Deterministic structural evaluation of a candidate item set."""

    outfit_id: str
    item_ids: tuple[str, ...]
    categories: tuple[str, ...]
    template_id: str | None
    structurally_valid: bool
    rejection_reasons: tuple[str, ...]
    relevant_pairs: tuple[tuple[str, str], ...]
    target_split: str | None
    config_version: str

    def to_ranked_outfit(self, provenance: RunIdentity) -> RankedOutfit:
        """Convert structural candidate into the shared M3 RankedOutfit contract."""
        return RankedOutfit(
            schema_version="wardiq.outfit.v1",
            outfit_id=self.outfit_id,
            item_ids=list(self.item_ids),
            structurally_valid=self.structurally_valid,
            rejection_reasons=list(self.rejection_reasons),
            pairwise_scores=[],
            ocs=None,
            rank=None,
            provenance=provenance,
        )

    def to_dict(self, provenance: RunIdentity) -> dict[str, Any]:
        """Serialize structural candidate with template and relevant pair metadata."""
        base = dict(self.to_ranked_outfit(provenance))
        base["template_id"] = self.template_id
        base["categories"] = list(self.categories)
        base["relevant_pairs"] = [
            {"left_item_id": left, "right_item_id": right}
            for left, right in self.relevant_pairs
        ]
        base["target_split"] = self.target_split
        base["config_version"] = self.config_version
        return base


@dataclass
class CandidateGenerationResult:
    """Summary of deterministic candidate generation, exclusions, and rejections."""

    config_version: str
    schema_version: str
    seed: int
    max_candidates: int
    max_items_per_category: int
    target_split: str | None
    input_item_count: int
    eligible_item_count: int
    excluded_item_count: int
    candidates_emitted: int
    rejected_combination_count: int
    truncated_by_max_candidates: bool
    eligible_by_category: dict[str, int] = field(default_factory=dict)
    item_rejection_counts: dict[str, int] = field(default_factory=dict)
    candidate_rejection_counts: dict[str, int] = field(default_factory=dict)
    template_counts: dict[str, int] = field(default_factory=dict)
    item_rejections: list[ItemRejection] = field(default_factory=list)
    valid_candidates: list[CandidateOutfitRecord] = field(default_factory=list)
    rejected_candidates: list[CandidateOutfitRecord] = field(default_factory=list)


def load_candidate_rules(path: str | Path | None = None) -> dict[str, Any]:
    """Load and validate the versioned candidate generation rule configuration."""
    rules_path = Path(path) if path is not None else DEFAULT_RULES_PATH
    rules: dict[str, Any] = json.loads(rules_path.read_text(encoding="utf-8"))
    if rules.get("schema_version") != "wardiq.m3.candidate-rules.v1":
        raise ValueError(f"Unsupported candidate rules schema: {rules.get('schema_version')!r}")
    required_keys = {
        "config_version",
        "category_vocabulary",
        "allowed_mapping_statuses",
        "rejected_mapping_statuses",
        "category_policy",
        "outfit_templates",
        "relevant_category_pairs",
        "enumeration_defaults",
    }
    missing = required_keys - set(rules)
    if missing:
        raise ValueError(f"Candidate rules missing required keys: {sorted(missing)}")
    return rules


def compute_stable_outfit_id(item_ids: Sequence[str], config_version: str = "1.0.0") -> str:
    """Compute a deterministic outfit ID from sorted item IDs and rule version."""
    canonical = "|".join(sorted(str(item_id).strip() for item_id in item_ids))
    payload = f"wardiq.outfit.v1:{config_version}:{canonical}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:16]
    return f"cand_{digest}"


def normalize_item_record(raw: Mapping[str, Any]) -> CandidateItem:
    """Extract normalized CandidateItem fields from M2/M3 JSON or CSV row dicts."""
    item_id = str(raw.get("item_id") or "").strip()

    category_obj = raw.get("category")
    if isinstance(category_obj, Mapping):
        common_category = category_obj.get("common_category")
        mapping_status = category_obj.get("mapping_status")
        source_category_id = category_obj.get("source_category_id")
        source_label = category_obj.get("source_label")
    else:
        common_category = raw.get("common_category") or raw.get("category_id")
        mapping_status = (
            raw.get("mapping_status")
            or raw.get("category_mapping_status")
            or ("direct" if common_category else "unmapped")
        )
        source_category_id = raw.get("source_category_id")
        source_label = raw.get("source_label") or raw.get("category_label")

    split_obj = raw.get("split")
    if isinstance(split_obj, Mapping):
        target_split = split_obj.get("target_split")
    else:
        source_obj = raw.get("source")
        if isinstance(source_obj, Mapping):
            target_split = source_obj.get("split")
        else:
            target_split = (
                raw.get("target_split")
                or raw.get("source_target_split")
                or raw.get("source_split")
                or raw.get("split")
            )

    provenance_obj = raw.get("provenance")
    image_sha256 = None
    if isinstance(provenance_obj, Mapping):
        image_sha256 = provenance_obj.get("source_image_sha256") or provenance_obj.get(
            "prepared_image_sha256"
        )
    if not image_sha256:
        image_sha256 = raw.get("image_sha256") or raw.get("source_image_sha256")

    clean_common = str(common_category).strip() if common_category not in (None, "") else None
    clean_status = str(mapping_status).strip() if mapping_status not in (None, "") else None
    clean_split = str(target_split).strip() if target_split not in (None, "") else None
    clean_dataset = (
        str(raw.get("source_dataset")).strip()
        if raw.get("source_dataset") not in (None, "")
        else None
    )
    clean_sha = str(image_sha256).strip() if image_sha256 not in (None, "") else None

    return CandidateItem(
        item_id=item_id,
        common_category=clean_common,
        mapping_status=clean_status,
        source_category_id=str(source_category_id) if source_category_id is not None else None,
        source_label=str(source_label) if source_label is not None else None,
        target_split=clean_split,
        source_dataset=clean_dataset,
        image_sha256=clean_sha,
    )


def filter_eligible_items(
    records: Sequence[Mapping[str, Any] | CandidateItem],
    rules: Mapping[str, Any],
    target_split: str | None = None,
) -> tuple[dict[str, CandidateItem], list[ItemRejection], dict[str, int]]:
    """Filter raw item records into deterministic eligible items and explicit rejections."""
    vocabulary = set(rules["category_vocabulary"])
    allowed_statuses = set(rules["allowed_mapping_statuses"])
    rejected_statuses = set(rules["rejected_mapping_statuses"])

    eligible: dict[str, CandidateItem] = {}
    seen_ids: set[str] = set()
    seen_hashes: dict[str, str] = {}
    rejections: list[ItemRejection] = []
    reason_counts: dict[str, int] = {}

    for raw in records:
        item = raw if isinstance(raw, CandidateItem) else normalize_item_record(raw)
        reasons: list[str] = []

        if not item.item_id:
            reasons.append("missing_item_id")
        elif item.item_id in seen_ids:
            reasons.append("duplicate_item_id")

        if target_split is not None and item.target_split != target_split:
            reasons.append("split_mismatch")

        if item.mapping_status in rejected_statuses:
            reasons.append(f"rejected_mapping_status:{item.mapping_status}")
        elif item.mapping_status not in allowed_statuses:
            reasons.append(f"invalid_mapping_status:{item.mapping_status or 'missing'}")

        if item.common_category is None:
            reasons.append("missing_common_category")
        elif item.common_category not in vocabulary:
            reasons.append(f"unknown_common_category:{item.common_category}")

        if (
            item.mapping_status in {"unmapped", "not_a_garment"}
            and item.common_category is not None
        ):
            reasons.append("inconsistent_unmapped_category")

        if item.image_sha256 and item.item_id not in seen_ids:
            existing_owner = seen_hashes.get(item.image_sha256)
            if existing_owner is not None and existing_owner != item.item_id:
                reasons.append("duplicate_image_sha256")

        if reasons:
            if item.item_id:
                seen_ids.add(item.item_id)
            rejection = ItemRejection(
                item_id=item.item_id or "<missing_id>",
                reasons=tuple(reasons),
                common_category=item.common_category,
                mapping_status=item.mapping_status,
                target_split=item.target_split,
            )
            rejections.append(rejection)
            for reason in reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            continue

        seen_ids.add(item.item_id)
        if item.image_sha256:
            seen_hashes[item.image_sha256] = item.item_id
        eligible[item.item_id] = item

    sorted_eligible = {k: eligible[k] for k in sorted(eligible)}
    return sorted_eligible, rejections, reason_counts


def _build_relevant_pair_set(rules: Mapping[str, Any]) -> set[tuple[str, str]]:
    pair_set: set[tuple[str, str]] = set()
    for pair in rules.get("relevant_category_pairs", []):
        if len(pair) == 2:
            left, right = sorted((str(pair[0]), str(pair[1])))
            pair_set.add((left, right))
    return pair_set


def evaluate_candidate_combination(
    item_ids: Sequence[str],
    item_lookup: Mapping[str, CandidateItem],
    rules: Mapping[str, Any],
) -> CandidateOutfitRecord:
    """Evaluate an arbitrary sequence of item IDs against versioned structural rules."""
    config_version = str(rules.get("config_version", "1.0.0"))
    raw_ids = [str(i).strip() for i in item_ids]
    sorted_unique_ids = tuple(sorted(set(raw_ids)))
    outfit_id = compute_stable_outfit_id(
        sorted_unique_ids if sorted_unique_ids else raw_ids, config_version
    )

    reasons: list[str] = []
    defaults = rules.get("enumeration_defaults", {})
    min_items = int(defaults.get("min_items_per_outfit", 2))
    max_items = int(defaults.get("max_items_per_outfit", 5))

    if len(raw_ids) != len(set(raw_ids)):
        reasons.append("duplicate_item_in_outfit")

    if len(raw_ids) < min_items:
        reasons.append("too_few_items")
    elif len(raw_ids) > max_items:
        reasons.append("too_many_items")

    resolved_items: list[CandidateItem] = []
    for iid in sorted_unique_ids:
        if iid not in item_lookup:
            reasons.append(f"unresolved_item_id:{iid}")
        else:
            resolved_items.append(item_lookup[iid])

    splits = {item.target_split for item in resolved_items if item.target_split is not None}
    if rules.get("category_policy", {}).get("require_single_split", True) and len(splits) > 1:
        reasons.append("cross_split_items")

    image_hashes = [item.image_sha256 for item in resolved_items if item.image_sha256 is not None]
    if len(image_hashes) != len(set(image_hashes)):
        reasons.append("duplicate_image_in_outfit")

    categories: list[str] = [
        item.common_category for item in resolved_items if item.common_category is not None
    ]
    if len(categories) != len(resolved_items):
        reasons.append("unmapped_item_in_outfit")

    if (
        rules.get("category_policy", {}).get("reject_duplicate_categories_in_outfit", True)
        and len(categories) != len(set(categories))
    ):
        reasons.append("duplicate_category_slot")

    cat_set = set(categories)
    for group in rules.get("category_policy", {}).get("mutually_exclusive_groups", []):
        if len(group) >= 2 and set(group).issubset(cat_set):
            reasons.append(f"mutually_exclusive_categories:{'+'.join(sorted(group))}")

    matched_template: str | None = None
    for template in rules.get("outfit_templates", []):
        req = set(template.get("required_categories", []))
        opt = set(template.get("optional_categories", []))
        if req.issubset(cat_set) and cat_set.issubset(req | opt):
            matched_template = str(template["template_id"])
            break

    if matched_template is None and not any(
        r.startswith("unresolved_item_id") for r in reasons
    ):
        if "footwear" not in cat_set:
            reasons.append("missing_required_footwear")
        if "one_piece" not in cat_set and not {"top", "bottom"}.issubset(cat_set):
            reasons.append("missing_core_garment_structure")
        reasons.append("no_matching_outfit_template")

    relevant_cat_pairs = _build_relevant_pair_set(rules)
    relevant_item_pairs: list[tuple[str, str]] = []
    if not reasons:
        ordered_items = sorted(resolved_items, key=lambda x: x.item_id)
        for left, right in itertools.combinations(ordered_items, 2):
            if left.common_category and right.common_category:
                cat_pair = tuple(sorted((left.common_category, right.common_category)))
                if cat_pair in relevant_cat_pairs:
                    relevant_item_pairs.append((left.item_id, right.item_id))

    target_split = next(iter(splits)) if len(splits) == 1 else None
    ordered_cats = tuple(
        item.common_category or "unmapped"
        for item in sorted(resolved_items, key=lambda x: x.item_id)
    )

    return CandidateOutfitRecord(
        outfit_id=outfit_id,
        item_ids=sorted_unique_ids if sorted_unique_ids else tuple(raw_ids),
        categories=ordered_cats,
        template_id=matched_template if not reasons else None,
        structurally_valid=len(reasons) == 0,
        rejection_reasons=tuple(reasons),
        relevant_pairs=tuple(relevant_item_pairs),
        target_split=target_split,
        config_version=config_version,
    )


def generate_candidates(
    records: Sequence[Mapping[str, Any] | CandidateItem],
    rules: Mapping[str, Any] | None = None,
    *,
    target_split: str | None = None,
    seed: int | None = None,
    max_candidates: int | None = None,
    max_items_per_category: int | None = None,
    explicit_combinations: Sequence[Sequence[str]] | None = None,
) -> CandidateGenerationResult:
    """Deterministically generate bounded valid outfit candidates and rejection metrics."""
    loaded_rules = dict(rules) if rules is not None else load_candidate_rules()
    defaults = loaded_rules.get("enumeration_defaults", {})
    effective_seed = int(defaults.get("seed", 42) if seed is None else seed)
    effective_max_candidates = int(
        defaults.get("max_candidates", 250) if max_candidates is None else max_candidates
    )
    effective_max_per_cat = int(
        defaults.get("max_items_per_category", 30)
        if max_items_per_category is None
        else max_items_per_category
    )
    if effective_max_candidates < 1:
        raise ValueError("max_candidates must be >= 1")
    if effective_max_per_cat < 1:
        raise ValueError("max_items_per_category must be >= 1")

    eligible_lookup, item_rejections, item_rejection_counts = filter_eligible_items(
        records, loaded_rules, target_split=target_split
    )

    by_category: dict[str, list[CandidateItem]] = {
        cat: [] for cat in loaded_rules["category_vocabulary"]
    }
    for item in eligible_lookup.values():
        if item.common_category in by_category:
            by_category[item.common_category].append(item)

    rng = random.Random(effective_seed)
    bounded_by_category: dict[str, list[CandidateItem]] = {}
    for cat in sorted(by_category):
        pool = list(sorted(by_category[cat], key=lambda x: x.item_id))
        if len(pool) > effective_max_per_cat:
            pool = sorted(rng.sample(pool, effective_max_per_cat), key=lambda x: x.item_id)
        bounded_by_category[cat] = pool

    eligible_by_category = {
        cat: len(items) for cat, items in sorted(by_category.items()) if len(items) > 0
    }

    valid_candidates: list[CandidateOutfitRecord] = []
    rejected_candidates: list[CandidateOutfitRecord] = []
    candidate_rejection_counts: dict[str, int] = {}
    template_counts: dict[str, int] = {}
    seen_outfit_ids: set[str] = set()
    truncated = False

    if explicit_combinations is not None:
        for combo in explicit_combinations:
            evaluated = evaluate_candidate_combination(combo, eligible_lookup, loaded_rules)
            if evaluated.structurally_valid:
                if evaluated.outfit_id in seen_outfit_ids:
                    dup_record = CandidateOutfitRecord(
                        outfit_id=evaluated.outfit_id,
                        item_ids=evaluated.item_ids,
                        categories=evaluated.categories,
                        template_id=None,
                        structurally_valid=False,
                        rejection_reasons=("duplicate_candidate_outfit",),
                        relevant_pairs=(),
                        target_split=evaluated.target_split,
                        config_version=evaluated.config_version,
                    )
                    rejected_candidates.append(dup_record)
                    candidate_rejection_counts["duplicate_candidate_outfit"] = (
                        candidate_rejection_counts.get("duplicate_candidate_outfit", 0) + 1
                    )
                    continue
                if len(valid_candidates) >= effective_max_candidates:
                    truncated = True
                    continue
                seen_outfit_ids.add(evaluated.outfit_id)
                valid_candidates.append(evaluated)
                if evaluated.template_id:
                    template_counts[evaluated.template_id] = (
                        template_counts.get(evaluated.template_id, 0) + 1
                    )
            else:
                rejected_candidates.append(evaluated)
                for reason in evaluated.rejection_reasons:
                    candidate_rejection_counts[reason] = (
                        candidate_rejection_counts.get(reason, 0) + 1
                    )
    else:
        raw_Enumerated: list[CandidateOutfitRecord] = []
        for template in loaded_rules.get("outfit_templates", []):
            req_cats = list(template.get("required_categories", []))
            if any(len(bounded_by_category.get(cat, [])) == 0 for cat in req_cats):
                reason = f"missing_category_pool:{template['template_id']}"
                candidate_rejection_counts[reason] = (
                    candidate_rejection_counts.get(reason, 0) + 1
                )
                continue
            pools = [bounded_by_category[cat] for cat in req_cats]
            for prod in itertools.product(*pools):
                combo_ids = [item.item_id for item in prod]
                evaluated = evaluate_candidate_combination(
                    combo_ids, eligible_lookup, loaded_rules
                )
                if evaluated.structurally_valid:
                    if evaluated.outfit_id not in seen_outfit_ids:
                        seen_outfit_ids.add(evaluated.outfit_id)
                        raw_Enumerated.append(evaluated)
                else:
                    rejected_candidates.append(evaluated)
                    for reason in evaluated.rejection_reasons:
                        candidate_rejection_counts[reason] = (
                            candidate_rejection_counts.get(reason, 0) + 1
                        )

        raw_Enumerated.sort(key=lambda c: c.outfit_id)
        if len(raw_Enumerated) > effective_max_candidates:
            truncated = True
            sampled = rng.sample(raw_Enumerated, effective_max_candidates)
            sampled.sort(key=lambda c: c.outfit_id)
            valid_candidates = sampled
        else:
            valid_candidates = raw_Enumerated

        for cand in valid_candidates:
            if cand.template_id:
                template_counts[cand.template_id] = (
                    template_counts.get(cand.template_id, 0) + 1
                )

    return CandidateGenerationResult(
        config_version=str(loaded_rules["config_version"]),
        schema_version=str(loaded_rules["schema_version"]),
        seed=effective_seed,
        max_candidates=effective_max_candidates,
        max_items_per_category=effective_max_per_cat,
        target_split=target_split,
        input_item_count=len(records),
        eligible_item_count=len(eligible_lookup),
        excluded_item_count=len(item_rejections),
        candidates_emitted=len(valid_candidates),
        rejected_combination_count=len(rejected_candidates),
        truncated_by_max_candidates=truncated,
        eligible_by_category=eligible_by_category,
        item_rejection_counts=dict(sorted(item_rejection_counts.items())),
        candidate_rejection_counts=dict(sorted(candidate_rejection_counts.items())),
        template_counts=dict(sorted(template_counts.items())),
        item_rejections=item_rejections,
        valid_candidates=valid_candidates,
        rejected_candidates=rejected_candidates,
    )
